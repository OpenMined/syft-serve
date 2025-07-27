"""
Comprehensive tests for syft-serve public API
"""

import pytest
import time
import requests
from typing import Dict
from pathlib import Path

import syft_serve as ss
from syft_serve import ServerAlreadyExistsError, ServerNotFoundError


# Test fixtures
@pytest.fixture
def simple_endpoint():
    """Simple endpoint function for testing"""
    def hello():
        return {"message": "Hello from test!"}
    return hello


@pytest.fixture
def complex_endpoints():
    """Multiple endpoints for testing"""
    def root():
        return {"status": "ok"}
    
    def echo(data: dict):
        return {"echo": data}
    
    def health():
        return {"healthy": True}
    
    return {
        "/": root,
        "/echo": echo,
        "/health": health
    }


@pytest.fixture(autouse=True)
def cleanup_servers():
    """Ensure all servers are terminated after each test"""
    yield
    # Cleanup any servers created during tests
    try:
        ss.terminate_all()
    except Exception:
        pass


class TestCreate:
    """Test the create() function"""
    
    def test_create_basic_server(self, simple_endpoint):
        """Test creating a basic server"""
        server = ss.create(
            name="test_basic",
            endpoints={"/": simple_endpoint}
        )
        
        assert server.name == "test_basic"
        assert server.status == "running"
        assert server.port > 0
        assert server.pid is not None
        assert "/" in server.endpoints
        
        # Test server is accessible
        response = requests.get(f"{server.url}/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from test!"}
        
        server.terminate()
    
    def test_create_with_dependencies(self, simple_endpoint):
        """Test creating a server with dependencies"""
        server = ss.create(
            name="test_deps",
            endpoints={"/": simple_endpoint},
            dependencies=["requests==2.31.0"]
        )
        
        assert server.name == "test_deps"
        assert server.status == "running"
        
        # Check environment has the dependency
        env_packages = server.env.list()
        assert any("requests" in pkg for pkg in env_packages)
        
        server.terminate()
    
    def test_create_with_expiration(self, simple_endpoint):
        """Test creating a server with expiration"""
        server = ss.create(
            name="test_expire",
            endpoints={"/": simple_endpoint},
            expiration_seconds=10  # 10 seconds
        )
        
        assert server.name == "test_expire"
        assert "s" in server.expiration_info or "10s" in server.expiration_info
        
        server.terminate()
    
    def test_create_never_expires(self, simple_endpoint):
        """Test creating a server that never expires"""
        server = ss.create(
            name="test_never_expire",
            endpoints={"/": simple_endpoint},
            expiration_seconds=-1
        )
        
        assert server.name == "test_never_expire"
        assert server.expiration_info == "Never"
        
        server.terminate()
    
    def test_create_duplicate_error(self, simple_endpoint):
        """Test that creating duplicate server raises error"""
        server1 = ss.create(
            name="test_duplicate",
            endpoints={"/": simple_endpoint}
        )
        
        with pytest.raises(ServerAlreadyExistsError):
            ss.create(
                name="test_duplicate",
                endpoints={"/": simple_endpoint}
            )
        
        server1.terminate()
    
    def test_create_with_force(self, simple_endpoint):
        """Test force creating a server (replacing existing)"""
        server1 = ss.create(
            name="test_force",
            endpoints={"/": simple_endpoint}
        )
        old_port = server1.port
        
        # Force create with same name
        server2 = ss.create(
            name="test_force",
            endpoints={"/": lambda: {"message": "New server"}},
            force=True
        )
        
        assert server2.port != old_port  # Should be a new server
        assert server1.status == "stopped"  # Old server should be stopped
        
        # Verify new endpoint
        response = requests.get(f"{server2.url}/")
        assert response.json() == {"message": "New server"}
        
        server2.terminate()
    
    def test_create_multiple_endpoints(self, complex_endpoints):
        """Test creating server with multiple endpoints"""
        server = ss.create(
            name="test_multiple",
            endpoints=complex_endpoints
        )
        
        assert len(server.endpoints) == 3
        assert "/" in server.endpoints
        assert "/echo" in server.endpoints
        assert "/health" in server.endpoints
        
        # Test each endpoint
        resp1 = requests.get(f"{server.url}/")
        assert resp1.json() == {"status": "ok"}
        
        resp2 = requests.get(f"{server.url}/health")
        assert resp2.json() == {"healthy": True}
        
        server.terminate()


