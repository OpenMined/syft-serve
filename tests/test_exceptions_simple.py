"""Tests for custom exceptions."""
import pytest

from syft_serve.exceptions import (
    ServerNotFoundError,
    ServerAlreadyExistsError,
    PortInUseError,
    ServerStartupError,
    ServerShutdownError
)


class TestServerNotFoundError:
    """Test ServerNotFoundError exception."""
    
    def test_server_not_found_error(self):
        """Test ServerNotFoundError creation and message."""
        error = ServerNotFoundError("Server 'unknown_server' not found")
        
        assert "unknown_server" in str(error)
        assert "not found" in str(error)
        assert isinstance(error, Exception)


class TestServerAlreadyExistsError:
    """Test ServerAlreadyExistsError exception."""
    
    def test_server_already_exists_error(self):
        """Test ServerAlreadyExistsError creation and message."""
        server_name = "test_server"
        error = ServerAlreadyExistsError(f"Server '{server_name}' already exists")
        
        assert "test_server" in str(error)
        assert "already exists" in str(error)
        assert isinstance(error, Exception)


class TestPortInUseError:
    """Test PortInUseError exception."""
    
    def test_port_in_use_error(self):
        """Test PortInUseError creation and message."""
        error = PortInUseError("Port 8000 is already in use")
        
        assert "8000" in str(error)
        assert "already in use" in str(error)
        assert isinstance(error, Exception)


class TestServerStartupError:
    """Test ServerStartupError exception."""
    
    def test_server_startup_error(self):
        """Test ServerStartupError creation and message."""
        error = ServerStartupError("Failed to start server within timeout")
        
        assert "Failed to start" in str(error)
        assert "timeout" in str(error)
        assert isinstance(error, Exception)


class TestServerShutdownError:
    """Test ServerShutdownError exception."""
    
    def test_server_shutdown_error(self):
        """Test ServerShutdownError creation and message."""
        error = ServerShutdownError("Failed to terminate process 12345")
        
        assert "12345" in str(error)
        assert "Failed to terminate" in str(error)
        assert isinstance(error, Exception)


class TestExceptionRaising:
    """Test that exceptions can be properly raised and caught."""
    
    def test_raise_and_catch_server_not_found_error(self):
        """Test raising and catching ServerNotFoundError."""
        with pytest.raises(ServerNotFoundError) as exc_info:
            raise ServerNotFoundError("Test server not found")
        
        assert "Test server not found" in str(exc_info.value)
    
    def test_raise_and_catch_server_startup_error(self):
        """Test raising and catching ServerStartupError."""
        with pytest.raises(ServerStartupError) as exc_info:
            raise ServerStartupError("Test startup failure")
        
        assert "Test startup failure" in str(exc_info.value)
    
    def test_exception_inheritance(self):
        """Test that all custom exceptions inherit from Exception."""
        exceptions = [
            ServerNotFoundError,
            ServerAlreadyExistsError,
            PortInUseError,
            ServerStartupError,
            ServerShutdownError
        ]
        
        for exc_class in exceptions:
            assert issubclass(exc_class, Exception)
    
    def test_exception_chaining(self):
        """Test exception chaining with custom exceptions."""
        original_error = ValueError("Original error")
        
        with pytest.raises(ServerStartupError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise ServerStartupError("Server failed to start") from e
        
        assert exc_info.value.__cause__ is original_error