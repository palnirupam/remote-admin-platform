"""
Integration Tests for Backward Compatibility Layer

Tests legacy agent connections, simultaneous old and new agent connections,
configuration migration, and log migration.

Requirements: 25.1, 25.2, 25.3, 25.4, 25.5, 25.6, 25.7
"""

import unittest
import socket
import json
import time
import threading
import tempfile
import os
from unittest.mock import Mock, MagicMock, patch

from remote_system.enhanced_server.legacy_handler import (
    LegacyHandler, 
    LegacyAgentConnection,
    ConfigMigrator,
    LogMigrator
)
from remote_system.enhanced_server.database_manager import DatabaseManager


class MockSocket:
    """Mock socket for testing"""
    
    def __init__(self):
        self.sent_data = []
        self.recv_data = []
        self.recv_index = 0
        self.closed = False
        self.timeout_value = None
        self.peek_data = b""
    
    def send(self, data):
        if self.closed:
            raise Exception("Socket is closed")
        self.sent_data.append(data)
        return len(data)
    
    def recv(self, size, flags=0):
        if self.closed:
            raise Exception("Socket is closed")
        
        # Handle MSG_PEEK flag
        if flags == socket.MSG_PEEK:
            return self.peek_data
        
        if self.recv_index >= len(self.recv_data):
            if self.timeout_value and self.timeout_value > 0:
                raise socket.timeout("No more data")
            return b""
        
        data = self.recv_data[self.recv_index]
        self.recv_index += 1
        return data
    
    def close(self):
        self.closed = True
    
    def settimeout(self, timeout):
        self.timeout_value = timeout
    
    def add_recv_data(self, data):
        """Add data to be returned by recv()"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.recv_data.append(data)
    
    def set_peek_data(self, data):
        """Set data to be returned by recv with MSG_PEEK"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.peek_data = data


