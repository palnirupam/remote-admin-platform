"""
Monitoring and Observability Module

Provides metrics collection, performance tracking, and Prometheus-compatible
metrics endpoint for system health monitoring.

Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 24.7
"""

import time
import threading
import psutil
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta


class MetricsCollector:
    """
    Collects and aggregates system metrics for monitoring and observability.
    
    Tracks:
    - Active agent count
    - Commands per second
    - Command execution time
    - Database query performance
    - Network bandwidth utilization per agent
    - Memory usage per component
    - Failed authentication attempts
    """
    
    def __init__(self, retention_seconds: int = 3600):
        """
        Initialize metrics collector.
        
        Args:
            retention_seconds: How long to retain time-series metrics (default 1 hour)
        """
        self._lock = threading.Lock()
        self._retention_seconds = retention_seconds
        
        # Active agent tracking
        self._active_agents: set = set()
        
        # Command metrics
        self._command_count = 0
        self._command_timestamps = deque()  # For calculating commands per second
        self._command_execution_times = deque()  # For average execution time
        
        # Database metrics
        self._db_query_times = deque()  # Query execution times
        self._db_write_times = deque()  # Write operation times
        
        # Network metrics per agent
        self._agent_bandwidth: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {'bytes_sent': 0, 'bytes_received': 0, 'last_update': time.time()}
        )
        
        # Memory metrics per component
        self._component_memory: Dict[str, int] = {}
        
        # Security metrics
        self._failed_auth_attempts = 0
        self._failed_auth_timestamps = deque()
        
        # Prometheus metrics cache
        self._metrics_cache: Optional[str] = None
        self._cache_timestamp = 0
        self._cache_ttl = 5  # Cache for 5 seconds
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        self._cleanup_thread.start()
    
    def register_agent(self, agent_id: str) -> None:
        """
        Register an active agent.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Requirements: 24.1
        """
        with self._lock:
            self._active_agents.add(agent_id)
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent (disconnected).
        
        Args:
            agent_id: Unique identifier for the agent
            
        Requirements: 24.1
        """
        with self._lock:
            self._active_agents.discard(agent_id)
            # Clean up bandwidth tracking for this agent
            if agent_id in self._agent_bandwidth:
                del self._agent_bandwidth[agent_id]
    
    def get_active_agent_count(self) -> int:
        """
        Get the current number of active agents.
        
        Returns:
            Number of active agents
            
        Requirements: 24.1
        """
        with self._lock:
            return len(self._active_agents)
    
    def record_command(self, execution_time: float) -> None:
        """
        Record a command execution.
        
        Args:
            execution_time: Time taken to execute the command in seconds
            
        Requirements: 24.1, 24.2
        """
        current_time = time.time()
        with self._lock:
            self._command_count += 1
            self._command_timestamps.append(current_time)
            self._command_execution_times.append(execution_time)
    
    def get_commands_per_second(self, window_seconds: int = 60) -> float:
        """
        Calculate commands per second over a time window.
        
        Args:
            window_seconds: Time window to calculate rate (default 60 seconds)
            
        Returns:
            Commands per second
            
        Requirements: 24.1
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        with self._lock:
            # Count commands in the time window
            recent_commands = sum(1 for ts in self._command_timestamps if ts >= cutoff_time)
            
            if window_seconds > 0:
                return recent_commands / window_seconds
            return 0.0
    
    def get_average_command_execution_time(self, window_seconds: int = 300) -> float:
        """
        Calculate average command execution time over a time window.
        
        Args:
            window_seconds: Time window to calculate average (default 5 minutes)
            
        Returns:
            Average execution time in seconds
            
        Requirements: 24.2
        """
        with self._lock:
            if not self._command_execution_times:
                return 0.0
            
            # For simplicity, use recent N samples
            # In production, would track timestamps with execution times
            recent_times = list(self._command_execution_times)[-100:]
            
            if recent_times:
                return sum(recent_times) / len(recent_times)
            return 0.0
    
    def record_db_query(self, execution_time: float, is_write: bool = False) -> None:
        """
        Record a database query execution.
        
        Args:
            execution_time: Time taken for the query in seconds
            is_write: Whether this was a write operation
            
        Requirements: 24.3
        """
        with self._lock:
            if is_write:
                self._db_write_times.append(execution_time)
            else:
                self._db_query_times.append(execution_time)
    
    def get_db_query_performance(self) -> Dict[str, float]:
        """
        Get database query performance metrics.
        
        Returns:
            Dictionary with 'avg_read_time' and 'avg_write_time' in milliseconds
            
        Requirements: 24.3
        """
        with self._lock:
            avg_read = 0.0
            avg_write = 0.0
            
            if self._db_query_times:
                recent_reads = list(self._db_query_times)[-100:]
                avg_read = (sum(recent_reads) / len(recent_reads)) * 1000  # Convert to ms
            
            if self._db_write_times:
                recent_writes = list(self._db_write_times)[-100:]
                avg_write = (sum(recent_writes) / len(recent_writes)) * 1000  # Convert to ms
            
            return {
                'avg_read_time_ms': avg_read,
                'avg_write_time_ms': avg_write
            }
    
    def record_agent_bandwidth(self, agent_id: str, bytes_sent: int, bytes_received: int) -> None:
        """
        Record network bandwidth usage for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            bytes_sent: Number of bytes sent to the agent
            bytes_received: Number of bytes received from the agent
            
        Requirements: 24.4
        """
        with self._lock:
            self._agent_bandwidth[agent_id]['bytes_sent'] += bytes_sent
            self._agent_bandwidth[agent_id]['bytes_received'] += bytes_received
            self._agent_bandwidth[agent_id]['last_update'] = time.time()
    
    def get_agent_bandwidth(self, agent_id: str) -> Dict[str, int]:
        """
        Get bandwidth usage for a specific agent.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Dictionary with 'bytes_sent' and 'bytes_received'
            
        Requirements: 24.4
        """
        with self._lock:
            if agent_id in self._agent_bandwidth:
                return {
                    'bytes_sent': self._agent_bandwidth[agent_id]['bytes_sent'],
                    'bytes_received': self._agent_bandwidth[agent_id]['bytes_received']
                }
            return {'bytes_sent': 0, 'bytes_received': 0}
    
    def get_total_bandwidth(self) -> Dict[str, int]:
        """
        Get total bandwidth usage across all agents.
        
        Returns:
            Dictionary with 'total_bytes_sent' and 'total_bytes_received'
            
        Requirements: 24.4
        """
        with self._lock:
            total_sent = sum(data['bytes_sent'] for data in self._agent_bandwidth.values())
            total_received = sum(data['bytes_received'] for data in self._agent_bandwidth.values())
            
            return {
                'total_bytes_sent': total_sent,
                'total_bytes_received': total_received
            }
    
    def record_component_memory(self, component_name: str, memory_bytes: int) -> None:
        """
        Record memory usage for a component.
        
        Args:
            component_name: Name of the component (e.g., 'server', 'database', 'plugin_manager')
            memory_bytes: Memory usage in bytes
            
        Requirements: 24.5
        """
        with self._lock:
            self._component_memory[component_name] = memory_bytes
    
    def get_component_memory(self, component_name: str) -> int:
        """
        Get memory usage for a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Memory usage in bytes
            
        Requirements: 24.5
        """
        with self._lock:
            return self._component_memory.get(component_name, 0)
    
    def get_all_component_memory(self) -> Dict[str, int]:
        """
        Get memory usage for all components.
        
        Returns:
            Dictionary mapping component names to memory usage in bytes
            
        Requirements: 24.5
        """
        with self._lock:
            return self._component_memory.copy()
    
    def get_process_memory(self) -> int:
        """
        Get current process memory usage.
        
        Returns:
            Memory usage in bytes
            
        Requirements: 24.5
        """
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            return 0
    
    def record_failed_auth(self) -> None:
        """
        Record a failed authentication attempt.
        
        Requirements: 24.6
        """
        current_time = time.time()
        with self._lock:
            self._failed_auth_attempts += 1
            self._failed_auth_timestamps.append(current_time)
    
    def get_failed_auth_count(self, window_seconds: int = 3600) -> int:
        """
        Get number of failed authentication attempts in a time window.
        
        Args:
            window_seconds: Time window to count failures (default 1 hour)
            
        Returns:
            Number of failed authentication attempts
            
        Requirements: 24.6
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        with self._lock:
            return sum(1 for ts in self._failed_auth_timestamps if ts >= cutoff_time)
    
    def get_total_failed_auth_count(self) -> int:
        """
        Get total number of failed authentication attempts since startup.
        
        Returns:
            Total failed authentication attempts
            
        Requirements: 24.6
        """
        with self._lock:
            return self._failed_auth_attempts
    
    def get_prometheus_metrics(self) -> str:
        """
        Generate Prometheus-compatible metrics endpoint output.
        
        Returns:
            Prometheus text format metrics
            
        Requirements: 24.7
        """
        current_time = time.time()
        
        # Check cache
        with self._lock:
            if self._metrics_cache and (current_time - self._cache_timestamp) < self._cache_ttl:
                return self._metrics_cache
        
        # Generate metrics
        metrics = []
        
        # Active agents
        metrics.append("# HELP remote_system_active_agents Number of currently active agents")
        metrics.append("# TYPE remote_system_active_agents gauge")
        metrics.append(f"remote_system_active_agents {self.get_active_agent_count()}")
        
        # Commands per second
        metrics.append("# HELP remote_system_commands_per_second Commands executed per second")
        metrics.append("# TYPE remote_system_commands_per_second gauge")
        metrics.append(f"remote_system_commands_per_second {self.get_commands_per_second():.2f}")
        
        # Average command execution time
        metrics.append("# HELP remote_system_avg_command_execution_seconds Average command execution time")
        metrics.append("# TYPE remote_system_avg_command_execution_seconds gauge")
        metrics.append(f"remote_system_avg_command_execution_seconds {self.get_average_command_execution_time():.4f}")
        
        # Total commands
        with self._lock:
            metrics.append("# HELP remote_system_total_commands Total number of commands executed")
            metrics.append("# TYPE remote_system_total_commands counter")
            metrics.append(f"remote_system_total_commands {self._command_count}")
        
        # Database performance
        db_perf = self.get_db_query_performance()
        metrics.append("# HELP remote_system_db_read_time_ms Average database read time in milliseconds")
        metrics.append("# TYPE remote_system_db_read_time_ms gauge")
        metrics.append(f"remote_system_db_read_time_ms {db_perf['avg_read_time_ms']:.2f}")
        
        metrics.append("# HELP remote_system_db_write_time_ms Average database write time in milliseconds")
        metrics.append("# TYPE remote_system_db_write_time_ms gauge")
        metrics.append(f"remote_system_db_write_time_ms {db_perf['avg_write_time_ms']:.2f}")
        
        # Network bandwidth
        bandwidth = self.get_total_bandwidth()
        metrics.append("# HELP remote_system_bytes_sent_total Total bytes sent to agents")
        metrics.append("# TYPE remote_system_bytes_sent_total counter")
        metrics.append(f"remote_system_bytes_sent_total {bandwidth['total_bytes_sent']}")
        
        metrics.append("# HELP remote_system_bytes_received_total Total bytes received from agents")
        metrics.append("# TYPE remote_system_bytes_received_total counter")
        metrics.append(f"remote_system_bytes_received_total {bandwidth['total_bytes_received']}")
        
        # Memory usage
        metrics.append("# HELP remote_system_memory_bytes Memory usage in bytes")
        metrics.append("# TYPE remote_system_memory_bytes gauge")
        
        # Process memory
        process_memory = self.get_process_memory()
        metrics.append(f'remote_system_memory_bytes{{component="process"}} {process_memory}')
        
        # Component memory
        for component, memory in self.get_all_component_memory().items():
            metrics.append(f'remote_system_memory_bytes{{component="{component}"}} {memory}')
        
        # Failed authentication attempts
        metrics.append("# HELP remote_system_failed_auth_total Total failed authentication attempts")
        metrics.append("# TYPE remote_system_failed_auth_total counter")
        metrics.append(f"remote_system_failed_auth_total {self.get_total_failed_auth_count()}")
        
        metrics.append("# HELP remote_system_failed_auth_recent Failed authentication attempts in last hour")
        metrics.append("# TYPE remote_system_failed_auth_recent gauge")
        metrics.append(f"remote_system_failed_auth_recent {self.get_failed_auth_count()}")
        
        # Join with newlines and add final newline
        result = "\n".join(metrics) + "\n"
        
        # Update cache
        with self._lock:
            self._metrics_cache = result
            self._cache_timestamp = current_time
        
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.
        
        Returns:
            Dictionary containing all current metrics
        """
        return {
            'active_agents': self.get_active_agent_count(),
            'commands_per_second': self.get_commands_per_second(),
            'avg_command_execution_time': self.get_average_command_execution_time(),
            'db_performance': self.get_db_query_performance(),
            'bandwidth': self.get_total_bandwidth(),
            'process_memory_bytes': self.get_process_memory(),
            'component_memory': self.get_all_component_memory(),
            'failed_auth_total': self.get_total_failed_auth_count(),
            'failed_auth_recent': self.get_failed_auth_count()
        }
    
    def _cleanup_old_metrics(self) -> None:
        """
        Background thread to clean up old time-series data.
        Runs periodically to prevent unbounded memory growth.
        """
        while True:
            try:
                time.sleep(60)  # Run every minute
                current_time = time.time()
                cutoff_time = current_time - self._retention_seconds
                
                with self._lock:
                    # Clean up command timestamps
                    while self._command_timestamps and self._command_timestamps[0] < cutoff_time:
                        self._command_timestamps.popleft()
                    
                    # Clean up command execution times (keep last 1000)
                    while len(self._command_execution_times) > 1000:
                        self._command_execution_times.popleft()
                    
                    # Clean up database query times (keep last 1000)
                    while len(self._db_query_times) > 1000:
                        self._db_query_times.popleft()
                    
                    while len(self._db_write_times) > 1000:
                        self._db_write_times.popleft()
                    
                    # Clean up failed auth timestamps
                    while self._failed_auth_timestamps and self._failed_auth_timestamps[0] < cutoff_time:
                        self._failed_auth_timestamps.popleft()
                    
                    # Clean up stale agent bandwidth data (no update in 1 hour)
                    stale_agents = [
                        agent_id for agent_id, data in self._agent_bandwidth.items()
                        if current_time - data['last_update'] > 3600
                    ]
                    for agent_id in stale_agents:
                        del self._agent_bandwidth[agent_id]
                        
            except Exception:
                # Silently continue on errors in cleanup thread
                pass
    
    def reset(self) -> None:
        """
        Reset all metrics. Useful for testing.
        """
        with self._lock:
            self._active_agents.clear()
            self._command_count = 0
            self._command_timestamps.clear()
            self._command_execution_times.clear()
            self._db_query_times.clear()
            self._db_write_times.clear()
            self._agent_bandwidth.clear()
            self._component_memory.clear()
            self._failed_auth_attempts = 0
            self._failed_auth_timestamps.clear()
            self._metrics_cache = None
            self._cache_timestamp = 0


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """
    Reset the global metrics collector. Useful for testing.
    """
    global _metrics_collector
    if _metrics_collector is not None:
        _metrics_collector.reset()
    _metrics_collector = None
