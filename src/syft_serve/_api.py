"""
Simplified high-level API for syft-serve
"""

from typing import Dict, Optional, List, Callable, Union
from pathlib import Path

from ._manager import ServerManager
from ._server import Server
from ._server_collection import ServerCollection
from ._exceptions import ServerAlreadyExistsError, ServerNotFoundError


# Global manager instance
_manager: Optional[ServerManager] = None


def _get_manager() -> ServerManager:
    """Get or create the global manager instance"""
    global _manager
    if _manager is None:
        _manager = ServerManager()
    return _manager


# Create the servers collection
servers = ServerCollection(_get_manager)


def create(
    name: str,
    endpoints: Dict[str, Callable],
    dependencies: Optional[List[str]] = None,
    force: bool = True,  # Default to True for better UX
    expiration_seconds: int = 86400,  # 24 hours default
) -> Server:
    """
    Create a new server

    Args:
        name: Unique server name (required)
        endpoints: Dictionary mapping paths to handler functions
        dependencies: List of Python packages to install or local paths to add to sys.path
        force: If True, destroy any existing server with the same name
        expiration_seconds: Server auto-expires after this many seconds (default: 86400 = 24 hours, -1 = never)

    Returns:
        Server object for the created server

    Examples:
        server = ss.create(
            name="my_api",
            endpoints={"/hello": hello_func}
        )

        # Server that expires in 1 hour
        server = ss.create(
            name="temp_api",
            endpoints={"/hello": hello_func},
            expiration_seconds=3600
        )

        # Server that never expires
        server = ss.create(
            name="permanent_api",
            endpoints={"/hello": hello_func},
            expiration_seconds=-1
        )
        
        # Server with local path dependency
        server = ss.create(
            name="dev_api",
            endpoints={"/": my_func},
            dependencies=[
                "/path/to/my/local/project",  # Automatically detected as local path
                "pandas",  # Regular pip package
                "numpy"
            ]
        )
    """
    manager = _get_manager()
    handle = manager.create_server(
        name=name,
        endpoints=endpoints,
        dependencies=dependencies,
        force=force,
        expiration_seconds=expiration_seconds,
    )
    return Server(handle)


def terminate_all() -> int:
    """Terminate all servers
    
    Returns:
        Number of servers terminated
    """
    results = _get_manager().terminate_all()
    return results.get("tracked_terminated", 0) + results.get("orphaned_terminated", 0)


__all__ = [
    "servers",
    "create",
    "terminate_all",
    "ServerAlreadyExistsError",
    "ServerNotFoundError",
]