class TestServersCollection:
    """Test the servers collection object"""
    
    def test_servers_empty(self):
        """Test servers collection when empty"""
        assert len(ss.servers) == 0
        assert list(ss.servers) == []
    
    def test_servers_contains(self, simple_endpoint):
        """Test checking if server exists"""
        assert "test_server" not in ss.servers
        
        server = ss.create(
            name="test_server",
            endpoints={"/": simple_endpoint}
        )
        
        assert "test_server" in ss.servers
        assert len(ss.servers) == 1
        
        server.terminate()
        
        # After termination, server should be removed
        assert "test_server" not in ss.servers
        assert len(ss.servers) == 0
    
    def test_servers_getitem(self, simple_endpoint):
        """Test accessing server by name"""
        server = ss.create(
            name="test_getitem",
            endpoints={"/": simple_endpoint}
        )
        
        # Access by name
        retrieved = ss.servers["test_getitem"]
        assert retrieved.name == server.name
        assert retrieved.port == server.port
        assert retrieved.pid == server.pid
        
        # Test accessing non-existent server
        with pytest.raises(ServerNotFoundError):
            _ = ss.servers["non_existent"]
        
        server.terminate()
    
    def test_servers_iteration(self, simple_endpoint):
        """Test iterating over servers"""
        # Create multiple servers
        servers = []
        for i in range(3):
            server = ss.create(
                name=f"test_iter_{i}",
                endpoints={"/": simple_endpoint}
            )
            servers.append(server)
        
        # Test iteration
        server_names = list(ss.servers)
        assert len(server_names) == 3
        assert all(name.startswith("test_iter_") for name in server_names)
        
        # Test repr
        repr_str = repr(ss.servers)
        assert "3 servers" in repr_str
        
        # Cleanup
        for server in servers:
            server.terminate()
    
    def test_servers_len(self, simple_endpoint):
        """Test length of servers collection"""
        assert len(ss.servers) == 0
        
        server1 = ss.create(name="test_len_1", endpoints={"/": simple_endpoint})
        assert len(ss.servers) == 1
        
        server2 = ss.create(name="test_len_2", endpoints={"/": simple_endpoint})
        assert len(ss.servers) == 2
        
        server1.terminate()
        assert len(ss.servers) == 1
        
        server2.terminate()
        assert len(ss.servers) == 0


