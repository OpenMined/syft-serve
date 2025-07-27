"""
Process discovery for finding all syft-serve servers
"""

import psutil
import requests
from typing import List, Dict, Any


def discover_syft_serve_processes() -> List[Dict[str, Any]]:
    """
    Discover all syft-serve processes by checking:
    1. Process command lines for uvicorn patterns
    2. Processes listening on ports 8000-9999
    3. Processes that respond to /health endpoint
    """
    discovered = []

    # Check all Python processes
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] and "python" in proc.info["name"].lower():
                cmdline = proc.info.get("cmdline", [])
                if cmdline and any("uvicorn" in str(arg) for arg in cmdline):
                    # This might be a uvicorn server
                    # Check if it's listening on any ports
                    try:
                        connections = proc.connections(kind="inet")
                        for conn in connections:
                            if conn.status == "LISTEN" and 8000 <= conn.laddr.port <= 9999:
                                # Try to verify it's a syft-serve server
                                server_info = {
                                    "pid": proc.pid,
                                    "port": conn.laddr.port,
                                    "cmdline": " ".join(cmdline),
                                    "process": proc,
                                }

                                # Try health check
                                try:
                                    resp = requests.get(
                                        f"http://localhost:{conn.laddr.port}/health", timeout=0.5
                                    )
                                    if resp.status_code == 200:
                                        server_info["verified"] = True
                                        server_info["health"] = "healthy"
                                    else:
                                        server_info["verified"] = False
                                        server_info["health"] = "unhealthy"
                                except Exception:
                                    server_info["verified"] = False
                                    server_info["health"] = "unreachable"

                                discovered.append(server_info)
                                break  # Only need one port per process
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return discovered


def terminate_all_syft_serve_processes(force: bool = True) -> Dict[str, Any]:
    """
    Find and terminate all syft-serve processes

    Returns dict with:
    - discovered: number of processes found
    - terminated: number successfully terminated
    - failed: list of PIDs that couldn't be terminated
    """
    import os
    import signal
    import time

    processes = discover_syft_serve_processes()
    result = {"discovered": len(processes), "terminated": 0, "failed": []}

    for proc_info in processes:
        proc = proc_info["process"]
        pid = proc_info["pid"]

        try:
            # Try to kill the process group first (if it's a session leader)
            try:
                os.killpg(pid, signal.SIGTERM)
                time.sleep(0.2)

                # Check if still alive
                if proc.is_running():
                    os.killpg(pid, signal.SIGKILL)
                    time.sleep(0.1)
            except (ProcessLookupError, PermissionError):
                # Fall back to killing just the process
                proc.terminate()
                proc.wait(timeout=1.0)

                if proc.is_running():
                    proc.kill()
                    proc.wait(timeout=0.5)

            if not proc.is_running():
                result["terminated"] += 1
            else:
                result["failed"].append(pid)

        except Exception as e:
            print(f"Failed to terminate PID {pid}: {e}")
            result["failed"].append(pid)

    return result