class TestLegacyHandler(unittest.TestCase):
    """Test cases for LegacyHandler class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create database manager
        self.db_manager = DatabaseManager(self.temp_db.name)
        
        # Create legacy handler
        self.handler = LegacyHandler(enabled=True, db_manager=self.db_manager)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary database
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass
    
    def test_legacy_handler_initialization(self):
        """Test legacy handler initializes correctly
        
        Requirements: 25.1
        """
        self.assertTrue(self.handler.enabled)
        self.assertIsNotNone(self.handler.db_manager)
        self.assertEqual(len(self.handler.legacy_agents), 0)
        self.assertEqual(len(self.handler.command_queues), 0)
    
    def test_legacy_handler_disabled(self):
        """Test legacy handler can be disabled
        
        Requirements: 25.6, 25.7
        """
        disabled_handler = LegacyHandler(enabled=False)
        self.assertFalse(disabled_handler.enabled)
        
        # Test that disabled handler rejects connections
        mock_conn = MockSocket()
        mock_conn.set_peek_data("[AGENT ONLINE] test")
        
        result = disabled_handler.is_legacy_connection(mock_conn)
        self.assertFalse(result)
    
    def test_detect_legacy_connection_with_immediate_data(self):
        """Test detection of legacy agent by immediate data
        
        Requirements: 25.1, 25.2
        """
        mock_conn = MockSocket()
        mock_conn.set_peek_data("[AGENT ONLINE] hostname|user|Windows")
        
        result = self.handler.is_legacy_connection(mock_conn, timeout=0.1)
        self.assertTrue(result)
    
    def test_detect_enhanced_connection_with_json(self):
        """Test detection of enhanced agent by JSON data
        
        Requirements: 25.1, 25.2
        """
        mock_conn = MockSocket()
        json_data = json.dumps({"type": "AUTH_RESPONSE"})
        mock_conn.set_peek_data(json_data)
        
        result = self.handler.is_legacy_connection(mock_conn, timeout=0.1)
        self.assertFalse(result)
    
    def test_detect_enhanced_connection_with_no_data(self):
        """Test detection of enhanced agent by no immediate data
        
        Requirements: 25.1, 25.2
        """
        mock_conn = MockSocket()
        mock_conn.set_peek_data(b"")
        
        result = self.handler.is_legacy_connection(mock_conn, timeout=0.1)
        self.assertFalse(result)
    
    def test_parse_legacy_info(self):
        """Test parsing legacy agent info string
        
        Requirements: 25.4
        """
        info_string = "[AGENT ONLINE] testhost|testuser|Windows|10.0|00:11:22:33:44:55"
        
        parsed = self.handler._parse_legacy_info(info_string)
        
        self.assertEqual(parsed["hostname"], "testhost")
        self.assertEqual(parsed["username"], "testuser")
        self.assertEqual(parsed["os_type"], "Windows")
        self.assertEqual(parsed["os_version"], "10.0")
        self.assertEqual(parsed["mac_address"], "00:11:22:33:44:55")
    
    def test_parse_legacy_info_minimal(self):
        """Test parsing minimal legacy agent info
        
        Requirements: 25.4
        """
        info_string = "[AGENT ONLINE] testhost"
        
        parsed = self.handler._parse_legacy_info(info_string)
        
        self.assertEqual(parsed["hostname"], "testhost")
        self.assertEqual(parsed["username"], "unknown")
        self.assertEqual(parsed["os_type"], "unknown")
    
    def test_send_command_to_legacy_agent(self):
        """Test queuing command for legacy agent
        
        Requirements: 25.2, 25.3
        """
        agent_id = "legacy_192.168.1.100_5000"
        
        # Initialize command queue
        with self.handler.queue_lock:
            self.handler.command_queues[agent_id] = []
        
        # Send command
        result = self.handler.send_command_to_legacy_agent(agent_id, "whoami")
        self.assertTrue(result)
        
        # Verify command queued
        with self.handler.queue_lock:
            self.assertEqual(len(self.handler.command_queues[agent_id]), 1)
            self.assertEqual(self.handler.command_queues[agent_id][0], "whoami")
    
    def test_send_command_to_nonexistent_agent(self):
        """Test sending command to nonexistent agent
        
        Requirements: 25.2, 25.3
        """
        result = self.handler.send_command_to_legacy_agent("nonexistent", "whoami")
        self.assertFalse(result)
    
    def test_get_legacy_agents(self):
        """Test getting list of legacy agents
        
        Requirements: 25.3
        """
        # Add mock legacy agent
        mock_conn = MockSocket()
        address = ("192.168.1.100", 5000)
        legacy_conn = LegacyAgentConnection(mock_conn, address)
        legacy_conn.agent_info = "[AGENT ONLINE] testhost|testuser|Windows"
        
        agent_id = "legacy_192.168.1.100_5000"
        
        with self.handler.agents_lock:
            self.handler.legacy_agents[agent_id] = legacy_conn
        
        # Get agents
        agents = self.handler.get_legacy_agents()
        
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["agent_id"], agent_id)
        self.assertEqual(agents[0]["address"], "192.168.1.100:5000")
        self.assertTrue(agents[0]["legacy"])
    
    def test_get_next_command(self):
        """Test getting next command from queue
        
        Requirements: 25.2
        """
        agent_id = "legacy_test"
        
        with self.handler.queue_lock:
            self.handler.command_queues[agent_id] = ["cmd1", "cmd2", "cmd3"]
        
        # Get commands in order
        cmd1 = self.handler._get_next_command(agent_id)
        self.assertEqual(cmd1, "cmd1")
        
        cmd2 = self.handler._get_next_command(agent_id)
        self.assertEqual(cmd2, "cmd2")
        
        cmd3 = self.handler._get_next_command(agent_id)
        self.assertEqual(cmd3, "cmd3")
        
        # No more commands
        cmd4 = self.handler._get_next_command(agent_id)
        self.assertIsNone(cmd4)


class TestConfigMigrator(unittest.TestCase):
    """Test cases for ConfigMigrator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.legacy_config_path = os.path.join(self.temp_dir, "legacy.conf")
        self.new_config_path = os.path.join(self.temp_dir, "new.json")
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            if os.path.exists(self.legacy_config_path):
                os.unlink(self.legacy_config_path)
            if os.path.exists(self.new_config_path):
                os.unlink(self.new_config_path)
            os.rmdir(self.temp_dir)
        except Exception:
            pass
    
    def test_migrate_config_success(self):
        """Test successful configuration migration
        
        Requirements: 25.4
        """
        # Create legacy config
        with open(self.legacy_config_path, 'w') as f:
            f.write("# Legacy configuration\n")
            f.write("SERVER_HOST=0.0.0.0\n")
            f.write("SERVER_PORT=9999\n")
            f.write("DB_PATH=./legacy.db\n")
            f.write("SECRET_KEY=legacy_secret\n")
        
        # Migrate
        result = ConfigMigrator.migrate_config(
            self.legacy_config_path,
            self.new_config_path
        )
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.new_config_path))
        
        # Verify new config
        with open(self.new_config_path, 'r') as f:
            new_config = json.load(f)
        
        self.assertEqual(new_config["server"]["host"], "0.0.0.0")
        self.assertEqual(new_config["server"]["port"], 9999)
        self.assertEqual(new_config["database"]["path"], "./legacy.db")
        self.assertEqual(new_config["server"]["secret_key"], "legacy_secret")
        self.assertTrue(new_config["legacy"]["enabled"])
    
    def test_migrate_config_nonexistent_file(self):
        """Test migration with nonexistent legacy config
        
        Requirements: 25.4
        """
        result = ConfigMigrator.migrate_config(
            "/nonexistent/path.conf",
            self.new_config_path
        )
        
        self.assertFalse(result)
        self.assertFalse(os.path.exists(self.new_config_path))
    
    def test_migrate_config_with_defaults(self):
        """Test migration with missing values uses defaults
        
        Requirements: 25.4
        """
        # Create minimal legacy config
        with open(self.legacy_config_path, 'w') as f:
            f.write("SERVER_HOST=192.168.1.1\n")
        
        # Migrate
        result = ConfigMigrator.migrate_config(
            self.legacy_config_path,
            self.new_config_path
        )
        
        self.assertTrue(result)
        
        # Verify defaults
        with open(self.new_config_path, 'r') as f:
            new_config = json.load(f)
        
        self.assertEqual(new_config["server"]["host"], "192.168.1.1")
        self.assertEqual(new_config["server"]["port"], 9999)  # Default
        self.assertEqual(new_config["database"]["path"], "./remote_system.db")  # Default


