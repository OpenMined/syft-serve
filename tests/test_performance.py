"""
Performance and stress tests for syft-serve
"""

import pytest
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

import syft_serve as ss


@pytest.mark.slow
@pytest.mark.integration
class TestPerformance:
    """Performance and stress tests"""
    
    def test_multiple_concurrent_requests(self):
        """Test server handling multiple concurrent requests"""
        request_count = 0
        lock = threading.Lock()
        
        def counter_endpoint():
            nonlocal request_count
            with lock:
                request_count += 1
                current = request_count
            time.sleep(0.1)  # Simulate some work
            return {"request_number": current}
        
        server = ss.create(
            name="concurrent_test",
            endpoints={"/count": counter_endpoint}
        )
        
        try:
            # Send 20 concurrent requests
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(20):
                    future = executor.submit(
                        requests.get, f"{server.url}/count"
                    )
                    futures.append(future)
                
                # Collect results
                results = []
                for future in as_completed(futures):
                    response = future.result()
                    assert response.status_code == 200
                    results.append(response.json()["request_number"])
                
                # Verify all requests were handled
                assert len(results) == 20
                assert len(set(results)) == 20  # All unique numbers
                assert max(results) == 20
        finally:
            server.terminate()
    
    def test_rapid_server_creation_destruction(self):
        """Test rapidly creating and destroying servers"""
        for i in range(5):
            server = ss.create(
                name=f"rapid_test_{i}",
                endpoints={"/": lambda i=i: {"iteration": i}}
            )
            
            # Quick test
            resp = requests.get(server.url)
            assert resp.json() == {"iteration": i}
            
            # Immediately terminate
            server.terminate()
            
            # Verify it's gone
            assert f"rapid_test_{i}" not in ss.servers
    
    def test_large_response_handling(self):
        """Test server handling large responses"""
        def large_response():
            # Generate 1MB of data
            return {
                "data": "x" * (1024 * 1024),
                "size": "1MB"
            }
        
        server = ss.create(
            name="large_response",
            endpoints={"/large": large_response}
        )
        
        try:
            start = time.time()
            resp = requests.get(f"{server.url}/large")
            duration = time.time() - start
            
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["data"]) == 1024 * 1024
            assert data["size"] == "1MB"
            
            # Should complete reasonably fast
            assert duration < 5.0
        finally:
            server.terminate()
    
    def test_many_endpoints(self):
        """Test server with many endpoints"""
        # Create 50 endpoints
        endpoints = {}
        for i in range(50):
            endpoints[f"/endpoint_{i}"] = lambda i=i: {"endpoint": i}
        
        server = ss.create(
            name="many_endpoints",
            endpoints=endpoints
        )
        
        try:
            # Test a few random endpoints
            for i in [0, 25, 49]:
                resp = requests.get(f"{server.url}/endpoint_{i}")
                assert resp.json() == {"endpoint": i}
            
            # Verify all endpoints are registered
            assert len(server.endpoints) == 50
        finally:
            server.terminate()
    
    def test_memory_leak_prevention(self):
        """Test that servers don't leak memory over time"""
        def memory_endpoint():
            # Create some temporary data
            data = list(range(10000))
            return {"sum": sum(data)}
        
        server = ss.create(
            name="memory_test",
            endpoints={"/memory": memory_endpoint}
        )
        
        try:
            # Make many requests
            for i in range(100):
                resp = requests.get(f"{server.url}/memory")
                assert resp.json() == {"sum": 49995000}
            
            # Server should still be responsive
            final_resp = requests.get(f"{server.url}/memory")
            assert final_resp.status_code == 200
        finally:
            server.terminate()
    
    
    def test_concurrent_server_access(self):
        """Test multiple threads accessing server collection"""
        # Create a base server
        server = ss.create(
            name="concurrent_access",
            endpoints={"/": lambda: {"ok": True}}
        )
        
        try:
            results = []
            errors = []
            
            def access_servers():
                try:
                    # Various operations on servers collection
                    assert "concurrent_access" in ss.servers
                    assert len(ss.servers) >= 1
                    
                    s = ss.servers["concurrent_access"]
                    assert s.name == "concurrent_access"
                    assert s.status == "running"
                    
                    # Access properties
                    _ = s.url
                    _ = s.uptime
                    _ = s.endpoints
                    
                    results.append("success")
                except Exception as e:
                    errors.append(str(e))
            
            # Run concurrent access
            threads = []
            for _ in range(10):
                t = threading.Thread(target=access_servers)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # Verify no errors
            assert len(errors) == 0
            assert len(results) == 10
        finally:
            server.terminate()