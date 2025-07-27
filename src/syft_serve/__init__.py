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
from ._api import servers, create

__version__ = "0.2.1"

__all__ = [
    "servers", 
    "create",
]