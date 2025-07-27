"""
Tests for error handling and edge cases
"""

import pytest
import time
import signal
import os

import syft_serve as ss
from syft_serve import ServerAlreadyExistsError, ServerNotFoundError


class TestErrorHandling:
    """Test various error conditions and edge cases"""
    
    def test_duplicate_server_name(self):
        """Test creating server with duplicate name"""
        server1 = ss.create(
            name="duplicate_test",
            endpoints={"/": lambda: {"server": 1}}
        )
        
        try:
            with pytest.raises(ServerAlreadyExistsError) as exc_info:
                ss.create(
                    name="duplicate_test",
                    endpoints={"/": lambda: {"server": 2}}
                )
            
            assert "duplicate_test" in str(exc_info.value)
        finally:
            server1.terminate()
    
    def test_server_not_found(self):
        """Test accessing non-existent server"""
        with pytest.raises(ServerNotFoundError):
            _ = ss.servers["nonexistent_server_xyz"]
    
    def test_invalid_server_name_empty(self):
        """Test empty server name"""
        with pytest.raises(ValueError) as exc_info:
            ss.create(
                name="",
                endpoints={"/": lambda: {}}
            )
        
        assert "name" in str(exc_info.value).lower()
    
    def test_invalid_server_name_special_chars(self):
        """Test server name with special characters"""
        # This should work - names are sanitized
        server = ss.create(
            name="test-server_123",
            endpoints={"/": lambda: {"ok": True}}
        )
        
        assert server.name == "test-server_123"
        assert server.status == "running"
        server.terminate()
    
    def test_empty_endpoints_dict(self):
        """Test creating server with no endpoints"""
        # API allows empty endpoints - server will have health endpoint
        server = ss.create(
            name="empty_endpoints",
            endpoints={}
        )
        
        try:
            assert server.status == "running"
            # Should still have health endpoint
            import requests
            resp = requests.get(f"{server.url}/health")
            assert resp.status_code == 200
        finally:
            server.terminate()
    
    
    def test_endpoint_with_error(self):
        """Test endpoint that raises an error"""
        def error_endpoint():
            raise RuntimeError("Intentional error")
        
        server = ss.create(
            name="error_endpoint",
            endpoints={"/error": error_endpoint}
        )
        
        try:
            # Server should still start
            assert server.status == "running"
            
            # Endpoint should return 500 error
            import requests
            response = requests.get(f"{server.url}/error")
            assert response.status_code == 500
        finally:
            server.terminate()
    
    def test_invalid_dependencies(self):
        """Test server with invalid dependency specification"""
        # This should fail during server startup
        with pytest.raises(Exception):  # Could be various exceptions
            ss.create(
                name="invalid_deps",
                endpoints={"/": lambda: {"ok": True}},
                dependencies=["nonexistent-package-xyz==99.99.99"]
            )
    
    def test_server_terminate_already_stopped(self):
        """Test terminating already stopped server"""
        server = ss.create(
            name="terminate_twice",
            endpoints={"/": lambda: {"ok": True}}
        )
        
        # First termination
        server.terminate()
        assert server.status == "stopped"
        
        # Second termination should not raise error
        server.terminate()  # Should handle gracefully
        assert server.status == "stopped"
    
    
    def test_server_url_after_terminate(self):
        """Test accessing server URL after termination"""
        server = ss.create(
            name="terminated_url",
            endpoints={"/": lambda: {"ok": True}}
        )
        
        url = server.url
        server.terminate()
        
        # URL property should still work
        assert server.url == url
        assert server.status == "stopped"
    
    def test_negative_expiration(self):
        """Test negative expiration values"""
        # -1 should mean never expire
        server = ss.create(
            name="negative_expire",
            endpoints={"/": lambda: {"ok": True}},
            expiration_seconds=-1
        )
        
        assert server.expiration_info == "Never"
        server.terminate()
        
        # Other negative values should also work
        server2 = ss.create(
            name="negative_expire2",
            endpoints={"/": lambda: {"ok": True}},
            expiration_seconds=-999
        )
        
        assert server2.expiration_info == "Never"
        server2.terminate()
    
    
    @pytest.mark.skipif(os.name == 'nt', reason="POSIX only test")
    def test_server_kill_process_group(self):
        """Test killing server process group on POSIX systems"""
        server = ss.create(
            name="process_group_test",
            endpoints={"/": lambda: {"ok": True}}
        )
        
        try:
            pid = server.pid
            assert pid is not None
            
            # Terminate should handle process groups
            server.terminate()
            assert server.status == "stopped"
        except Exception as e:
            # Cleanup
            server.force_terminate()
            raise e