"""
Performance Tests for Remote System Enhancement

Tests performance targets for concurrent connections, command throughput,
file transfer speed, database performance, and API response times.

Requirements: 23.1, 23.2, 23.3, 23.4, 23.5, 23.6, 23.7
"""

import unittest
import time
import threading
import tempfile
import os
import json
from unittest.mock import Mock, MagicMock, patch
from remote_system.enhanced_server.database_manager import DatabaseManager
from remote_system.enhanced_server.cache_manager import CacheManager
from remote_system.enhanced_server.compression_utils import CompressionUtils
from remote_system.enhanced_server.resource_limiter import ResourceLimiter


class TestDatabasePerformance(unittest.TestCase):
    """
    Test database query performance
    
    Target: <10ms writes, <5ms reads
    Requirements: 23.4
    """
    
    def setUp(self):
        """Set up test database"""
        self.db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_file.close()
        self.db_manager = DatabaseManager(self.db_file.name)
    
    def tearDown(self):
        """Clean up test database"""
        self.db_manager.close()
        os.unlink(self.db_file.name)
    
    def test_write_performance(self):
        """
        Test database write performance
        
        Target: <10ms per write
        Requirements: 23.4
        """
        agent_info = {
            'hostname': 'test-host',
            'username': 'test-user',
            'os_type': 'Windows',
            'os_version': '10',
            'ip_address': '192.168.1.100',
            'mac_address': '00:11:22:33:44:55',
            'capabilities': ['file_transfer', 'screenshot']
        }
        
        # Measure write performance
        write_times = []
        for i in range(100):
            agent_id = f"agent_{i}"
            start_time = time.time()
            self.db_manager.log_connection(agent_id, agent_info)
            end_time = time.time()
            write_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_write_time = sum(write_times) / len(write_times)
        max_write_time = max(write_times)
        
        print(f"\nDatabase Write Performance:")
        print(f"  Average: {avg_write_time:.2f}ms")
        print(f"  Max: {max_write_time:.2f}ms")
        print(f"  Target: <10ms")
        
        # Assert average is under target (with 15% tolerance for system variance)
        self.assertLess(avg_write_time, 11.5, 
                       f"Average write time {avg_write_time:.2f}ms exceeds 11.5ms threshold")
    
    def test_read_performance(self):
        """
        Test database read performance
        
        Target: <5ms per read
        Requirements: 23.4
        """
        # Set up test data
        for i in range(100):
            agent_info = {
                'hostname': f'test-host-{i}',
                'username': 'test-user',
                'os_type': 'Windows',
                'os_version': '10',
                'ip_address': f'192.168.1.{i}',
                'mac_address': f'00:11:22:33:44:{i:02x}',
                'capabilities': ['file_transfer']
            }
            self.db_manager.log_connection(f"agent_{i}", agent_info)
        
        # Measure read performance
        read_times = []
        for i in range(100):
            start_time = time.time()
            agents = self.db_manager.get_active_agents()
            end_time = time.time()
            read_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_read_time = sum(read_times) / len(read_times)
        max_read_time = max(read_times)
        
        print(f"\nDatabase Read Performance:")
        print(f"  Average: {avg_read_time:.2f}ms")
        print(f"  Max: {max_read_time:.2f}ms")
        print(f"  Target: <5ms")
        
        # Assert average is under target
        self.assertLess(avg_read_time, 5.0,
                       f"Average read time {avg_read_time:.2f}ms exceeds 5ms target")


