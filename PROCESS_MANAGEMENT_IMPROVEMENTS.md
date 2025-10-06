# syft-serve Process Management Improvements Plan

## Problem Statement

Currently, syft-serve has several critical issues with process management:

1. **Ghost Processes**: Servers leave behind uvicorn processes after termination
2. **Duplicate Termination Methods**: `syft_serve.terminate_all()` vs `syft_serve.servers.terminate_all()`
3. **Manual Cleanup Required**: Users need to run `kill -9` commands to clean up
4. **422 Errors**: Servers in bad states return 422 errors instead of being detected as unhealthy
5. **Lock File Issues**: Stale lock files prevent server recreation

## Root Causes

1. **Incomplete Process Tracking**
   - Only tracking parent PID, not process groups
   - Child processes (uvicorn workers) escape termination
   - No verification that processes actually died

2. **Missing Health Verification**
   - Servers are assumed healthy after `start()`
   - No startup verification
   - No ongoing health monitoring

3. **Poor State Management**
   - No distinction between "starting", "healthy", "unhealthy"
   - Registry can contain dead servers
   - Lock files not cleaned up properly

## Proposed Solution

### 1. Process Group Management

**File**: `syft_serve/_server.py`

#### Current State:
```python
# Simple process creation
self.process = subprocess.Popen(cmd, ...)
self.pid = self.process.pid
```

#### Improved State:
```python
# Process group management
self.process = subprocess.Popen(
    cmd,
    preexec_fn=os.setsid,  # New session
    start_new_session=True  # Windows compatible
)
self.pid = self.process.pid
self.pgid = os.getpgid(self.pid)
```

### 2. Comprehensive Server States

**File**: `syft_serve/_server.py`

Add server state tracking:
```python
class ServerState(Enum):
    CREATED = "created"          # Initialized but not started
    STARTING = "starting"        # Process launched, waiting for ready
    HEALTHY = "healthy"          # Verified working
    UNHEALTHY = "unhealthy"      # Running but failing health checks
    STOPPING = "stopping"        # Shutdown initiated
    STOPPED = "stopped"          # Process terminated cleanly
    ZOMBIE = "zombie"            # Process dead but artifacts remain
```

### 3. Health Check System

**New File**: `syft_serve/_health.py`

```python
class HealthChecker:
    """Manages health checks for servers"""
    
    def __init__(self):
        self.default_timeout = 10.0
        self.retry_delays = [0.5, 2.0, 5.0]
    
    def verify_startup(self, server: Server) -> bool:
        """Verify server started correctly"""
        # 1. Wait for port to be bound
        # 2. Test each endpoint
        # 3. Retry with backoff
        # 4. Return success or raise
    
    def check_health(self, server: Server) -> bool:
        """Quick health check"""
        # Test health endpoint or default endpoint
```

### 4. Process Discovery and Cleanup

**New File**: `syft_serve/_process_manager.py`

```python
class ProcessManager:
    """System-wide process management"""
    
    @staticmethod
    def find_uvicorn_processes() -> List[ProcessInfo]:
        """Find all uvicorn processes on system"""
        # Use psutil or subprocess to find processes
        
    @staticmethod
    def find_processes_by_port(port: int) -> List[ProcessInfo]:
        """Find processes listening on a port"""
        
    @staticmethod
    def kill_process_tree(pid: int, timeout: float = 5.0) -> bool:
        """Kill process and all children"""
        # 1. Send SIGTERM to process group
        # 2. Wait for graceful shutdown
        # 3. Send SIGKILL if needed
        # 4. Verify all dead
        
    @staticmethod
    def cleanup_orphaned_processes(name_pattern: str = None):
        """Find and kill orphaned server processes"""
```

### 5. Enhanced Server Manager

**File**: `syft_serve/_manager.py`

#### Improvements to `create()`:
```python
def create(self, name: str, ..., verify_startup: bool = True, 
          startup_timeout: float = 10.0, force_cleanup: bool = False):
    """
    Create a server with health verification
    
    Steps:
    1. Check if server exists
       - If healthy -> return it
       - If unhealthy -> cleanup if force_cleanup
    2. Check for conflicts
       - Port in use?
       - Stale lock files?
       - Orphaned processes?
    3. Create and start server
    4. Verify startup if requested
    5. Return only if healthy
    """
```

