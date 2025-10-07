#!/usr/bin/env python3
"""
Test the ServerManager directly with process management improvements
"""

import sys
sys.path.insert(0, '/Users/atrask/Desktop/Laboratory/syft-serve/src')

from syft_serve._manager import ServerManager
from syft_serve._process_manager import ProcessManager
import time
import requests
import os

print("Testing ServerManager with process management improvements...\n")

# Create a manager instance
manager = ServerManager()
print("✓ ServerManager created")

# Test 1: Create server with verify_startup=True
print("\n1. Testing server creation with startup verification:")
try:
    def hello():
        return {"message": "Hello from verified server!"}
    
    server = manager.create_server(
        name="test_verified",
        endpoints={"/": hello, "/health": lambda: {"status": "healthy"}},
        force=True,
        verify_startup=True,
        startup_timeout=10.0
    )
    
    print(f"   ✓ Server created with verification: {server.name}")
    print(f"   ✓ URL: {server.url}")
    print(f"   ✓ PID: {server.pid}")
    
    # Test the endpoint
    response = requests.get(server.url, timeout=5)
    print(f"   ✓ Response: {response.json()}")
    
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Test terminate_all with detailed results
print("\n2. Testing terminate_all with detailed results:")
try:
    # Create multiple servers
    for i in range(2):
        server = manager.create_server(
            name=f"test_term_{i}",
            endpoints={"/": lambda i=i: {"server": i}},
            force=True,
            verify_startup=False  # Faster for this test
        )
        print(f"   ✓ Created server: {server.name}")
    
    # Run terminate_all
    results = manager.terminate_all(force=True)
    print(f"\n   Termination results:")
    print(f"   - Tracked servers total: {results['tracked_total']}")
    print(f"   - Tracked servers terminated: {results['tracked_terminated']}")
    print(f"   - Tracked servers failed: {results['tracked_failed']}")
    print(f"   - Orphaned processes discovered: {results['orphaned_discovered']}")
    print(f"   - Orphaned processes terminated: {results['orphaned_terminated']}")
    print(f"   - Success: {results['success']}")
    
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Test failed server startup
print("\n3. Testing failed server startup handling:")
try:
    # This should fail because we can't serialize the import statement
    def bad_endpoint():
        import nonexistent_module  # This will fail
        return {"error": "This should fail"}
    
    try:
        server = manager.create_server(
            name="test_fail",
            endpoints={"/": bad_endpoint},
            force=True,
            verify_startup=True
        )
        print("   ✗ Server creation should have failed!")
    except Exception as e:
        print(f"   ✓ Server creation failed as expected: {type(e).__name__}")
        print(f"   ✓ Error: {str(e)[:100]}...")
        
        # Check no zombies
        time.sleep(1)
        zombies = ProcessManager.find_uvicorn_processes()
        zombie_count = sum(1 for p in zombies if 'test_fail' in ' '.join(p.cmdline))
        print(f"   ✓ Zombie processes: {zombie_count} (should be 0)")
        
except Exception as e:
    print(f"   ✗ Unexpected error: {e}")

# Test 4: Test orphaned process simulation
print("\n4. Testing orphaned process cleanup:")
try:
    # Create a server
    server = manager.create_server(
        name="test_orphan",
        endpoints={"/": lambda: {"msg": "orphan test"}},
        force=True,
        verify_startup=False
    )
    pid = server.pid
    print(f"   ✓ Created server with PID: {pid}")
    
    # Simulate orphaning by removing from manager's registry
    if "test_orphan" in manager._servers:
        del manager._servers["test_orphan"]
        print(f"   ✓ Removed server from tracking (simulated orphan)")
    
    # Check process still exists
    try:
        os.kill(pid, 0)
        print(f"   ✓ Process {pid} still running (orphaned)")
    except:
        print(f"   ✗ Process {pid} already dead")
    
    # Run cleanup
    cleaned = ProcessManager.cleanup_orphaned_processes(port_range=range(8000, 9000))
    print(f"   ✓ Cleaned up {cleaned} orphaned processes")
    
    # Verify cleanup
    time.sleep(1)
    try:
        os.kill(pid, 0)
        print(f"   ✗ Process {pid} still running!")
    except:
        print(f"   ✓ Process {pid} successfully cleaned up")
        
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

# Final cleanup
print("\n5. Final cleanup:")
try:
    results = manager.terminate_all()
    print(f"   ✓ Final cleanup complete: {results['tracked_terminated'] + results['orphaned_terminated']} processes terminated")
except Exception as e:
    print(f"   ✗ Cleanup failed: {e}")

print("\nManager tests complete!")