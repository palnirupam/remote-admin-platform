"""
Unit tests for Lifecycle Plugin

Tests temporary disconnect, stop until reboot, remote uninstall, self-destruct,
and result buffering functionality.

**Validates: Requirements 13.1-13.7**
"""

import pytest
import time
import sys
import os
import platform
from unittest.mock import Mock, patch, MagicMock, mock_open, call
from remote_system.plugins.lifecycle_plugin import (
    LifecyclePlugin,
    LifecycleResult
)


@pytest.fixture
def plugin():
    """Create a LifecyclePlugin instance for testing"""
    return LifecyclePlugin()


class TestLifecyclePluginBasics:
    """Test basic plugin functionality"""
    
    def test_get_name(self, plugin):
        """Test plugin name"""
        assert plugin.get_name() == "lifecycle"
    
    def test_get_required_arguments(self, plugin):
        """Test required arguments"""
        required = plugin.get_required_arguments()
        assert 'action' in required
    
    def test_execute_invalid_action(self, plugin):
        """Test execute with invalid action"""
        with pytest.raises(ValueError, match="Invalid action"):
            plugin.execute({'action': 'invalid_action'})
    
    def test_set_uninstall_password(self, plugin):
        """Test setting uninstall password"""
        plugin.set_uninstall_password('test_password')
        assert plugin.uninstall_password == 'test_password'



class TestTemporaryDisconnect:
    """
    Test temporary disconnect and reconnect functionality
    
    **Validates: Requirements 13.1, 13.5**
    """
    
    def test_temporary_disconnect_success(self, plugin):
        """Test successful temporary disconnect with valid delay"""
        delay = 5
        result = plugin.temporary_disconnect(delay)
        
        assert result.success is True
        assert result.action == 'temporary_disconnect'
        assert f'Disconnecting for {delay} seconds' in result.message
        assert result.scheduled_time is not None
        assert result.scheduled_time > time.time()
        assert result.error is None
        assert plugin.disconnect_scheduled is True
    
    def test_temporary_disconnect_zero_delay(self, plugin):
        """Test temporary disconnect with zero delay"""
        result = plugin.temporary_disconnect(0)
        
        assert result.success is True
        assert result.action == 'temporary_disconnect'
        assert result.scheduled_time is not None
        assert plugin.disconnect_scheduled is True
    
    def test_temporary_disconnect_negative_delay(self, plugin):
        """Test temporary disconnect with negative delay (should fail)"""
        result = plugin.temporary_disconnect(-10)
        
        assert result.success is False
        assert result.action == 'temporary_disconnect'
        assert 'Delay must be non-negative' in result.error
        assert result.scheduled_time is None
    
    def test_temporary_disconnect_default_delay(self, plugin):
        """Test temporary disconnect with default delay"""
        result = plugin.temporary_disconnect()
        
        assert result.success is True
        assert result.action == 'temporary_disconnect'
        assert 'Disconnecting for 60 seconds' in result.message
    
    @patch('threading.Thread')
    def test_temporary_disconnect_thread_creation(self, mock_thread, plugin):
        """Test that disconnect creates a thread for reconnection"""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        result = plugin.temporary_disconnect(5)
        
        assert result.success is True
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    def test_execute_temporary_disconnect_action(self, plugin):
        """Test execute with temporary_disconnect action"""
        result = plugin.execute({'action': 'temporary_disconnect', 'delay': 10})
        
        assert result['success'] is True
        assert result['action'] == 'temporary_disconnect'
        assert result['scheduled_time'] is not None
    
    def test_execute_temporary_disconnect_invalid_delay(self, plugin):
        """Test execute with invalid delay type"""
        result = plugin.execute({'action': 'temporary_disconnect', 'delay': 'invalid'})
        
        # Should default to 60 seconds
        assert result['success'] is True
        assert 'Disconnecting for 60 seconds' in result['message']



class TestStopUntilReboot:
    """
    Test stop until reboot functionality
    
    **Validates: Requirements 13.2, 13.6**
    """
    
    @patch('threading.Thread')
    def test_stop_until_reboot_success(self, mock_thread, plugin):
        """Test successful stop until reboot"""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        result = plugin.stop_until_reboot()
        
        assert result.success is True
        assert result.action == 'stop_until_reboot'
        assert 'Agent will terminate in 2 seconds' in result.message
        assert result.scheduled_time is not None
        assert result.scheduled_time > time.time()
        assert result.error is None
        
        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    @patch('threading.Thread')
    @patch('sys.exit')
    def test_stop_until_reboot_termination(self, mock_exit, mock_thread, plugin):
        """Test that stop until reboot schedules termination"""
        # Capture the thread target function
        thread_target = None
        
        def capture_thread(*args, **kwargs):
            nonlocal thread_target
            thread_target = kwargs.get('target')
            mock_instance = MagicMock()
            return mock_instance
        
        mock_thread.side_effect = capture_thread
        
        result = plugin.stop_until_reboot()
        
        assert result.success is True
        assert thread_target is not None
        
        # Execute the thread target with mocked sleep
        with patch('time.sleep'):
            thread_target()
        
        # Verify sys.exit was called
        mock_exit.assert_called_once_with(0)
    
    def test_execute_stop_until_reboot_action(self, plugin):
        """Test execute with stop_until_reboot action"""
        with patch('threading.Thread'):
            result = plugin.execute({'action': 'stop_until_reboot'})
        
        assert result['success'] is True
        assert result['action'] == 'stop_until_reboot'
        assert result['scheduled_time'] is not None



