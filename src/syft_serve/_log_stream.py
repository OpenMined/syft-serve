"""
Simplified log stream access for server stdout and stderr
"""

from pathlib import Path
from typing import List


class LogStream:
    """Access to a server's log stream (stdout or stderr)"""
    
    def __init__(self, log_path: Path, stream_type: str = "stdout"):
        self.log_path = log_path
        self.stream_type = stream_type
    
    def tail(self, n: int = 10) -> str:
        """Return last n lines"""
        if not self.log_path.exists():
            return ""
        try:
            content = self.log_path.read_text()
            if not content:
                return ""
            lines = content.splitlines()
            return '\n'.join(lines[-n:])
        except Exception:
            return ""
    
    def head(self, n: int = 10) -> str:
        """Return first n lines"""
        if not self.log_path.exists():
            return ""
        try:
            content = self.log_path.read_text()
            if not content:
                return ""
            lines = content.splitlines()
            return '\n'.join(lines[:n])
        except Exception:
            return ""
    
    def lines(self) -> List[str]:
        """Return log lines as a list"""
        if not self.log_path.exists():
            return []
        try:
            content = self.log_path.read_text()
            if not content:
                return []
            return content.splitlines()
        except Exception:
            return []
    
    def __repr__(self) -> str:
        """Show recent log entries"""
        recent = self.tail(5)
        if recent:
            return f"<LogStream {self.stream_type}>\n{recent}"
        else:
            return f"<LogStream {self.stream_type}: empty>"