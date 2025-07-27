"""Tests for custom exceptions."""

import pytest

from syft_serve._exceptions import (
    SyftServeError,
    DuplicateServerError,
    ServerStartupError,
    ServerNotFoundError,
    PortConflictError,
    ProcessTerminationError,
)


class TestSyftServeError:
    """Test the base SyftServeError exception."""

    def test_base_exception_creation(self):
        """Test creating base exception."""
        error = SyftServeError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_base_exception_inheritance(self):
        """Test that all custom exceptions inherit from SyftServeError."""
        assert issubclass(DuplicateServerError, SyftServeError)
        assert issubclass(ServerStartupError, SyftServeError)
        assert issubclass(ServerNotFoundError, SyftServeError)
        assert issubclass(PortConflictError, SyftServeError)
        assert issubclass(ProcessTerminationError, SyftServeError)


class TestDuplicateServerError:
    """Test DuplicateServerError exception."""

    def test_duplicate_server_error(self):
        """Test DuplicateServerError creation and message."""
        server_name = "test_server"
        error = DuplicateServerError(f"Server '{server_name}' already exists")

        assert "test_server" in str(error)
        assert "already exists" in str(error)
        assert isinstance(error, SyftServeError)

    def test_duplicate_server_error_with_details(self):
        """Test DuplicateServerError with additional details."""
        error = DuplicateServerError(
            "Server 'api_server' already exists on port 8000. Use force=True to replace."
        )

        assert "api_server" in str(error)
        assert "8000" in str(error)
        assert "force=True" in str(error)


class TestServerStartupError:
    """Test ServerStartupError exception."""

    def test_server_startup_error(self):
        """Test ServerStartupError creation and message."""
        error = ServerStartupError("Failed to start server within timeout")

        assert "Failed to start" in str(error)
        assert "timeout" in str(error)
        assert isinstance(error, SyftServeError)

    def test_server_startup_error_with_details(self):
        """Test ServerStartupError with server details."""
        error = ServerStartupError("Server 'ml_api' failed to start on port 8001 after 30 seconds")

        assert "ml_api" in str(error)
        assert "8001" in str(error)
        assert "30 seconds" in str(error)


class TestServerNotFoundError:
    """Test ServerNotFoundError exception."""

    def test_server_not_found_error(self):
        """Test ServerNotFoundError creation and message."""
        error = ServerNotFoundError("Server 'unknown_server' not found")

        assert "unknown_server" in str(error)
        assert "not found" in str(error)
        assert isinstance(error, SyftServeError)

    def test_server_not_found_error_with_suggestions(self):
        """Test ServerNotFoundError with helpful suggestions."""
        error = ServerNotFoundError(
            "Server 'api' not found. Available servers: ['data_api', 'ml_api']"
        )

        assert "api" in str(error)
        assert "Available servers" in str(error)
        assert "data_api" in str(error)


class TestPortConflictError:
    """Test PortConflictError exception."""

    def test_port_conflict_error(self):
        """Test PortConflictError creation and message."""
        error = PortConflictError("Port 8000 is already in use")

        assert "8000" in str(error)
        assert "already in use" in str(error)
        assert isinstance(error, SyftServeError)

    def test_port_conflict_error_with_range(self):
        """Test PortConflictError with port range information."""
        error = PortConflictError("No available ports in range 8000-8010. All ports are in use.")

        assert "8000-8010" in str(error)
        assert "No available ports" in str(error)


class TestProcessTerminationError:
    """Test ProcessTerminationError exception."""

    def test_process_termination_error(self):
        """Test ProcessTerminationError creation and message."""
        error = ProcessTerminationError("Failed to terminate process 12345")

        assert "12345" in str(error)
        assert "Failed to terminate" in str(error)
        assert isinstance(error, SyftServeError)

    def test_process_termination_error_with_reason(self):
        """Test ProcessTerminationError with termination reason."""
        error = ProcessTerminationError("Process 12345 could not be terminated: Permission denied")

        assert "12345" in str(error)
        assert "Permission denied" in str(error)


class TestExceptionRaising:
    """Test that exceptions can be properly raised and caught."""

    def test_raise_and_catch_duplicate_server_error(self):
        """Test raising and catching DuplicateServerError."""
        with pytest.raises(DuplicateServerError) as exc_info:
            raise DuplicateServerError("Test duplicate server")

        assert "Test duplicate server" in str(exc_info.value)
        assert isinstance(exc_info.value, SyftServeError)

    def test_raise_and_catch_server_startup_error(self):
        """Test raising and catching ServerStartupError."""
        with pytest.raises(ServerStartupError) as exc_info:
            raise ServerStartupError("Test startup failure")

        assert "Test startup failure" in str(exc_info.value)

    def test_catch_base_exception(self):
        """Test catching specific exceptions as base SyftServeError."""
        with pytest.raises(SyftServeError):
            raise DuplicateServerError("This is a duplicate server error")

        with pytest.raises(SyftServeError):
            raise ServerStartupError("This is a startup error")

    def test_exception_chaining(self):
        """Test exception chaining with custom exceptions."""
        original_error = ValueError("Original error")

        with pytest.raises(ServerStartupError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise ServerStartupError("Server failed to start") from e

        assert exc_info.value.__cause__ is original_error


class TestExceptionAttributes:
    """Test exception attributes and properties."""

    def test_exception_has_args(self):
        """Test that exceptions properly store arguments."""
        message = "Test error message"
        error = SyftServeError(message)

        assert error.args == (message,)
        assert len(error.args) == 1

    def test_exception_multiple_args(self):
        """Test exceptions with multiple arguments."""
        error = ServerStartupError("Startup failed", "Port 8000", "Timeout 30s")

        assert len(error.args) == 3
        assert error.args[0] == "Startup failed"
        assert error.args[1] == "Port 8000"
        assert error.args[2] == "Timeout 30s"

    def test_exception_repr(self):
        """Test exception representation."""
        error = DuplicateServerError("Test message")
        repr_str = repr(error)

        assert "DuplicateServerError" in repr_str
        assert "Test message" in repr_str


class TestExceptionDocstrings:
    """Test that exceptions have proper docstrings."""

    def test_all_exceptions_have_docstrings(self):
        """Test that all exception classes have docstrings."""
        exceptions = [
            SyftServeError,
            DuplicateServerError,
            ServerStartupError,
            ServerNotFoundError,
            PortConflictError,
            ProcessTerminationError,
        ]

        for exc_class in exceptions:
            assert exc_class.__doc__ is not None
            assert len(exc_class.__doc__.strip()) > 0, f"{exc_class.__name__} missing docstring"
