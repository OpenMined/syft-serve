"""Tests for the process discovery module."""
from unittest.mock import Mock, patch
import psutil

from syft_serve._process_discovery import (
    discover_syft_serve_processes,
    is_syft_serve_process,
    terminate_orphaned_processes
)


class TestProcessDiscovery:
    """Test process discovery functionality."""
    
    @patch('psutil.process_iter')
    def test_discover_syft_serve_processes(self, mock_process_iter):
        """Test discovering syft-serve processes."""
        # Create mock processes
        syft_process = Mock()
        syft_process.info = {
            'pid': 12345,
            'name': 'python',
            'cmdline': ['python', '-m', 'uvicorn', 'app:app', '--port', '8000'],
            'create_time': 1234567890.0
        }
        
        other_process = Mock()
        other_process.info = {
            'pid': 12346,
            'name': 'python',
            'cmdline': ['python', 'other_script.py'],
            'create_time': 1234567890.0
        }
        
        mock_process_iter.return_value = [syft_process, other_process]
        
        processes = discover_syft_serve_processes()
        
        assert len(processes) == 1
        assert processes[0]['pid'] == 12345
        assert 'uvicorn' in ' '.join(processes[0]['cmdline'])
    
    @patch('psutil.process_iter')
    def test_discover_no_processes(self, mock_process_iter):
        """Test discovering when no syft-serve processes exist."""
        other_process = Mock()
        other_process.info = {
            'pid': 12346,
            'name': 'python',
            'cmdline': ['python', 'other_script.py'],
            'create_time': 1234567890.0
        }
        
        mock_process_iter.return_value = [other_process]
        
        processes = discover_syft_serve_processes()
        
        assert len(processes) == 0
    
    @patch('psutil.process_iter')
    def test_discover_with_access_denied(self, mock_process_iter):
        """Test discovery when access is denied to some processes."""
        syft_process = Mock()
        syft_process.info = {
            'pid': 12345,
            'name': 'python',
            'cmdline': ['python', '-m', 'uvicorn', 'app:app'],
            'create_time': 1234567890.0
        }
        
        # Process that raises AccessDenied
        denied_process = Mock()
        denied_process.side_effect = psutil.AccessDenied(12347)
        
        mock_process_iter.return_value = [syft_process, denied_process]
        
        processes = discover_syft_serve_processes()
        
        # Should still find the accessible syft-serve process
        assert len(processes) == 1
        assert processes[0]['pid'] == 12345
    
    @patch('psutil.process_iter')
    def test_discover_with_no_such_process(self, mock_process_iter):
        """Test discovery when process disappears during iteration."""
        syft_process = Mock()
        syft_process.info = {
            'pid': 12345,
            'name': 'python',
            'cmdline': ['python', '-m', 'uvicorn', 'app:app'],
            'create_time': 1234567890.0
        }
        
        # Process that no longer exists
        missing_process = Mock()
        missing_process.side_effect = psutil.NoSuchProcess(12348)
        
        mock_process_iter.return_value = [syft_process, missing_process]
        
        processes = discover_syft_serve_processes()
        
        assert len(processes) == 1
        assert processes[0]['pid'] == 12345


class TestIsSyftServeProcess:
    """Test is_syft_serve_process function."""
    
    def test_is_syft_serve_uvicorn_process(self):
        """Test identifying uvicorn process as syft-serve."""
        process_info = {
            'name': 'python',
            'cmdline': ['python', '-m', 'uvicorn', 'app:app', '--port', '8000']
        }
        
        assert is_syft_serve_process(process_info) is True
    
    def test_is_syft_serve_direct_uvicorn(self):
        """Test identifying direct uvicorn command."""
        process_info = {
            'name': 'uvicorn',
            'cmdline': ['uvicorn', 'app:app', '--host', '0.0.0.0']
        }
        
        assert is_syft_serve_process(process_info) is True
    
    def test_is_not_syft_serve_process(self):
        """Test identifying non-syft-serve process."""
        process_info = {
            'name': 'python',
            'cmdline': ['python', 'regular_script.py']
        }
        
        assert is_syft_serve_process(process_info) is False
    
    def test_is_syft_serve_with_app_pattern(self):
        """Test identifying process with syft-serve app pattern."""
        process_info = {
            'name': 'python',
            'cmdline': ['python', '-m', 'uvicorn', 'generated_app:app']
        }
        
        assert is_syft_serve_process(process_info) is True
    
    def test_is_syft_serve_with_server_name(self):
        """Test identifying process with server name in cmdline."""
        process_info = {
            'name': 'python',
            'cmdline': ['python', '-m', 'uvicorn', 'app:app', '--syft-serve-name', 'my_server']
        }
        
        # Note: This might be an old pattern, but test it for completeness
        assert is_syft_serve_process(process_info) is True
    
    def test_is_not_syft_serve_empty_cmdline(self):
        """Test with empty command line."""
        process_info = {
            'name': 'python',
            'cmdline': []
        }
        
        assert is_syft_serve_process(process_info) is False
    
    def test_is_not_syft_serve_none_cmdline(self):
        """Test with None command line."""
        process_info = {
            'name': 'python',
            'cmdline': None
        }
        
        assert is_syft_serve_process(process_info) is False
    
    def test_is_syft_serve_case_insensitive(self):
        """Test case insensitive matching."""
        process_info = {
            'name': 'Python',
            'cmdline': ['Python', '-m', 'UVICORN', 'app:app']
        }
        
        assert is_syft_serve_process(process_info) is True