class TestRemoteUninstall:
    """
    Test remote uninstall with password validation
    
    **Validates: Requirements 13.3**
    """
    
    def test_remote_uninstall_no_password_configured(self, plugin):
        """Test remote uninstall when password is not configured"""
        result = plugin.remote_uninstall('any_password')
        
        assert result.success is False
        assert result.action == 'remote_uninstall'
        assert 'Uninstall password not configured' in result.error
        assert result.scheduled_time is None
    
    def test_remote_uninstall_invalid_password(self, plugin):
        """Test remote uninstall with invalid password"""
        plugin.set_uninstall_password('correct_password')
        result = plugin.remote_uninstall('wrong_password')
        
        assert result.success is False
        assert result.action == 'remote_uninstall'
        assert 'Invalid password' in result.error
        assert result.scheduled_time is None
    
    @patch('threading.Thread')
    def test_remote_uninstall_valid_password(self, mock_thread, plugin):
        """Test remote uninstall with valid password"""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        plugin.set_uninstall_password('correct_password')
        result = plugin.remote_uninstall('correct_password')
        
        assert result.success is True
        assert result.action == 'remote_uninstall'
        assert 'Uninstalling agent in 2 seconds' in result.message
        assert result.scheduled_time is not None
        assert result.error is None
        
        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    @patch('platform.system', return_value='Windows')
    @patch('threading.Thread')
    @patch('subprocess.Popen')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.exit')
    def test_remote_uninstall_windows_execution(self, mock_exit, mock_file, 
                                                 mock_popen, mock_thread, mock_system, plugin):
        """Test remote uninstall execution on Windows"""
        # Capture the thread target function
        thread_target = None
        
        def capture_thread(*args, **kwargs):
            nonlocal thread_target
            thread_target = kwargs.get('target')
            return MagicMock()
        
        mock_thread.side_effect = capture_thread
        
        plugin.set_uninstall_password('test_password')
        result = plugin.remote_uninstall('test_password')
        
        assert result.success is True
        assert thread_target is not None
        
        # Execute the thread target with mocked dependencies
        with patch('time.sleep'), \
             patch.dict('os.environ', {'TEMP': 'C:\\Temp'}):
            thread_target()
        
        # Verify batch file was created and executed
        mock_file.assert_called()
        mock_popen.assert_called()
        mock_exit.assert_called_once_with(0)
    
    @patch('platform.system', return_value='Linux')
    @patch('threading.Thread')
    @patch('subprocess.Popen')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.chmod')
    @patch('sys.exit')
    def test_remote_uninstall_linux_execution(self, mock_exit, mock_chmod, 
                                               mock_file, mock_popen, mock_thread, 
                                               mock_system, plugin):
        """Test remote uninstall execution on Linux"""
        # Capture the thread target function
        thread_target = None
        
        def capture_thread(*args, **kwargs):
            nonlocal thread_target
            thread_target = kwargs.get('target')
            return MagicMock()
        
        mock_thread.side_effect = capture_thread
        
        plugin.set_uninstall_password('test_password')
        result = plugin.remote_uninstall('test_password')
        
        assert result.success is True
        assert thread_target is not None
        
        # Execute the thread target with mocked dependencies
        with patch('time.sleep'):
            thread_target()
        
        # Verify shell script was created and executed
        mock_file.assert_called()
        mock_chmod.assert_called_once_with('/tmp/uninstall.sh', 0o755)
        mock_popen.assert_called()
        mock_exit.assert_called_once_with(0)
    
    def test_execute_remote_uninstall_action(self, plugin):
        """Test execute with remote_uninstall action"""
        plugin.set_uninstall_password('test_password')
        
        with patch('threading.Thread'):
            result = plugin.execute({
                'action': 'remote_uninstall',
                'password': 'test_password'
            })
        
        assert result['success'] is True
        assert result['action'] == 'remote_uninstall'
    
    def test_execute_remote_uninstall_no_password(self, plugin):
        """Test execute with remote_uninstall action without password"""
        result = plugin.execute({
            'action': 'remote_uninstall',
            'password': ''
        })
        
        assert result['success'] is False
        assert 'Uninstall password not configured' in result['error']



