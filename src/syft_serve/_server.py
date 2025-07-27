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
        except Exception:
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
    
    @property
    def expiration_info(self) -> str:
        """Human-readable expiration information"""
        if not hasattr(self._handle, 'expiration_seconds'):
            return "Unknown"
        
        if self._handle.expiration_seconds == -1:
            return "Never"
        
        # Calculate remaining time
        elapsed = time.time() - self._handle.created_at
        remaining = self._handle.expiration_seconds - elapsed
        
        if remaining <= 0:
            return "Expired"
        
        # Format remaining time
        if remaining < 60:
            return f"{int(remaining)}s"
        elif remaining < 3600:
            minutes = int(remaining // 60)
            return f"{minutes}m"
        elif remaining < 86400:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
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
    def terminate(self, timeout: float = 5.0) -> None:
        """Terminate the server completely
        
        Args:
            timeout: Maximum time to wait for graceful shutdown (default: 5.0 seconds)
        """
        self._handle.terminate(timeout=timeout)
    
    def force_terminate(self) -> None:
        """Nuclear option - forcefully kill the server process
        
        Uses OS-level commands to ensure termination. Use only when terminate() fails.
        """
        self._handle.force_terminate()
    
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
        # Get expiration info
        expiration = self.expiration_info
        expiration_emoji = "♾️" if expiration == "Never" else "⏰"
        if expiration == "Expired":
            expiration_emoji = "💀"
        
        lines = [
            f"Server: {self.name}",
            f"├── Status: {status_icon} {self.status.title()}",
            f"├── URL: {self.url}",
            f"├── Endpoints: {', '.join(self.endpoints) if self.endpoints else 'none'}",
            f"├── Uptime: {self.uptime}",
            f"├── Expires: {expiration_emoji} {expiration}",
            f"└── PID: {self.pid or '-'}"
        ]
        return '\n'.join(lines)
    
    def _repr_html_(self) -> str:
        """Jupyter notebook representation"""
        # Detect dark mode
        from jupyter_dark_detect import is_dark
        is_dark_mode = is_dark()
        
        # Theme-aware colors
        if is_dark_mode:
            # Dark mode colors
            bg_color = "#1e1e1e"
            border_color = "#3e3e3e"
            text_color = "#e0e0e0"
            label_color = "#a0a0a0"
            code_bg = "#2d2d2d"
            log_bg = "#1a1a1a"
            error_bg = "#1a1a1a"
            link_color = "#66b3ff"
        else:
            # Light mode colors
            bg_color = "#ffffff"
            border_color = "#ddd"
            text_color = "#333"
            label_color = "#666"
            code_bg = "#f8f9fa"
            log_bg = "#f8f9fa"
            error_bg = "#fef2f2"
            link_color = "#3498db"
        
        status_color = "#27ae60" if self.status == "running" else "#e74c3c"
        status_icon = "✅" if self.status == "running" else "❌"
        
        # Get expiration info
        expiration = self.expiration_info
        expiration_emoji = "♾️" if expiration == "Never" else "⏰"
        expiration_color = "#666"
        if expiration == "Never":
            expiration_color = "#059669"
        elif expiration == "Expired":
            expiration_emoji = "💀"
            expiration_color = "#dc2626"
        elif expiration != "Unknown":
            # Parse time to determine urgency
            if "s" in expiration or ("m" in expiration and "h" not in expiration):
                # Less than 1 hour - urgent
                expiration_color = "#ea580c"
            elif "h" in expiration and "d" not in expiration:
                # Less than 1 day - warning
                expiration_color = "#f59e0b"
        
        endpoints_html = ""
        if self.endpoints:
            endpoint_items = "".join(f"<li><code>{ep}</code></li>" for ep in self.endpoints)
            endpoints_html = f"<ul style='margin: 0; padding-left: 20px;'>{endpoint_items}</ul>"
        else:
            endpoints_html = "<em style='color: #888;'>No endpoints</em>"
        
        # Get recent logs preview for both stdout and stderr
        recent_stdout = self.stdout.tail(3)
        recent_stderr = self.stderr.tail(3)
        
        logs_section = ""
        if recent_stdout or recent_stderr:
            stdout_html = ""
            stderr_html = ""
            
            if recent_stdout:
                stdout_lines = recent_stdout.split('\n')
                log_text_color = "#9ca3af" if is_dark_mode else "#374151"
                stdout_html = '<br>'.join(f"<span style='color: {log_text_color}; font-family: monospace;'>{line}</span>" for line in stdout_lines[:3])
            else:
                stdout_html = "<em style='color: #888;'>No recent output</em>"
                
            if recent_stderr:
                stderr_lines = recent_stderr.split('\n')
                error_text_color = "#ff6b6b" if is_dark_mode else "#d73a49"
                stderr_html = '<br>'.join(f"<span style='color: {error_text_color}; font-family: monospace;'>{line}</span>" for line in stderr_lines[:3])
            else:
                stderr_html = "<em style='color: #888;'>No recent errors</em>"
            
            logs_section = f"""
            <div style="margin-top: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div style="padding: 8px; background: {log_bg}; border-radius: 3px; border: 1px solid {border_color};">
                    <div style="color: {label_color}; font-size: 11px; margin-bottom: 5px;">Recent logs:</div>
                    <div style="font-size: 11px; color: {text_color};">{stdout_html}</div>
                </div>
                <div style="padding: 8px; background: {error_bg}; border-radius: 3px; border: 1px solid {border_color};">
                    <div style="color: {label_color}; font-size: 11px; margin-bottom: 5px;">Recent errors:</div>
                    <div style="font-size: 11px;">{stderr_html}</div>
                </div>
            </div>
            """
        
        return f"""
        <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 5px; padding: 15px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: {text_color};">🚀 {self.name}</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: {label_color}; vertical-align: top;">Status:</td>
                    <td style="padding: 5px 0; color: {status_color}; font-weight: bold;">{status_icon} {self.status.title()}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: {label_color}; vertical-align: top;">URL:</td>
                    <td style="padding: 5px 0;"><a href="{self.url}" target="_blank" style="color: {link_color}; text-decoration: none;">{self.url}</a></td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: {label_color}; vertical-align: top;">Endpoints:</td>
                    <td style="padding: 5px 0; color: {text_color};">{endpoints_html}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: {label_color}; vertical-align: top;">Uptime:</td>
                    <td style="padding: 5px 0; color: {text_color};">{self.uptime}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: {label_color}; vertical-align: top;">Expires In:</td>
                    <td style="padding: 5px 0; font-weight: bold; color: {expiration_color};">{expiration_emoji} {expiration}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0; color: {label_color}; vertical-align: top;">PID:</td>
                    <td style="padding: 5px 0;"><code style="background: {code_bg}; padding: 2px 4px; border-radius: 3px; color: {text_color};">{self.pid or '-'}</code></td>
                </tr>
            </table>
            {logs_section}
            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid {border_color}; font-size: 12px; color: {label_color};">
                Try: <code style="background: {code_bg}; padding: 2px 4px; border-radius: 3px;">server.stdout.tail(20)</code>, <code style="background: {code_bg}; padding: 2px 4px; border-radius: 3px;">server.stderr.tail(20)</code>, <code style="background: {code_bg}; padding: 2px 4px; border-radius: 3px;">server.env</code>, <code style="background: {code_bg}; padding: 2px 4px; border-radius: 3px;">server.terminate()</code>
            </div>
        </div>
        """