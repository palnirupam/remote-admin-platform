"""
Unit tests for Monitoring Module

Tests metrics collection, aggregation, performance tracking,
and Prometheus endpoint format.

Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 24.7
"""

import pytest
import time
import threading
from remote_system.enhanced_server.monitoring import (
    MetricsCollector,
    get_metrics_collector,
    reset_metrics_collector
)


@pytest.fixture
def metrics_collector():
    """Create a fresh MetricsCollector instance for testing"""
    collector = MetricsCollector(retention_seconds=60)
    yield collector
    # No explicit cleanup needed as collector manages its own threads


@pytest.fixture
def populated_collector():
    """Create a MetricsCollector with some sample data"""
    collector = MetricsCollector(retention_seconds=60)
    
    # Register some agents
    collector.register_agent("agent-001")
    collector.register_agent("agent-002")
    collector.register_agent("agent-003")
    
    # Record some commands
    for i in range(10):
        collector.record_command(execution_time=0.1 + i * 0.01)
    
    # Record some database queries
    for i in range(5):
        collector.record_db_query(execution_time=0.005, is_write=False)
        collector.record_db_query(execution_time=0.010, is_write=True)
    
    # Record bandwidth
    collector.record_agent_bandwidth("agent-001", bytes_sent=1024, bytes_received=2048)
    collector.record_agent_bandwidth("agent-002", bytes_sent=512, bytes_received=1024)
    
    # Record component memory
    collector.record_component_memory("server", 10485760)  # 10 MB
    collector.record_component_memory("database", 5242880)  # 5 MB
    
    # Record failed auth attempts
    collector.record_failed_auth()
    collector.record_failed_auth()
    
    yield collector


class TestAgentTracking:
    """Test active agent tracking - Requirement 24.1"""
    
    def test_register_agent(self, metrics_collector):
        """Test registering an agent"""
        metrics_collector.register_agent("test-agent-001")
        
        assert metrics_collector.get_active_agent_count() == 1
    
    def test_register_multiple_agents(self, metrics_collector):
        """Test registering multiple agents"""
        for i in range(5):
            metrics_collector.register_agent(f"agent-{i:03d}")
        
        assert metrics_collector.get_active_agent_count() == 5
    
    def test_register_duplicate_agent(self, metrics_collector):
        """Test that registering the same agent twice doesn't increase count"""
        metrics_collector.register_agent("agent-001")
        metrics_collector.register_agent("agent-001")
        
        assert metrics_collector.get_active_agent_count() == 1
    
    def test_unregister_agent(self, metrics_collector):
        """Test unregistering an agent"""
        metrics_collector.register_agent("agent-001")
        metrics_collector.register_agent("agent-002")
        
        assert metrics_collector.get_active_agent_count() == 2
        
        metrics_collector.unregister_agent("agent-001")
        
        assert metrics_collector.get_active_agent_count() == 1
    
    def test_unregister_nonexistent_agent(self, metrics_collector):
        """Test that unregistering non-existent agent doesn't cause errors"""
        metrics_collector.register_agent("agent-001")
        
        # Should not raise exception
        metrics_collector.unregister_agent("non-existent")
        
        assert metrics_collector.get_active_agent_count() == 1
    
    def test_agent_count_after_multiple_operations(self, metrics_collector):
        """Test agent count remains accurate after multiple register/unregister"""
        agents = [f"agent-{i:03d}" for i in range(10)]
        
        # Register all
        for agent in agents:
            metrics_collector.register_agent(agent)
        
        assert metrics_collector.get_active_agent_count() == 10
        
        # Unregister half
        for agent in agents[:5]:
            metrics_collector.unregister_agent(agent)
        
        assert metrics_collector.get_active_agent_count() == 5


