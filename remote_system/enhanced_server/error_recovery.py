"""
Error Recovery Module for Enhanced Server

This module provides error recovery and resilience mechanisms for the enhanced server,
including database connection failure handling, log buffering, plugin crash recovery,
and graceful degradation.

Requirements: 12.7, 20.1, 20.2, 20.3, 20.4, 20.7, 20.8
"""

import os
import json
import time
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable
from collections import deque
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogBuffer:
    """
    In-memory buffer for logs when database is unavailable
    
    Requirements: 12.7, 20.1, 20.2, 20.3
    """
    
    def __init__(self, max_size: int = 10000, overflow_file: str = "overflow_logs.json"):
        """
        Initialize log buffer
        
        Args:
            max_size: Maximum number of entries to buffer in memory (default 10,000)
            overflow_file: File path for overflow logs when buffer is full
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        
        self.max_size = max_size
        self.overflow_file = overflow_file
        self.buffer: deque = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.overflow_count = 0
    
    def add_log(self, log_entry: Dict[str, Any]) -> bool:
        """
        Add a log entry to the buffer
        
        Args:
            log_entry: Dictionary containing log data
        
        Returns:
            True if added to buffer, False if written to overflow file
        
        Requirement 12.7: Buffer logs in memory up to 10,000 entries
        Requirement 20.2: Write overflow logs to file backup
        """
        with self.lock:
            # Check if buffer is at capacity
            if len(self.buffer) >= self.max_size:
                # Write to overflow file
                self._write_to_overflow_file(log_entry)
                return False
            
            # Add timestamp if not present
            if 'buffered_at' not in log_entry:
                log_entry['buffered_at'] = datetime.now(timezone.utc).isoformat()
            
            self.buffer.append(log_entry)
            return True
    
    def _write_to_overflow_file(self, log_entry: Dict[str, Any]) -> None:
        """
        Write log entry to overflow file when buffer is full
        
        Args:
            log_entry: Dictionary containing log data
        
        Requirement 20.2: Write overflow logs to file backup
        """
        try:
            # Ensure directory exists
            overflow_dir = os.path.dirname(self.overflow_file)
            if overflow_dir and not os.path.exists(overflow_dir):
                os.makedirs(overflow_dir, exist_ok=True)
            
            # Append to overflow file
            with open(self.overflow_file, 'a') as f:
                json.dump(log_entry, f)
                f.write('\n')
            
            self.overflow_count += 1
            logger.warning(f"Buffer full, wrote log to overflow file: {self.overflow_file}")
        
        except Exception as e:
            logger.error(f"Failed to write to overflow file: {e}")
    
    def get_all_logs(self) -> List[Dict[str, Any]]:
        """
        Get all buffered logs
        
        Returns:
            List of log entries
        """
        with self.lock:
            return list(self.buffer)
    
    def clear(self) -> int:
        """
        Clear all buffered logs
        
        Returns:
            Number of logs that were cleared
        """
        with self.lock:
            count = len(self.buffer)
            self.buffer.clear()
            return count
    
    def size(self) -> int:
        """
        Get current buffer size
        
        Returns:
            Number of logs in buffer
        """
        with self.lock:
            return len(self.buffer)
    
    def load_overflow_logs(self) -> List[Dict[str, Any]]:
        """
        Load logs from overflow file
        
        Returns:
            List of log entries from overflow file
        """
        overflow_logs = []
        
        if not os.path.exists(self.overflow_file):
            return overflow_logs
        
        try:
            with open(self.overflow_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            log_entry = json.loads(line)
                            overflow_logs.append(log_entry)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse overflow log line: {line}")
            
            logger.info(f"Loaded {len(overflow_logs)} logs from overflow file")
        
        except Exception as e:
            logger.error(f"Failed to load overflow logs: {e}")
        
        return overflow_logs
    
    def clear_overflow_file(self) -> None:
        """
        Clear the overflow file after successful flush
        """
        try:
            if os.path.exists(self.overflow_file):
                os.remove(self.overflow_file)
                self.overflow_count = 0
                logger.info("Cleared overflow file")
        except Exception as e:
            logger.error(f"Failed to clear overflow file: {e}")


class DatabaseRecoveryManager:
    """
    Manages database connection recovery and log buffering
    
    Requirements: 20.1, 20.2, 20.3
    """
    
    def __init__(self, database_manager, reconnect_interval: int = 30,
                 max_buffer_size: int = 10000, overflow_file: str = "overflow_logs.json"):
        """
        Initialize database recovery manager
        
        Args:
            database_manager: DatabaseManager instance
            reconnect_interval: Seconds between reconnection attempts (default 30)
            max_buffer_size: Maximum buffer size (default 10,000)
            overflow_file: Path for overflow logs
        """
        self.database_manager = database_manager
        self.reconnect_interval = reconnect_interval
        self.log_buffer = LogBuffer(max_buffer_size, overflow_file)
        self.is_connected = True
        self.reconnect_thread: Optional[threading.Thread] = None
        self.stop_reconnect = threading.Event()
    
    def check_connection(self) -> bool:
        """
        Check if database connection is active
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Try a simple query to check connection
            self.database_manager.get_active_agents()
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            self.is_connected = False
            return False
    
    def log_with_recovery(self, log_type: str, *args, **kwargs) -> bool:
        """
        Log data with automatic recovery handling
        
        Args:
            log_type: Type of log (connection, command, file_transfer)
            *args: Positional arguments for the log method
            **kwargs: Keyword arguments for the log method
        
        Returns:
            True if logged successfully, False if buffered
        
        Requirement 20.1: Buffer logs and retry connection periodically
        """
        # Try to log to database
        try:
            if log_type == 'connection':
                self.database_manager.log_connection(*args, **kwargs)
            elif log_type == 'command':
                return self.database_manager.log_command(*args, **kwargs)
            elif log_type == 'file_transfer':
                self.database_manager.log_file_transfer(*args, **kwargs)
            elif log_type == 'update_command':
                self.database_manager.update_command_log(*args, **kwargs)
            elif log_type == 'update_status':
                self.database_manager.update_agent_status(*args, **kwargs)
            else:
                raise ValueError(f"Unknown log type: {log_type}")
            
            self.is_connected = True
            return True
        
        except Exception as e:
            logger.warning(f"Database logging failed, buffering: {e}")
            self.is_connected = False
            
            # Buffer the log entry
            log_entry = {
                'log_type': log_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.log_buffer.add_log(log_entry)
            
            # Start reconnection attempts if not already running
            if not self.reconnect_thread or not self.reconnect_thread.is_alive():
                self._start_reconnection_attempts()
            
            return False
    
    def _start_reconnection_attempts(self) -> None:
        """
        Start periodic reconnection attempts
        
        Requirement 20.1: Retry connection periodically
        """
        self.stop_reconnect.clear()
        self.reconnect_thread = threading.Thread(
            target=self._reconnection_loop,
            daemon=True
        )
        self.reconnect_thread.start()
        logger.info("Started database reconnection attempts")
    
    def _reconnection_loop(self) -> None:
        """
        Periodic reconnection loop
        
        Requirement 20.1: Retry connection periodically
        """
        while not self.stop_reconnect.is_set():
            time.sleep(self.reconnect_interval)
            
            logger.info("Attempting database reconnection...")
            
            if self.check_connection():
                logger.info("Database reconnected successfully")
                self._flush_buffered_logs()
                break
            else:
                logger.warning(f"Reconnection failed, will retry in {self.reconnect_interval}s")
    
    def _flush_buffered_logs(self) -> None:
        """
        Flush buffered logs to database after reconnection
        
        Requirement 20.3: Flush buffered logs to database on reconnection
        """
        logger.info("Flushing buffered logs to database...")
        
        # Get all buffered logs
        buffered_logs = self.log_buffer.get_all_logs()
        
        # Load overflow logs if any
        overflow_logs = self.log_buffer.load_overflow_logs()
        
        # Combine all logs
        all_logs = buffered_logs + overflow_logs
        
        if not all_logs:
            logger.info("No buffered logs to flush")
            return
        
        success_count = 0
        failure_count = 0
        
        for log_entry in all_logs:
            try:
                log_type = log_entry.get('log_type')
                args = log_entry.get('args', ())
                kwargs = log_entry.get('kwargs', {})
                
                # Replay the log operation
                if log_type == 'connection':
                    self.database_manager.log_connection(*args, **kwargs)
                elif log_type == 'command':
                    self.database_manager.log_command(*args, **kwargs)
                elif log_type == 'file_transfer':
                    self.database_manager.log_file_transfer(*args, **kwargs)
                elif log_type == 'update_command':
                    self.database_manager.update_command_log(*args, **kwargs)
                elif log_type == 'update_status':
                    self.database_manager.update_agent_status(*args, **kwargs)
                
                success_count += 1
            
            except Exception as e:
                logger.error(f"Failed to flush log entry: {e}")
                failure_count += 1
        
        # Clear buffer and overflow file after successful flush
        self.log_buffer.clear()
        self.log_buffer.clear_overflow_file()
        
        logger.info(f"Flushed {success_count} logs successfully, {failure_count} failed")
    
    def stop(self) -> None:
        """
        Stop reconnection attempts
        """
        self.stop_reconnect.set()
        if self.reconnect_thread:
            self.reconnect_thread.join(timeout=5)


class PluginRecoveryManager:
    """
    Manages plugin crash recovery and restart
    
    Requirement 20.4: Restart crashed plugins
    """
    
    def __init__(self, plugin_manager):
        """
        Initialize plugin recovery manager
        
        Args:
            plugin_manager: PluginManager instance
        """
        self.plugin_manager = plugin_manager
        self.crash_counts: Dict[str, int] = {}
        self.max_restart_attempts = 3
        self.lock = threading.Lock()
    
    def execute_with_recovery(self, plugin_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute plugin with automatic crash recovery
        
        Args:
            plugin_name: Name of the plugin to execute
            args: Arguments for plugin execution
        
        Returns:
            Plugin execution result
        
        Requirement 20.4: Restart plugin on crash
        """
        attempt = 0
        last_exception = None
        
        while attempt < self.max_restart_attempts:
            try:
                result = self.plugin_manager.execute_plugin(plugin_name, args)
                
                # Reset crash count on successful execution
                with self.lock:
                    if plugin_name in self.crash_counts:
                        self.crash_counts[plugin_name] = 0
                
                return result
            
            except Exception as e:
                last_exception = e
                attempt += 1
                
                with self.lock:
                    self.crash_counts[plugin_name] = self.crash_counts.get(plugin_name, 0) + 1
                
                logger.error(f"Plugin {plugin_name} crashed (attempt {attempt}/{self.max_restart_attempts}): {e}")
                
                if attempt < self.max_restart_attempts:
                    # Try to reload the plugin
                    try:
                        self.plugin_manager.load_plugins()
                        logger.info(f"Reloaded plugin {plugin_name}")
                    except Exception as reload_error:
                        logger.error(f"Failed to reload plugin {plugin_name}: {reload_error}")
                else:
                    logger.error(f"Plugin {plugin_name} failed after {self.max_restart_attempts} attempts")
        
        # If we get here, all attempts failed
        raise RuntimeError(f"Plugin {plugin_name} failed after {self.max_restart_attempts} attempts")
    
    def get_crash_count(self, plugin_name: str) -> int:
        """
        Get crash count for a plugin
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            Number of crashes
        """
        with self.lock:
            return self.crash_counts.get(plugin_name, 0)
    
    def reset_crash_count(self, plugin_name: str) -> None:
        """
        Reset crash count for a plugin
        
        Args:
            plugin_name: Name of the plugin
        """
        with self.lock:
            if plugin_name in self.crash_counts:
                self.crash_counts[plugin_name] = 0


class GracefulDegradationManager:
    """
    Manages graceful degradation for component failures
    
    Requirement 20.7, 20.8: Graceful degradation for failures
    """
    
    def __init__(self):
        """
        Initialize graceful degradation manager
        """
        self.component_status: Dict[str, bool] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.lock = threading.Lock()
    
    def register_component(self, component_name: str, fallback_handler: Optional[Callable] = None) -> None:
        """
        Register a component for graceful degradation
        
        Args:
            component_name: Name of the component
            fallback_handler: Optional fallback function to call on failure
        """
        with self.lock:
            self.component_status[component_name] = True
            if fallback_handler:
                self.fallback_handlers[component_name] = fallback_handler
    
    def mark_component_failed(self, component_name: str) -> None:
        """
        Mark a component as failed
        
        Args:
            component_name: Name of the component
        """
        with self.lock:
            self.component_status[component_name] = False
            logger.warning(f"Component {component_name} marked as failed")
    
    def mark_component_healthy(self, component_name: str) -> None:
        """
        Mark a component as healthy
        
        Args:
            component_name: Name of the component
        """
        with self.lock:
            self.component_status[component_name] = True
            logger.info(f"Component {component_name} marked as healthy")
    
    def is_component_healthy(self, component_name: str) -> bool:
        """
        Check if a component is healthy
        
        Args:
            component_name: Name of the component
        
        Returns:
            True if healthy, False otherwise
        """
        with self.lock:
            return self.component_status.get(component_name, False)
    
    def execute_with_fallback(self, component_name: str, primary_func: Callable,
                             *args, **kwargs) -> Any:
        """
        Execute function with fallback on failure
        
        Args:
            component_name: Name of the component
            primary_func: Primary function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result from primary or fallback function
        """
        try:
            result = primary_func(*args, **kwargs)
            self.mark_component_healthy(component_name)
            return result
        
        except Exception as e:
            logger.error(f"Component {component_name} failed: {e}")
            self.mark_component_failed(component_name)
            
            # Try fallback handler if available
            with self.lock:
                fallback_handler = self.fallback_handlers.get(component_name)
            
            if fallback_handler:
                try:
                    logger.info(f"Executing fallback for {component_name}")
                    return fallback_handler(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback for {component_name} also failed: {fallback_error}")
                    raise
            else:
                raise
    
    def get_system_health(self) -> Dict[str, bool]:
        """
        Get health status of all components
        
        Returns:
            Dictionary mapping component names to health status
        """
        with self.lock:
            return dict(self.component_status)