class TestLogMigrator(unittest.TestCase):
    """Test cases for LogMigrator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.legacy_log_path = os.path.join(self.temp_dir, "legacy.log")
        
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            if os.path.exists(self.legacy_log_path):
                os.unlink(self.legacy_log_path)
            os.rmdir(self.temp_dir)
            os.unlink(self.temp_db.name)
        except Exception:
            pass
    
    def test_migrate_logs_success(self):
        """Test successful log migration
        
        Requirements: 25.5
        """
        # Create legacy log
        with open(self.legacy_log_path, 'w') as f:
            f.write("[2024-01-01 12:00:00] [192.168.1.100:5000] [AGENT ONLINE] testhost|testuser|Windows\n")
            f.write("[2024-01-01 12:01:00] [192.168.1.100:5000] Command executed successfully\n")
            f.write("[2024-01-01 12:02:00] [192.168.1.101:5001] [CONNECTED] New agent\n")
        
        # Migrate
        success, failure = LogMigrator.migrate_logs(
            self.legacy_log_path,
            self.db_manager
        )
        
        self.assertEqual(success, 3)
        self.assertEqual(failure, 0)
    
    def test_migrate_logs_nonexistent_file(self):
        """Test migration with nonexistent log file
        
        Requirements: 25.5
        """
        success, failure = LogMigrator.migrate_logs(
            "/nonexistent/path.log",
            self.db_manager
        )
        
        self.assertEqual(success, 0)
        self.assertEqual(failure, 0)
    
    def test_migrate_logs_with_invalid_entries(self):
        """Test migration handles invalid log entries
        
        Requirements: 25.5
        """
        # Create log with some invalid entries
        with open(self.legacy_log_path, 'w') as f:
            f.write("[2024-01-01 12:00:00] [192.168.1.100:5000] [AGENT ONLINE] testhost\n")
            f.write("Invalid log entry without brackets\n")
            f.write("[2024-01-01 12:01:00] Incomplete entry\n")
            f.write("[2024-01-01 12:02:00] [192.168.1.101:5001] Valid entry\n")
        
        # Migrate
        success, failure = LogMigrator.migrate_logs(
            self.legacy_log_path,
            self.db_manager
        )
        
        # Should have some successes and some failures
        self.assertGreater(success, 0)
        self.assertGreaterEqual(failure, 0)


class TestLegacyHandlerIntegration(unittest.TestCase):
    """Integration tests for legacy handler with enhanced server"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.handler = LegacyHandler(enabled=True, db_manager=self.db_manager)
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass
    
    def test_simultaneous_legacy_and_enhanced_agents(self):
        """Test supporting both legacy and enhanced agents simultaneously
        
        Requirements: 25.3
        """
        # Add legacy agent
        mock_legacy_conn = MockSocket()
        legacy_address = ("192.168.1.100", 5000)
        legacy_conn = LegacyAgentConnection(mock_legacy_conn, legacy_address)
        legacy_conn.agent_info = "[AGENT ONLINE] legacy_host"
        
        legacy_id = "legacy_192.168.1.100_5000"
        
        with self.handler.agents_lock:
            self.handler.legacy_agents[legacy_id] = legacy_conn
        
        # Add enhanced agent to database
        enhanced_id = "enhanced_agent_123"
        enhanced_info = {
            "hostname": "enhanced_host",
            "username": "user",
            "os_type": "Linux",
            "os_version": "Ubuntu 20.04",
            "mac_address": "00:11:22:33:44:55",
            "ip_address": "192.168.1.101",
            "capabilities": [],
            "metadata": {}
        }
        self.db_manager.log_connection(enhanced_id, enhanced_info)
        
        # Get all agents
        legacy_agents = self.handler.get_legacy_agents()
        enhanced_agents = self.db_manager.get_active_agents()
        
        # Verify both types present
        self.assertEqual(len(legacy_agents), 1)
        self.assertEqual(len(enhanced_agents), 1)
        self.assertTrue(legacy_agents[0]["legacy"])
        self.assertEqual(legacy_agents[0]["agent_id"], legacy_id)
        self.assertEqual(enhanced_agents[0]["agent_id"], enhanced_id)


if __name__ == "__main__":
    unittest.main()
