"""
SyftServe - Easy launch and management of stateless FastAPI servers

This package provides a simple API for creating and managing FastAPI server processes
with isolated environments and custom dependencies.

Main API:
- servers: Access and manage all servers
- create(): Create a new server
- config: Configure syft-serve behavior
- logs(): View server logs

Example:
    import syft_serve as ss

    # Create a server
    server = ss.create(
        name="my_api",
        endpoints={"/hello": lambda: {"message": "Hello!"}},
        dependencies=["pandas", "numpy"]
    )

    # Access servers
    print(ss.servers)  # Shows all servers
    api = ss.servers["my_api"]  # Get specific server

    # View logs
    print(api.stdout.tail(20))
"""

# Import only what we need for the public API
from ._api import servers, create, terminate_all, ServerAlreadyExistsError, ServerNotFoundError

__version__ = "0.2.10"

# Clean up orphaned processes on module import
import psutil
import os

def _cleanup_orphaned_processes():
    """Clean up orphaned syft-serve processes on module import"""
    try:
        for proc in psutil.process_iter(['pid', 'ppid', 'cmdline']):
            try:
                # Check if it's an orphaned syft-serve process
                if (proc.info['ppid'] == 1 and  # Orphaned (parent is init)
                    proc.info['cmdline'] and
                    any('syft-serve' in arg or 'uvicorn' in arg for arg in proc.info['cmdline'])):
                    
                    # Additional check: see if it's a syft-serve managed process
                    cmdline = ' '.join(proc.info['cmdline'])
                    if ('watcher_sender' in cmdline or 'receiver_' in cmdline or 
                        '_app:app' in cmdline):
                        # Kill orphaned process
                        try:
                            proc.terminate()
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        except:
                            pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except:
        # Don't fail module import if cleanup fails
        pass

# Run cleanup on import
_cleanup_orphaned_processes()

# Register graceful shutdown hooks
import atexit
import signal

def _cleanup_all_servers():
    """Clean up all servers on exit"""
    try:
        from ._api import terminate_all
        terminate_all()
    except:
        pass

# Register cleanup
atexit.register(_cleanup_all_servers)

# Handle signals gracefully
def _signal_handler(signum, frame):
    _cleanup_all_servers()
    # Re-raise the signal to allow normal termination
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)

# Register signal handlers
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, _signal_handler)
if hasattr(signal, 'SIGINT'):
    signal.signal(signal.SIGINT, _signal_handler)

__all__ = [
    "servers",
    "create",
    "terminate_all",
    "ServerAlreadyExistsError",
    "ServerNotFoundError",
]
