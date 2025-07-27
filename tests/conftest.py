"""
Pytest configuration and shared fixtures
"""

import pytest
import time
import os
import signal
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def cleanup_session():
    """Ensure clean state before and after test session"""
    # Cleanup any leftover servers from previous runs
    try:
        import syft_serve as ss
        ss.terminate_all()
    except Exception:
        pass
    
    yield
    
    # Final cleanup
    try:
        import syft_serve as ss
        ss.terminate_all()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def cleanup_test():
    """Ensure clean state for each test"""
    import syft_serve as ss
    
    # Record initial servers
    initial_servers = set(ss.servers)
    
    yield
    
    # Cleanup any servers created during test
    current_servers = set(ss.servers)
    new_servers = current_servers - initial_servers
    
    for server_name in new_servers:
        try:
            server = ss.servers[server_name]
            server.terminate()
        except Exception:
            pass
    
    # Extra cleanup attempt
    if len(ss.servers) > len(initial_servers):
        try:
            ss.terminate_all()
        except Exception:
            pass


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests"""
    return tmp_path


@pytest.fixture
def simple_endpoints():
    """Common set of simple endpoints for testing"""
    def hello():
        return {"message": "Hello, World!"}
    
    def echo(data: dict):
        return {"echo": data}
    
    def status():
        return {"status": "ok", "timestamp": time.time()}
    
    def error():
        raise ValueError("Test error")
    
    return {
        "/": hello,
        "/echo": echo,
        "/status": status,
        "/error": error
    }


@pytest.fixture
def slow_endpoint():
    """Endpoint that takes time to respond"""
    def slow():
        time.sleep(2)
        return {"slow": True}
    
    return slow


@pytest.fixture
def cpu_intensive_endpoint():
    """Endpoint that uses CPU"""
    def compute():
        # Simple CPU-intensive task
        result = sum(i**2 for i in range(1000000))
        return {"result": result}
    
    return compute


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (may take longer)"
    )
    config.addinivalue_line(
        "markers", 
        "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers",
        "windows_only: mark test to run only on Windows"
    )
    config.addinivalue_line(
        "markers",
        "posix_only: mark test to run only on POSIX systems"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on conditions"""
    for item in items:
        # Add markers based on test names
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        if "slow" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)
        
        # Skip platform-specific tests
        if "windows_only" in item.keywords and os.name != 'nt':
            item.add_marker(pytest.mark.skip(reason="Windows only test"))
        
        if "posix_only" in item.keywords and os.name == 'nt':
            item.add_marker(pytest.mark.skip(reason="POSIX only test"))


# Timeout for tests
pytest_timeout = 300  # 5 minutes default timeout