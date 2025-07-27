"""Tests for the Server class."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from syft_serve._server import Server
from syft_serve._handle import Handle
from syft_serve._log_stream import LogStream
from syft_serve._environment import Environment


class TestServer:
    """Test the Server class."""
    
    def test_server_initialization(self, mock_config):
        """Test server initialization."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        mock_handle.port = 8000
        mock_handle.url = "http://localhost:8000"
        mock_handle.pid = 12345
        mock_handle.status = "running"
        
        endpoints = ["/hello", "/goodbye"]
        
        server = Server(
            handle=mock_handle,
            endpoints=endpoints,
            config=mock_config
        )
        
        assert server.name == "test_server"
        assert server.port == 8000
        assert server.url == "http://localhost:8000"
        assert server.pid == 12345
        assert server.status == "running"
        assert server.endpoints == endpoints
    
    def test_server_uptime_property(self, mock_config):
        """Test server uptime property."""
        mock_handle = Mock(spec=Handle)
        mock_handle.uptime = "5m 30s"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        assert server.uptime == "5m 30s"
    
    def test_server_stdout_property(self, mock_config):
        """Test server stdout property."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        stdout = server.stdout
        assert isinstance(stdout, LogStream)
        assert stdout._log_file.name == "stdout.log"
    
    def test_server_stderr_property(self, mock_config):
        """Test server stderr property."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        stderr = server.stderr
        assert isinstance(stderr, LogStream)
        assert stderr._log_file.name == "stderr.log"
    
    def test_server_env_property(self, mock_config):
        """Test server env property."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        env = server.env
        assert isinstance(env, Environment)
    
    def test_server_terminate(self, mock_config):
        """Test server terminate method."""
        mock_handle = Mock(spec=Handle)
        mock_handle.terminate.return_value = None
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        server.terminate()
        mock_handle.terminate.assert_called_once()
    
    def test_server_is_running(self, mock_config):
        """Test server is_running method."""
        mock_handle = Mock(spec=Handle)
        mock_handle.is_running.return_value = True
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        assert server.is_running() is True
        mock_handle.is_running.assert_called_once()
    
    def test_server_repr(self, mock_config):
        """Test server string representation."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        mock_handle.port = 8000
        mock_handle.status = "running"
        
        server = Server(
            handle=mock_handle,
            endpoints=["/hello"],
            config=mock_config
        )
        
        repr_str = repr(server)
        assert "test_server" in repr_str
        assert "8000" in repr_str
        assert "running" in repr_str
    
    def test_server_str(self, mock_config):
        """Test server string conversion."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        assert str(server) == "test_server"
    
    def test_server_eq(self, mock_config):
        """Test server equality comparison."""
        mock_handle1 = Mock(spec=Handle)
        mock_handle1.name = "server1"
        
        mock_handle2 = Mock(spec=Handle)
        mock_handle2.name = "server2"
        
        mock_handle3 = Mock(spec=Handle)
        mock_handle3.name = "server1"
        
        server1 = Server(handle=mock_handle1, endpoints=[], config=mock_config)
        server2 = Server(handle=mock_handle2, endpoints=[], config=mock_config)
        server3 = Server(handle=mock_handle3, endpoints=[], config=mock_config)
        
        assert server1 == server3  # Same name
        assert server1 != server2  # Different name
        assert server1 != "not_a_server"  # Different type
    
    def test_server_hash(self, mock_config):
        """Test server hash function."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        # Should be hashable
        hash_value = hash(server)
        assert isinstance(hash_value, int)
        
        # Same server should have same hash
        server2 = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        assert hash(server) == hash(server2)


class TestServerLogStreams:
    """Test server log stream functionality."""
    
    def test_log_streams_creation(self, mock_config, temp_dir):
        """Test that log streams are created correctly."""
        # Create log files
        server_dir = temp_dir / "test_server"
        server_dir.mkdir()
        (server_dir / "stdout.log").write_text("stdout content")
        (server_dir / "stderr.log").write_text("stderr content")
        
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        # Mock the server directory path
        mock_config.servers_dir = temp_dir
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        # Test stdout
        stdout = server.stdout
        assert isinstance(stdout, LogStream)
        
        # Test stderr
        stderr = server.stderr
        assert isinstance(stderr, LogStream)
    
    def test_log_streams_caching(self, mock_config):
        """Test that log streams are cached."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        # Get streams multiple times
        stdout1 = server.stdout
        stdout2 = server.stdout
        stderr1 = server.stderr
        stderr2 = server.stderr
        
        # Should be the same instances
        assert stdout1 is stdout2
        assert stderr1 is stderr2


class TestServerEnvironment:
    """Test server environment functionality."""
    
    def test_environment_creation(self, mock_config):
        """Test that environment is created correctly."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        env = server.env
        assert isinstance(env, Environment)
    
    def test_environment_caching(self, mock_config):
        """Test that environment is cached."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        # Get environment multiple times
        env1 = server.env
        env2 = server.env
        
        # Should be the same instance
        assert env1 is env2


class TestServerErrorHandling:
    """Test server error handling."""
    
    def test_server_with_none_handle(self, mock_config):
        """Test server creation with None handle."""
        with pytest.raises(ValueError, match="Handle cannot be None"):
            Server(handle=None, endpoints=[], config=mock_config)
    
    def test_server_with_none_config(self):
        """Test server creation with None config."""
        mock_handle = Mock(spec=Handle)
        
        with pytest.raises(ValueError, match="Config cannot be None"):
            Server(handle=mock_handle, endpoints=[], config=None)
    
    def test_server_terminate_error(self, mock_config):
        """Test server terminate with error."""
        mock_handle = Mock(spec=Handle)
        mock_handle.terminate.side_effect = Exception("Termination failed")
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        # Should propagate the exception
        with pytest.raises(Exception, match="Termination failed"):
            server.terminate()


class TestServerProperties:
    """Test server property access."""
    
    def test_all_properties_delegate_to_handle(self, mock_config):
        """Test that all properties delegate to handle."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_name"
        mock_handle.port = 8080
        mock_handle.url = "http://test:8080"
        mock_handle.pid = 99999
        mock_handle.status = "test_status"
        mock_handle.uptime = "test_uptime"
        mock_handle.is_running.return_value = False
        
        server = Server(
            handle=mock_handle,
            endpoints=["/test"],
            config=mock_config
        )
        
        # Test all property delegations
        assert server.name == "test_name"
        assert server.port == 8080
        assert server.url == "http://test:8080"
        assert server.pid == 99999
        assert server.status == "test_status"
        assert server.uptime == "test_uptime"
        assert server.is_running() is False
        assert server.endpoints == ["/test"]
    
    def test_property_with_handle_exception(self, mock_config):
        """Test property access when handle raises exception."""
        mock_handle = Mock(spec=Handle)
        mock_handle.name = "test_server"
        mock_handle.status = property(lambda self: exec('raise Exception("Handle error")'))
        
        server = Server(
            handle=mock_handle,
            endpoints=[],
            config=mock_config
        )
        
        # Should propagate handle exceptions
        with pytest.raises(Exception, match="Handle error"):
            _ = server.status