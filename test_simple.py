#!/usr/bin/env python3
"""
Simple test to check syft-serve basic functionality
"""

import sys
sys.path.insert(0, '/Users/atrask/Desktop/Laboratory/syft-serve/src')

import syft_serve as ss
import time
import requests

print("Testing syft-serve basic functionality...")

# Test 1: Create a simple server
print("\n1. Creating a simple server...")
try:
    def hello():
        return {"message": "Hello, World!"}
    
    server = ss.create(
        name="test_simple",
        endpoints={"/": hello},
        force=True
    )
    
    print(f"   ✓ Server created: {server.name}")
    print(f"   ✓ URL: {server.url}")
    print(f"   ✓ PID: {server.pid}")
    
    # Give it a moment to start
    time.sleep(2)
    
    # Test the endpoint
    try:
        response = requests.get(server.url, timeout=5)
        print(f"   ✓ Response: {response.json()}")
    except Exception as e:
        print(f"   ✗ Failed to get response: {e}")
    
except Exception as e:
    print(f"   ✗ Failed to create server: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Check server collection
print("\n2. Checking server collection...")
try:
    print(f"   ✓ Servers: {ss.servers}")
    if "test_simple" in ss.servers:
        print("   ✓ Server found in collection")
    else:
        print("   ✗ Server not found in collection")
except Exception as e:
    print(f"   ✗ Failed to check servers: {e}")

# Test 3: Terminate all servers
print("\n3. Terminating all servers...")
try:
    count = ss.terminate_all()
    print(f"   ✓ Terminated {count} servers")
except Exception as e:
    print(f"   ✗ Failed to terminate servers: {e}")

print("\nTest complete.")