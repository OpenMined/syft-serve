"""
Process management utilities for syft-serve.
Handles process discovery, termination, and cleanup.
"""

import os
import signal
import subprocess
import time
from typing import List, Optional, Dict, Any
import psutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessInfo:
    """Information about a process"""
    pid: int
    name: str
    cmdline: List[str]
    create_time: float
    status: str
    port: Optional[int] = None
    
    @classmethod
    def from_psutil(cls, process: psutil.Process) -> 'ProcessInfo':
        """Create ProcessInfo from psutil.Process"""
        try:
            return cls(
                pid=process.pid,
                name=process.name(),
                cmdline=process.cmdline(),
                create_time=process.create_time(),
                status=process.status()
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None


class ProcessManager:
    """System-wide process management for syft-serve"""
    
    @staticmethod
    def find_uvicorn_processes() -> List[ProcessInfo]:
        """Find all uvicorn processes on the system"""
        uvicorn_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Check if it's a uvicorn process
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('uvicorn' in str(arg) for arg in cmdline):
                        info = ProcessInfo.from_psutil(proc)
                        if info:
                            uvicorn_processes.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            # Fallback to subprocess if psutil fails
            return ProcessManager._find_processes_with_ps('uvicorn')
            
        return uvicorn_processes
    
    @staticmethod
    def find_processes_by_port(port: int) -> List[ProcessInfo]:
        """Find all processes listening on a specific port"""
        processes = []
        
        try:
            # This can hang or fail with permission issues on some systems
            # Set a short internal timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Port check timed out")
            
            # Set 2 second timeout for this operation
            old_handler = signal.signal(signal.SIGALRM, timeout_handler) if hasattr(signal, 'SIGALRM') else None
            if old_handler is not None:
                signal.alarm(2)
            
            try:
                for conn in psutil.net_connections(kind='inet'):
                    if conn.laddr.port == port and conn.status == 'LISTEN':
                        try:
                            proc = psutil.Process(conn.pid)
                            info = ProcessInfo.from_psutil(proc)
                            if info:
                                info.port = port
                                processes.append(info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
            finally:
                # Cancel alarm
                if old_handler is not None:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
        except Exception:
            # Fallback to lsof/netstat
            return ProcessManager._find_processes_by_port_fallback(port)
            
        return processes
    
    @staticmethod
    def kill_process_tree(pid: int, timeout: float = 5.0) -> bool:
        """
        Kill a process and all its children.
        
        Args:
            pid: Process ID to kill
            timeout: Time to wait for graceful shutdown before force kill
            
        Returns:
            True if all processes were terminated successfully
        """
        try:
            # Get the process and all its children
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            all_procs = children + [parent]
            
            # Send SIGTERM to all processes
            for proc in all_procs:
                try:
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Wait for graceful termination
            gone, alive = psutil.wait_procs(all_procs, timeout=timeout)
            
            # Force kill any remaining processes
            for proc in alive:
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Final wait
            gone, alive = psutil.wait_procs(alive, timeout=1)
            
            return len(alive) == 0
            
        except psutil.NoSuchProcess:
            # Process already dead
            return True
        except Exception:
            # Fallback to OS-specific commands
            return ProcessManager._kill_process_tree_fallback(pid)
    
    @staticmethod
    def kill_process_group(pgid: int, timeout: float = 5.0) -> bool:
        """
        Kill an entire process group.
        
        Args:
            pgid: Process group ID
            timeout: Time to wait for graceful shutdown
            
        Returns:
            True if successful
        """
        try:
            # Send SIGTERM to the process group
            os.killpg(pgid, signal.SIGTERM)
            
            # Wait for processes to terminate
            time.sleep(min(timeout, 2.0))
            
            # Check if any processes remain
            try:
                os.killpg(pgid, 0)  # Check if group exists
                # Group still exists, force kill
                os.killpg(pgid, signal.SIGKILL)
                time.sleep(0.5)
            except ProcessLookupError:
                # Group is gone
                return True
                
            # Final check
            try:
                os.killpg(pgid, 0)
                return False  # Still alive
            except ProcessLookupError:
                return True  # Dead
                
        except Exception:
            return False
    
    @staticmethod
    def cleanup_orphaned_processes(name_pattern: str = "uvicorn", 
                                 port_range: Optional[range] = None) -> int:
        """
        Find and kill orphaned server processes.
        
        Args:
            name_pattern: Process name pattern to search for
            port_range: Optional range of ports to check
            
        Returns:
            Number of processes cleaned up
        """
        killed_count = 0
        
        # Find processes by name
        orphans = []
        if name_pattern:
            orphans.extend(ProcessManager.find_uvicorn_processes())
        
        # Find processes by ports
        if port_range:
            for port in port_range:
                orphans.extend(ProcessManager.find_processes_by_port(port))
        
        # Remove duplicates
        seen_pids = set()
        unique_orphans = []
        for proc in orphans:
            if proc.pid not in seen_pids:
                seen_pids.add(proc.pid)
                unique_orphans.append(proc)
        
        # Kill orphaned processes
        for proc_info in unique_orphans:
            if ProcessManager.kill_process_tree(proc_info.pid):
                killed_count += 1
                
        return killed_count
    
    @staticmethod
    def verify_process_dead(pid: int, timeout: float = 2.0) -> bool:
        """
        Verify that a process is actually dead.
        
        Args:
            pid: Process ID to check
            timeout: Maximum time to wait
            
        Returns:
            True if process is dead
        """
        try:
            proc = psutil.Process(pid)
            proc.wait(timeout=timeout)
            return True
        except psutil.NoSuchProcess:
            return True
        except psutil.TimeoutExpired:
            return False
        except Exception:
            # Fallback check
            return ProcessManager._is_process_dead_fallback(pid)
    
    # Fallback methods for systems without psutil
    
    @staticmethod
    def _find_processes_with_ps(pattern: str) -> List[ProcessInfo]:
        """Fallback: Find processes using ps command"""
        processes = []
        try:
            cmd = f"ps aux | grep {pattern} | grep -v grep"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(None, 10)
                    if len(parts) > 10:
                        pid = int(parts[1])
                        processes.append(ProcessInfo(
                            pid=pid,
                            name=pattern,
                            cmdline=[parts[10]],
                            create_time=0,
                            status='running'
                        ))
        except Exception:
            pass
        return processes
    
    @staticmethod
    def _find_processes_by_port_fallback(port: int) -> List[ProcessInfo]:
        """Fallback: Find processes by port using lsof or netstat"""
        processes = []
        try:
            # Try lsof first (macOS/Linux)
            cmd = f"lsof -i :{port} -sTCP:LISTEN -t"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1.0)
            
            if result.stdout:
                for pid_str in result.stdout.strip().split('\n'):
                    if pid_str:
                        pid = int(pid_str)
                        processes.append(ProcessInfo(
                            pid=pid,
                            name='unknown',
                            cmdline=[],
                            create_time=0,
                            status='running',
                            port=port
                        ))
        except subprocess.TimeoutExpired:
            # Don't wait for lsof if it's slow
            pass
        except Exception:
            pass
        return processes
    
    @staticmethod
    def _kill_process_tree_fallback(pid: int) -> bool:
        """Fallback: Kill process tree using OS commands"""
        try:
            # Try to kill the process group
            os.kill(-pid, signal.SIGTERM)
            time.sleep(2)
            os.kill(-pid, signal.SIGKILL)
            return True
        except Exception:
            try:
                # Simple kill
                os.kill(pid, signal.SIGKILL)
                return True
            except:
                return False
    
    @staticmethod
    def _is_process_dead_fallback(pid: int) -> bool:
        """Fallback: Check if process is dead"""
        try:
            os.kill(pid, 0)
            return False  # Process exists
        except ProcessLookupError:
            return True  # Process is dead
        except Exception:
            return False  # Assume alive if we can't check