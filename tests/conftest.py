"""Test configuration and fixtures."""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Callable
import pytest
from unittest.mock import Mock, patch
import psutil

from syft_serve._config import ServerConfig
from syft_serve._server import Server
from syft_serve._handle import ServerHandle
from syft_serve._server_collection import ServerCollection


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_config(temp_dir: Path) -> ServerConfig:
    """Create a mock config with temporary directories."""
    config = ServerConfig()
    config.log_dir = temp_dir / "logs"
    config.persistence_file = temp_dir / "servers.json"
    
    # Create directories
    config.log_dir.mkdir(parents=True, exist_ok=True)
    config.persistence_file.parent.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def mock_process():
    """Create a mock psutil process."""
    process = Mock(spec=psutil.Process)
    process.pid = 12345
    process.is_running.return_value = True
    process.status.return_value = psutil.STATUS_RUNNING
    process.create_time.return_value = 1234567890.0
    process.cmdline.return_value = ["uvicorn", "app:app", "--port", "8000"]
    process.terminate.return_value = None
    process.wait.return_value = None
    return process


@pytest.fixture
def sample_endpoints() -> Dict[str, Callable]:
    """Create sample endpoint functions for testing."""
    def hello():
        return {"message": "Hello World"}
    
    def goodbye():
        return {"message": "Goodbye"}
    
    def echo(data: str):
        return {"echo": data}
    
    return {
        "/hello": hello,
        "/goodbye": goodbye,
        "/echo": echo
    }


@pytest.fixture
def mock_server(mock_config: ServerConfig, sample_endpoints: Dict[str, Callable]) -> Server:
    """Create a mock server instance."""
    handle = Mock(spec=ServerHandle)
    handle.name = "test_server"
    handle.port = 8000
    handle.pid = 12345
    handle.url = "http://localhost:8000"
    handle.status = "running"
    handle.uptime = "5m 30s"
    handle.is_running.return_value = True
    handle.terminate.return_value = None
    
    server = Server(
        handle=handle,
        endpoints=list(sample_endpoints.keys()),
        config=mock_config
    )
    return server


@pytest.fixture
def mock_server_collection(mock_config: ServerConfig) -> ServerCollection:
    """Create a mock server collection."""
    return ServerCollection(config=mock_config)


@pytest.fixture
def mock_uvicorn_process():
    """Mock a uvicorn process."""
    process = Mock()
    process.pid = 12345
    process.info = {
        'pid': 12345,
        'name': 'python',
        'cmdline': ['python', '-m', 'uvicorn', 'app:app', '--port', '8000'],
        'create_time': 1234567890.0
    }
    return process


@pytest.fixture(autouse=True)
def cleanup_env():
    """Clean up environment variables and servers after each test."""
    original_env = os.environ.copy()
    yield
    # Clean up any existing servers
    try:
        import syft_serve
        syft_serve.terminate_all()
    except Exception:
        pass  # Ignore cleanup errors
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for health check tests."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_subprocess_popen():
    """Mock subprocess.Popen for process creation tests."""
    with patch('subprocess.Popen') as mock_popen:
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_process.returncode = None
        mock_popen.return_value = mock_process
        yield mock_popen


@pytest.fixture
def mock_psutil_process_iter():
    """Mock psutil.process_iter for process discovery tests."""
    with patch('psutil.process_iter') as mock_iter:
        yield mock_iter


@pytest.fixture
def isolated_test_env(monkeypatch, temp_dir):
    """Create an isolated test environment with mocked paths."""
    # Mock the home directory and config paths
    monkeypatch.setenv("HOME", str(temp_dir))
    
    # Create a mock syft-serve directory structure
    syft_serve_dir = temp_dir / ".syft_serve"
    servers_dir = syft_serve_dir / "servers"
    logs_dir = syft_serve_dir / "logs"
    
    syft_serve_dir.mkdir()
    servers_dir.mkdir()
    logs_dir.mkdir()
    
    return {
        "temp_dir": temp_dir,
        "syft_serve_dir": syft_serve_dir,
        "servers_dir": servers_dir,
        "logs_dir": logs_dir
    }