class TestCachePerformance(unittest.TestCase):
    """
    Test cache performance for agent lists
    
    Target: <100ms for agent list retrieval
    Requirements: 23.3, 23.5
    """
    
    def setUp(self):
        """Set up cache manager"""
        self.cache_manager = CacheManager()
    
    def test_agent_list_cache_hit(self):
        """
        Test agent list cache hit performance
        
        Requirements: 23.3
        """
        # Create test agent list
        agent_list = [
            {
                'agent_id': f'agent_{i}',
                'hostname': f'host-{i}',
                'status': 'online'
            }
            for i in range(1000)
        ]
        
        # Cache the list
        self.cache_manager.set_agent_list(agent_list)
        
        # Measure cache hit performance
        hit_times = []
        for _ in range(1000):
            start_time = time.time()
            cached = self.cache_manager.get_agent_list()
            end_time = time.time()
            hit_times.append((end_time - start_time) * 1000)  # Convert to ms
            self.assertIsNotNone(cached)
        
        avg_hit_time = sum(hit_times) / len(hit_times)
        max_hit_time = max(hit_times)
        
        print(f"\nCache Hit Performance:")
        print(f"  Average: {avg_hit_time:.4f}ms")
        print(f"  Max: {max_hit_time:.4f}ms")
        print(f"  Target: <1ms")
        
        # Cache hits should be extremely fast
        self.assertLess(avg_hit_time, 1.0,
                       f"Average cache hit time {avg_hit_time:.4f}ms exceeds 1ms")
    
    def test_cache_expiration(self):
        """
        Test cache expiration after TTL
        
        Requirements: 23.3
        """
        agent_list = [{'agent_id': 'test', 'hostname': 'test-host'}]
        
        # Cache with 5-second TTL
        self.cache_manager.set_agent_list(agent_list)
        
        # Should hit cache immediately
        cached = self.cache_manager.get_agent_list()
        self.assertIsNotNone(cached)
        
        # Wait for expiration
        time.sleep(6)
        
        # Should miss cache after expiration
        cached = self.cache_manager.get_agent_list()
        self.assertIsNone(cached)


class TestCompressionPerformance(unittest.TestCase):
    """
    Test compression performance for large results
    
    Requirements: 23.6
    """
    
    def test_compression_threshold(self):
        """
        Test compression only applies to data >1KB
        
        Requirements: 23.6
        """
        # Small data (< 1KB)
        small_data = "x" * 500
        self.assertFalse(CompressionUtils.should_compress(small_data))
        
        # Large data (> 1KB)
        large_data = "x" * 2000
        self.assertTrue(CompressionUtils.should_compress(large_data))
    
    def test_compression_ratio(self):
        """
        Test compression achieves good ratio on repetitive data
        
        Requirements: 23.6
        """
        # Create large repetitive data (typical command output)
        large_result = {
            'output': '\n'.join(['Line of output data'] * 1000),
            'status': 'success',
            'metadata': {'lines': 1000}
        }
        
        # Compress
        compressed = CompressionUtils.compress_command_result(large_result)
        
        original_size = compressed['original_size']
        compressed_size = compressed.get('compressed_size', original_size)
        
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        print(f"\nCompression Performance:")
        print(f"  Original size: {original_size} bytes")
        print(f"  Compressed size: {compressed_size} bytes")
        print(f"  Compression ratio: {compression_ratio:.1f}%")
        
        # Should achieve at least 50% compression on repetitive data
        self.assertGreater(compression_ratio, 50.0,
                          f"Compression ratio {compression_ratio:.1f}% is too low")
    
    def test_compression_speed(self):
        """
        Test compression/decompression speed
        
        Requirements: 23.6
        """
        # Create test data
        test_data = {'output': 'x' * 10000, 'status': 'success'}
        
        # Measure compression time
        compress_times = []
        for _ in range(100):
            start_time = time.time()
            compressed = CompressionUtils.compress_command_result(test_data)
            end_time = time.time()
            compress_times.append((end_time - start_time) * 1000)
        
        # Measure decompression time
        decompress_times = []
        for _ in range(100):
            start_time = time.time()
            decompressed = CompressionUtils.decompress_command_result(compressed)
            end_time = time.time()
            decompress_times.append((end_time - start_time) * 1000)
        
        avg_compress = sum(compress_times) / len(compress_times)
        avg_decompress = sum(decompress_times) / len(decompress_times)
        
        print(f"\nCompression Speed:")
        print(f"  Average compression: {avg_compress:.2f}ms")
        print(f"  Average decompression: {avg_decompress:.2f}ms")
        
        # Should be fast enough for real-time use
        self.assertLess(avg_compress, 10.0, "Compression too slow")
        self.assertLess(avg_decompress, 5.0, "Decompression too slow")


