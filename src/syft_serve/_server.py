"""
Simplified Server class - the main interface for interacting with servers
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ._handle import ServerHandle
from ._log_stream import LogStream
from ._environment import Environment


class Server:
    """High-level interface for a FastAPI server"""
    
    def __init__(self, handle: ServerHandle):
        self._handle = handle
        self._start_time = datetime.now()
    
    # Basic properties
    @property
    def name(self) -> str:
        """Server name"""
        return self._handle.name
    
    @property
    def port(self) -> int:
        """Server port"""
        return self._handle.port
    
    @property
    def pid(self) -> Optional[int]:
        """Process ID"""
        return self._handle.pid
    
    @property
    def status(self) -> str:
        """Server status (running/stopped)"""
        return self._handle.status
    
    @property
    def url(self) -> str:
        """Base URL for the server"""
        return f"http://localhost:{self.port}"
    
    @property
    def endpoints(self) -> list:
        """List of endpoints"""
        return self._handle.endpoints
    
    @property
    def uptime(self) -> str:
        """Human-readable uptime"""
        if self.status != "running":
            return "-"
        
        try:
            # Get actual process start time from psutil
            import psutil
            process = psutil.Process(self.pid)
            start_time = datetime.fromtimestamp(process.create_time())
            delta = datetime.now() - start_time
        except:
            # Fallback to object creation time
            delta = datetime.now() - self._start_time
        
        total_seconds = int(delta.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            return f"{days}d {hours}h"
    
    # Log access
    @property
    def stdout(self) -> LogStream:
        """Access to stdout logs"""
        if not hasattr(self, '_stdout'):
            stdout_path = self._get_log_path('stdout')
            self._stdout = LogStream(stdout_path, 'stdout')
        return self._stdout
    
    @property
    def stderr(self) -> LogStream:
        """Access to stderr logs"""
        if not hasattr(self, '_stderr'):
            stderr_path = self._get_log_path('stderr')
            self._stderr = LogStream(stderr_path, 'stderr')
        return self._stderr
    
    # Environment access
    @property
    def env(self) -> Environment:
        """Read-only view of server environment"""
        if not hasattr(self, '_env'):
            server_dir = self._get_server_dir()
            self._env = Environment(server_dir)
        return self._env
    
    # Actions
    def terminate(self) -> None:
        """Terminate the server completely"""
        self._handle.terminate()
    
    # Helper methods
    def _get_server_dir(self) -> Path:
        """Get the server's environment directory"""
        from ._config import get_config
        config = get_config()
        return config.log_dir / "server_envs" / self.name
    
    def _get_log_path(self, stream: str) -> Path:
        """Get path to log file"""
        server_dir = self._get_server_dir()
        return server_dir / f"{self.name}_{stream}.log"
    
    def __repr__(self) -> str:
        """Console representation"""
        status_icon = "✅" if self.status == "running" else "❌"
        lines = [
            f"Server: {self.name}",
            f"├── Status: {status_icon} {self.status.title()}",
            f"├── URL: {self.url}",
            f"├── Endpoints: {', '.join(self.endpoints) if self.endpoints else 'none'}",
            f"├── Uptime: {self.uptime}",
            f"└── PID: {self.pid or '-'}"
        ]
        return '\n'.join(lines)
    
    def _repr_html_(self) -> str:
        """Jupyter notebook representation"""
        status_color = "#27ae60" if self.status == "running" else "#e74c3c"
        status_icon = "✅" if self.status == "running" else "❌"
        
        endpoints_html = ""
        if self.endpoints:
            endpoint_items = "".join(f"<li><code>{ep}</code></li>" for ep in self.endpoints)
            endpoints_html = f"<ul style='margin: 0; padding-left: 20px;'>{endpoint_items}</ul>"
        else:
            endpoints_html = "<em style='color: #888;'>No endpoints</em>"
        
        # Get recent logs preview
        recent_stdout = self.stdout.tail(3)
        log_preview = ""
        if recent_stdout:
            log_lines = recent_stdout.split('\n')
            log_html = '<br>'.join(f"<code>{line}</code>" for line in log_lines[:3])
            log_preview = f"""
            <div style="margin-top: 10px; padding: 8px; background: #f8f9fa; border-radius: 3px;">
                <div style="color: #666; font-size: 11px; margin-bottom: 5px;">Recent logs:</div>
                <div style="font-size: 11px; color: #333;">{log_html}</div>
            </div>
            """
        
        return f"""
        <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: #333;">🚀 {self.name}</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: #666; vertical-align: top;">Status:</td>
                    <td style="padding: 5px 0; color: {status_color}; font-weight: bold;">{status_icon} {self.status.title()}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: #666; vertical-align: top;">URL:</td>
                    <td style="padding: 5px 0;"><a href="{self.url}" target="_blank" style="color: #3498db; text-decoration: none;">{self.url}</a></td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: #666; vertical-align: top;">Endpoints:</td>
                    <td style="padding: 5px 0;">{endpoints_html}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: #666; vertical-align: top;">Uptime:</td>
                    <td style="padding: 5px 0;">{self.uptime}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: #666; vertical-align: top;">PID:</td>
                    <td style="padding: 5px 0;"><code>{self.pid or '-'}</code></td>
                </tr>
            </table>
            {log_preview}
            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; font-size: 12px; color: #666;">
                Try: <code>server.stdout.tail(20)</code>, <code>server.env</code>, <code>server.terminate()</code>
            </div>
        </div>
        """