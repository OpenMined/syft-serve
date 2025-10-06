"""
Minimal configuration for SyftServe - only what's actually used
"""

import os
from pathlib import Path
from typing import Tuple
from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    """Minimal configuration for server management"""

    # Port management
    port_range: Tuple[int, int] = (8000, 8010)

    # Persistence
    persistence_file: Path = field(default_factory=lambda: Path.home() / ".syft_servers.json")

    # Logging
    log_dir: Path = field(default_factory=lambda: Path.home() / ".syft_logs")

    # Process management
    startup_timeout: float = 30.0  # seconds (increased from 10.0 for complex services)
    health_check_interval: float = 1.0  # seconds

    def __post_init__(self) -> None:
        """Ensure directories exist"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)


def get_config() -> ServerConfig:
    """Get the server configuration"""
    config = ServerConfig()
    
    # Allow environment variable override for startup timeout
    if timeout_env := os.environ.get('SYFT_SERVE_STARTUP_TIMEOUT'):
        try:
            config.startup_timeout = float(timeout_env)
        except ValueError:
            pass  # Keep default if invalid
    
    return config