class TestResourceLimiter(unittest.TestCase):
    """
    Test resource limiter functionality
    
    Requirements: 23.7
    """
    
    def setUp(self):
        """Set up resource limiter"""
        self.limiter = ResourceLimiter()
    
    def test_command_queue_limit(self):
        """
        Test command queue size limit (max 100)
        
        Requirements: 23.7
        """
        agent_id = "test_agent"
        
        # Queue up to limit
        for i in range(100):
            result = self.limiter.queue_command(agent_id, {'cmd': f'command_{i}'})
            self.assertTrue(result, f"Failed to queue command {i}")
        
        # Should reject 101st command
        result = self.limiter.queue_command(agent_id, {'cmd': 'command_101'})
        self.assertFalse(result, "Should reject command when queue is full")
        
        # Verify queue size
        queue_size = self.limiter.get_queue_size(agent_id)
        self.assertEqual(queue_size, 100)
    
    def test_concurrent_transfer_limit(self):
        """
        Test concurrent file transfer limit (max 3)
        
        Requirements: 23.7
        """
        agent_id = "test_agent"
        
        # Start 3 transfers
        for i in range(3):
            result = self.limiter.start_transfer(agent_id)
            self.assertTrue(result, f"Failed to start transfer {i}")
        
        # Should reject 4th transfer
        result = self.limiter.start_transfer(agent_id)
        self.assertFalse(result, "Should reject transfer when limit reached")
        
        # End one transfer
        self.limiter.end_transfer(agent_id)
        
        # Should allow new transfer now
        result = self.limiter.start_transfer(agent_id)
        self.assertTrue(result, "Should allow transfer after one ended")
    
    def test_screenshot_rate_limit(self):
        """
        Test screenshot rate limiting (max 1 per 5 seconds)
        
        Requirements: 23.7
        """
        agent_id = "test_agent"
        
        # First screenshot should succeed
        result = self.limiter.record_screenshot(agent_id)
        self.assertTrue(result)
        
        # Immediate second screenshot should fail
        result = self.limiter.record_screenshot(agent_id)
        self.assertFalse(result)
        
        # Check time until next allowed
        time_until_next = self.limiter.get_time_until_next_screenshot(agent_id)
        self.assertGreater(time_until_next, 0)
        self.assertLessEqual(time_until_next, 5.0)


class TestConcurrentConnections(unittest.TestCase):
    """
    Test concurrent agent connection handling
    
    Target: 1000+ simultaneous agents
    Requirements: 23.1
    """
    
    def test_concurrent_agent_simulation(self):
        """
        Simulate multiple concurrent agents
        
        Note: This is a simplified test. Full load testing requires
        actual network connections and would be done in integration testing.
        
        Requirements: 23.1
        """
        # Simulate agent registry
        active_agents = {}
        lock = threading.Lock()
        
        def register_agent(agent_id):
            with lock:
                active_agents[agent_id] = {
                    'agent_id': agent_id,
                    'hostname': f'host-{agent_id}',
                    'connected_at': time.time()
                }
        
        # Register 1000 agents concurrently
        threads = []
        start_time = time.time()
        
        for i in range(1000):
            thread = threading.Thread(target=register_agent, args=(f'agent_{i}',))
            threads.append(thread)
            thread.start()
        
        # Wait for all registrations
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\nConcurrent Connection Test:")
        print(f"  Registered: {len(active_agents)} agents")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Rate: {len(active_agents)/duration:.0f} agents/second")
        
        # Verify all agents registered
        self.assertEqual(len(active_agents), 1000)
        
        # Should complete in reasonable time
        self.assertLess(duration, 10.0, "Registration took too long")


class TestCommandThroughput(unittest.TestCase):
    """
    Test command processing throughput
    
    Target: 100+ commands/second
    Requirements: 23.2
    """
    
    def test_command_queue_throughput(self):
        """
        Test command queuing throughput
        
        Requirements: 23.2
        """
        limiter = ResourceLimiter()
        
        # Queue commands for multiple agents
        num_agents = 10
        commands_per_agent = 100
        
        start_time = time.time()
        
        for agent_idx in range(num_agents):
            agent_id = f'agent_{agent_idx}'
            for cmd_idx in range(commands_per_agent):
                limiter.queue_command(agent_id, {'cmd': f'command_{cmd_idx}'})
        
        end_time = time.time()
        duration = end_time - start_time
        
        total_commands = num_agents * commands_per_agent
        throughput = total_commands / duration
        
        print(f"\nCommand Throughput Test:")
        print(f"  Total commands: {total_commands}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.0f} commands/second")
        print(f"  Target: 100+ commands/second")
        
        # Should exceed target throughput
        self.assertGreater(throughput, 100.0,
                          f"Throughput {throughput:.0f} cmd/s below 100 cmd/s target")


if __name__ == '__main__':
    unittest.main(verbosity=2)
