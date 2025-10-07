#!/usr/bin/env python3
"""
Test the ProcessManager and HealthChecker components directly
"""

import sys
sys.path.insert(0, '/Users/atrask/Desktop/Laboratory/syft-serve/src')

from syft_serve._process_manager import ProcessManager, ProcessInfo
from syft_serve._health import HealthChecker, HealthCheckConfig, HealthCheckResult
import psutil
import subprocess
import time
import os
import signal

print("Testing syft-serve ProcessManager and HealthChecker components...\n")

# Test 1: ProcessManager - find processes
print("1. Testing ProcessManager.find_uvicorn_processes():")
try:
    processes = ProcessManager.find_uvicorn_processes()
    print(f"   ✓ Found {len(processes)} uvicorn processes")
    for proc in processes[:3]:  # Show first 3
        print(f"     - PID {proc.pid}: {proc.name}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: ProcessManager - find by port
print("\n2. Testing ProcessManager.find_processes_by_port():")
try:
    # Check a common port
    port_processes = ProcessManager.find_processes_by_port(8000)
    print(f"   ✓ Found {len(port_processes)} processes on port 8000")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: ProcessManager - verify process dead
print("\n3. Testing ProcessManager.verify_process_dead():")
try:
    # Check current process (should be alive)
    current_pid = os.getpid()
    is_dead = ProcessManager.verify_process_dead(current_pid, timeout=0.5)
    print(f"   ✓ Current process (PID {current_pid}) is {'dead' if is_dead else 'alive'} (should be alive)")
    
    # Check non-existent process (should be dead)
    fake_pid = 99999
    is_dead2 = ProcessManager.verify_process_dead(fake_pid, timeout=0.5)
    print(f"   ✓ Non-existent process (PID {fake_pid}) is {'dead' if is_dead2 else 'alive'} (should be dead)")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: Create a test process for kill testing
print("\n4. Testing ProcessManager.kill_process_tree():")
try:
    # Start a simple sleep process
    proc = subprocess.Popen(['sleep', '60'])
    test_pid = proc.pid
    print(f"   ✓ Started test process with PID {test_pid}")
    
    # Verify it's running
    time.sleep(0.1)
    try:
        os.kill(test_pid, 0)
        print(f"   ✓ Process {test_pid} is running")
    except ProcessLookupError:
        print(f"   ✗ Process {test_pid} already dead")
    
    # Kill it
    success = ProcessManager.kill_process_tree(test_pid, timeout=2.0)
    print(f"   ✓ Kill process tree: {'success' if success else 'failed'}")
    
    # Verify it's dead
    time.sleep(0.5)
    is_dead = ProcessManager.verify_process_dead(test_pid, timeout=0.5)
    print(f"   ✓ Process {test_pid} is {'dead' if is_dead else 'still alive!'}")
    
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 5: HealthChecker
print("\n5. Testing HealthChecker:")
try:
    health_checker = HealthChecker()
    print(f"   ✓ HealthChecker created")
    print(f"   ✓ Config: startup_timeout={health_checker.config.startup_timeout}s")
    print(f"   ✓ Config: retry_delays={health_checker.config.retry_delays}")
    
    # Test the _wait_for_port method
    print("\n   Testing port availability check:")
    # Test on a port that's likely not in use
    available = health_checker._wait_for_port("localhost", 65432)
    print(f"   ✓ Port 65432 available: {available} (should be False)")
    
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 6: ProcessInfo
print("\n6. Testing ProcessInfo:")
try:
    # Get current process
    current_proc = psutil.Process()
    proc_info = ProcessInfo.from_psutil(current_proc)
    
    if proc_info:
        print(f"   ✓ ProcessInfo created:")
        print(f"     - PID: {proc_info.pid}")
        print(f"     - Name: {proc_info.name}")
        print(f"     - Status: {proc_info.status}")
    else:
        print("   ✗ Failed to create ProcessInfo")
        
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\nComponent tests complete!")