"""
ServerCollection - simplified collection of servers with dict-like access
"""

from typing import List, Optional, Iterator, Union

from .server import Server


class ServerCollection:
    """Collection of servers with name and index access"""
    
    def __init__(self, manager_or_callable):
        # Accept either a manager instance or a callable that returns one
        if callable(manager_or_callable):
            self._manager_func = manager_or_callable
        else:
            self._manager_func = lambda: manager_or_callable
    
    @property
    def _manager(self):
        """Get the manager instance"""
        return self._manager_func()
    
    def _get_servers(self) -> List[Server]:
        """Get all servers as Server objects"""
        handles = self._manager.list_servers()
        return [Server(handle) for handle in handles]
    
    def __getitem__(self, key: Union[str, int]) -> Optional[Server]:
        """Access server by name or index"""
        servers = self._get_servers()
        
        if isinstance(key, str):
            # Access by name
            for server in servers:
                if server.name == key:
                    return server
            # Helpful error message
            names = [s.name for s in servers]
            if names:
                raise KeyError(
                    f"No server found with name '{key}'. "
                    f"Available servers: {', '.join(names)}"
                )
            else:
                raise KeyError(f"No servers are currently running")
                
        elif isinstance(key, int):
            # Access by index
            try:
                return servers[key]
            except IndexError:
                raise IndexError(
                    f"Server index {key} out of range. "
                    f"Valid range: 0-{len(servers)-1}"
                )
        else:
            raise TypeError(
                f"Invalid key type: {type(key).__name__}. "
                "Use string (name) or int (index)"
            )
    
    def __contains__(self, name: str) -> bool:
        """Check if server name exists"""
        try:
            self[name]
            return True
        except KeyError:
            return False
    
    def __len__(self) -> int:
        """Number of servers"""
        return len(self._get_servers())
    
    def __iter__(self) -> Iterator[Server]:
        """Iterate over servers"""
        return iter(self._get_servers())
    
    def __repr__(self) -> str:
        """Console representation - table format"""
        servers = self._get_servers()
        if not servers:
            return "No servers"
        
        # Try to use tabulate if available
        try:
            from tabulate import tabulate
            
            headers = ["Name", "Port", "Status", "Endpoints", "Uptime", "PID"]
            rows = []
            
            for server in servers:
                status_icon = "✅" if server.status == "running" else "❌"
                status = f"{status_icon} {server.status.title()}"
                endpoints = ", ".join(server.endpoints[:2])  # Show first 2
                if len(server.endpoints) > 2:
                    endpoints += f" +{len(server.endpoints)-2}"
                
                rows.append([
                    server.name,
                    server.port,
                    status,
                    endpoints or "-",
                    server.uptime,
                    server.pid or "-"
                ])
            
            table = tabulate(rows, headers=headers, tablefmt="simple", stralign="left")
            
            # Add summary
            running = len([s for s in servers if s.status == "running"])
            stopped = len(servers) - running
            summary = f"\n{len(servers)} servers ({running} running, {stopped} stopped)"
            
            return table + summary
            
        except ImportError:
            # Fallback without tabulate
            lines = []
            for i, server in enumerate(servers):
                lines.append(f"{i}. {server.name} (port {server.port}) - {server.status}")
            return '\n'.join(lines)
    
    def _repr_html_(self) -> str:
        """Jupyter notebook representation - HTML table"""
        servers = self._get_servers()
        if not servers:
            return "<p style='color: #888;'>No servers</p>"
        
        # Build HTML table
        rows = []
        for server in servers:
            status_color = "#27ae60" if server.status == "running" else "#e74c3c"
            status_icon = "✅" if server.status == "running" else "❌"
            
            endpoints = ", ".join(f"<code>{ep}</code>" for ep in server.endpoints[:2])
            if len(server.endpoints) > 2:
                endpoints += f" <em>+{len(server.endpoints)-2} more</em>"
            
            row = f"""
            <tr>
                <td style="padding: 8px;"><strong>{server.name}</strong></td>
                <td style="padding: 8px;">{server.port}</td>
                <td style="padding: 8px; color: {status_color};">{status_icon} {server.status.title()}</td>
                <td style="padding: 8px;">{endpoints or '<em>-</em>'}</td>
                <td style="padding: 8px;">{server.uptime}</td>
                <td style="padding: 8px;"><code>{server.pid or '-'}</code></td>
            </tr>
            """
            rows.append(row)
        
        # Summary
        running = len([s for s in servers if s.status == "running"])
        stopped = len(servers) - running
        
        return f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <table style="border-collapse: collapse; width: 100%; margin-bottom: 10px;">
                <thead>
                    <tr style="border-bottom: 2px solid #ddd;">
                        <th style="padding: 8px; text-align: left;">Name</th>
                        <th style="padding: 8px; text-align: left;">Port</th>
                        <th style="padding: 8px; text-align: left;">Status</th>
                        <th style="padding: 8px; text-align: left;">Endpoints</th>
                        <th style="padding: 8px; text-align: left;">Uptime</th>
                        <th style="padding: 8px; text-align: left;">PID</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
            <div style="color: #666; font-size: 14px;">
                {len(servers)} servers ({running} running, {stopped} stopped)
            </div>
        </div>
        """