#### Unified `terminate_all()`:
```python
def terminate_all(self, timeout: float = 5.0, force: bool = False):
    """
    Comprehensive termination of all servers
    
    Steps:
    1. Stop all registered servers gracefully
    2. Wait for graceful shutdown (up to timeout)
    3. Force kill remaining registered servers
    4. Find orphaned processes by multiple methods:
       - By process name (uvicorn)
       - By ports we know about
       - By lock file references
    5. Kill all orphaned processes
    6. Clean up all lock files
    7. Clear registry
    8. Final verification - no processes remain
    """
```

### 6. Lock File Improvements

**File**: `syft_serve/_utils.py`

```python
class LockFile:
    """Robust lock file management"""
    
    def __init__(self, path: Path):
        self.path = path
        
    def acquire(self, pid: int) -> bool:
        """Atomic lock acquisition"""
        # Write PID atomically
        # Check for stale locks
        
    def release(self):
        """Release lock"""
        
    def is_stale(self) -> bool:
        """Check if lock's PID is dead"""
        
    @classmethod
    def cleanup_stale_locks(cls, directory: Path):
        """Remove all stale lock files"""
```

### 7. Module-Level Functions

**File**: `syft_serve/__init__.py`

Ensure module-level functions delegate properly:
```python
def terminate_all(**kwargs):
    """Terminate all servers (delegates to manager)"""
    return servers.terminate_all(**kwargs)

def cleanup_all():
    """Complete system cleanup"""
    # 1. Terminate all servers
    # 2. Find and kill orphans
    # 3. Clean lock files
    # 4. Reset state
```

### 8. Configuration Updates

**File**: `syft_serve/_config.py`

Add new configuration options:
```python
class ServerConfig:
    # Startup verification
    verify_startup: bool = True
    startup_timeout: float = 10.0
    startup_retries: int = 3
    
    # Health checking
    health_check_enabled: bool = True
    health_check_interval: float = 30.0
    health_check_endpoint: str = "/health"
    
    # Process management
    graceful_shutdown_timeout: float = 5.0
    force_kill_after_timeout: bool = True
    cleanup_orphans_on_start: bool = True
```

## Implementation Plan

### Phase 1: Process Management Foundation
1. Implement `ProcessManager` class
2. Update `Server` to use process groups
3. Implement proper `kill_process_tree()`
4. Add process discovery methods

### Phase 2: Health Checking
1. Create `HealthChecker` class
2. Add server state management
3. Integrate health checks into `create()`
4. Add startup verification

### Phase 3: Cleanup and Recovery
1. Implement comprehensive `terminate_all()`
2. Add orphan process cleanup
3. Improve lock file management
4. Add automatic recovery

### Phase 4: Testing and Polish
1. Add extensive tests for process management
2. Test on different platforms (Linux, macOS, Windows)
3. Add logging and debugging
4. Update documentation

## Expected Outcomes

1. **No More Ghost Processes**: Complete cleanup every time
2. **Self-Healing**: Automatic detection and recovery from bad states
3. **No Manual Intervention**: No need for `kill -9` commands
4. **Better Error Messages**: Clear indication of what went wrong
5. **Reliable Operation**: Servers always start in a verified healthy state

## Backward Compatibility

- Default behavior includes verification (safer)
- Add `create_no_verify()` for old behavior
- Existing code continues to work
- Can disable with config options

## Testing Strategy

1. **Unit Tests**:
   - Process group creation/termination
   - Health check logic
   - Lock file management

2. **Integration Tests**:
   - Full server lifecycle
   - Multiple server management
   - Failure recovery

3. **Stress Tests**:
   - Rapid create/destroy cycles
   - Simulated crashes
   - Port conflicts
   - System resource limits

## Success Criteria

1. Running `terminate_all()` kills ALL processes - verified with `ps aux | grep uvicorn`
2. Creating a server always results in a working server or a clear error
3. No stale lock files remain after termination
4. Servers can be created/destroyed 100+ times without issues
5. 422 errors are caught during startup, not after