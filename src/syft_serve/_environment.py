"""
Simplified read-only environment access for servers
"""

import subprocess  # nosec B404
import json
from pathlib import Path
from typing import List, Dict, Optional


class Environment:
    """Read-only view of a server's Python environment"""

    def __init__(self, server_dir: Path):
        self.server_dir = server_dir
        self._cache: Optional[Dict[str, str]] = None
        self._cache_time: float = 0.0

    def _run_uv_command(self, args: List[str]) -> str:
        """Run a uv command in the server's environment"""
        # Check if server directory exists
        if not self.server_dir.exists():
            return ""

        # Check if we have a virtual environment
        venv_path = self.server_dir / ".venv"
        if venv_path.exists():
            # Use uv run to execute within the virtual environment
            cmd = ["uv", "run"] + args
        else:
            # Fallback to direct command
            cmd = ["uv"] + args

        try:
            result = subprocess.run(  # nosec B603
                cmd, cwd=str(self.server_dir), capture_output=True, text=True, check=True
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    def _get_packages(self) -> Dict[str, str]:
        """Get installed packages as a dict"""
        # Use cache if recent (within 5 seconds)
        import time

        if self._cache and (time.time() - self._cache_time) < 5:
            return self._cache

        # Run pip list --format=json within the environment
        output = self._run_uv_command(["pip", "list", "--format=json"])
        if not output:
            return {}

        try:
            packages = json.loads(output)
            result = {pkg["name"]: pkg["version"] for pkg in packages}
            self._cache = result
            self._cache_time = time.time()
            return result
        except (json.JSONDecodeError, KeyError):
            return {}

    def list(self) -> List[str]:
        """List installed packages as strings (name==version)"""
        packages = self._get_packages()
        return [f"{name}=={version}" for name, version in sorted(packages.items())]

    def __repr__(self) -> str:
        """Pretty tree-style representation"""
        packages = self.list()
        if not packages:
            return f"Environment: {self.server_dir.name} (empty)"

        lines = [f"Environment: {self.server_dir.name}"]

        # Show key packages first
        key_packages = [
            "fastapi",
            "uvicorn",
            "pandas",
            "numpy",
            "scikit-learn",
            "tensorflow",
            "torch",
        ]
        shown = []

        for pkg_str in packages:
            name = pkg_str.split("==")[0]
            if name in key_packages:
                shown.append(pkg_str)

        # Then show others
        other_count = len(packages) - len(shown)

        # Format as tree
        for i, pkg in enumerate(shown[:10]):  # Show max 10 key packages
            if i == len(shown) - 1 and other_count == 0:
                lines.append(f"└── {pkg}")
            else:
                lines.append(f"├── {pkg}")

        if other_count > 0:
            lines.append(f"└── ... and {other_count} more packages")

        return "\n".join(lines)
