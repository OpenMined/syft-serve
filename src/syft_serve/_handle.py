"""
Simplified ServerHandle - Individual server control and monitoring
"""

import time
from typing import List, Optional
import psutil
import requests

from ._config import get_config
from ._exceptions import ServerNotFoundError, ServerShutdownError


class ServerHandle:
    """Handle for controlling and monitoring an individual server"""
    
    def __init__(
        self, 
        port: int, 
        pid: int, 
        endpoints: List[str],
        name: Optional[str] = None,
        app_module: Optional[str] = None,
        expiration_seconds: int = 86400
    ):
        self.port = port
        self.pid = pid
        self.endpoints = endpoints
        self.name = name or f"server_{port}"
        self.app_module = app_module
        self.expiration_seconds = expiration_seconds
        self.created_at = time.time()
        self._process: Optional[psutil.Process] = None
        self._config = get_config()
        
    @property
    def status(self) -> str:
        """Get current server status"""
        try:
            # Check if server has expired
            if self.is_expired():
                return "expired"
            
            if self._get_process().is_running():
                if self.health_check():
                    return "running"
                else:
                    return "unhealthy"
            else:
                return "stopped"
        except (psutil.NoSuchProcess, ServerNotFoundError):
            return "stopped"
        except Exception:
            return "error"
    
    def _get_process(self) -> psutil.Process:
        """Get or refresh the process object"""
        if self._process is None or not self._process.is_running():
            try:
                self._process = psutil.Process(self.pid)
            except psutil.NoSuchProcess:
                raise ServerNotFoundError(f"Server process {self.pid} not found")
        return self._process
    
    def health_check(self, timeout: float = 2.0) -> bool:
        """Check if server is responding to HTTP requests"""
        try:
            response = requests.get(
                f"http://localhost:{self.port}/health",
                timeout=timeout
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def is_expired(self) -> bool:
        """Check if server has expired based on creation time and expiration_seconds"""
        if self.expiration_seconds == -1:  # Never expires
            return False
        
        current_time = time.time()
        elapsed_seconds = current_time - self.created_at
        return elapsed_seconds > self.expiration_seconds
    
    def check_and_self_destruct(self) -> bool:
        """Check if expired and self-destruct if so. Returns True if destroyed."""
        if self.is_expired():
            try:
                self.terminate()
                return True
            except Exception:
                # If termination fails, still consider it destroyed
                return True
        return False
    
    def terminate(self, timeout: float = 5.0) -> None:
        """Terminate the server process and entire process group
        
        Args:
            timeout: Maximum time to wait for graceful shutdown (default: 5.0 seconds)
        """
        import signal
        import os
        
        try:
            process = self._get_process()
            
            # Since we use start_new_session=True, kill the entire process group
            # The process group ID is the same as the process ID for session leaders
            pgid = process.pid
            
            try:
                # Send SIGTERM to entire process group
                os.killpg(pgid, signal.SIGTERM)
                
                # Wait for graceful shutdown with timeout
                start_time = time.time()
                while process.is_running() and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                
                # Check if main process is still alive
                if process.is_running():
                    # Force kill the entire process group
                    os.killpg(pgid, signal.SIGKILL)
                    
                    # Wait a bit more for SIGKILL to take effect
                    kill_timeout = 2.0
                    start_time = time.time()
                    while process.is_running() and (time.time() - start_time) < kill_timeout:
                        time.sleep(0.1)
                    
                    # Final check - if still running, try fallback method
                    if process.is_running():
                        self._terminate_process_tree(process)
                        
                        # One last check after fallback
                        time.sleep(0.5)
                        if process.is_running():
                            raise ServerShutdownError(
                                f"Failed to kill server process group {pgid} after {timeout + kill_timeout}s"
                            )
            except ProcessLookupError:
                # Process group already dead
                pass
            except PermissionError:
                # Fall back to killing individual processes
                self._terminate_process_tree(process)
                
        except psutil.NoSuchProcess:
            # Process already dead
            pass
    
    def _terminate_process_tree(self, process: psutil.Process) -> None:
        """Fallback method to terminate process and all children"""
        try:
            # Get all child processes first
            children = process.children(recursive=True)
            
            # Kill all children
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # Kill parent
            process.kill()
            
            # Wait briefly
            gone, alive = psutil.wait_procs([process] + children, timeout=1.0)
            
            if alive:
                # Log which processes couldn't be killed
                alive_pids = [p.pid for p in alive]
                raise ServerShutdownError(
                    f"Failed to kill processes: {alive_pids}"
                )
        except psutil.NoSuchProcess:
            pass