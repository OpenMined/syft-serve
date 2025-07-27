"""Tests for the ServerManager class."""
import pytest
from unittest.mock import Mock, patch

from syft_serve._manager import ServerManager
from syft_serve._exceptions import (
    DuplicateServerError, 
    ServerStartupError, 
    PortConflictError
)
from syft_serve._server import Server


class TestServerManager:
    """Test the ServerManager class."""
    
    def test_manager_initialization(self, mock_config):
        """Test manager initialization."""
        manager = ServerManager(mock_config)
        assert manager.config == mock_config
    
    def test_manager_servers_property(self, mock_config):
        """Test servers property returns ServerCollection."""
        manager = ServerManager(mock_config)
        servers = manager.servers
        
        # Should return a ServerCollection instance
        from syft_serve._server_collection import ServerCollection
        assert isinstance(servers, ServerCollection)
    
    def test_find_available_port(self, mock_config):
        """Test finding available port."""
        manager = ServerManager(mock_config)
        
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_sock.bind.return_value = None
            mock_sock.getsockname.return_value = ('localhost', 8000)
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            port = manager._find_available_port()
            assert port == 8000
    
    def test_find_available_port_retry(self, mock_config):
        """Test finding available port with retry."""
        manager = ServerManager(mock_config)
        
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            # First call fails, second succeeds
            mock_sock.bind.side_effect = [OSError("Port in use"), None]
            mock_sock.getsockname.return_value = ('localhost', 8001)
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            port = manager._find_available_port()
            assert port == 8001
            assert mock_sock.bind.call_count == 2


class TestCreateServer:
    """Test server creation functionality."""
    
    def test_create_server_success(self, mock_config, sample_endpoints):
        """Test successful server creation."""
        manager = ServerManager(mock_config)
        
        with patch.object(manager, '_find_available_port', return_value=8000), \
             patch.object(manager, '_start_server_process', return_value=12345), \
             patch.object(manager, '_wait_for_server_ready', return_value=True), \
             patch.object(manager.servers, 'add_server') as mock_add:
            
            server = manager.create_server(
                name="test_server",
                endpoints=sample_endpoints
            )
            
            assert isinstance(server, Server)
            assert server.name == "test_server"
            assert server.port == 8000
            mock_add.assert_called_once()
    
    def test_create_server_duplicate_without_force(self, mock_config, sample_endpoints):
        """Test creating duplicate server without force."""
        manager = ServerManager(mock_config)
        
        with patch.object(manager.servers, 'get_server', return_value=Mock()):
            with pytest.raises(DuplicateServerError):
                manager.create_server(
                    name="existing_server",
                    endpoints=sample_endpoints,
                    force=False
                )
    
    def test_create_server_duplicate_with_force(self, mock_config, sample_endpoints):
        """Test creating duplicate server with force."""
        manager = ServerManager(mock_config)
        
        existing_server = Mock()
        existing_server.terminate.return_value = None
        
        with patch.object(manager.servers, 'get_server', return_value=existing_server), \
             patch.object(manager.servers, 'remove_server'), \
             patch.object(manager, '_find_available_port', return_value=8000), \
             patch.object(manager, '_start_server_process', return_value=12345), \
             patch.object(manager, '_wait_for_server_ready', return_value=True), \
             patch.object(manager.servers, 'add_server'):
            
            server = manager.create_server(
                name="existing_server",
                endpoints=sample_endpoints,
                force=True
            )
            
            existing_server.terminate.assert_called_once()
            assert isinstance(server, Server)
    
    def test_create_server_startup_timeout(self, mock_config, sample_endpoints):
        """Test server creation with startup timeout."""
        manager = ServerManager(mock_config)
        
        with patch.object(manager, '_find_available_port', return_value=8000), \
             patch.object(manager, '_start_server_process', return_value=12345), \
             patch.object(manager, '_wait_for_server_ready', return_value=False):
            
            with pytest.raises(ServerStartupError, match="Server did not become ready"):
                manager.create_server(
                    name="test_server",
                    endpoints=sample_endpoints
                )
    
    def test_create_server_with_dependencies(self, mock_config, sample_endpoints):
        """Test creating server with dependencies."""
        manager = ServerManager(mock_config)
        dependencies = ["pandas", "numpy"]
        
        with patch.object(manager, '_find_available_port', return_value=8000), \
             patch.object(manager, '_install_dependencies') as mock_install, \
             patch.object(manager, '_start_server_process', return_value=12345), \
             patch.object(manager, '_wait_for_server_ready', return_value=True), \
             patch.object(manager.servers, 'add_server'):
            
            manager.create_server(
                name="test_server",
                endpoints=sample_endpoints,
                dependencies=dependencies
            )
            
            mock_install.assert_called_once_with("test_server", dependencies)


