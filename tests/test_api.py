"""Tests for the main API module."""

import pytest
from unittest.mock import Mock, patch

from syft_serve import _api as api
from syft_serve._exceptions import ServerStartupError, DuplicateServerError
from syft_serve._server import Server


class TestCreateFunction:
    """Test the create() function."""

    def test_create_simple_server(self, sample_endpoints, mock_config):
        """Test creating a simple server."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_server = Mock(spec=Server)
            mock_server.name = "test_server"
            mock_server.url = "http://localhost:8000"

            mock_manager.create_server.return_value = mock_server
            mock_manager_class.return_value = mock_manager

            result = api.create(name="test_server", endpoints=sample_endpoints)

            assert result == mock_server
            mock_manager.create_server.assert_called_once_with(
                name="test_server", endpoints=sample_endpoints, dependencies=None, force=False
            )

    def test_create_server_with_dependencies(self, sample_endpoints):
        """Test creating a server with dependencies."""
        dependencies = ["pandas", "numpy"]

        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_server = Mock(spec=Server)
            mock_manager.create_server.return_value = mock_server
            mock_manager_class.return_value = mock_manager

            api.create(name="test_server", endpoints=sample_endpoints, dependencies=dependencies)

            mock_manager.create_server.assert_called_once_with(
                name="test_server",
                endpoints=sample_endpoints,
                dependencies=dependencies,
                force=False,
            )

    def test_create_server_with_force(self, sample_endpoints):
        """Test creating a server with force=True."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_server = Mock(spec=Server)
            mock_manager.create_server.return_value = mock_server
            mock_manager_class.return_value = mock_manager

            api.create(name="test_server", endpoints=sample_endpoints, force=True)

            mock_manager.create_server.assert_called_once_with(
                name="test_server", endpoints=sample_endpoints, dependencies=None, force=True
            )

    def test_create_server_duplicate_error(self, sample_endpoints):
        """Test creating a server that already exists without force."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_manager.create_server.side_effect = DuplicateServerError("Server already exists")
            mock_manager_class.return_value = mock_manager

            with pytest.raises(DuplicateServerError):
                api.create(name="test_server", endpoints=sample_endpoints)

    def test_create_server_startup_error(self, sample_endpoints):
        """Test server startup failure."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_manager.create_server.side_effect = ServerStartupError("Failed to start")
            mock_manager_class.return_value = mock_manager

            with pytest.raises(ServerStartupError):
                api.create(name="test_server", endpoints=sample_endpoints)

    def test_create_validates_name(self, sample_endpoints):
        """Test that create validates server name."""
        with pytest.raises(ValueError, match="Server name cannot be empty"):
            api.create(name="", endpoints=sample_endpoints)

        with pytest.raises(ValueError, match="Server name cannot be empty"):
            api.create(name=None, endpoints=sample_endpoints)

    def test_create_validates_endpoints(self):
        """Test that create validates endpoints."""
        with pytest.raises(ValueError, match="Endpoints cannot be empty"):
            api.create(name="test", endpoints={})

        with pytest.raises(ValueError, match="Endpoints cannot be empty"):
            api.create(name="test", endpoints=None)


class TestTerminateAllFunction:
    """Test the terminate_all() function."""

    def test_terminate_all_success(self):
        """Test successful termination of all servers."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager

            api.terminate_all()

            mock_manager.terminate_all.assert_called_once()

    def test_terminate_all_with_exception(self):
        """Test terminate_all handles exceptions gracefully."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_manager.terminate_all.side_effect = Exception("Termination failed")
            mock_manager_class.return_value = mock_manager

            # Should not raise exception, but log it
            with patch("syft_serve._api.logger") as mock_logger:
                api.terminate_all()
                mock_logger.error.assert_called_once()


class TestServersProperty:
    """Test the servers property."""

    def test_servers_property(self):
        """Test that servers property returns ServerCollection."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_collection = Mock()
            mock_manager.servers = mock_collection
            mock_manager_class.return_value = mock_manager

            result = api.servers

            assert result == mock_collection

    def test_servers_property_caching(self):
        """Test that servers property uses the same manager instance."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_collection = Mock()
            mock_manager.servers = mock_collection
            mock_manager_class.return_value = mock_manager

            # Call multiple times
            result1 = api.servers
            result2 = api.servers

            # Should only create manager once
            assert mock_manager_class.call_count == 1
            assert result1 == result2


class TestModuleImports:
    """Test module imports and exports."""

    def test_api_exports(self):
        """Test that api module exports expected functions."""
        assert hasattr(api, "create")
        assert hasattr(api, "terminate_all")
        assert hasattr(api, "servers")

        assert callable(api.create)
        assert callable(api.terminate_all)

    def test_api_docstrings(self):
        """Test that API functions have docstrings."""
        assert api.create.__doc__ is not None
        assert api.terminate_all.__doc__ is not None
        assert len(api.create.__doc__.strip()) > 0
        assert len(api.terminate_all.__doc__.strip()) > 0


class TestAPIIntegration:
    """Integration tests for the API."""

    @pytest.mark.integration
    def test_create_and_terminate_flow(self, sample_endpoints):
        """Test the complete create and terminate flow."""
        with patch("syft_serve._api.ServerManager") as mock_manager_class:
            mock_manager = Mock()
            mock_server = Mock(spec=Server)
            mock_server.name = "integration_test"
            mock_server.url = "http://localhost:8000"

            mock_manager.create_server.return_value = mock_server
            mock_manager_class.return_value = mock_manager

            # Create server
            server = api.create(name="integration_test", endpoints=sample_endpoints)

            assert server.name == "integration_test"

            # Terminate all
            api.terminate_all()

            mock_manager.create_server.assert_called_once()
            mock_manager.terminate_all.assert_called_once()


class TestErrorHandling:
    """Test error handling in API functions."""

    def test_create_with_invalid_endpoint_type(self):
        """Test create with invalid endpoint type."""
        with pytest.raises(TypeError):
            api.create(name="test", endpoints="not_a_dict")

    def test_create_with_non_callable_endpoint(self):
        """Test create with non-callable endpoint."""
        with pytest.raises(ValueError, match="All endpoint values must be callable"):
            api.create(name="test", endpoints={"/test": "not_callable"})

    def test_create_with_invalid_dependencies_type(self, sample_endpoints):
        """Test create with invalid dependencies type."""
        with pytest.raises(TypeError):
            api.create(name="test", endpoints=sample_endpoints, dependencies="not_a_list")
