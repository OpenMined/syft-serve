"""
Simplified high-level API for syft-serve
"""

from typing import Dict, Optional, List, Callable

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
    force: bool = False
) -> Server:
    """
    Create a new server
    
    Args:
        name: Unique server name (required)
        endpoints: Dictionary mapping paths to handler functions
        dependencies: List of Python packages to install
        force: If True, destroy any existing server with the same name
    
    Returns:
        Server object for the created server
    
    Examples:
        server = ss.create(
            name="my_api",
            endpoints={"/hello": hello_func}
        )
    """
    manager = _get_manager()
    handle = manager.create_server(
        name=name,
        endpoints=endpoints,
        dependencies=dependencies,
        force=force
    )
    return Server(handle)


def terminate_all():
    """Terminate all servers"""
    _get_manager().terminate_all()


__all__ = [
    "servers",
    "create", 
    "terminate_all",
    "ServerAlreadyExistsError",
    "ServerNotFoundError",
]