class TestServerProcessManagement:
    """Test server process management."""
    
    def test_start_server_process(self, mock_config, temp_dir):
        """Test starting server process."""
        manager = ServerManager(mock_config)
        
        # Create server directory
        server_dir = temp_dir / "test_server"
        server_dir.mkdir()
        
        mock_config.servers_dir = temp_dir
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            pid = manager._start_server_process("test_server", 8000)
            
            assert pid == 12345
            mock_popen.assert_called_once()
    
    def test_wait_for_server_ready_success(self, mock_config):
        """Test waiting for server to become ready - success."""
        manager = ServerManager(mock_config)
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = manager._wait_for_server_ready("http://localhost:8000", timeout=1)
            assert result is True
    
    def test_wait_for_server_ready_timeout(self, mock_config):
        """Test waiting for server to become ready - timeout."""
        manager = ServerManager(mock_config)
        
        with patch('requests.get', side_effect=Exception("Connection failed")), \
             patch('time.sleep'):
            
            result = manager._wait_for_server_ready("http://localhost:8000", timeout=0.1)
            assert result is False
    
    def test_install_dependencies(self, mock_config, temp_dir):
        """Test installing dependencies."""
        manager = ServerManager(mock_config)
        
        # Create server directory with venv
        server_dir = temp_dir / "test_server"
        venv_dir = server_dir / "venv"
        venv_dir.mkdir(parents=True)
        
        mock_config.servers_dir = temp_dir
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            manager._install_dependencies("test_server", ["pandas", "numpy"])
            
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "pip" in args
            assert "install" in args
            assert "pandas" in args
            assert "numpy" in args


class TestTerminateServers:
    """Test server termination functionality."""
    
    def test_terminate_all_servers(self, mock_config):
        """Test terminating all servers."""
        manager = ServerManager(mock_config)
        
        # Create mock servers
        server1 = Mock()
        server2 = Mock()
        servers = [server1, server2]
        
        with patch.object(manager.servers, 'list_servers', return_value=servers), \
             patch.object(manager.servers, 'clear_servers'):
            
            manager.terminate_all()
            
            server1.terminate.assert_called_once()
            server2.terminate.assert_called_once()
    
    def test_terminate_all_with_orphaned_processes(self, mock_config):
        """Test terminating all servers including orphaned processes."""
        manager = ServerManager(mock_config)
        
        with patch.object(manager.servers, 'list_servers', return_value=[]), \
             patch.object(manager.servers, 'clear_servers'), \
             patch('syft_serve._process_discovery.discover_syft_serve_processes') as mock_discover, \
             patch('psutil.Process') as mock_process_class:
            
            # Mock orphaned process
            orphaned_process = {
                'pid': 99999,
                'name': 'python',
                'cmdline': ['python', '-m', 'uvicorn']
            }
            mock_discover.return_value = [orphaned_process]
            
            mock_process = Mock()
            mock_process_class.return_value = mock_process
            
            manager.terminate_all()
            
            mock_process.terminate.assert_called_once()
    
    def test_terminate_server_by_name(self, mock_config):
        """Test terminating specific server by name."""
        manager = ServerManager(mock_config)
        
        mock_server = Mock()
        
        with patch.object(manager.servers, 'get_server', return_value=mock_server), \
             patch.object(manager.servers, 'remove_server'):
            
            manager.terminate_server("test_server")
            
            mock_server.terminate.assert_called_once()


