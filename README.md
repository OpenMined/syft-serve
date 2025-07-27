# syft-serve

**Self-hosting should be effortless**

Turn any Python function into a self-hosted server in one line. No DevOps required.

```python
import syft_serve as ss
import requests

def hello():
    return "Hi!"

server = ss.create("my_api", {"/": hello})

requests.get(server.url).text  # "Hi!"
```

## Installation

```bash
pip install syft-serve
```

## Why syft-serve?

☁️ **The cloud isn't yours** - Not your computer, not your control  
🏠 **Yours is inconvenient** - Self-hosting means wrestling with configs  
✨ **Convenience is possible** - Self-hosting should be a 1-liner

## What it does

```python
# You write:
server = ss.create("my_api", {"/predict": my_function})

# Behind the scenes:
# ✓ Spins up isolated Python environment
# ✓ Installs your dependencies safely  
# ✓ Generates production-ready FastAPI code
# ✓ Manages server process lifecycle
# ✓ Streams logs for easy debugging
# ✓ Cleans up everything when done

# No orphan processes. No port conflicts. No hassle.
```

## Documentation

📖 **[Full documentation and examples](https://openmined.github.io/syft-serve/)**

See interactive tutorials, videos, and complete API reference.

## License

Apache 2.0 - see [LICENSE](LICENSE) file for details.