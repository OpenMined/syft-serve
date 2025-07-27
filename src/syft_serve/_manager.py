"""
Simplified ServerManager - only what's needed for tutorial
"""

import json
import shutil
import subprocess
import time
import socket
import re
from pathlib import Path
from typing import List, Dict, Optional, Callable
import psutil

from ._handle import ServerHandle
from ._config import get_config
from ._exceptions import (
    ServerNotFoundError, 
    PortInUseError, 
    ServerStartupError,
    ServerAlreadyExistsError
)
from ._endpoint_serializer import generate_app_code_from_endpoints


class ServerManager:
    """Simple manager for FastAPI server processes"""
    
    def __init__(self):
        self._config = get_config()
        self._servers: Dict[str, ServerHandle] = {}  # name -> ServerHandle
        self._load_persistent_servers()
        
        # Create base directory for isolated server environments
        self._envs_dir = self._config.log_dir / "server_envs"
        self._envs_dir.mkdir(parents=True, exist_ok=True)
    
    def list_servers(self) -> List[ServerHandle]:
        """List all managed servers"""
        self._cleanup_dead_servers()
        return list(self._servers.values())
    
    def create_server(
        self,
        name: str,
        endpoints: Dict[str, Callable],
        dependencies: Optional[List[str]] = None,
        force: bool = False
    ) -> ServerHandle:
        """
        Create a new server with a unique name
        
        Args:
            name: Unique server name (required)
            endpoints: Dictionary of endpoint paths to handler functions
            dependencies: Optional list of Python packages to install
            force: If True, destroy existing server with same name
            
        Returns:
            ServerHandle for the created server
        """
        # Validate name
        if not name:
            raise ValueError("Server name is required")
        
        if not self._is_valid_name(name):
            raise ValueError(
                f"Invalid server name '{name}'. Names must contain only letters, "
                "numbers, underscores, and hyphens. No spaces or special characters."
            )
        
        # Check if name already exists
        if name in self._servers:
            if force:
                # Destroy existing server
                self.terminate_server(name)
            else:
                raise ServerAlreadyExistsError(
                    f"Server '{name}' already exists. Use force=True to replace."
                )
        
        # Find available port
        port = self._find_free_port()
        
        # Extract endpoint paths
        endpoint_paths = list(endpoints.keys())
        
        # Start the server process
        pid = self._start_server_from_endpoints(port, endpoints, name, dependencies)
        
        # Create server handle
        server = ServerHandle(
            port=port,
            pid=pid,
            endpoints=endpoint_paths,
            name=name
        )
        
        # Wait for server to be ready
        self._wait_for_server_ready(server)
        
        # Register server
        self._servers[name] = server
        self._save_persistent_servers()
        
        return server
    
    def get_server(self, name: str) -> ServerHandle:
        """Get server by name"""
        if name not in self._servers:
            available = list(self._servers.keys())
            if available:
                raise ServerNotFoundError(
                    f"No server found with name '{name}'. "
                    f"Available servers: {', '.join(available)}"
                )
            else:
                raise ServerNotFoundError("No servers are currently registered")
        return self._servers[name]
    
    def terminate_server(self, name: str) -> None:
        """Terminate specific server by name"""
        server = self.get_server(name)
        server.terminate()
        
        # Clean up environment
        server_dir = self._envs_dir / name
        if server_dir.exists():
            shutil.rmtree(server_dir)
        
        # Remove from registry
        del self._servers[name]
        self._save_persistent_servers()
    
    def terminate_all(self) -> None:
        """Terminate all servers - both tracked and orphaned"""
        # First terminate tracked servers
        names = list(self._servers.keys())
        for name in names:
            try:
                self.terminate_server(name)
            except Exception as e:
                print(f"Warning: Failed to terminate tracked server {name}: {e}")
        
        # Then find and terminate any orphaned processes
        from ._process_discovery import terminate_all_syft_serve_processes
        
        result = terminate_all_syft_serve_processes()
        if result['discovered'] > 0:
            print(f"Found {result['discovered']} orphaned server process(es)")
            print(f"Terminated {result['terminated']} process(es)")
            if result['failed']:
                print(f"Failed to terminate PIDs: {result['failed']}")
    
    # Helper methods
    def _is_valid_name(self, name: str) -> bool:
        """Check if server name is valid"""
        # Only allow letters, numbers, underscores, and hyphens
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))
    
    def _find_free_port(self) -> int:
        """Find a free port within the configured range"""
        start_port, end_port = self._config.port_range
        
        for port in range(start_port, end_port + 1):
            if self._is_port_free(port):
                return port
        
        raise PortInUseError(f"No free ports in range {start_port}-{end_port}")
    
    def _is_port_free(self, port: int) -> bool:
        """Check if port is free"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def _create_server_environment(self, name: str, dependencies: Optional[List[str]] = None) -> Path:
        """Create an isolated uv environment for a server"""
        server_dir = self._envs_dir / name
        server_dir.mkdir(parents=True, exist_ok=True)
        
        # Default dependencies
        default_deps = [
            "fastapi",
            "uvicorn[standard]",
            "httpx",  # for health checks
        ]
        
        # Combine default and custom dependencies
        all_deps = default_deps + (dependencies or [])
        
        # Create pyproject.toml
        pyproject_path = server_dir / "pyproject.toml"
        deps_str = ',\n    '.join(f'"{dep}"' for dep in all_deps)
        
        pyproject_content = f'''[project]
name = "{name}"
version = "0.1.0"
dependencies = [
    {deps_str}
]

[tool.uv]
package = false
'''
        pyproject_path.write_text(pyproject_content)
        
        # Create virtual environment
        result = subprocess.run(
            ["uv", "venv", "--python", "3.12"],
            cwd=str(server_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ServerStartupError(f"Failed to create venv for {name}: {result.stderr}")
        
        # Install dependencies
        result = subprocess.run(
            ["uv", "sync"],
            cwd=str(server_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ServerStartupError(f"Failed to install dependencies for {name}: {result.stderr}")
        
        return server_dir
    
    def _start_server_from_endpoints(self, port: int, endpoints: Dict[str, Callable], name: str, dependencies: Optional[List[str]] = None) -> int:
        """Start server from endpoint dictionary"""
        # Generate app code directly from endpoints
        if shutil.which('uv'):
            server_dir = self._create_server_environment(name, dependencies)
            app_file = server_dir / f"{name}_app.py"
            stdout_log = server_dir / f"{name}_stdout.log"
            stderr_log = server_dir / f"{name}_stderr.log"
        else:
            app_dir = self._config.log_dir / "apps"
            app_dir.mkdir(exist_ok=True)
            app_file = app_dir / f"{name}_app.py"
            stdout_log = self._config.log_dir / f"{name}_stdout.log"
            stderr_log = self._config.log_dir / f"{name}_stderr.log"
            server_dir = None
        
        # Generate the app code
        app_code = generate_app_code_from_endpoints(endpoints, name)
        app_file.write_text(app_code)
        
        # Use uv run if available for better dependency management
        if shutil.which('uv') and server_dir:
            cmd = [
                "uv", "run", "uvicorn", 
                f"{app_file.stem}:app",
                "--host", "0.0.0.0", 
                "--port", str(port),
                "--log-level", "info"
            ]
        else:
            cmd = [
                "uvicorn", 
                f"{app_file.stem}:app",
                "--host", "0.0.0.0", 
                "--port", str(port),
                "--log-level", "info"
            ]
        
        try:
            # Set working directory if we created an environment
            cwd = str(server_dir) if server_dir else None
            
            with open(stdout_log, 'w') as out, open(stderr_log, 'w') as err:
                # Use start_new_session=True to detach from parent process group
                process = subprocess.Popen(
                    cmd,
                    stdout=out,
                    stderr=err,
                    text=True,
                    cwd=cwd,
                    start_new_session=True  # Creates new process group
                )
            return process.pid
        except Exception as e:
            raise ServerStartupError(f"Failed to start server {name}: {e}")
    
    def _wait_for_server_ready(self, server: ServerHandle) -> None:
        """Wait for server to be ready to accept requests"""
        start_time = time.time()
        timeout = self._config.startup_timeout
        
        while time.time() - start_time < timeout:
            if server.health_check():
                return
            time.sleep(self._config.health_check_interval)
        
        raise ServerStartupError(
            f"Server {server.name} did not become ready within {timeout}s"
        )
    
    def _cleanup_dead_servers(self) -> None:
        """Remove dead servers from registry"""
        dead_servers = []
        
        for name, server in self._servers.items():
            if server.status == "stopped":
                dead_servers.append(name)
        
        for name in dead_servers:
            del self._servers[name]
        
        if dead_servers:
            self._save_persistent_servers()
    
    def _load_persistent_servers(self) -> None:
        """Load server registry from persistence file"""
        if not self._config.persistence_file.exists():
            return
        
        try:
            with open(self._config.persistence_file, 'r') as f:
                data = json.load(f)
            
            for server_data in data.get('servers', []):
                # Verify process still exists
                try:
                    psutil.Process(server_data['pid'])
                    server = ServerHandle(
                        port=server_data['port'],
                        pid=server_data['pid'],
                        endpoints=server_data['endpoints'],
                        name=server_data['name'],
                        app_module=server_data.get('app_module')
                    )
                    self._servers[server.name] = server
                except psutil.NoSuchProcess:
                    # Process is dead, skip
                    pass
                    
        except Exception as e:
            print(f"Warning: Failed to load persistent servers: {e}")
    
    def _save_persistent_servers(self) -> None:
        """Save server registry to persistence file"""
        try:
            data = {
                'servers': [
                    {
                        'name': server.name,
                        'port': server.port,
                        'pid': server.pid,
                        'endpoints': server.endpoints,
                        'app_module': server.app_module,
                    }
                    for server in self._servers.values()
                    if server.status == "running"
                ]
            }
            
            with open(self._config.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Failed to save persistent servers: {e}")