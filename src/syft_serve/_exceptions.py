"""
Minimal exception classes for SyftServe - only what's used
"""


class ServerNotFoundError(Exception):
    """Raised when a requested server cannot be found"""

    pass


class ServerAlreadyExistsError(Exception):
    """Raised when trying to create a server with a name that already exists"""

    pass


class PortInUseError(Exception):
    """Raised when no free ports are available"""

    pass


class ServerStartupError(Exception):
    """Raised when a server fails to start"""

    pass


class ServerShutdownError(Exception):
    """Raised when a server fails to shutdown cleanly"""

    pass
