"""Test to ensure public API remains stable and clean."""
import pytest
from unittest.mock import Mock, patch, MagicMock

try:
    import syft_serve as ss
    SYFT_SERVE_AVAILABLE = True
except ImportError as e:
    SYFT_SERVE_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not SYFT_SERVE_AVAILABLE, reason=f"syft_serve import failed: {IMPORT_ERROR if not SYFT_SERVE_AVAILABLE else ''}")
class TestPublicAPI:
    """Test the public API to ensure it remains clean and stable."""
    
    def test_syft_serve_module_public_api(self):
        """Test that syft_serve module only exposes expected public attributes."""
        # Get all non-private attributes (not starting with _)
        public_attrs = [attr for attr in dir(ss) if not attr.startswith('_')]
        
        # Expected public API for syft_serve module
        expected_attrs = [
            'create',
            'servers',
        ]
        
        # Sort for consistent comparison
        public_attrs.sort()
        expected_attrs.sort()
        
        assert public_attrs == expected_attrs, (
            f"Public API mismatch!\n"
            f"Expected: {expected_attrs}\n"
            f"Actual: {public_attrs}\n"
            f"Extra: {set(public_attrs) - set(expected_attrs)}\n"
            f"Missing: {set(expected_attrs) - set(public_attrs)}"
        )
    
    def test_servers_collection_public_api(self):
        """Test that servers collection only exposes expected public attributes."""
        # Get public attributes of the servers collection
        public_attrs = [attr for attr in dir(ss.servers) if not attr.startswith('_')]
        
        # Expected public API for ServerCollection
        expected_attrs = [
            'terminate_all',  # Method to terminate all servers
        ]
        
        # Sort for consistent comparison
        public_attrs.sort()
        expected_attrs.sort()
        
        assert public_attrs == expected_attrs, (
            f"ServerCollection public API mismatch!\n"
            f"Expected: {expected_attrs}\n"
            f"Actual: {public_attrs}\n"
            f"Extra: {set(public_attrs) - set(expected_attrs)}\n"
            f"Missing: {set(expected_attrs) - set(public_attrs)}"
        )
    
    @patch('syft_serve._manager.ServerManager')
    def test_server_instance_public_api(self, mock_manager_class):
        """Test that Server instances only expose expected public attributes."""
        # Mock the manager and create a test server
        mock_manager = Mock()
        mock_handle = Mock()
        mock_handle.name = "test_server"
        mock_handle.port = 8000
        mock_handle.pid = 12345
        mock_handle.status = "running"
        mock_handle.url = "http://localhost:8000"
        mock_handle.endpoints = ["/test"]
        
        mock_manager.create_server.return_value = mock_handle
        mock_manager_class.return_value = mock_manager
        
        # Create a server instance
        with patch('syft_serve._api._get_manager', return_value=mock_manager):
            server = ss.create(
                name="test_server",
                endpoints={"/test": lambda: {"message": "test"}}
            )
            
            # Get public attributes of the server instance
            public_attrs = [attr for attr in dir(server) if not attr.startswith('_')]
            
            # Expected public API for Server instances
            expected_attrs = [
                'endpoints',
                'env',
                'name', 
                'pid',
                'port',
                'status',
                'stderr',
                'stdout',
                'terminate',
                'uptime',
                'url',
            ]
            
            # Sort for consistent comparison
            public_attrs.sort()
            expected_attrs.sort()
            
            assert public_attrs == expected_attrs, (
                f"Server instance public API mismatch!\n"
                f"Expected: {expected_attrs}\n"
                f"Actual: {public_attrs}\n"
                f"Extra: {set(public_attrs) - set(expected_attrs)}\n"
                f"Missing: {set(expected_attrs) - set(public_attrs)}"
            )
    
    def test_syft_serve_all_attribute(self):
        """Test that __all__ contains exactly what we expect."""
        assert hasattr(ss, '__all__'), "syft_serve module should have __all__ defined"
        
        expected_all = ['servers', 'create']
        actual_all = sorted(ss.__all__)
        expected_all = sorted(expected_all)
        
        assert actual_all == expected_all, (
            f"__all__ mismatch!\n"
            f"Expected: {expected_all}\n"
            f"Actual: {actual_all}"
        )
    
    def test_no_internal_modules_exposed(self):
        """Test that internal modules are not exposed in the public API."""
        # These modules should NOT be accessible via syft_serve.module_name
        internal_modules = [
            'api', 'config', 'endpoint_serializer', 'environment', 
            'exceptions', 'handle', 'log_stream', 'manager', 
            'process_discovery', 'server', 'server_collection'
        ]
        
        for module_name in internal_modules:
            assert not hasattr(ss, module_name), (
                f"Internal module '{module_name}' should not be accessible as syft_serve.{module_name}"
            )
    
    def test_create_function_exists_and_callable(self):
        """Test that create function exists and is callable."""
        assert hasattr(ss, 'create'), "syft_serve should have 'create' function"
        assert callable(ss.create), "syft_serve.create should be callable"
    
    def test_servers_collection_exists(self):
        """Test that servers collection exists and has expected behavior."""
        assert hasattr(ss, 'servers'), "syft_serve should have 'servers' collection"
        
        # Test that it behaves like a collection (has __len__, __iter__, __getitem__)
        assert hasattr(ss.servers, '__len__'), "servers should support len()"
        assert hasattr(ss.servers, '__iter__'), "servers should support iteration"
        assert hasattr(ss.servers, '__getitem__'), "servers should support indexing"
        assert hasattr(ss.servers, '__contains__'), "servers should support 'in' operator"
        
        # Test that it has terminate_all method
        assert hasattr(ss.servers, 'terminate_all'), "servers should have terminate_all method"
        assert callable(ss.servers.terminate_all), "servers.terminate_all should be callable"


