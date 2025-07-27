# SyftServe Documentation

This is the documentation website for SyftServe - the simplest way to create and manage FastAPI servers.

## Overview

SyftServe provides just two functions:
- `create()` - Launch a new server
- `terminate_all()` - Stop all servers

## Key Features

- 🚀 **Instant servers** - From Python function to running API in one line
- 📦 **Isolated environments** - Each server gets its own dependencies  
- 📝 **Named access** - No more port confusion
- 🔍 **Easy logs** - `server.stdout.tail(20)`
- 💪 **Persistent** - Servers survive notebook restarts
- 🧹 **Clean shutdown** - Properly terminates all processes

## Quick Example

```python
import syft_serve as ss

# Define an endpoint
def hello():
    return {"message": "Hello World!"}

# Create a server
server = ss.create(
    name="my_api",
    endpoints={"/hello": hello}
)

# Access it
print(f"Server running at {server.url}")
```

## Documentation Structure

- `index.html` - Main landing page
- `quickstart.html` - 1-minute quick start guide
- `server-features.html` - Detailed features and capabilities
- `api/index.html` - Complete API reference
- `tutorial.ipynb` - Comprehensive Jupyter notebook tutorial

## Building the Docs

The documentation is static HTML/CSS/JS. To serve locally:

```bash
cd docs
python -m http.server 8080
```

Then visit http://localhost:8080

## Contributing

To update the documentation:
1. Edit the HTML files directly
2. Keep the same visual style and tone
3. Test locally before submitting PR