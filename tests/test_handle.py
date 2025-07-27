"""Tests for the Handle class."""

import pytest
import time
from unittest.mock import Mock, patch
import psutil

from syft_serve._handle import Handle


class TestHandle:
    """Test the Handle class."""

    def test_handle_initialization(self, mock_config):
        """Test handle initialization."""
        handle = Handle(name="test_server", port=8000, pid=12345, config=mock_config)

        assert handle.name == "test_server"
        assert handle.port == 8000
        assert handle.pid == 12345
        assert handle.url == "http://localhost:8000"

    def test_handle_url_property(self, mock_config):
        """Test handle URL property."""
        handle = Handle("test", 8080, 12345, mock_config)
        assert handle.url == "http://localhost:8080"

        handle = Handle("test", 9000, 12345, mock_config)
        assert handle.url == "http://localhost:9000"

    @patch("psutil.Process")
    def test_handle_status_running(self, mock_process_class, mock_config):
        """Test handle status when process is running."""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = psutil.STATUS_RUNNING
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.status == "running"

    @patch("psutil.Process")
    def test_handle_status_terminated(self, mock_process_class, mock_config):
        """Test handle status when process is terminated."""
        mock_process = Mock()
        mock_process.is_running.return_value = False
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.status == "terminated"

    @patch("psutil.Process")
    def test_handle_status_not_found(self, mock_process_class, mock_config):
        """Test handle status when process is not found."""
        mock_process_class.side_effect = psutil.NoSuchProcess(12345)

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.status == "not_found"

    @patch("psutil.Process")
    def test_handle_uptime(self, mock_process_class, mock_config):
        """Test handle uptime calculation."""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process.create_time.return_value = time.time() - 300  # 5 minutes ago
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)
        uptime = handle.uptime

        # Should be approximately 5 minutes
        assert "5m" in uptime or "4m" in uptime  # Allow for timing variance

    @patch("psutil.Process")
    def test_handle_uptime_not_running(self, mock_process_class, mock_config):
        """Test handle uptime when process is not running."""
        mock_process_class.side_effect = psutil.NoSuchProcess(12345)

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.uptime == "-"

    @patch("psutil.Process")
    def test_handle_is_running_true(self, mock_process_class, mock_config):
        """Test is_running when process is running."""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.is_running() is True

    @patch("psutil.Process")
    def test_handle_is_running_false(self, mock_process_class, mock_config):
        """Test is_running when process is not running."""
        mock_process = Mock()
        mock_process.is_running.return_value = False
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.is_running() is False

    @patch("psutil.Process")
    def test_handle_is_running_no_such_process(self, mock_process_class, mock_config):
        """Test is_running when process doesn't exist."""
        mock_process_class.side_effect = psutil.NoSuchProcess(12345)

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.is_running() is False

    @patch("psutil.Process")
    def test_handle_terminate_success(self, mock_process_class, mock_config):
        """Test successful process termination."""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)

        with patch("os.killpg") as mock_killpg:
            handle.terminate()
            mock_killpg.assert_called_once_with(12345, 15)  # SIGTERM

    @patch("psutil.Process")
    def test_handle_terminate_not_running(self, mock_process_class, mock_config):
        """Test termination when process is not running."""
        mock_process_class.side_effect = psutil.NoSuchProcess(12345)

        handle = Handle("test", 8000, 12345, mock_config)

        # Should not raise exception
        handle.terminate()

    @patch("psutil.Process")
    def test_handle_terminate_with_kill(self, mock_process_class, mock_config):
        """Test termination with SIGKILL after timeout."""
        mock_process = Mock()
        mock_process.is_running.side_effect = [True, True, False]  # Still running after SIGTERM
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)

        with patch("os.killpg") as mock_killpg, patch("time.sleep"):

            handle.terminate()

            # Should call SIGTERM and then SIGKILL
            assert mock_killpg.call_count == 2
            mock_killpg.assert_any_call(12345, 15)  # SIGTERM
            mock_killpg.assert_any_call(12345, 9)  # SIGKILL

    def test_handle_get_process_cache(self, mock_config):
        """Test that _get_process caches the process object."""
        with patch("psutil.Process") as mock_process_class:
            mock_process = Mock()
            mock_process_class.return_value = mock_process

            handle = Handle("test", 8000, 12345, mock_config)

            # Call _get_process multiple times
            process1 = handle._get_process()
            process2 = handle._get_process()

            # Should return the same instance and only create once
            assert process1 is process2
            mock_process_class.assert_called_once_with(12345)

    def test_handle_str_representation(self, mock_config):
        """Test handle string representation."""
        handle = Handle("test_server", 8000, 12345, mock_config)
        assert str(handle) == "test_server"

    def test_handle_repr_representation(self, mock_config):
        """Test handle repr representation."""
        handle = Handle("test_server", 8000, 12345, mock_config)
        repr_str = repr(handle)

        assert "Handle" in repr_str
        assert "test_server" in repr_str
        assert "8000" in repr_str
        assert "12345" in repr_str