class TestPublicAPIStructure:
    """Test the public API structure without requiring full imports."""
    
    def test_init_file_structure(self):
        """Test that __init__.py has the correct structure."""
        import os
        
        # Get the path to the syft_serve package
        package_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'syft_serve')
        init_file = os.path.join(package_dir, '__init__.py')
        
        assert os.path.exists(init_file), "__init__.py should exist"
        
        with open(init_file, 'r') as f:
            content = f.read()
        
        # Check that __all__ is defined and contains only expected items
        assert '__all__ = [' in content, "__all__ should be defined"
        assert '"servers"' in content, "__all__ should contain 'servers'"
        assert '"create"' in content, "__all__ should contain 'create'"
        
        # Check that we're importing from _api (underscore-prefixed module)
        assert 'from ._api import servers, create' in content, "Should import from _api module"
        
        # Check that we're not importing old module names
        bad_imports = ['from .api import', 'from .manager import', 'from .server import']
        for bad_import in bad_imports:
            assert bad_import not in content, f"Should not have '{bad_import}' in __init__.py"
    
    def test_internal_modules_renamed(self):
        """Test that internal modules are properly renamed with underscores."""
        import os
        
        package_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'syft_serve')
        
        # These files should exist with underscore prefixes
        expected_files = [
            '_api.py', '_config.py', '_endpoint_serializer.py', '_environment.py',
            '_exceptions.py', '_handle.py', '_log_stream.py', '_manager.py',
            '_process_discovery.py', '_server.py', '_server_collection.py'
        ]
        
        for filename in expected_files:
            filepath = os.path.join(package_dir, filename)
            assert os.path.exists(filepath), f"Expected internal module {filename} should exist"
        
        # These files should NOT exist (old names without underscores)
        old_files = [
            'api.py', 'config.py', 'endpoint_serializer.py', 'environment.py',
            'exceptions.py', 'handle.py', 'log_stream.py', 'manager.py',
            'process_discovery.py', 'server.py', 'server_collection.py'
        ]
        
        for filename in old_files:
            filepath = os.path.join(package_dir, filename)
            assert not os.path.exists(filepath), f"Old module {filename} should not exist"