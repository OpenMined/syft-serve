"""
Tests for Environment functionality
"""

import pytest
from pathlib import Path

import syft_serve as ss


@pytest.fixture
def server_with_deps():
    """Create a server with specific dependencies"""
    server = ss.create(
        name="test_env_deps",
        endpoints={"/": lambda: {"test": True}},
        dependencies=["tabulate==0.9.0", "toml>=0.10.0"]
    )
    yield server
    server.terminate()


class TestEnvironment:
    """Test Environment class functionality"""
    
    def test_environment_list(self, server_with_deps):
        """Test listing packages in environment"""
        env = server_with_deps.env
        packages = env.list()
        
        assert isinstance(packages, list)
        assert len(packages) > 0
        
        # Check format is name==version
        for pkg in packages:
            assert "==" in pkg
            name, version = pkg.split("==", 1)
            assert len(name) > 0
            assert len(version) > 0
        
        # Check our dependencies are installed
        assert any("tabulate==0.9.0" in pkg for pkg in packages)
        assert any("toml" in pkg for pkg in packages)
    
    def test_environment_repr(self, server_with_deps):
        """Test environment string representation"""
        env = server_with_deps.env
        repr_str = repr(env)
        
        assert "Environment: test_env_deps" in repr_str
        assert "├──" in repr_str or "└──" in repr_str  # Tree characters
        
        # Should show some key packages if present
        if any("fastapi" in pkg for pkg in env.list()):
            assert "fastapi" in repr_str
    
    def test_environment_caching(self, server_with_deps):
        """Test that environment results are cached"""
        env = server_with_deps.env
        
        # First call
        packages1 = env.list()
        
        # Second call should use cache (fast)
        import time
        start = time.time()
        packages2 = env.list()
        duration = time.time() - start
        
        assert packages1 == packages2
        assert duration < 0.1  # Should be very fast due to cache
    
    def test_environment_empty(self):
        """Test environment with minimal dependencies"""
        server = ss.create(
            name="test_env_empty",
            endpoints={"/": lambda: {"test": True}},
            dependencies=[]  # No extra dependencies
        )
        
        try:
            env = server.env
            packages = env.list()
            
            # Should still have base packages (FastAPI, uvicorn, etc.)
            assert len(packages) > 0
            assert any("fastapi" in pkg for pkg in packages)
            assert any("uvicorn" in pkg for pkg in packages)
        finally:
            server.terminate()
    
    def test_environment_key_packages_display(self, server_with_deps):
        """Test that key packages are prioritized in display"""
        env = server_with_deps.env
        repr_str = repr(env)
        
        # If we have many packages, should show "and X more packages"
        packages = env.list()
        if len(packages) > 10:
            assert "more packages" in repr_str
    
    def test_environment_nonexistent_server(self):
        """Test environment for a path that doesn't exist"""
        from syft_serve._environment import Environment
        import tempfile
        
        # Create a temporary directory that we then remove
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_path = Path(tmpdir) / "nonexistent_server"
            fake_path.mkdir()
            # Now remove it to simulate non-existent
            import shutil
            shutil.rmtree(fake_path)
            
            env = Environment(fake_path)
            
            # Should return empty list
            packages = env.list()
            assert packages == []
            
            # Repr should indicate empty
            repr_str = repr(env)
            assert "(empty)" in repr_str