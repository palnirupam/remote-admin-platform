"""
Unit Tests for Error Recovery Module

Tests database failure handling, log buffering, plugin crash recovery,
and graceful degradation.

Requirements: 12.7, 20.1, 20.2, 20.3, 20.4
"""

import pytest
import os
import json
import time
import tempfile
import threading
from unittest.mock import Mock, MagicMock, patch
from remote_system.enhanced_server.error_recovery import (
    LogBuffer,
    DatabaseRecoveryManager,
    PluginRecoveryManager,
    GracefulDegradationManager
)


class TestLogBuffer:
    """
    Test LogBuffer class for in-memory log buffering
    
    Requirements: 12.7, 20.1, 20.2
    """
    
    def test_initialization(self):
        """Test LogBuffer initialization"""
        buffer = LogBuffer(max_size=100)
        assert buffer.max_size == 100
        assert buffer.size() == 0
    
    def test_initialization_invalid_size(self):
        """Test LogBuffer initialization with invalid size"""
        with pytest.raises(ValueError):
            LogBuffer(max_size=0)
        
        with pytest.raises(ValueError):
            LogBuffer(max_size=-1)
    
    def test_add_log_to_buffer(self):
        """Test adding logs to buffer"""
        buffer = LogBuffer(max_size=10)
        
        log_entry = {
            'log_type': 'command',
            'agent_id': 'test-agent',
            'command': 'test command'
        }
        
        result = buffer.add_log(log_entry)
        assert result is True
        assert buffer.size() == 1
    
    def test_add_log_with_timestamp(self):
        """Test that timestamp is added to log entries"""
        buffer = LogBuffer(max_size=10)
        
        log_entry = {'log_type': 'command'}
        buffer.add_log(log_entry)
        
        logs = buffer.get_all_logs()
        assert len(logs) == 1
        assert 'buffered_at' in logs[0]
    
    def test_buffer_max_capacity(self):
        """Test buffer behavior at max capacity
        
        Requirement 12.7: Buffer up to 10,000 entries
        """
        buffer = LogBuffer(max_size=5)
        
        # Fill buffer to capacity
        for i in range(5):
            result = buffer.add_log({'index': i})
            assert result is True
        
        assert buffer.size() == 5
    
    def test_overflow_to_file(self, tmp_path):
        """Test overflow logs written to file
        
        Requirement 20.2: Write overflow logs to file backup
        """
        overflow_file = tmp_path / "overflow.json"
        buffer = LogBuffer(max_size=3, overflow_file=str(overflow_file))
        
        # Fill buffer
        for i in range(3):
            buffer.add_log({'index': i})
        
        # Next log should overflow to file
        result = buffer.add_log({'index': 3, 'overflow': True})
        assert result is False
        assert overflow_file.exists()
        
        # Verify overflow file content
        with open(overflow_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            overflow_log = json.loads(lines[0])
            assert overflow_log['index'] == 3
            assert overflow_log['overflow'] is True
    
    def test_get_all_logs(self):
        """Test retrieving all buffered logs"""
        buffer = LogBuffer(max_size=10)
        
        for i in range(5):
            buffer.add_log({'index': i})
        
        logs = buffer.get_all_logs()
        assert len(logs) == 5
        assert logs[0]['index'] == 0
        assert logs[4]['index'] == 4
    
    def test_clear_buffer(self):
        """Test clearing buffer"""
        buffer = LogBuffer(max_size=10)
        
        for i in range(5):
            buffer.add_log({'index': i})
        
        count = buffer.clear()
        assert count == 5
        assert buffer.size() == 0
    
    def test_load_overflow_logs(self, tmp_path):
        """Test loading logs from overflow file"""
        overflow_file = tmp_path / "overflow.json"
        buffer = LogBuffer(max_size=2, overflow_file=str(overflow_file))
        
        # Create overflow logs
        for i in range(2):
            buffer.add_log({'index': i})
        
        # Overflow some logs
        for i in range(2, 5):
            buffer.add_log({'index': i})
        
        # Load overflow logs
        overflow_logs = buffer.load_overflow_logs()
        assert len(overflow_logs) == 3
        assert overflow_logs[0]['index'] == 2
        assert overflow_logs[2]['index'] == 4
    
    def test_clear_overflow_file(self, tmp_path):
        """Test clearing overflow file"""
        overflow_file = tmp_path / "overflow.json"
        buffer = LogBuffer(max_size=1, overflow_file=str(overflow_file))
        
        # Create overflow
        buffer.add_log({'index': 0})
        buffer.add_log({'index': 1})
        
        assert overflow_file.exists()
        
        buffer.clear_overflow_file()
        assert not overflow_file.exists()
    
    def test_thread_safety(self):
        """Test thread-safe operations on buffer"""
        buffer = LogBuffer(max_size=1000)
        
        def add_logs(start, count):
            for i in range(start, start + count):
                buffer.add_log({'thread_id': threading.current_thread().ident, 'index': i})
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_logs, args=(i * 100, 100))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert buffer.size() == 500