class TestSelfDestruct:
    """
    Test self-destruct functionality
    
    **Validates: Requirements 13.4, 13.7**
    """
    
    @patch('threading.Thread')
    def test_self_destruct_success(self, mock_thread, plugin):
        """Test successful self-destruct initiation"""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        result = plugin.self_destruct()
        
        assert result.success is True
        assert result.action == 'self_destruct'
        assert 'Self-destruct initiated' in result.message
        assert result.scheduled_time is not None
        assert result.error is None
        
        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    @patch('platform.system', return_value='Windows')
    @patch('threading.Thread')
    @patch('subprocess.Popen')
    @patch('builtins.open', new_callable=mock_open)
    @patch('shutil.rmtree')
    @patch('os._exit')
    def test_self_destruct_windows_execution(self, mock_exit, mock_rmtree, 
                                             mock_file, mock_popen, mock_thread, 
                                             mock_system, plugin):
        """Test self-destruct execution on Windows"""
        # Capture the thread target function
        thread_target = None
        
        def capture_thread(*args, **kwargs):
            nonlocal thread_target
            thread_target = kwargs.get('target')
            return MagicMock()
        
        mock_thread.side_effect = capture_thread
        
        result = plugin.self_destruct()
        
        assert result.success is True
        assert thread_target is not None
        
        # Execute the thread target with mocked dependencies
        with patch('time.sleep'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.dirname', return_value='C:\\agent'), \
             patch.dict('os.environ', {'TEMP': 'C:\\Temp'}):
            thread_target()
        
        # Verify cleanup operations
        mock_rmtree.assert_called()
        mock_file.assert_called()
        mock_popen.assert_called()
        mock_exit.assert_called_once_with(0)
    
    @patch('platform.system', return_value='Linux')
    @patch('threading.Thread')
    @patch('subprocess.Popen')
    @patch('builtins.open', new_callable=mock_open)
    @patch('shutil.rmtree')
    @patch('os.chmod')
    @patch('os._exit')
    def test_self_destruct_linux_execution(self, mock_exit, mock_chmod, 
                                           mock_rmtree, mock_file, mock_popen, 
                                           mock_thread, mock_system, plugin):
        """Test self-destruct execution on Linux"""
        # Capture the thread target function
        thread_target = None
        
        def capture_thread(*args, **kwargs):
            nonlocal thread_target
            thread_target = kwargs.get('target')
            return MagicMock()
        
        mock_thread.side_effect = capture_thread
        
        result = plugin.self_destruct()
        
        assert result.success is True
        assert thread_target is not None
        
        # Execute the thread target with mocked dependencies
        with patch('time.sleep'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.dirname', return_value='/opt/agent'):
            thread_target()
        
        # Verify cleanup operations
        mock_rmtree.assert_called()
        mock_file.assert_called()
        mock_chmod.assert_called_once_with('/tmp/destruct.sh', 0o755)
        mock_popen.assert_called()
        mock_exit.assert_called_once_with(0)
    
    def test_execute_self_destruct_action(self, plugin):
        """Test execute with self_destruct action"""
        with patch('threading.Thread'):
            result = plugin.execute({'action': 'self_destruct'})
        
        assert result['success'] is True
        assert result['action'] == 'self_destruct'
        assert result['scheduled_time'] is not None



class TestResultBuffering:
    """
    Test result buffering for disconnect/reconnect scenarios
    
    **Validates: Requirements 13.5**
    """
    
    def test_buffer_result_success(self, plugin):
        """Test buffering a result"""
        test_result = {'status': 'success', 'data': 'test_data'}
        success = plugin.buffer_result(test_result)
        
        assert success is True
        assert len(plugin.result_buffer) == 1
        assert plugin.result_buffer[0]['result'] == test_result
        assert 'timestamp' in plugin.result_buffer[0]
    
    def test_buffer_multiple_results(self, plugin):
        """Test buffering multiple results"""
        results = [
            {'id': 1, 'data': 'first'},
            {'id': 2, 'data': 'second'},
            {'id': 3, 'data': 'third'}
        ]
        
        for result in results:
            success = plugin.buffer_result(result)
            assert success is True
        
        assert len(plugin.result_buffer) == 3
        
        # Verify order is preserved
        for i, buffered in enumerate(plugin.result_buffer):
            assert buffered['result']['id'] == i + 1
    
    def test_get_buffered_results(self, plugin):
        """Test retrieving buffered results"""
        # Buffer some results
        test_results = [
            {'id': 1, 'data': 'first'},
            {'id': 2, 'data': 'second'}
        ]
        
        for result in test_results:
            plugin.buffer_result(result)
        
        # Get buffered results
        buffered = plugin.get_buffered_results()
        
        assert len(buffered) == 2
        assert buffered[0]['result']['id'] == 1
        assert buffered[1]['result']['id'] == 2
        
        # Verify buffer is cleared
        assert len(plugin.result_buffer) == 0
    
    def test_get_buffered_results_empty(self, plugin):
        """Test retrieving buffered results when buffer is empty"""
        buffered = plugin.get_buffered_results()
        
        assert len(buffered) == 0
        assert isinstance(buffered, list)
    
    def test_execute_buffer_result_action(self, plugin):
        """Test execute with buffer_result action"""
        test_result = {'status': 'success', 'data': 'test'}
        
        result = plugin.execute({
            'action': 'buffer_result',
            'result': test_result
        })
        
        assert result['success'] is True
        assert result['buffer_size'] == 1
    
    def test_execute_buffer_result_no_result(self, plugin):
        """Test execute with buffer_result action without result"""
        result = plugin.execute({'action': 'buffer_result'})
        
        assert result['success'] is False
        assert 'No result provided' in result['error']
    
    def test_execute_get_buffered_results_action(self, plugin):
        """Test execute with get_buffered_results action"""
        # Buffer some results first
        plugin.buffer_result({'id': 1})
        plugin.buffer_result({'id': 2})
        
        result = plugin.execute({'action': 'get_buffered_results'})
        
        assert 'buffered_results' in result
        assert result['count'] == 2
        assert len(result['buffered_results']) == 2
    
    def test_buffer_result_with_timestamp(self, plugin):
        """Test that buffered results include timestamps"""
        before_time = time.time()
        plugin.buffer_result({'data': 'test'})
        after_time = time.time()
        
        buffered = plugin.get_buffered_results()
        
        assert len(buffered) == 1
        timestamp = buffered[0]['timestamp']
        assert before_time <= timestamp <= after_time



class TestLifecycleResultDataclass:
    """Test LifecycleResult dataclass"""
    
    def test_lifecycle_result_creation(self):
        """Test creating a LifecycleResult"""
        result = LifecycleResult(
            success=True,
            action='test_action',
            message='Test message',
            scheduled_time=time.time(),
            error=None
        )
        
        assert result.success is True
        assert result.action == 'test_action'
        assert result.message == 'Test message'
        assert result.scheduled_time is not None
        assert result.error is None
    
    def test_lifecycle_result_with_error(self):
        """Test creating a LifecycleResult with error"""
        result = LifecycleResult(
            success=False,
            action='test_action',
            message='',
            scheduled_time=None,
            error='Test error'
        )
        
        assert result.success is False
        assert result.error == 'Test error'
        assert result.scheduled_time is None


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_temporary_disconnect_large_delay(self, plugin):
        """Test temporary disconnect with very large delay"""
        large_delay = 86400  # 1 day
        result = plugin.temporary_disconnect(large_delay)
        
        assert result.success is True
        assert result.scheduled_time > time.time()
    
    def test_buffer_result_none_value(self, plugin):
        """Test buffering None as a result"""
        success = plugin.buffer_result(None)
        
        assert success is True
        buffered = plugin.get_buffered_results()
        assert buffered[0]['result'] is None
    
    def test_buffer_result_complex_object(self, plugin):
        """Test buffering complex nested objects"""
        complex_result = {
            'nested': {
                'data': [1, 2, 3],
                'info': {'key': 'value'}
            },
            'list': [{'a': 1}, {'b': 2}]
        }
        
        success = plugin.buffer_result(complex_result)
        assert success is True
        
        buffered = plugin.get_buffered_results()
        assert buffered[0]['result'] == complex_result
    
    def test_multiple_disconnect_schedules(self, plugin):
        """Test scheduling multiple disconnects"""
        result1 = plugin.temporary_disconnect(5)
        result2 = plugin.temporary_disconnect(10)
        
        assert result1.success is True
        assert result2.success is True
        assert plugin.disconnect_scheduled is True
    
    @patch('threading.Thread', side_effect=Exception('Thread creation failed'))
    def test_temporary_disconnect_thread_failure(self, mock_thread, plugin):
        """Test temporary disconnect when thread creation fails"""
        result = plugin.temporary_disconnect(5)
        
        assert result.success is False
        assert 'Failed to schedule disconnect' in result.error
    
    @patch('threading.Thread', side_effect=Exception('Thread creation failed'))
    def test_stop_until_reboot_thread_failure(self, mock_thread, plugin):
        """Test stop until reboot when thread creation fails"""
        result = plugin.stop_until_reboot()
        
        assert result.success is False
        assert 'Failed to stop agent' in result.error
