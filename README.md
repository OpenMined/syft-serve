# SyftServe

**Generic FastAPI server process management and deduplication**

SyftServe provides a high-level API for creating, managing, and deduplicating FastAPI server processes. It's designed to solve the common problem of multiple applications accidentally starting duplicate servers on the same ports.

## Features

- 🚀 **Easy Server Creation** - Simple API for launching FastAPI servers
- 🔄 **Smart Deduplication** - Automatically reuse compatible servers 
- 📊 **Process Management** - Full lifecycle control (start/stop/restart/logs)
- 🔍 **Endpoint Compatibility** - Only connect to servers with required endpoints
- 💾 **Persistent Tracking** - Servers survive Python session restarts
- 🌐 **Cross-Platform** - Works on macOS, Linux, and Windows

## Quick Start

```python
from syft_serve import ServerManager
from fastapi import FastAPI

# Create a simple FastAPI app
app = FastAPI()

@app.get("/api/hello")
def hello():
    return {"message": "Hello, World!"}

# Start server with automatic deduplication
manager = ServerManager()
server = manager.create_server(
    app=app,
    endpoints=["/api/hello"],
    name="hello_server"
)

print(f"Server running on port {server.port}")
print(f"Health check: {server.health_check()}")
print(f"Logs: {server.get_logs()}")
```

## Architecture

SyftServe is designed as a foundation for other packages that need reliable FastAPI server management:

- **syft-widget**: Uses syft-serve for widget server deduplication
- **syft-apps**: Uses syft-serve for application server management
- **Your package**: Can use syft-serve for any FastAPI server needs

## Installation

```bash
pip install syft-serve
```

## Documentation

See the [full documentation](https://docs.syft-serve.org) for detailed usage examples and API reference.