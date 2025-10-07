"""
Health checking system for syft-serve servers.
"""

import time
import requests
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
import socket


@dataclass
class HealthCheckConfig:
    """Configuration for health checks"""
    startup_timeout: float = 10.0
    retry_delays: List[float] = None
    health_endpoint: str = "/health"
    test_all_endpoints: bool = True
    port_check_timeout: float = 5.0
    
    def __post_init__(self):
        if self.retry_delays is None:
            self.retry_delays = [0.5, 2.0, 5.0]


class HealthCheckResult:
    """Result of a health check"""
    def __init__(self, healthy: bool, details: Dict[str, Any] = None):
        self.healthy = healthy
        self.details = details or {}
        self.timestamp = time.time()
        
    def __bool__(self):
        return self.healthy


class HealthChecker:
    """Manages health checks for syft-serve servers"""
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        self.config = config or HealthCheckConfig()
    
    def verify_startup(self, server: 'Server', verbose: bool = False) -> HealthCheckResult:
        """
        Verify that a server started correctly.
        
        Args:
            server: Server instance to verify
            verbose: Whether to print progress
            
        Returns:
            HealthCheckResult indicating success/failure
        """
        start_time = time.time()
        
        # Step 1: Wait for port to be available
        if verbose:
            print(f"\r⏳ Waiting for server '{server.name}' to bind to port {server.port}...", end='', flush=True)
        
        # Get host - handle both ServerHandle and Server objects
        host = getattr(server, 'host', 'localhost')
        
        if not self._wait_for_port(host, server.port):
            return HealthCheckResult(
                healthy=False, 
                details={"error": f"Port {server.port} not available after {self.config.port_check_timeout}s"}
            )
        
        # Step 2: Try health endpoint first
        health_url = f"http://{host}:{server.port}{self.config.health_endpoint}"
        
        for attempt, delay in enumerate(self.config.retry_delays):
            if attempt > 0:
                if verbose:
                    print(f"\r⏳ Retrying ({attempt+1}/{len(self.config.retry_delays)})...", end='', flush=True)
                time.sleep(delay)
            
            # Try health endpoint
            result = self._check_endpoint(health_url, timeout=2.0)
            if result.healthy:
                if verbose:
                    elapsed = time.time() - start_time
                    print(f"\r✅ Server healthy after {elapsed:.1f}s")
                return result
            
            # If health endpoint doesn't exist, try other endpoints
            if result.details.get('status_code') == 404 and self.config.test_all_endpoints:
                # Don't print this message - it's too verbose
                pass
                
                # Test each configured endpoint
                working_endpoints = []
                endpoints = server.endpoints if hasattr(server, 'endpoints') and isinstance(server.endpoints, dict) else (server.endpoints if isinstance(server.endpoints, list) else [])
                if isinstance(endpoints, dict):
                    endpoint_paths = list(endpoints.keys())
                else:
                    endpoint_paths = endpoints
                    
                for path in endpoint_paths:
                    test_url = f"http://{host}:{server.port}{path}"
                    endpoint_result = self._check_endpoint(test_url, timeout=2.0)
                    if endpoint_result.healthy:
                        working_endpoints.append(path)
                
                if working_endpoints:
                    if verbose:
                        elapsed = time.time() - start_time
                        print(f"\r✅ Server healthy after {elapsed:.1f}s")
                    return HealthCheckResult(
                        healthy=True,
                        details={
                            "working_endpoints": working_endpoints,
                            "startup_time": time.time() - start_time
                        }
                    )
        
        # All retries failed
        return HealthCheckResult(
            healthy=False,
            details={
                "error": "Server not responding after all retries",
                "attempts": len(self.config.retry_delays),
                "total_time": time.time() - start_time
            }
        )
    
    def check_health(self, server: 'Server') -> HealthCheckResult:
        """
        Quick health check for a running server.
        
        Args:
            server: Server instance to check
            
        Returns:
            HealthCheckResult
        """
        # First check if process is alive
        is_running = False
        if hasattr(server, 'is_running'):
            is_running = server.is_running()
        elif hasattr(server, 'status'):
            is_running = server.status == "running"
        elif hasattr(server, 'pid'):
            # For ServerHandle objects
            try:
                import psutil
                psutil.Process(server.pid)
                is_running = True
            except psutil.NoSuchProcess:
                is_running = False
                
        if not is_running:
            return HealthCheckResult(
                healthy=False,
                details={"error": "Server process is not running"}
            )
        
        # Get host - handle both ServerHandle and Server objects
        host = getattr(server, 'host', 'localhost')
        
        # Check health endpoint or any endpoint
        health_url = f"http://{host}:{server.port}{self.config.health_endpoint}"
        result = self._check_endpoint(health_url, timeout=1.0)
        
        if not result.healthy and result.details.get('status_code') == 404:
            # Try any endpoint
            endpoints = server.endpoints if hasattr(server, 'endpoints') and isinstance(server.endpoints, dict) else (server.endpoints if isinstance(server.endpoints, list) else [])
            if isinstance(endpoints, dict):
                endpoint_paths = list(endpoints.keys())
            else:
                endpoint_paths = endpoints
                
            for path in endpoint_paths:
                test_url = f"http://{host}:{server.port}{path}"
                result = self._check_endpoint(test_url, timeout=1.0)
                if result.healthy:
                    break
        
        return result
    
    def _wait_for_port(self, host: str, port: int) -> bool:
        """
        Wait for a port to become available.
        
        Args:
            host: Host to check
            port: Port to check
            
        Returns:
            True if port becomes available within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < self.config.port_check_timeout:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            try:
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    return True
            except Exception:
                pass
            finally:
                sock.close()
            
            time.sleep(0.1)
        
        return False
    
    def _check_endpoint(self, url: str, timeout: float = 2.0) -> HealthCheckResult:
        """
        Check if an endpoint is responding.
        
        Args:
            url: URL to check
            timeout: Request timeout
            
        Returns:
            HealthCheckResult
        """
        try:
            response = requests.get(url, timeout=timeout)
            
            # Accept any 2xx or 4xx status (4xx means server is responding)
            if 200 <= response.status_code < 500:
                return HealthCheckResult(
                    healthy=True,
                    details={
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds()
                    }
                )
            else:
                return HealthCheckResult(
                    healthy=False,
                    details={
                        "status_code": response.status_code,
                        "error": f"Unexpected status code: {response.status_code}"
                    }
                )
                
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                healthy=False,
                details={"error": f"Request timed out after {timeout}s"}
            )
        except requests.exceptions.ConnectionError as e:
            return HealthCheckResult(
                healthy=False,
                details={"error": f"Connection error: {str(e)}"}
            )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                details={"error": f"Unexpected error: {str(e)}"}
            )
    
    def add_custom_check(self, name: str, check_func: Callable[['Server'], bool]):
        """
        Add a custom health check function.
        
        Args:
            name: Name of the check
            check_func: Function that takes a Server and returns bool
        """
        # This would be implemented if we need custom checks
        # For now, the basic HTTP checks should suffice
        pass