class TestTerminateOrphanedProcesses:
    """Test orphaned process termination."""
    
    @patch('syft_serve._process_discovery.discover_syft_serve_processes')
    @patch('psutil.Process')
    def test_terminate_orphaned_processes(self, mock_process_class, mock_discover):
        """Test terminating orphaned processes."""
        # Mock discovered processes
        orphaned_processes = [
            {
                'pid': 12345,
                'name': 'python',
                'cmdline': ['python', '-m', 'uvicorn', 'app:app']
            },
            {
                'pid': 12346,
                'name': 'uvicorn',
                'cmdline': ['uvicorn', 'app:app']
            }
        ]
        mock_discover.return_value = orphaned_processes
        
        # Mock Process objects
        mock_processes = []
        for proc_info in orphaned_processes:
            mock_proc = Mock()
            mock_proc.pid = proc_info['pid']
            mock_proc.terminate.return_value = None
            mock_processes.append(mock_proc)
        
        mock_process_class.side_effect = mock_processes
        
        terminated_count = terminate_orphaned_processes()
        
        assert terminated_count == 2
        for mock_proc in mock_processes:
            mock_proc.terminate.assert_called_once()
    
    @patch('syft_serve._process_discovery.discover_syft_serve_processes')
    @patch('psutil.Process')
    def test_terminate_with_no_such_process(self, mock_process_class, mock_discover):
        """Test termination when process no longer exists."""
        orphaned_processes = [
            {
                'pid': 12345,
                'name': 'python',
                'cmdline': ['python', '-m', 'uvicorn', 'app:app']
            }
        ]
        mock_discover.return_value = orphaned_processes
        
        # Process no longer exists
        mock_process_class.side_effect = psutil.NoSuchProcess(12345)
        
        terminated_count = terminate_orphaned_processes()
        
        # Should handle gracefully and return 0
        assert terminated_count == 0
    
    @patch('syft_serve._process_discovery.discover_syft_serve_processes')
    @patch('psutil.Process')
    def test_terminate_with_access_denied(self, mock_process_class, mock_discover):
        """Test termination when access is denied."""
        orphaned_processes = [
            {
                'pid': 12345,
                'name': 'python',
                'cmdline': ['python', '-m', 'uvicorn', 'app:app']
            }
        ]
        mock_discover.return_value = orphaned_processes
        
        mock_proc = Mock()
        mock_proc.terminate.side_effect = psutil.AccessDenied(12345)
        mock_process_class.return_value = mock_proc
        
        terminated_count = terminate_orphaned_processes()
        
        # Should handle gracefully and return 0
        assert terminated_count == 0
    
    @patch('syft_serve._process_discovery.discover_syft_serve_processes')
    def test_terminate_no_orphaned_processes(self, mock_discover):
        """Test termination when no orphaned processes exist."""
        mock_discover.return_value = []
        
        terminated_count = terminate_orphaned_processes()
        
        assert terminated_count == 0
    
    @patch('syft_serve._process_discovery.discover_syft_serve_processes')
    @patch('psutil.Process')
    def test_terminate_partial_success(self, mock_process_class, mock_discover):
        """Test termination with partial success."""
        orphaned_processes = [
            {'pid': 12345, 'name': 'python', 'cmdline': ['python', '-m', 'uvicorn']},
            {'pid': 12346, 'name': 'python', 'cmdline': ['python', '-m', 'uvicorn']},
            {'pid': 12347, 'name': 'python', 'cmdline': ['python', '-m', 'uvicorn']}
        ]
        mock_discover.return_value = orphaned_processes
        
        # First succeeds, second fails with NoSuchProcess, third succeeds
        mock_proc1 = Mock()
        mock_proc1.terminate.return_value = None
        
        mock_proc3 = Mock()
        mock_proc3.terminate.return_value = None
        
        mock_process_class.side_effect = [
            mock_proc1,
            psutil.NoSuchProcess(12346),
            mock_proc3
        ]
        
        terminated_count = terminate_orphaned_processes()
        
        assert terminated_count == 2  # Two successful terminations