class TestServerObject:
    """Test the Server object methods and properties"""
    
    def test_server_properties(self, simple_endpoint):
        """Test basic server properties"""
        server = ss.create(
            name="test_props",
            endpoints={"/": simple_endpoint}
        )
        
        assert server.name == "test_props"
        assert server.status == "running"
        assert isinstance(server.port, int)
        assert server.port > 0
        assert server.pid is not None
        assert server.url.startswith("http://localhost:")
        assert server.uptime != "-"
        
        server.terminate()
    
    def test_server_stdout_logs(self, simple_endpoint):
        """Test accessing stdout logs"""
        server = ss.create(
            name="test_stdout",
            endpoints={"/": simple_endpoint}
        )
        
        # Wait for server to start and generate some logs
        time.sleep(2)
        requests.get(f"{server.url}/")
        
        # Test log methods
        assert hasattr(server.stdout, 'tail')
        assert hasattr(server.stdout, 'head')
        assert hasattr(server.stdout, 'follow')
        assert hasattr(server.stdout, 'search')
        
        # Get last few lines
        logs = server.stdout.tail(10)
        assert isinstance(logs, str)
        
        server.terminate()
    
    def test_server_stderr_logs(self, simple_endpoint):
        """Test accessing stderr logs"""
        server = ss.create(
            name="test_stderr",
            endpoints={"/": simple_endpoint}
        )
        
        # Test log methods exist
        assert hasattr(server.stderr, 'tail')
        assert hasattr(server.stderr, 'head')
        assert hasattr(server.stderr, 'follow')
        assert hasattr(server.stderr, 'search')
        
        server.terminate()
    
    def test_server_environment(self, simple_endpoint):
        """Test accessing server environment"""
        server = ss.create(
            name="test_env",
            endpoints={"/": simple_endpoint},
            dependencies=["tabulate>=0.9.0"]
        )
        
        # Test environment access
        env = server.env
        packages = env.list()
        
        assert isinstance(packages, list)
        assert len(packages) > 0
        assert any("tabulate" in pkg for pkg in packages)
        
        # Test repr
        env_repr = repr(env)
        assert "test_env" in env_repr
        
        server.terminate()
    
    def test_server_terminate(self, simple_endpoint):
        """Test terminating a server"""
        server = ss.create(
            name="test_terminate",
            endpoints={"/": simple_endpoint}
        )
        
        assert server.status == "running"
        
        # Terminate
        server.terminate(timeout=5.0)
        
        # Check server is stopped
        assert server.status == "stopped"
        assert server.pid is None
        
        # Server should be removed from collection
        assert "test_terminate" not in ss.servers
    
    def test_server_force_terminate(self, simple_endpoint):
        """Test force terminating a server"""
        server = ss.create(
            name="test_force_terminate",
            endpoints={"/": simple_endpoint}
        )
        
        assert server.status == "running"
        
        # Force terminate
        server.force_terminate()
        
        # Check server is stopped
        assert server.status == "stopped"
        assert server.pid is None
    
    def test_server_uptime_format(self, simple_endpoint):
        """Test uptime formatting"""
        server = ss.create(
            name="test_uptime",
            endpoints={"/": simple_endpoint}
        )
        
        # Just started - should be seconds
        uptime = server.uptime
        assert uptime.endswith("s") or "m" in uptime
        
        server.terminate()
    
    def test_server_repr(self, simple_endpoint):
        """Test server string representation"""
        server = ss.create(
            name="test_repr",
            endpoints={"/": simple_endpoint},
            expiration_seconds=3600  # 1 hour
        )
        
        repr_str = repr(server)
        
        assert "test_repr" in repr_str
        assert "✅" in repr_str  # Running status
        assert "http://localhost:" in repr_str
        assert "PID:" in repr_str
        assert "⏰" in repr_str  # Expiration emoji
        
        server.terminate()


class TestTerminateAll:
    """Test the terminate_all function"""
    
    def test_terminate_all_servers(self, simple_endpoint):
        """Test terminating all servers at once"""
        # Create multiple servers
        servers = []
        for i in range(3):
            server = ss.create(
                name=f"test_terminate_all_{i}",
                endpoints={"/": simple_endpoint}
            )
            servers.append(server)
        
        assert len(ss.servers) == 3
        
        # Terminate all
        ss.terminate_all()
        
        # Check all are terminated
        assert len(ss.servers) == 0
        for server in servers:
            assert server.status == "stopped"


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_server_name(self, simple_endpoint):
        """Test creating server with invalid name"""
        with pytest.raises(ValueError):
            ss.create(
                name="",  # Empty name
                endpoints={"/": simple_endpoint}
            )
    
    def test_empty_endpoints(self):
        """Test creating server with no endpoints"""
        with pytest.raises(ValueError):
            ss.create(
                name="test_empty",
                endpoints={}  # No endpoints
            )
    
    
    def test_server_not_found_error(self):
        """Test accessing non-existent server"""
        with pytest.raises(ServerNotFoundError):
            _ = ss.servers["does_not_exist"]


