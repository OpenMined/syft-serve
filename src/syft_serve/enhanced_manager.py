"""
Enhanced ServerManager with health checking and comprehensive process management.
This file shows the modifications needed to the existing _manager.py
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
import os
import signal

from ._handle import ServerHandle
from ._config import get_config
from ._exceptions import (
    ServerNotFoundError,
    PortInUseError,
    ServerStartupError,
    ServerAlreadyExistsError,
)
from ._endpoint_serializer import generate_app_code_from_endpoints
from ._health import HealthChecker, HealthCheckConfig
from ._process_manager import ProcessManager


class EnhancedServerManager:
    """Enhanced manager with health checking and better process management"""

    def __init__(self) -> None:
        self._config = get_config()
        self._servers: Dict[str, ServerHandle] = {}
        self._health_checker = HealthChecker()
        
        # Create base directory for isolated server environments
        self._envs_dir = self._config.log_dir / "server_envs"
        self._envs_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up dead environments and orphaned processes on startup
        self._cleanup_dead_environments()
        self._cleanup_orphaned_processes_on_startup()

    def create_server(
        self,
        name: str,
        endpoints: Dict[str, Callable],
        dependencies: Optional[List[str]] = None,
        force: bool = False,
        expiration_seconds: int = 86400,
        verify_startup: bool = True,
        startup_timeout: float = 10.0,
        cleanup_on_failure: bool = True,
    ) -> ServerHandle:
        """
        Create a new server with health verification
        
        Args:
            name: Unique server name (required)
            endpoints: Dictionary of endpoint paths to handler functions
            dependencies: Optional list of Python packages to install
            force: If True, destroy existing server with same name
            expiration_seconds: Server auto-expires after this many seconds
            verify_startup: Whether to verify server health after starting
            startup_timeout: Maximum time to wait for server to be healthy
            cleanup_on_failure: Whether to clean up if startup fails
            
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

        # Check if server already exists
        existing_server = self._check_existing_server(name, force)
        if existing_server:
            # Server exists and is healthy, return it
            return existing_server

        # Check for port conflicts and orphaned processes
        self._check_for_conflicts(name)

        # Find available port
        port = self._find_free_port()

        # Extract endpoint paths
        endpoint_paths = list(endpoints.keys())

        try:
            # Start the server process
            pid = self._start_server_from_endpoints(
                port, endpoints, name, dependencies, expiration_seconds
            )

            # Create server handle
            server = ServerHandle(
                port=port,
                pid=pid,
                endpoints=endpoint_paths,
                name=name,
                expiration_seconds=expiration_seconds,
            )

            # Verify startup if requested
            if verify_startup:
                health_config = HealthCheckConfig(startup_timeout=startup_timeout)
                self._health_checker.config = health_config
                
                health_result = self._health_checker.verify_startup(server, verbose=True)
                if not health_result.healthy:
                    # Cleanup failed server
                    if cleanup_on_failure:
                        try:
                            ProcessManager.kill_process_tree(pid)
                        except:
                            pass
                    raise ServerStartupError(
                        f"Server {name} failed health check: {health_result.details.get('error', 'Unknown error')}"
                    )
            else:
                # Use old wait method
                self._wait_for_server_ready(server)

            # Register server
            self._servers[name] = server
            self._save_persistent_servers()

            return server
            
        except Exception as e:
            # Clean up on any failure
            if cleanup_on_failure:
                self._cleanup_failed_server(name, port)
            raise

    def _check_existing_server(self, name: str, force: bool) -> Optional[ServerHandle]:
        """Check if server exists and handle accordingly"""
        if name in self._servers:
            server = self._servers[name]
            
            # Check if existing server is healthy
            if not force:
                health_result = self._health_checker.check_health(server)
                if health_result.healthy:
                    # Existing server is healthy, return it
                    print(f"ℹ️  Server '{name}' already exists and is healthy")
                    return server
                else:
                    raise ServerAlreadyExistsError(
                        f"Server '{name}' exists but is unhealthy. Use force=True to replace."
                    )
            else:
                # Force destroy existing server
                self.terminate_server(name, force=True)
                
        return None

    def _check_for_conflicts(self, name: str) -> None:
        """Check for port conflicts and orphaned processes"""
        # Check for processes using our typical port range
        # This is where we'd check for orphaned uvicorn processes
        pass

    def _cleanup_failed_server(self, name: str, port: int) -> None:
        """Clean up after a failed server start"""
        # Kill any processes on the port
        processes = ProcessManager.find_processes_by_port(port)
        for proc_info in processes:
            ProcessManager.kill_process_tree(proc_info.pid)
        
        # Clean up environment directory
        server_dir = self._envs_dir / name
        if server_dir.exists():
            try:
                shutil.rmtree(server_dir)
            except:
                pass

    def _cleanup_orphaned_processes_on_startup(self) -> None:
        """Clean up any orphaned uvicorn processes on startup"""
        if self._config.get("cleanup_orphans_on_start", True):
            killed_count = ProcessManager.cleanup_orphaned_processes(
                name_pattern="uvicorn",
                port_range=range(8000, 9000)  # Common range for syft-serve
            )
            if killed_count > 0:
                print(f"🧹 Cleaned up {killed_count} orphaned server process(es)")

    def terminate_all(self, timeout: float = 5.0, force: bool = True) -> Dict[str, Any]:
        """
        Comprehensive termination of all servers
        
        Steps:
        1. Stop all registered servers gracefully
        2. Find and kill orphaned processes by multiple methods
        3. Clean up all artifacts
        """
        results = {
            "tracked_total": 0,
            "tracked_terminated": 0,
            "tracked_failed": [],
            "orphaned_discovered": 0,
            "orphaned_terminated": 0,
            "orphaned_failed": [],
            "lock_files_cleaned": 0,
            "success": True,
        }

        # First terminate tracked servers
        names = list(self._servers.keys())
        results["tracked_total"] = len(names)

        for name in names:
            try:
                self.terminate_server(name, force=force)
                results["tracked_terminated"] += 1
            except Exception as e:
                print(f"⚠️  Failed to terminate tracked server {name}: {e}")
                results["tracked_failed"].append(name)
                results["success"] = False

        # Find and kill ALL uvicorn processes
        print("🔍 Searching for orphaned processes...")
        
        # Method 1: Find by process name
        uvicorn_processes = ProcessManager.find_uvicorn_processes()
        results["orphaned_discovered"] = len(uvicorn_processes)
        
        for proc_info in uvicorn_processes:
            try:
                if ProcessManager.kill_process_tree(proc_info.pid, timeout=timeout):
                    results["orphaned_terminated"] += 1
                else:
                    results["orphaned_failed"].append(proc_info.pid)
                    results["success"] = False
            except Exception as e:
                print(f"⚠️  Failed to kill process {proc_info.pid}: {e}")
                results["orphaned_failed"].append(proc_info.pid)
                results["success"] = False

        # Method 2: Find by ports (in case process name doesn't match)
        for port in range(8000, 9000):
            port_processes = ProcessManager.find_processes_by_port(port)
            for proc_info in port_processes:
                if proc_info.pid not in results["orphaned_failed"]:
                    try:
                        if ProcessManager.kill_process_tree(proc_info.pid):
                            results["orphaned_terminated"] += 1
                            results["orphaned_discovered"] += 1
                    except:
                        pass

        # Clean up lock files
        lock_files = self._cleanup_lock_files()
        results["lock_files_cleaned"] = len(lock_files)

        # Clear registry
        self._servers.clear()
        self._save_persistent_servers()

        # Final verification
        remaining = ProcessManager.find_uvicorn_processes()
        if remaining:
            print(f"⚠️  {len(remaining)} process(es) still running after cleanup")
            results["success"] = False

        return results

    def _cleanup_lock_files(self) -> List[Path]:
        """Clean up stale lock files"""
        cleaned = []
        lock_pattern = "*.lock"
        
        # Check common lock file locations
        for lock_dir in [Path("/tmp"), self._config.log_dir]:
            if lock_dir.exists():
                for lock_file in lock_dir.glob(lock_pattern):
                    try:
                        # Check if lock file is stale
                        if lock_file.exists():
                            # Read PID from lock file
                            try:
                                pid = int(lock_file.read_text().strip())
                                # Check if process exists
                                if not ProcessManager.verify_process_dead(pid):
                                    continue  # Process still alive, don't remove lock
                            except:
                                pass  # Invalid lock file, remove it
                            
                            lock_file.unlink()
                            cleaned.append(lock_file)
                    except:
                        pass
                        
        return cleaned

    def _is_valid_name(self, name: str) -> bool:
        """Check if server name is valid"""
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))