class TestProcessDiscoveryEdgeCases:
    """Test edge cases in process discovery."""
    
    @patch('psutil.process_iter')
    def test_discover_with_malformed_cmdline(self, mock_process_iter):
        """Test discovery with malformed command line."""
        malformed_process = Mock()
        malformed_process.info = {
            'pid': 12345,
            'name': 'python',
            'cmdline': ['python', '-m'],  # Incomplete command
            'create_time': 1234567890.0
        }
        
        mock_process_iter.return_value = [malformed_process]
        
        processes = discover_syft_serve_processes()
        
        # Should not match incomplete commands
        assert len(processes) == 0
    
    @patch('psutil.process_iter')
    def test_discover_with_missing_fields(self, mock_process_iter):
        """Test discovery with missing process info fields."""
        incomplete_process = Mock()
        incomplete_process.info = {
            'pid': 12345,
            'name': 'python'
            # Missing cmdline and create_time
        }
        
        mock_process_iter.return_value = [incomplete_process]
        
        processes = discover_syft_serve_processes()
        
        # Should handle gracefully
        assert len(processes) == 0
    
    def test_is_syft_serve_with_unicode_cmdline(self):
        """Test process identification with unicode in command line."""
        process_info = {
            'name': 'python',
            'cmdline': ['python', '-m', 'uvicorn', 'café_app:app']
        }
        
        assert is_syft_serve_process(process_info) is True
    
    def test_is_syft_serve_with_complex_args(self):
        """Test process identification with complex arguments."""
        process_info = {
            'name': 'python',
            'cmdline': [
                'python', '-m', 'uvicorn', 'app:app',
                '--host', '0.0.0.0',
                '--port', '8000',
                '--workers', '4',
                '--log-level', 'info'
            ]
        }
        
        assert is_syft_serve_process(process_info) is True


class TestProcessDiscoveryIntegration:
    """Integration tests for process discovery."""
    
    @patch('psutil.process_iter')
    @patch('psutil.Process')
    def test_full_discovery_and_termination_flow(self, mock_process_class, mock_process_iter):
        """Test complete discovery and termination flow."""
        # Setup discovered processes
        syft_process1 = Mock()
        syft_process1.info = {
            'pid': 12345,
            'name': 'python',
            'cmdline': ['python', '-m', 'uvicorn', 'app1:app'],
            'create_time': 1234567890.0
        }
        
        syft_process2 = Mock()
        syft_process2.info = {
            'pid': 12346,
            'name': 'uvicorn',
            'cmdline': ['uvicorn', 'app2:app'],
            'create_time': 1234567891.0
        }
        
        other_process = Mock()
        other_process.info = {
            'pid': 12347,
            'name': 'python',
            'cmdline': ['python', 'other_script.py'],
            'create_time': 1234567892.0
        }
        
        mock_process_iter.return_value = [syft_process1, syft_process2, other_process]
        
        # Setup Process mocks for termination
        mock_proc1 = Mock()
        mock_proc1.terminate.return_value = None
        mock_proc2 = Mock()
        mock_proc2.terminate.return_value = None
        
        mock_process_class.side_effect = [mock_proc1, mock_proc2]
        
        # Discover processes
        discovered = discover_syft_serve_processes()
        assert len(discovered) == 2
        
        # Terminate orphaned processes
        terminated_count = terminate_orphaned_processes()
        assert terminated_count == 2
        
        # Verify termination was called
        mock_proc1.terminate.assert_called_once()
        mock_proc2.terminate.assert_called_once()