class TestValidation:
    """Test input validation in ServerManager."""
    
    def test_create_server_invalid_name(self, mock_config, sample_endpoints):
        """Test creating server with invalid name."""
        manager = ServerManager(mock_config)
        
        with pytest.raises(ValueError, match="Server name cannot be empty"):
            manager.create_server("", sample_endpoints)
        
        with pytest.raises(ValueError, match="Server name cannot be empty"):
            manager.create_server(None, sample_endpoints)
    
    def test_create_server_invalid_endpoints(self, mock_config):
        """Test creating server with invalid endpoints."""
        manager = ServerManager(mock_config)
        
        with pytest.raises(ValueError, match="Endpoints cannot be empty"):
            manager.create_server("test", {})
        
        with pytest.raises(ValueError, match="Endpoints cannot be empty"):
            manager.create_server("test", None)
    
    def test_create_server_invalid_endpoint_values(self, mock_config):
        """Test creating server with non-callable endpoints."""
        manager = ServerManager(mock_config)
        
        with pytest.raises(ValueError, match="All endpoint values must be callable"):
            manager.create_server("test", {"/test": "not_callable"})


class TestErrorHandling:
    """Test error handling in ServerManager."""
    
    def test_create_server_process_start_failure(self, mock_config, sample_endpoints):
        """Test server creation when process start fails."""
        manager = ServerManager(mock_config)
        
        with patch.object(manager, '_find_available_port', return_value=8000), \
             patch.object(manager, '_start_server_process', side_effect=Exception("Process failed")):
            
            with pytest.raises(ServerStartupError, match="Failed to start server process"):
                manager.create_server("test_server", sample_endpoints)
    
    def test_terminate_server_not_found(self, mock_config):
        """Test terminating non-existent server."""
        manager = ServerManager(mock_config)
        
        with patch.object(manager.servers, 'get_server', return_value=None):
            # Should not raise exception
            manager.terminate_server("nonexistent")
    
    def test_terminate_server_with_error(self, mock_config):
        """Test terminating server that fails to terminate."""
        manager = ServerManager(mock_config)
        
        mock_server = Mock()
        mock_server.terminate.side_effect = Exception("Termination failed")
        
        with patch.object(manager.servers, 'get_server', return_value=mock_server):
            # Should handle the exception gracefully
            manager.terminate_server("test_server")


class TestDirectoryManagement:
    """Test directory creation and management."""
    
    def test_ensure_server_directory(self, mock_config, temp_dir):
        """Test ensuring server directory exists."""
        manager = ServerManager(mock_config)
        mock_config.servers_dir = temp_dir
        
        server_dir = manager._ensure_server_directory("test_server")
        
        assert server_dir.exists()
        assert server_dir.is_dir()
        assert server_dir.name == "test_server"
    
    def test_ensure_server_directory_already_exists(self, mock_config, temp_dir):
        """Test ensuring server directory when it already exists."""
        manager = ServerManager(mock_config)
        mock_config.servers_dir = temp_dir
        
        # Create directory first
        existing_dir = temp_dir / "test_server"
        existing_dir.mkdir()
        
        server_dir = manager._ensure_server_directory("test_server")
        
        assert server_dir == existing_dir
        assert server_dir.exists()


class TestPortManagement:
    """Test port allocation and management."""
    
    def test_port_range_limits(self, mock_config):
        """Test port allocation within valid range."""
        manager = ServerManager(mock_config)
        
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_sock.getsockname.return_value = ('localhost', 8000)
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            port = manager._find_available_port(start_port=8000, end_port=8010)
            
            assert 8000 <= port <= 8010
    
    def test_port_exhaustion(self, mock_config):
        """Test behavior when no ports are available."""
        manager = ServerManager(mock_config)
        
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_sock.bind.side_effect = OSError("No ports available")
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            with pytest.raises(PortConflictError, match="No available ports"):
                manager._find_available_port(start_port=8000, end_port=8000)