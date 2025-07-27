#!/usr/bin/env python3
"""
Test script to verify the public API when dependencies are available.
Run this after installing dependencies with: pip install -e ".[dev]"
"""

def test_public_api():
    """Test the public API when syft_serve can be imported."""
    try:
        import syft_serve as ss
        print("✓ syft_serve imported successfully")
        
        # Test syft_serve module public API
        public_attrs = [attr for attr in dir(ss) if not attr.startswith('_')]
        print(f"Public attributes: {sorted(public_attrs)}")
        
        expected_attrs = ['create', 'servers', 'terminate_all']
        assert sorted(public_attrs) == sorted(expected_attrs), (
            f"Expected {expected_attrs}, got {public_attrs}"
        )
        print("✓ syft_serve module public API is clean")
        
        # Test __all__ attribute
        assert hasattr(ss, '__all__'), "Should have __all__ defined"
        assert sorted(ss.__all__) == sorted(['servers', 'create', 'terminate_all']), (
            f"__all__ should be ['servers', 'create', 'terminate_all'], got {ss.__all__}"
        )
        print("✓ __all__ attribute is correct")
        
        # Test servers collection
        servers_attrs = [attr for attr in dir(ss.servers) if not attr.startswith('_')]
        print(f"Servers collection public attributes: {sorted(servers_attrs)}")
        
        # Should have minimal public API
        assert len(servers_attrs) <= 5, (
            f"Servers collection should have minimal public API, got {servers_attrs}"
        )
        print("✓ servers collection API is minimal")
        
        # Test create function
        assert callable(ss.create), "create should be callable"
        print("✓ create function is callable")
        
        # Test servers collection methods
        assert hasattr(ss.servers, '__len__'), "servers should support len()"
        assert hasattr(ss.servers, '__iter__'), "servers should support iteration"
        assert hasattr(ss.servers, '__getitem__'), "servers should support indexing"
        assert hasattr(ss.servers, '__contains__'), "servers should support 'in' operator"
        print("✓ servers collection has expected dunder methods")
        
        # Test that internal modules are not exposed
        internal_modules = [
            'api', 'config', 'endpoint_serializer', 'environment', 
            'exceptions', 'handle', 'log_stream', 'manager', 
            'process_discovery', 'server', 'server_collection'
        ]
        
        for module_name in internal_modules:
            assert not hasattr(ss, module_name), (
                f"Internal module '{module_name}' should not be accessible as syft_serve.{module_name}"
            )
        print("✓ Internal modules are properly hidden")
        
        print("\n🎉 All public API tests passed!")
        print("The public API is clean with only 'create', 'servers', and 'terminate_all' exposed.")
        
    except ImportError as e:
        print(f"⚠️  Could not import syft_serve: {e}")
        print("This is expected if dependencies are not installed.")
        print("Install with: pip install -e \".[dev]\"")
        return False
    
    return True

if __name__ == "__main__":
    test_public_api()