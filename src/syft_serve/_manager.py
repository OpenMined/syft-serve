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
from typing import List, Dict, Optional, Callable, Any
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
        force: bool = False,
        expiration_seconds: int = 86400
    ) -> ServerHandle:
        """
        Create a new server with a unique name
        
        Args:
            name: Unique server name (required)
            endpoints: Dictionary of endpoint paths to handler functions
            dependencies: Optional list of Python packages to install
            force: If True, destroy existing server with same name
            expiration_seconds: Server auto-expires after this many seconds (default: 86400 = 24 hours, -1 = never)
            
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
        pid = self._start_server_from_endpoints(port, endpoints, name, dependencies, expiration_seconds)
        
        # Create server handle
        server = ServerHandle(
            port=port,
            pid=pid,
            endpoints=endpoint_paths,
            name=name,
            expiration_seconds=expiration_seconds
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
    
    def terminate_server(self, name: str, force: bool = False) -> None:
        """Terminate specific server by name
        
        Args:
            name: Server name
            force: If True, use force_terminate if normal termination fails
        """
        server = self.get_server(name)
        
        try:
            server.terminate()
        except Exception:
            if force:
                print(f"Normal termination failed for {name}, using force terminate...")
                server.force_terminate()
            else:
                raise
        
        # Clean up environment
        server_dir = self._envs_dir / name
        if server_dir.exists():
            shutil.rmtree(server_dir)
        
        # Remove from registry
        del self._servers[name]
        self._save_persistent_servers()
    
    def terminate_all(self, force: bool = True) -> Dict[str, Any]:
        """Terminate all servers - both tracked and orphaned
        
        Args:
            force: If True, use force_terminate for stubborn processes
        
        Returns:
            dict: Summary of termination results with keys:
                - tracked_total: number of tracked servers
                - tracked_terminated: number of tracked servers successfully terminated
                - tracked_failed: list of server names that failed to terminate
                - orphaned_discovered: number of orphaned processes found
                - orphaned_terminated: number of orphaned processes terminated
                - orphaned_failed: list of PIDs that failed to terminate
                - success: bool indicating if all servers were terminated
        """
        results = {
            'tracked_total': 0,
            'tracked_terminated': 0,
            'tracked_failed': [],
            'orphaned_discovered': 0,
            'orphaned_terminated': 0,
            'orphaned_failed': [],
            'success': True
        }
        
        # First terminate tracked servers
        names = list(self._servers.keys())
        results['tracked_total'] = len(names)
        
        for name in names:
            try:
                self.terminate_server(name, force=force)
                results['tracked_terminated'] += 1
            except Exception as e:
                print(f"Warning: Failed to terminate tracked server {name}: {e}")
                results['tracked_failed'].append(name)
                results['success'] = False
        
        # Then find and terminate any orphaned processes
        from ._process_discovery import terminate_all_syft_serve_processes
        
        orphan_result = terminate_all_syft_serve_processes(force=force)
        results['orphaned_discovered'] = orphan_result['discovered']
        results['orphaned_terminated'] = orphan_result['terminated']
        results['orphaned_failed'] = orphan_result['failed']
        
        if orphan_result['failed']:
            results['success'] = False
            print(f"Failed to terminate orphaned PIDs: {orphan_result['failed']}")
        
        # Print summary
        if results['tracked_failed']:
            print(f"Failed to terminate {len(results['tracked_failed'])} tracked server(s): {', '.join(results['tracked_failed'])}")
        
        if results['orphaned_discovered'] > 0:
            print(f"Found {results['orphaned_discovered']} orphaned process(es), terminated {results['orphaned_terminated']}")
        
        return results
    
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
        result = subprocess.run(  # nosec B603,B607 - Fixed command, no user input
            ["uv", "venv", "--python", "3.12"],
            cwd=str(server_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ServerStartupError(f"Failed to create venv for {name}: {result.stderr}")
        
        # Install dependencies
        result = subprocess.run(  # nosec B603,B607 - Fixed command, no user input
            ["uv", "sync"],
            cwd=str(server_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ServerStartupError(f"Failed to install dependencies for {name}: {result.stderr}")
        
        return server_dir
    
    def _start_server_from_endpoints(self, port: int, endpoints: Dict[str, Callable], name: str, dependencies: Optional[List[str]] = None, expiration_seconds: int = 86400) -> int:
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
        app_code = generate_app_code_from_endpoints(endpoints, name, expiration_seconds)
        app_file.write_text(app_code)
        
        # Use uv run if available for better dependency management
        if shutil.which('uv') and server_dir:
            cmd = [
                "uv", "run", "uvicorn", 
                f"{app_file.stem}:app",
                "--host", "127.0.0.1",  # Only bind to localhost for security
                "--port", str(port),
                "--log-level", "info"
            ]
        else:
            cmd = [
                "uvicorn", 
                f"{app_file.stem}:app",
                "--host", "127.0.0.1",  # Only bind to localhost for security
                "--port", str(port),
                "--log-level", "info"
            ]
        
        try:
            # Set working directory if we created an environment
            cwd = str(server_dir) if server_dir else None
            
            with open(stdout_log, 'w') as out, open(stderr_log, 'w') as err:
                # Use start_new_session=True to detach from parent process group
                process = subprocess.Popen(  # nosec B603 - Command built from validated inputs
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
        """Remove dead, expired, and stopped servers from registry"""
        dead_servers = []
        
        for name, server in self._servers.items():
            status = server.status
            if status in ["stopped", "expired", "error"]:
                dead_servers.append(name)
            elif hasattr(server, 'check_and_self_destruct') and server.check_and_self_destruct():
                # Server expired and self-destructed
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