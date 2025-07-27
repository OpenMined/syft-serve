"""Tests for the ServerCollection class."""

import pytest
from unittest.mock import Mock, patch

from syft_serve._server_collection import ServerCollection
from syft_serve._server import Server


class TestServerCollection:
    """Test the ServerCollection class."""

    def test_collection_initialization(self, mock_config):
        """Test collection initialization."""
        collection = ServerCollection(mock_config)
        assert collection.config == mock_config
        assert len(collection) == 0

    def test_add_server(self, mock_config, mock_server):
        """Test adding a server to the collection."""
        collection = ServerCollection(mock_config)

        collection.add_server(mock_server)

        assert len(collection) == 1
        assert collection.get_server("test_server") == mock_server

    def test_remove_server(self, mock_config, mock_server):
        """Test removing a server from the collection."""
        collection = ServerCollection(mock_config)
        collection.add_server(mock_server)

        removed_server = collection.remove_server("test_server")

        assert removed_server == mock_server
        assert len(collection) == 0

    def test_remove_nonexistent_server(self, mock_config):
        """Test removing a server that doesn't exist."""
        collection = ServerCollection(mock_config)

        result = collection.remove_server("nonexistent")
        assert result is None

    def test_get_server_by_name(self, mock_config, mock_server):
        """Test getting server by name."""
        collection = ServerCollection(mock_config)
        collection.add_server(mock_server)

        retrieved_server = collection.get_server("test_server")
        assert retrieved_server == mock_server

    def test_get_nonexistent_server(self, mock_config):
        """Test getting server that doesn't exist."""
        collection = ServerCollection(mock_config)

        result = collection.get_server("nonexistent")
        assert result is None

    def test_list_servers(self, mock_config):
        """Test listing all servers."""
        collection = ServerCollection(mock_config)

        # Create multiple mock servers
        server1 = Mock(spec=Server)
        server1.name = "server1"
        server2 = Mock(spec=Server)
        server2.name = "server2"

        collection.add_server(server1)
        collection.add_server(server2)

        servers = collection.list_servers()
        assert len(servers) == 2
        assert server1 in servers
        assert server2 in servers

    def test_clear_servers(self, mock_config, mock_server):
        """Test clearing all servers."""
        collection = ServerCollection(mock_config)
        collection.add_server(mock_server)

        assert len(collection) == 1

        collection.clear_servers()

        assert len(collection) == 0

    def test_contains_server(self, mock_config, mock_server):
        """Test checking if server exists in collection."""
        collection = ServerCollection(mock_config)

        assert "test_server" not in collection

        collection.add_server(mock_server)

        assert "test_server" in collection

    def test_iteration(self, mock_config):
        """Test iterating over servers."""
        collection = ServerCollection(mock_config)

        server1 = Mock(spec=Server)
        server1.name = "server1"
        server2 = Mock(spec=Server)
        server2.name = "server2"

        collection.add_server(server1)
        collection.add_server(server2)

        servers = list(collection)
        assert len(servers) == 2
        assert server1 in servers
        assert server2 in servers

    def test_getitem_by_name(self, mock_config, mock_server):
        """Test accessing server by name using []."""
        collection = ServerCollection(mock_config)
        collection.add_server(mock_server)

        retrieved_server = collection["test_server"]
        assert retrieved_server == mock_server

    def test_getitem_by_index(self, mock_config):
        """Test accessing server by index using []."""
        collection = ServerCollection(mock_config)

        server1 = Mock(spec=Server)
        server1.name = "server1"
        server2 = Mock(spec=Server)
        server2.name = "server2"

        collection.add_server(server1)
        collection.add_server(server2)

        # Test index access
        assert collection[0] == server1
        assert collection[1] == server2

    def test_getitem_invalid_key(self, mock_config):
        """Test accessing server with invalid key."""
        collection = ServerCollection(mock_config)

        with pytest.raises(KeyError):
            _ = collection["nonexistent"]

        with pytest.raises(IndexError):
            _ = collection[5]

    def test_repr(self, mock_config):
        """Test string representation of collection."""
        collection = ServerCollection(mock_config)

        repr_str = repr(collection)
        assert "ServerCollection" in repr_str
        assert "0 servers" in repr_str

        # Add a server
        server = Mock(spec=Server)
        server.name = "test"
        collection.add_server(server)

        repr_str = repr(collection)
        assert "1 servers" in repr_str


class TestServerPersistence:
    """Test server persistence functionality."""

    def test_save_servers(self, mock_config, temp_dir):
        """Test saving servers to disk."""
        mock_config.servers_dir = temp_dir
        collection = ServerCollection(mock_config)

        # Create a mock server
        server = Mock(spec=Server)
        server.name = "test_server"
        server.port = 8000
        server.pid = 12345
        server.to_dict.return_value = {"name": "test_server", "port": 8000, "pid": 12345}

        collection.add_server(server)
        collection.save_servers()

        # Check that file was created
        servers_file = temp_dir / "servers.json"
        assert servers_file.exists()

    def test_load_servers(self, mock_config, temp_dir):
        """Test loading servers from disk."""
        mock_config.servers_dir = temp_dir

        # Create a servers.json file
        servers_file = temp_dir / "servers.json"
        servers_data = [{"name": "test_server", "port": 8000, "pid": 12345}]

        import json

        servers_file.write_text(json.dumps(servers_data))

        collection = ServerCollection(mock_config)

        with patch("syft_serve._server_collection.Server") as mock_server_class:
            mock_server = Mock(spec=Server)
            mock_server.name = "test_server"
            mock_server_class.from_dict.return_value = mock_server

            collection.load_servers()

            assert len(collection) == 1
            assert collection.get_server("test_server") == mock_server

    def test_load_servers_no_file(self, mock_config, temp_dir):
        """Test loading servers when no file exists."""
        mock_config.servers_dir = temp_dir
        collection = ServerCollection(mock_config)

        # Should not raise exception
        collection.load_servers()
        assert len(collection) == 0

    def test_load_servers_invalid_json(self, mock_config, temp_dir):
        """Test loading servers with invalid JSON."""
        mock_config.servers_dir = temp_dir

        servers_file = temp_dir / "servers.json"
        servers_file.write_text("invalid json")

        collection = ServerCollection(mock_config)

        # Should handle gracefully
        collection.load_servers()
        assert len(collection) == 0