class TestHandleValidation:
    """Test handle input validation."""

    def test_handle_invalid_name(self, mock_config):
        """Test handle with invalid name."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            Handle("", 8000, 12345, mock_config)

        with pytest.raises(ValueError, match="Name cannot be empty"):
            Handle(None, 8000, 12345, mock_config)

    def test_handle_invalid_port(self, mock_config):
        """Test handle with invalid port."""
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            Handle("test", 0, 12345, mock_config)

        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            Handle("test", 65536, 12345, mock_config)

        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            Handle("test", -1, 12345, mock_config)

    def test_handle_invalid_pid(self, mock_config):
        """Test handle with invalid PID."""
        with pytest.raises(ValueError, match="PID must be positive"):
            Handle("test", 8000, 0, mock_config)

        with pytest.raises(ValueError, match="PID must be positive"):
            Handle("test", 8000, -1, mock_config)

    def test_handle_none_config(self):
        """Test handle with None config."""
        with pytest.raises(ValueError, match="Config cannot be None"):
            Handle("test", 8000, 12345, None)


class TestHandleEdgeCases:
    """Test handle edge cases and error scenarios."""

    @patch("psutil.Process")
    def test_handle_process_access_denied(self, mock_process_class, mock_config):
        """Test handle when process access is denied."""
        mock_process_class.side_effect = psutil.AccessDenied(12345)

        handle = Handle("test", 8000, 12345, mock_config)

        assert handle.status == "unknown"
        assert handle.is_running() is False
        assert handle.uptime == "-"

    @patch("psutil.Process")
    def test_handle_zombie_process(self, mock_process_class, mock_config):
        """Test handle with zombie process."""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = psutil.STATUS_ZOMBIE
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.status == "zombie"

    @patch("psutil.Process")
    def test_handle_terminate_permission_error(self, mock_process_class, mock_config):
        """Test termination with permission error."""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)

        with patch("os.killpg", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                handle.terminate()

    @patch("psutil.Process")
    def test_handle_uptime_with_exception(self, mock_process_class, mock_config):
        """Test uptime calculation with exception."""
        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process.create_time.side_effect = psutil.AccessDenied(12345)
        mock_process_class.return_value = mock_process

        handle = Handle("test", 8000, 12345, mock_config)
        assert handle.uptime == "-"


class TestHandleClassMethods:
    """Test handle class methods."""

    def test_handle_from_dict(self, mock_config):
        """Test creating handle from dictionary."""
        data = {"name": "test_server", "port": 8000, "pid": 12345}

        handle = Handle.from_dict(data, mock_config)

        assert handle.name == "test_server"
        assert handle.port == 8000
        assert handle.pid == 12345

    def test_handle_to_dict(self, mock_config):
        """Test converting handle to dictionary."""
        handle = Handle("test_server", 8000, 12345, mock_config)

        data = handle.to_dict()

        expected = {
            "name": "test_server",
            "port": 8000,
            "pid": 12345,
            "url": "http://localhost:8000",
        }

        assert data == expected

    def test_handle_equality(self, mock_config):
        """Test handle equality comparison."""
        handle1 = Handle("test", 8000, 12345, mock_config)
        handle2 = Handle("test", 8000, 12345, mock_config)
        handle3 = Handle("different", 8000, 12345, mock_config)

        assert handle1 == handle2
        assert handle1 != handle3
        assert handle1 != "not_a_handle"

    def test_handle_hash(self, mock_config):
        """Test handle hash function."""
        handle1 = Handle("test", 8000, 12345, mock_config)
        handle2 = Handle("test", 8000, 12345, mock_config)

        assert hash(handle1) == hash(handle2)

        # Should be usable in sets/dicts
        handle_set = {handle1, handle2}
        assert len(handle_set) == 1