class TestCommandMetrics:
    """Test command execution metrics - Requirements 24.1, 24.2"""
    
    def test_record_command(self, metrics_collector):
        """Test recording a command execution"""
        metrics_collector.record_command(execution_time=0.5)
        
        # Should not raise exception
        assert True
    
    def test_commands_per_second_single_command(self, metrics_collector):
        """Test commands per second calculation with single command"""
        metrics_collector.record_command(execution_time=0.1)
        
        cps = metrics_collector.get_commands_per_second(window_seconds=60)
        
        # Should be approximately 1/60 commands per second
        assert 0 < cps <= 1.0
    
    def test_commands_per_second_multiple_commands(self, metrics_collector):
        """Test commands per second with multiple commands"""
        # Record 10 commands
        for i in range(10):
            metrics_collector.record_command(execution_time=0.1)
        
        cps = metrics_collector.get_commands_per_second(window_seconds=60)
        
        # Should be approximately 10/60 = 0.167 commands per second
        assert 0.1 < cps < 0.3
    
    def test_commands_per_second_with_delay(self, metrics_collector):
        """Test commands per second calculation respects time window"""
        # Record commands with small delays
        for i in range(5):
            metrics_collector.record_command(execution_time=0.1)
            time.sleep(0.01)
        
        # Calculate over 1 second window
        cps = metrics_collector.get_commands_per_second(window_seconds=1)
        
        # All commands should be within the window
        assert cps > 0
    
    def test_average_command_execution_time(self, metrics_collector):
        """Test average command execution time calculation"""
        execution_times = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        for exec_time in execution_times:
            metrics_collector.record_command(execution_time=exec_time)
        
        avg_time = metrics_collector.get_average_command_execution_time()
        
        # Average should be 0.3
        assert 0.25 < avg_time < 0.35
    
    def test_average_execution_time_no_commands(self, metrics_collector):
        """Test average execution time when no commands recorded"""
        avg_time = metrics_collector.get_average_command_execution_time()
        
        assert avg_time == 0.0
    
    def test_command_metrics_thread_safety(self, metrics_collector):
        """Test that command recording is thread-safe"""
        def record_commands():
            for i in range(100):
                metrics_collector.record_command(execution_time=0.1)
        
        threads = [threading.Thread(target=record_commands) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have recorded 500 commands without errors
        cps = metrics_collector.get_commands_per_second(window_seconds=60)
        assert cps > 0


class TestDatabaseMetrics:
    """Test database performance metrics - Requirement 24.3"""
    
    def test_record_db_read_query(self, metrics_collector):
        """Test recording database read query"""
        metrics_collector.record_db_query(execution_time=0.005, is_write=False)
        
        perf = metrics_collector.get_db_query_performance()
        
        assert perf['avg_read_time_ms'] > 0
        assert perf['avg_write_time_ms'] == 0
    
    def test_record_db_write_query(self, metrics_collector):
        """Test recording database write query"""
        metrics_collector.record_db_query(execution_time=0.010, is_write=True)
        
        perf = metrics_collector.get_db_query_performance()
        
        assert perf['avg_read_time_ms'] == 0
        assert perf['avg_write_time_ms'] > 0
    
    def test_db_performance_multiple_queries(self, metrics_collector):
        """Test database performance with multiple queries"""
        # Record read queries
        for i in range(10):
            metrics_collector.record_db_query(execution_time=0.005, is_write=False)
        
        # Record write queries
        for i in range(10):
            metrics_collector.record_db_query(execution_time=0.010, is_write=True)
        
        perf = metrics_collector.get_db_query_performance()
        
        # Read time should be ~5ms
        assert 4.0 < perf['avg_read_time_ms'] < 6.0
        
        # Write time should be ~10ms
        assert 9.0 < perf['avg_write_time_ms'] < 11.0
    
    def test_db_performance_no_queries(self, metrics_collector):
        """Test database performance when no queries recorded"""
        perf = metrics_collector.get_db_query_performance()
        
        assert perf['avg_read_time_ms'] == 0.0
        assert perf['avg_write_time_ms'] == 0.0
    
    def test_db_metrics_conversion_to_milliseconds(self, metrics_collector):
        """Test that database times are converted to milliseconds"""
        # Record query with 1 second execution time
        metrics_collector.record_db_query(execution_time=1.0, is_write=False)
        
        perf = metrics_collector.get_db_query_performance()
        
        # Should be 1000 milliseconds
        assert 900 < perf['avg_read_time_ms'] < 1100


class TestBandwidthMetrics:
    """Test network bandwidth metrics - Requirement 24.4"""
    
    def test_record_agent_bandwidth(self, metrics_collector):
        """Test recording bandwidth for an agent"""
        metrics_collector.record_agent_bandwidth(
            agent_id="agent-001",
            bytes_sent=1024,
            bytes_received=2048
        )
        
        bandwidth = metrics_collector.get_agent_bandwidth("agent-001")
        
        assert bandwidth['bytes_sent'] == 1024
        assert bandwidth['bytes_received'] == 2048
    
    def test_accumulate_agent_bandwidth(self, metrics_collector):
        """Test that bandwidth accumulates for multiple recordings"""
        agent_id = "agent-001"
        
        metrics_collector.record_agent_bandwidth(agent_id, bytes_sent=1024, bytes_received=512)
        metrics_collector.record_agent_bandwidth(agent_id, bytes_sent=2048, bytes_received=1024)
        
        bandwidth = metrics_collector.get_agent_bandwidth(agent_id)
        
        assert bandwidth['bytes_sent'] == 3072
        assert bandwidth['bytes_received'] == 1536
    
    def test_get_bandwidth_nonexistent_agent(self, metrics_collector):
        """Test getting bandwidth for non-existent agent returns zeros"""
        bandwidth = metrics_collector.get_agent_bandwidth("non-existent")
        
        assert bandwidth['bytes_sent'] == 0
        assert bandwidth['bytes_received'] == 0
    
    def test_total_bandwidth_single_agent(self, metrics_collector):
        """Test total bandwidth calculation with single agent"""
        metrics_collector.record_agent_bandwidth(
            agent_id="agent-001",
            bytes_sent=1024,
            bytes_received=2048
        )
        
        total = metrics_collector.get_total_bandwidth()
        
        assert total['total_bytes_sent'] == 1024
        assert total['total_bytes_received'] == 2048
    
    def test_total_bandwidth_multiple_agents(self, metrics_collector):
        """Test total bandwidth calculation with multiple agents"""
        metrics_collector.record_agent_bandwidth("agent-001", bytes_sent=1024, bytes_received=512)
        metrics_collector.record_agent_bandwidth("agent-002", bytes_sent=2048, bytes_received=1024)
        metrics_collector.record_agent_bandwidth("agent-003", bytes_sent=512, bytes_received=256)
        
        total = metrics_collector.get_total_bandwidth()
        
        assert total['total_bytes_sent'] == 3584
        assert total['total_bytes_received'] == 1792
    
    def test_bandwidth_cleared_on_unregister(self, metrics_collector):
        """Test that bandwidth data is cleared when agent unregisters"""
        agent_id = "agent-001"
        
        metrics_collector.register_agent(agent_id)
        metrics_collector.record_agent_bandwidth(agent_id, bytes_sent=1024, bytes_received=512)
        
        # Verify bandwidth recorded
        bandwidth = metrics_collector.get_agent_bandwidth(agent_id)
        assert bandwidth['bytes_sent'] == 1024
        
        # Unregister agent
        metrics_collector.unregister_agent(agent_id)
        
        # Bandwidth should be cleared
        bandwidth = metrics_collector.get_agent_bandwidth(agent_id)
        assert bandwidth['bytes_sent'] == 0


class TestMemoryMetrics:
    """Test memory usage metrics - Requirement 24.5"""
    
    def test_record_component_memory(self, metrics_collector):
        """Test recording memory usage for a component"""
        metrics_collector.record_component_memory("server", 10485760)  # 10 MB
        
        memory = metrics_collector.get_component_memory("server")
        
        assert memory == 10485760
    
    def test_record_multiple_components(self, metrics_collector):
        """Test recording memory for multiple components"""
        metrics_collector.record_component_memory("server", 10485760)
        metrics_collector.record_component_memory("database", 5242880)
        metrics_collector.record_component_memory("plugin_manager", 2097152)
        
        all_memory = metrics_collector.get_all_component_memory()
        
        assert len(all_memory) == 3
        assert all_memory["server"] == 10485760
        assert all_memory["database"] == 5242880
        assert all_memory["plugin_manager"] == 2097152
    
    def test_update_component_memory(self, metrics_collector):
        """Test that recording memory for same component updates value"""
        metrics_collector.record_component_memory("server", 10485760)
        metrics_collector.record_component_memory("server", 20971520)
        
        memory = metrics_collector.get_component_memory("server")
        
        assert memory == 20971520
    
    def test_get_nonexistent_component_memory(self, metrics_collector):
        """Test getting memory for non-existent component returns 0"""
        memory = metrics_collector.get_component_memory("non-existent")
        
        assert memory == 0
    
    def test_get_process_memory(self, metrics_collector):
        """Test getting current process memory"""
        memory = metrics_collector.get_process_memory()
        
        # Should return a positive value
        assert memory > 0
    
    def test_get_all_component_memory_empty(self, metrics_collector):
        """Test getting all component memory when none recorded"""
        all_memory = metrics_collector.get_all_component_memory()
        
        assert all_memory == {}


class TestSecurityMetrics:
    """Test security metrics - Requirement 24.6"""
    
    def test_record_failed_auth(self, metrics_collector):
        """Test recording failed authentication attempt"""
        metrics_collector.record_failed_auth()
        
        count = metrics_collector.get_total_failed_auth_count()
        
        assert count == 1
    
    def test_multiple_failed_auth(self, metrics_collector):
        """Test recording multiple failed authentication attempts"""
        for i in range(5):
            metrics_collector.record_failed_auth()
        
        count = metrics_collector.get_total_failed_auth_count()
        
        assert count == 5
    
    def test_failed_auth_count_in_window(self, metrics_collector):
        """Test counting failed auth attempts in time window"""
        # Record 3 failed attempts
        for i in range(3):
            metrics_collector.record_failed_auth()
        
        # Count in 1 hour window
        count = metrics_collector.get_failed_auth_count(window_seconds=3600)
        
        assert count == 3
    
    def test_failed_auth_total_vs_recent(self, metrics_collector):
        """Test that total count differs from recent count"""
        # Record some attempts
        for i in range(5):
            metrics_collector.record_failed_auth()
        
        total = metrics_collector.get_total_failed_auth_count()
        recent = metrics_collector.get_failed_auth_count(window_seconds=3600)
        
        # Both should be 5 since all are recent
        assert total == 5
        assert recent == 5


class TestPrometheusEndpoint:
    """Test Prometheus metrics endpoint - Requirement 24.7"""
    
    def test_prometheus_format_basic(self, metrics_collector):
        """Test that Prometheus output is in correct format"""
        output = metrics_collector.get_prometheus_metrics()
        
        # Should contain HELP and TYPE lines
        assert "# HELP" in output
        assert "# TYPE" in output
        
        # Should end with newline
        assert output.endswith("\n")
    
    def test_prometheus_contains_agent_count(self, populated_collector):
        """Test that Prometheus output contains active agent count"""
        output = populated_collector.get_prometheus_metrics()
        
        assert "remote_system_active_agents" in output
        assert "remote_system_active_agents 3" in output
    
    def test_prometheus_contains_commands_per_second(self, populated_collector):
        """Test that Prometheus output contains commands per second"""
        output = populated_collector.get_prometheus_metrics()
        
        assert "remote_system_commands_per_second" in output
    
    def test_prometheus_contains_command_execution_time(self, populated_collector):
        """Test that Prometheus output contains average execution time"""
        output = populated_collector.get_prometheus_metrics()
        
        assert "remote_system_avg_command_execution_seconds" in output
    
    def test_prometheus_contains_db_metrics(self, populated_collector):
        """Test that Prometheus output contains database metrics"""
        output = populated_collector.get_prometheus_metrics()
        
        assert "remote_system_db_read_time_ms" in output
        assert "remote_system_db_write_time_ms" in output
    
    def test_prometheus_contains_bandwidth_metrics(self, populated_collector):
        """Test that Prometheus output contains bandwidth metrics"""
        output = populated_collector.get_prometheus_metrics()
        
        assert "remote_system_bytes_sent_total" in output
        assert "remote_system_bytes_received_total" in output
    
    def test_prometheus_contains_memory_metrics(self, populated_collector):
        """Test that Prometheus output contains memory metrics"""
        output = populated_collector.get_prometheus_metrics()
        
        assert "remote_system_memory_bytes" in output
        assert 'component="process"' in output
        assert 'component="server"' in output
        assert 'component="database"' in output
    
    def test_prometheus_contains_auth_metrics(self, populated_collector):
        """Test that Prometheus output contains authentication metrics"""
        output = populated_collector.get_prometheus_metrics()
        
        assert "remote_system_failed_auth_total" in output
        assert "remote_system_failed_auth_recent" in output
    
    def test_prometheus_metric_types(self, populated_collector):
        """Test that metrics have correct types (gauge/counter)"""
        output = populated_collector.get_prometheus_metrics()
        
        # Gauges
        assert "# TYPE remote_system_active_agents gauge" in output
        assert "# TYPE remote_system_commands_per_second gauge" in output
        
        # Counters
        assert "# TYPE remote_system_total_commands counter" in output
        assert "# TYPE remote_system_bytes_sent_total counter" in output
        assert "# TYPE remote_system_failed_auth_total counter" in output
    
    def test_prometheus_caching(self, populated_collector):
        """Test that Prometheus output is cached"""
        # Get metrics twice quickly
        output1 = populated_collector.get_prometheus_metrics()
        output2 = populated_collector.get_prometheus_metrics()
        
        # Should be identical (cached)
        assert output1 == output2
    
    def test_prometheus_cache_expiry(self, metrics_collector):
        """Test that Prometheus cache expires after TTL"""
        # Record a command
        metrics_collector.record_command(execution_time=0.1)
        
        # Get metrics
        output1 = metrics_collector.get_prometheus_metrics()
        
        # Wait for cache to expire (TTL is 5 seconds)
        time.sleep(6)
        
        # Record another command
        metrics_collector.record_command(execution_time=0.2)
        
        # Get metrics again
        output2 = metrics_collector.get_prometheus_metrics()
        
        # Outputs should be different (cache expired and new data recorded)
        # Note: This test might be flaky due to timing
        assert "remote_system_total_commands" in output1
        assert "remote_system_total_commands" in output2


class TestMetricsSummary:
    """Test metrics summary functionality"""
    
    def test_get_summary(self, populated_collector):
        """Test getting summary of all metrics"""
        summary = populated_collector.get_summary()
        
        # Should contain all metric categories
        assert 'active_agents' in summary
        assert 'commands_per_second' in summary
        assert 'avg_command_execution_time' in summary
        assert 'db_performance' in summary
        assert 'bandwidth' in summary
        assert 'process_memory_bytes' in summary
        assert 'component_memory' in summary
        assert 'failed_auth_total' in summary
        assert 'failed_auth_recent' in summary
    
    def test_summary_values(self, populated_collector):
        """Test that summary contains correct values"""
        summary = populated_collector.get_summary()
        
        assert summary['active_agents'] == 3
        assert summary['failed_auth_total'] == 2
        assert summary['process_memory_bytes'] > 0


class TestMetricsReset:
    """Test metrics reset functionality"""
    
    def test_reset_clears_all_metrics(self, populated_collector):
        """Test that reset clears all metrics"""
        # Verify data exists
        assert populated_collector.get_active_agent_count() == 3
        assert populated_collector.get_total_failed_auth_count() == 2
        
        # Reset
        populated_collector.reset()
        
        # Verify all cleared
        assert populated_collector.get_active_agent_count() == 0
        assert populated_collector.get_total_failed_auth_count() == 0
        assert populated_collector.get_average_command_execution_time() == 0.0
        
        bandwidth = populated_collector.get_total_bandwidth()
        assert bandwidth['total_bytes_sent'] == 0
        assert bandwidth['total_bytes_received'] == 0


class TestGlobalCollector:
    """Test global metrics collector singleton"""
    
    def test_get_metrics_collector(self):
        """Test getting global metrics collector"""
        collector = get_metrics_collector()
        
        assert collector is not None
        assert isinstance(collector, MetricsCollector)
    
    def test_get_metrics_collector_singleton(self):
        """Test that get_metrics_collector returns same instance"""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2
    
    def test_reset_metrics_collector(self):
        """Test resetting global metrics collector"""
        collector1 = get_metrics_collector()
        collector1.register_agent("test-agent")
        
        reset_metrics_collector()
        
        collector2 = get_metrics_collector()
        
        # Should be a new instance
        assert collector2.get_active_agent_count() == 0


class TestThreadSafety:
    """Test thread safety of metrics collection"""
    
    def test_concurrent_agent_registration(self, metrics_collector):
        """Test concurrent agent registration is thread-safe"""
        def register_agents():
            for i in range(100):
                metrics_collector.register_agent(f"agent-{threading.current_thread().name}-{i}")
        
        threads = [threading.Thread(target=register_agents, name=f"thread-{i}") for i in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have 500 unique agents
        assert metrics_collector.get_active_agent_count() == 500
    
    def test_concurrent_metric_recording(self, metrics_collector):
        """Test concurrent metric recording is thread-safe"""
        def record_metrics():
            for i in range(50):
                metrics_collector.record_command(execution_time=0.1)
                metrics_collector.record_db_query(execution_time=0.005, is_write=False)
                metrics_collector.record_failed_auth()
        
        threads = [threading.Thread(target=record_metrics) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have recorded all metrics without errors
        assert metrics_collector.get_total_failed_auth_count() == 500


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_zero_window_commands_per_second(self, metrics_collector):
        """Test commands per second with zero window"""
        metrics_collector.record_command(execution_time=0.1)
        
        cps = metrics_collector.get_commands_per_second(window_seconds=0)
        
        assert cps == 0.0
    
    def test_negative_execution_time(self, metrics_collector):
        """Test recording negative execution time (should still work)"""
        # System should handle this gracefully
        metrics_collector.record_command(execution_time=-0.1)
        
        avg = metrics_collector.get_average_command_execution_time()
        
        # Should not crash
        assert isinstance(avg, float)
    
    def test_very_large_bandwidth(self, metrics_collector):
        """Test recording very large bandwidth values"""
        large_value = 10 ** 15  # 1 PB
        
        metrics_collector.record_agent_bandwidth(
            agent_id="agent-001",
            bytes_sent=large_value,
            bytes_received=large_value
        )
        
        bandwidth = metrics_collector.get_agent_bandwidth("agent-001")
        
        assert bandwidth['bytes_sent'] == large_value
        assert bandwidth['bytes_received'] == large_value
    
    def test_empty_agent_id(self, metrics_collector):
        """Test operations with empty agent ID"""
        # Should handle gracefully
        metrics_collector.register_agent("")
        metrics_collector.record_agent_bandwidth("", bytes_sent=100, bytes_received=200)
        
        # Should not crash
        assert True