class TestDatabaseRecoveryManager:
    """
    Test DatabaseRecoveryManager for database failure handling
    
    Requirements: 20.1, 20.2, 20.3
    """
    
    def test_initialization(self):
        """Test DatabaseRecoveryManager initialization"""
        mock_db = Mock()
        manager = DatabaseRecoveryManager(mock_db, reconnect_interval=10)
        
        assert manager.database_manager == mock_db
        assert manager.reconnect_interval == 10
        assert manager.is_connected is True
    
    def test_check_connection_success(self):
        """Test successful connection check"""
        mock_db = Mock()
        mock_db.get_active_agents.return_value = []
        
        manager = DatabaseRecoveryManager(mock_db)
        result = manager.check_connection()
        
        assert result is True
        assert manager.is_connected is True
        mock_db.get_active_agents.assert_called_once()
    
    def test_check_connection_failure(self):
        """Test failed connection check"""
        mock_db = Mock()
        mock_db.get_active_agents.side_effect = Exception("Connection failed")
        
        manager = DatabaseRecoveryManager(mock_db)
        result = manager.check_connection()
        
        assert result is False
        assert manager.is_connected is False
    
    def test_log_with_recovery_success(self):
        """Test successful logging to database"""
        mock_db = Mock()
        mock_db.log_command.return_value = 123
        
        manager = DatabaseRecoveryManager(mock_db)
        result = manager.log_with_recovery('command', 'agent-1', 'test command')
        
        assert result == 123
        assert manager.is_connected is True
        mock_db.log_command.assert_called_once_with('agent-1', 'test command')
    
    def test_log_with_recovery_failure_buffers(self, tmp_path):
        """Test logging failure triggers buffering
        
        Requirement 20.1: Buffer logs when database fails
        """
        mock_db = Mock()
        mock_db.log_command.side_effect = Exception("Database unavailable")
        
        overflow_file = tmp_path / "overflow.json"
        manager = DatabaseRecoveryManager(
            mock_db,
            reconnect_interval=1,
            overflow_file=str(overflow_file)
        )
        
        result = manager.log_with_recovery('command', 'agent-1', 'test command')
        
        assert result is False
        assert manager.is_connected is False
        assert manager.log_buffer.size() == 1
    
    def test_buffer_flush_on_reconnection(self, tmp_path):
        """Test buffer flush when database reconnects
        
        Requirement 20.3: Flush buffered logs on reconnection
        """
        mock_db = Mock()
        
        # First call fails, subsequent calls succeed
        call_count = [0]
        
        def side_effect_func(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Database unavailable")
            return None
        
        mock_db.log_command.side_effect = side_effect_func
        mock_db.get_active_agents.return_value = []
        
        overflow_file = tmp_path / "overflow.json"
        manager = DatabaseRecoveryManager(
            mock_db,
            reconnect_interval=1,
            overflow_file=str(overflow_file)
        )
        
        # First log fails and buffers
        manager.log_with_recovery('command', 'agent-1', 'test command')
        assert manager.log_buffer.size() == 1
        
        # Manually trigger flush (simulating reconnection)
        manager.is_connected = True
        manager._flush_buffered_logs()
        
        # Buffer should be cleared
        assert manager.log_buffer.size() == 0
    
    def test_reconnection_loop_stops_on_success(self, tmp_path):
        """Test reconnection loop stops when connection succeeds"""
        mock_db = Mock()
        mock_db.get_active_agents.return_value = []
        
        overflow_file = tmp_path / "overflow.json"
        manager = DatabaseRecoveryManager(
            mock_db,
            reconnect_interval=1,
            overflow_file=str(overflow_file)
        )
        
        # Add a buffered log
        manager.log_buffer.add_log({'test': 'log'})
        
        # Start reconnection
        manager._start_reconnection_attempts()
        
        # Wait for reconnection to complete
        time.sleep(2)
        
        # Thread should have stopped
        assert not manager.reconnect_thread.is_alive()
    
    def test_stop_reconnection(self):
        """Test stopping reconnection attempts"""
        mock_db = Mock()
        mock_db.get_active_agents.side_effect = Exception("Still failing")
        
        manager = DatabaseRecoveryManager(mock_db, reconnect_interval=1)
        manager._start_reconnection_attempts()
        
        # Stop reconnection
        manager.stop()
        
        # Thread should stop
        time.sleep(2)
        assert manager.stop_reconnect.is_set()


class TestPluginRecoveryManager:
    """
    Test PluginRecoveryManager for plugin crash recovery
    
    Requirement 20.4: Restart crashed plugins
    """
    
    def test_initialization(self):
        """Test PluginRecoveryManager initialization"""
        mock_plugin_manager = Mock()
        manager = PluginRecoveryManager(mock_plugin_manager)
        
        assert manager.plugin_manager == mock_plugin_manager
        assert manager.max_restart_attempts == 3
    
    def test_execute_with_recovery_success(self):
        """Test successful plugin execution"""
        mock_plugin_manager = Mock()
        mock_result = Mock(success=True, data="result")
        mock_plugin_manager.execute_plugin.return_value = mock_result
        
        manager = PluginRecoveryManager(mock_plugin_manager)
        result = manager.execute_with_recovery('test_plugin', {'arg': 'value'})
        
        assert result == mock_result
        mock_plugin_manager.execute_plugin.assert_called_once_with('test_plugin', {'arg': 'value'})
    
    def test_execute_with_recovery_crash_and_restart(self):
        """Test plugin crash recovery and restart
        
        Requirement 20.4: Restart plugin on crash
        """
        mock_plugin_manager = Mock()
        
        # First call fails, second succeeds
        call_count = [0]
        
        def side_effect_func(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Plugin crashed")
            return Mock(success=True, data="recovered")
        
        mock_plugin_manager.execute_plugin.side_effect = side_effect_func
        
        manager = PluginRecoveryManager(mock_plugin_manager)
        result = manager.execute_with_recovery('test_plugin', {'arg': 'value'})
        
        assert result.success is True
        assert result.data == "recovered"
        assert mock_plugin_manager.load_plugins.called
    
    def test_execute_with_recovery_max_attempts(self):
        """Test plugin fails after max restart attempts"""
        mock_plugin_manager = Mock()
        mock_plugin_manager.execute_plugin.side_effect = Exception("Plugin keeps crashing")
        
        manager = PluginRecoveryManager(mock_plugin_manager)
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.execute_with_recovery('test_plugin', {'arg': 'value'})
        
        assert "failed after 3 attempts" in str(exc_info.value)
        assert mock_plugin_manager.execute_plugin.call_count == 3
    
    def test_crash_count_tracking(self):
        """Test crash count tracking for plugins"""
        mock_plugin_manager = Mock()
        mock_plugin_manager.execute_plugin.side_effect = Exception("Crash")
        
        manager = PluginRecoveryManager(mock_plugin_manager)
        
        try:
            manager.execute_with_recovery('test_plugin', {})
        except:
            pass
        
        crash_count = manager.get_crash_count('test_plugin')
        assert crash_count == 3
    
    def test_reset_crash_count(self):
        """Test resetting crash count"""
        mock_plugin_manager = Mock()
        
        manager = PluginRecoveryManager(mock_plugin_manager)
        manager.crash_counts['test_plugin'] = 5
        
        manager.reset_crash_count('test_plugin')
        assert manager.get_crash_count('test_plugin') == 0


class TestGracefulDegradationManager:
    """
    Test GracefulDegradationManager for component failure handling
    
    Requirements: 20.7, 20.8
    """
    
    def test_initialization(self):
        """Test GracefulDegradationManager initialization"""
        manager = GracefulDegradationManager()
        assert len(manager.component_status) == 0
    
    def test_register_component(self):
        """Test registering a component"""
        manager = GracefulDegradationManager()
        manager.register_component('database')
        
        assert manager.is_component_healthy('database') is True
    
    def test_mark_component_failed(self):
        """Test marking component as failed"""
        manager = GracefulDegradationManager()
        manager.register_component('database')
        
        manager.mark_component_failed('database')
        assert manager.is_component_healthy('database') is False
    
    def test_mark_component_healthy(self):
        """Test marking component as healthy"""
        manager = GracefulDegradationManager()
        manager.register_component('database')
        manager.mark_component_failed('database')
        
        manager.mark_component_healthy('database')
        assert manager.is_component_healthy('database') is True
    
    def test_execute_with_fallback_success(self):
        """Test successful execution without fallback"""
        manager = GracefulDegradationManager()
        manager.register_component('test_component')
        
        def primary_func(x, y):
            return x + y
        
        result = manager.execute_with_fallback('test_component', primary_func, 2, 3)
        assert result == 5
        assert manager.is_component_healthy('test_component') is True
    
    def test_execute_with_fallback_failure_no_fallback(self):
        """Test execution failure without fallback handler"""
        manager = GracefulDegradationManager()
        manager.register_component('test_component')
        
        def primary_func():
            raise Exception("Primary failed")
        
        with pytest.raises(Exception) as exc_info:
            manager.execute_with_fallback('test_component', primary_func)
        
        assert "Primary failed" in str(exc_info.value)
        assert manager.is_component_healthy('test_component') is False
    
    def test_execute_with_fallback_uses_fallback(self):
        """Test fallback handler is used on failure"""
        manager = GracefulDegradationManager()
        
        def fallback_handler(x, y):
            return x * y  # Different operation
        
        manager.register_component('test_component', fallback_handler)
        
        def primary_func(x, y):
            raise Exception("Primary failed")
        
        result = manager.execute_with_fallback('test_component', primary_func, 2, 3)
        assert result == 6  # Fallback result
        assert manager.is_component_healthy('test_component') is False
    
    def test_get_system_health(self):
        """Test getting system health status"""
        manager = GracefulDegradationManager()
        manager.register_component('database')
        manager.register_component('api')
        manager.mark_component_failed('api')
        
        health = manager.get_system_health()
        assert health['database'] is True
        assert health['api'] is False
    
    def test_thread_safety(self):
        """Test thread-safe operations"""
        manager = GracefulDegradationManager()
        
        def toggle_status(component_name, iterations):
            for i in range(iterations):
                if i % 2 == 0:
                    manager.mark_component_failed(component_name)
                else:
                    manager.mark_component_healthy(component_name)
        
        manager.register_component('test_component')
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=toggle_status, args=('test_component', 100))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        health = manager.is_component_healthy('test_component')
        assert isinstance(health, bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
