# syft-serve

[![PyPI](https://img.shields.io/pypi/v/syft-serve.svg)](https://pypi.org/project/syft-serve/)
[![Python](https://img.shields.io/pypi/pyversions/syft-serve.svg)](https://pypi.org/project/syft-serve/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docs](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://openmined.github.io/syft-serve/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-FCC21B.svg)](https://github.com/astral-sh/ruff)
[![OpenMined](https://img.shields.io/badge/by-OpenMined-blue.svg)](https://github.com/OpenMined)

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

## See It In Action

![syft-serve Demo](https://github.com/OpenMined/syft-serve/blob/main/docs/syft_serve_demo_focused.gif?raw=true)

## Documentation

📖 **[Full documentation and examples](https://openmined.github.io/syft-serve/)**

See interactive tutorials, videos, and complete API reference.

## License

Apache 2.0 - see [LICENSE](LICENSE) file for details.