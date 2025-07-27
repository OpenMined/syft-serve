"""
Tests for LogStream functionality
"""

import pytest
import time
from pathlib import Path
import tempfile

import syft_serve as ss


@pytest.fixture
def test_server():
    """Create a test server that generates logs"""
    def logging_endpoint():
        import logging
        logger = logging.getLogger("uvicorn.access")
        return {"message": "Log test"}
    
    server = ss.create(
        name="test_logs",
        endpoints={"/log": logging_endpoint}
    )
    yield server
    server.terminate()


class TestLogStream:
    """Test LogStream methods"""
    
    def test_log_tail(self, test_server):
        """Test tail method"""
        # Generate some log entries
        import requests
        for i in range(5):
            requests.get(f"{test_server.url}/log")
        
        time.sleep(1)  # Wait for logs to be written
        
        # Test tail
        logs = test_server.stdout.tail(10)
        assert isinstance(logs, str)
        assert len(logs) > 0
    
    def test_log_head(self, test_server):
        """Test head method"""
        # Generate some log entries
        import requests
        requests.get(f"{test_server.url}/log")
        
        time.sleep(1)
        
        # Test head
        logs = test_server.stdout.head(5)
        assert isinstance(logs, str)
        # Should contain startup messages
        assert "Uvicorn running" in logs or "Started" in logs
    
    def test_log_search(self, test_server):
        """Test search method"""
        # Generate specific log entry
        import requests
        requests.get(f"{test_server.url}/log")
        
        time.sleep(1)
        
        # Search for GET request
        results = test_server.stdout.search("GET")
        assert isinstance(results, list)
        assert len(results) > 0
        assert all("GET" in line for line in results)
    
    def test_log_follow(self, test_server):
        """Test follow method (generator)"""
        # Get follow generator
        follower = test_server.stdout.follow()
        
        # Generate a log entry
        import requests
        requests.get(f"{test_server.url}/log")
        
        # Read from follower (with timeout to prevent hanging)
        lines = []
        start_time = time.time()
        for line in follower:
            lines.append(line)
            if len(lines) >= 1 or (time.time() - start_time) > 2:
                break
        
        assert len(lines) >= 1
    
    def test_log_empty_file(self):
        """Test handling of empty log file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            log_path = Path(f.name)
        
        from syft_serve._log_stream import LogStream
        stream = LogStream(log_path, "test")
        
        # Should handle empty file gracefully
        assert stream.tail(10) == ""
        assert stream.head(10) == ""
        assert stream.search("test") == []
        
        # Cleanup
        log_path.unlink()
    
    def test_log_repr(self, test_server):
        """Test LogStream representation"""
        repr_str = repr(test_server.stdout)
        assert "LogStream" in repr_str
        assert "stdout" in repr_str
    
    def test_stderr_logs(self, test_server):
        """Test stderr log stream"""
        # stderr might be empty, but methods should still work
        stderr_tail = test_server.stderr.tail(10)
        assert isinstance(stderr_tail, str)
        
        stderr_search = test_server.stderr.search("ERROR")
        assert isinstance(stderr_search, list)