class TestServerDisplay:
    """Test server display functionality."""

    def test_display_empty_collection(self, mock_config):
        """Test displaying empty collection."""
        collection = ServerCollection(mock_config)

        # Should not raise exception
        display_result = collection._display()
        assert display_result is not None

    def test_display_with_servers(self, mock_config):
        """Test displaying collection with servers."""
        collection = ServerCollection(mock_config)

        # Create mock servers
        server1 = Mock(spec=Server)
        server1.name = "server1"
        server1.port = 8000
        server1.status = "running"
        server1.endpoints = ["/hello"]
        server1.uptime = "5m 30s"
        server1.pid = 12345

        server2 = Mock(spec=Server)
        server2.name = "server2"
        server2.port = 8001
        server2.status = "running"
        server2.endpoints = ["/goodbye"]
        server2.uptime = "2m 15s"
        server2.pid = 12346

        collection.add_server(server1)
        collection.add_server(server2)

        display_result = collection._display()
        assert display_result is not None

    @patch("syft_serve._server_collection.tabulate")
    def test_display_table_format(self, mock_tabulate, mock_config):
        """Test that display uses correct table format."""
        collection = ServerCollection(mock_config)

        server = Mock(spec=Server)
        server.name = "test"
        server.port = 8000
        server.status = "running"
        server.endpoints = ["/test"]
        server.uptime = "1m 0s"
        server.pid = 12345

        collection.add_server(server)
        collection._display()

        # Verify tabulate was called with correct format
        mock_tabulate.assert_called_once()
        args, kwargs = mock_tabulate.call_args
        assert "headers" in kwargs
        assert "tablefmt" in kwargs


class TestServerCollectionEdgeCases:
    """Test edge cases and error conditions."""

    def test_add_duplicate_server(self, mock_config):
        """Test adding server with duplicate name."""
        collection = ServerCollection(mock_config)

        server1 = Mock(spec=Server)
        server1.name = "duplicate"

        server2 = Mock(spec=Server)
        server2.name = "duplicate"

        collection.add_server(server1)

        # Adding duplicate should replace
        collection.add_server(server2)

        assert len(collection) == 1
        assert collection.get_server("duplicate") == server2

    def test_add_none_server(self, mock_config):
        """Test adding None as server."""
        collection = ServerCollection(mock_config)

        with pytest.raises(ValueError, match="Server cannot be None"):
            collection.add_server(None)

    def test_add_invalid_server(self, mock_config):
        """Test adding invalid server object."""
        collection = ServerCollection(mock_config)

        with pytest.raises(TypeError, match="Expected Server instance"):
            collection.add_server("not_a_server")

    def test_negative_index_access(self, mock_config, mock_server):
        """Test negative index access."""
        collection = ServerCollection(mock_config)
        collection.add_server(mock_server)

        # Should support negative indexing
        assert collection[-1] == mock_server

    def test_slice_access(self, mock_config):
        """Test slice access."""
        collection = ServerCollection(mock_config)

        servers = []
        for i in range(3):
            server = Mock(spec=Server)
            server.name = f"server{i}"
            servers.append(server)
            collection.add_server(server)

        # Test slicing
        sliced = collection[0:2]
        assert len(sliced) == 2
        assert sliced[0] == servers[0]
        assert sliced[1] == servers[1]


class TestServerCollectionIntegration:
    """Integration tests for ServerCollection."""

    def test_full_lifecycle(self, mock_config, temp_dir):
        """Test complete server lifecycle in collection."""
        mock_config.servers_dir = temp_dir
        collection = ServerCollection(mock_config)

        # Create and add server
        server = Mock(spec=Server)
        server.name = "lifecycle_test"
        server.port = 8000
        server.pid = 12345
        server.to_dict.return_value = {"name": "lifecycle_test", "port": 8000, "pid": 12345}

        # Add server
        collection.add_server(server)
        assert "lifecycle_test" in collection

        # Save to disk
        collection.save_servers()

        # Create new collection and load
        new_collection = ServerCollection(mock_config)

        with patch("syft_serve._server_collection.Server") as mock_server_class:
            mock_loaded_server = Mock(spec=Server)
            mock_loaded_server.name = "lifecycle_test"
            mock_server_class.from_dict.return_value = mock_loaded_server

            new_collection.load_servers()

            assert len(new_collection) == 1
            assert "lifecycle_test" in new_collection

        # Remove server
        removed = new_collection.remove_server("lifecycle_test")
        assert removed is not None
        assert len(new_collection) == 0
