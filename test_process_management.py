#!/usr/bin/env python3
"""
Test script for syft-serve process management improvements.
Tests ProcessManager, HealthChecker, and server lifecycle management.
"""

import sys
import time
import subprocess
import signal
import os
from pathlib import Path

# Add syft-serve to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import syft_serve as ss
from syft_serve._process_manager import ProcessManager
from syft_serve._health import HealthChecker, HealthCheckConfig


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def test_basic_server_creation():
    """Test 1: Basic server creation and health verification"""
    print_header("Test 1: Basic Server Creation")
    
    try:
        # Simple test endpoint
        def hello():
            return {"message": "Hello from test server!"}
        
        # Create a server with verify_startup=True (should be default)
        print("📦 Creating test server...")
        server = ss.create(
            name="test_basic",
            endpoints={"/": hello, "/health": lambda: {"status": "ok"}},
            force=True
        )
        
        print(f"✅ Server created: {server.name}")
        print(f"   URL: {server.url}")
        print(f"   PID: {server.pid}")
        print(f"   Status: {server.status}")
        
        # Test the endpoint
        import requests
        response = requests.get(server.url)
        print(f"   Response: {response.json()}")
        
        # Check health
        health_response = requests.get(f"{server.url}/health")
        print(f"   Health: {health_response.json()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_terminate_all():
    """Test 2: Test terminate_all() properly cleans up all processes"""
    print_header("Test 2: Terminate All")
    
    try:
        # Create multiple servers
        print("📦 Creating multiple test servers...")
        
        for i in range(3):
            server = ss.create(
                name=f"test_terminate_{i}",
                endpoints={"/": lambda i=i: {"server": i}},
                force=True
            )
            print(f"   Created server: {server.name} (PID: {server.pid})")
        
        # Check running processes before termination
        print("\n🔍 Checking processes before termination...")
        uvicorn_procs = ProcessManager.find_uvicorn_processes()
        print(f"   Found {len(uvicorn_procs)} uvicorn processes")
        
        # Terminate all
        print("\n🧹 Running terminate_all()...")
        terminated_count = ss.terminate_all()
        print(f"   Terminated {terminated_count} servers")
        
        # Wait a moment for cleanup
        time.sleep(2)
        
        # Check processes after termination
        print("\n🔍 Checking processes after termination...")
        remaining_procs = ProcessManager.find_uvicorn_processes()
        print(f"   Found {len(remaining_procs)} uvicorn processes")
        
        if remaining_procs:
            print("   ⚠️  Warning: Some processes still running:")
            for proc in remaining_procs:
                print(f"      PID {proc.pid}: {' '.join(proc.cmdline[:3])}")
        
        return len(remaining_procs) == 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_failed_startup():
    """Test 3: Test behavior when server fails to start"""
    print_header("Test 3: Failed Server Startup")
    
    try:
        # Try to create a server with an invalid endpoint that will cause startup failure
        def bad_endpoint():
            # This will fail during serialization
            import nonexistent_module
            return {"error": "This should fail"}
        
        print("📦 Creating server with bad endpoint (should fail)...")
        try:
            server = ss.create(
                name="test_failed",
                endpoints={"/": bad_endpoint},
                force=True
            )
            print("❌ Server creation should have failed but didn't!")
            return False
            
        except Exception as e:
            print(f"✅ Server creation failed as expected: {type(e).__name__}")
            print(f"   Error: {str(e)}")
            
            # Check that no zombie processes were left
            print("\n🔍 Checking for zombie processes...")
            uvicorn_procs = ProcessManager.find_uvicorn_processes()
            zombie_count = 0
            for proc in uvicorn_procs:
                if 'test_failed' in ' '.join(proc.cmdline):
                    zombie_count += 1
                    print(f"   ⚠️  Found zombie process: PID {proc.pid}")
            
            if zombie_count == 0:
                print("   ✅ No zombie processes found")
                return True
            else:
                print(f"   ❌ Found {zombie_count} zombie processes")
                return False
        
    except Exception as e:
        print(f"❌ Test failed unexpectedly: {e}")
        return False


def test_orphaned_process_cleanup():
    """Test 4: Test cleanup of orphaned processes"""
    print_header("Test 4: Orphaned Process Cleanup")
    
    try:
        # Create a server
        print("📦 Creating test server...")
        server = ss.create(
            name="test_orphan",
            endpoints={"/": lambda: {"message": "orphan test"}},
            force=True
        )
        pid = server.pid
        print(f"   Server PID: {pid}")
        
        # Manually "orphan" the process by removing it from tracking
        # but not killing it (simulating a crash)
        print("\n💥 Simulating crash (orphaning process)...")
        if hasattr(ss, '_manager') and ss._manager:
            if 'test_orphan' in ss._manager._servers:
                del ss._manager._servers['test_orphan']
                print("   Removed server from tracking (process still running)")
        
        # Check that the process is still running
        print("\n🔍 Checking if process is still running...")
        try:
            os.kill(pid, 0)
            print(f"   Process {pid} is still running (orphaned)")
        except ProcessLookupError:
            print(f"   ❌ Process {pid} is already dead")
            return False
        
        # Test cleanup
        print("\n🧹 Running orphaned process cleanup...")
        cleaned = ProcessManager.cleanup_orphaned_processes()
        print(f"   Cleaned up {cleaned} orphaned processes")
        
        # Verify the process is now dead
        time.sleep(1)
        print("\n🔍 Verifying process is dead...")
        try:
            os.kill(pid, 0)
            print(f"   ❌ Process {pid} is still running!")
            return False
        except ProcessLookupError:
            print(f"   ✅ Process {pid} is dead")
            return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_process_manager_functions():
    """Test 5: Test ProcessManager utility functions"""
    print_header("Test 5: ProcessManager Functions")
    
    try:
        # Create a test server
        print("📦 Creating test server for ProcessManager tests...")
        server = ss.create(
            name="test_pm",
            endpoints={"/": lambda: {"test": "process_manager"}},
            force=True
        )
        
        # Test find_uvicorn_processes
        print("\n🔍 Testing find_uvicorn_processes()...")
        uvicorn_procs = ProcessManager.find_uvicorn_processes()
        print(f"   Found {len(uvicorn_procs)} uvicorn processes")
        for proc in uvicorn_procs[:3]:  # Show first 3
            print(f"   - PID {proc.pid}: {proc.name}")
        
        # Test find_processes_by_port
        print(f"\n🔍 Testing find_processes_by_port({server.port})...")
        port_procs = ProcessManager.find_processes_by_port(server.port)
        print(f"   Found {len(port_procs)} processes on port {server.port}")
        for proc in port_procs:
            print(f"   - PID {proc.pid} on port {proc.port}")
        
        # Test verify_process_dead
        print(f"\n🔍 Testing verify_process_dead({server.pid})...")
        is_dead = ProcessManager.verify_process_dead(server.pid, timeout=0.5)
        print(f"   Process {server.pid} is {'dead' if is_dead else 'alive'}")
        
        # Test kill_process_tree
        print(f"\n💀 Testing kill_process_tree({server.pid})...")
        killed = ProcessManager.kill_process_tree(server.pid)
        print(f"   Kill successful: {killed}")
        
        # Verify it's dead
        time.sleep(1)
        is_dead_after = ProcessManager.verify_process_dead(server.pid, timeout=0.5)
        print(f"   Process {server.pid} is {'dead' if is_dead_after else 'still alive!'}")
        
        return is_dead_after
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_health_checker():
    """Test 6: Test HealthChecker functionality"""
    print_header("Test 6: HealthChecker")
    
    try:
        from syft_serve._server import Server
        from syft_serve._handle import ServerHandle
        
        # Create a basic server
        print("📦 Creating test server for health checks...")
        server = ss.create(
            name="test_health",
            endpoints={
                "/": lambda: {"status": "ok"},
                "/health": lambda: {"healthy": True, "timestamp": time.time()}
            },
            force=True
        )
        
        # Create health checker
        health_checker = HealthChecker()
        
        # Test health check on running server
        print("\n🏥 Testing health check on running server...")
        
        # We need to construct a Server object from the handle
        # This is a bit hacky but necessary for testing
        class MockServer:
            def __init__(self, handle):
                self.name = handle.name
                self.host = handle.host
                self.port = handle.port
                self.endpoints = {"/": None, "/health": None}
                self._handle = handle
            
            def is_running(self):
                return self._handle.is_running()
        
        mock_server = MockServer(server._handle)
        health_result = health_checker.check_health(mock_server)
        
        print(f"   Healthy: {health_result.healthy}")
        print(f"   Details: {health_result.details}")
        
        # Test on a dead server
        print("\n💀 Killing server and testing health check...")
        server.terminate()
        time.sleep(1)
        
        health_result2 = health_checker.check_health(mock_server)
        print(f"   Healthy: {health_result2.healthy}")
        print(f"   Details: {health_result2.details}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def cleanup_all_test_servers():
    """Clean up any remaining test servers"""
    print("\n🧹 Cleaning up all test servers...")
    
    # First try graceful termination
    ss.terminate_all()
    time.sleep(2)
    
    # Then force cleanup of any orphans
    cleaned = ProcessManager.cleanup_orphaned_processes()
    if cleaned > 0:
        print(f"   Cleaned up {cleaned} orphaned processes")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  SYFT-SERVE PROCESS MANAGEMENT TEST SUITE")
    print("="*60)
    
    tests = [
        ("Basic Server Creation", test_basic_server_creation),
        ("Terminate All", test_terminate_all),
        ("Failed Startup Handling", test_failed_startup),
        ("Orphaned Process Cleanup", test_orphaned_process_cleanup),
        ("ProcessManager Functions", test_process_manager_functions),
        ("HealthChecker", test_health_checker),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            # Clean up before each test
            cleanup_all_test_servers()
            
            # Run test
            passed = test_func()
            results.append((test_name, passed))
            
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Final cleanup
    cleanup_all_test_servers()
    
    # Print summary
    print_header("TEST SUMMARY")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n  Total: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())