"""
Unit Tests for Enhanced Server Module

Tests connection handling, authentication flow, agent registration,
heartbeat mechanism, and broadcast commands.

Requirements: 1.1, 16.1, 19.1-19.5
"""

import unittest
import socket
import json
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
import tempfile
import os

from remote_system.enhanced_server.enhanced_server import EnhancedServer, AgentConnection
from remote_system.enhanced_server.auth_module import AuthenticationModule


class MockSocket:
    """Mock socket for testing"""
    
    def __init__(self):
        self.sent_data = []
        self.recv_data = []
        self.recv_index = 0
        self.closed = False
        self.timeout_value = None
    
    def sendall(self, data):
        if self.closed:
            raise Exception("Socket is closed")
        self.sent_data.append(data)
    
    def recv(self, size):
        if self.closed:
            raise Exception("Socket is closed")
        if self.recv_index >= len(self.recv_data):
            raise socket.timeout("No more data")
        data = self.recv_data[self.recv_index]
        self.recv_index += 1
        return data
    
    def close(self):
        self.closed = True
    
    def settimeout(self, timeout):
        self.timeout_value = timeout
    
    def add_recv_data(self, data):
        """Add data to be returned by recv()"""
        self.recv_data.append(data)


class TestEnhancedServer(unittest.TestCase):
    """Test cases for EnhancedServer class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create server instance without TLS for testing
        self.server = EnhancedServer(
            host="127.0.0.1",
            port=9999,
            db_path=self.temp_db.name,
            use_tls=False,
            secret_key="test_secret_key"
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Stop server if running
        if self.server.running:
            self.server.stop()
        
        # Remove temporary database
        try:
            os.unlink(self.temp_db.name)
        except Exception:
            pass
    
    def test_server_initialization(self):
        """Test server initializes correctly"""
        self.assertEqual(self.server.host, "127.0.0.1")
        self.assertEqual(self.server.port, 9999)
        self.assertFalse(self.server.use_tls)
        self.assertIsNotNone(self.server.db_manager)
        self.assertIsNotNone(self.server.auth_module)
        self.assertEqual(len(self.server.active_agents), 0)
    
    def test_register_agent(self):
        """Test agent registration"""
        mock_conn = MockSocket()
        address = ("192.168.1.100", 12345)
        agent_info = {
            "hostname": "test-host",
            "username": "test-user",
            "os_type": "Windows",
            "os_version": "10",
            "ip_address": "192.168.1.100",
            "mac_address": "00:11:22:33:44:55"
        }
        
        agent_id = self.server._register_agent(mock_conn, address, agent_info)
        
        # Verify agent is registered
        self.assertIsNotNone(agent_id)
        self.assertIn(agent_id, self.server.active_agents)
        # Command queue is now managed by resource_limiter
        self.assertEqual(self.server.resource_limiter.get_queue_size(agent_id), 0)
        
        # Verify agent connection object
        agent_conn = self.server.active_agents[agent_id]
        self.assertEqual(agent_conn.agent_id, agent_id)
        self.assertEqual(agent_conn.connection, mock_conn)
        self.assertEqual(agent_conn.address, address)
    
    def test_unregister_agent(self):
        """Test agent unregistration"""
        # First register an agent
        mock_conn = MockSocket()
        address = ("192.168.1.100", 12345)
        agent_info = {
            "hostname": "test-host",
            "username": "test-user",
            "os_type": "Windows",
            "os_version": "10",
            "ip_address": "192.168.1.100",
            "mac_address": "00:11:22:33:44:55"
        }
        
        agent_id = self.server._register_agent(mock_conn, address, agent_info)
        
        # Verify agent is registered
        self.assertIn(agent_id, self.server.active_agents)
        
        # Unregister agent
        self.server._unregister_agent(agent_id)
        
        # Verify agent is removed
        self.assertNotIn(agent_id, self.server.active_agents)
        # Command queue is cleaned up by resource_limiter
        self.assertEqual(self.server.resource_limiter.get_queue_size(agent_id), 0)
    
    def test_broadcast_command_all_agents(self):
        """Test broadcasting command to all agents"""
        # Register multiple agents
        agent_ids = []
        for i in range(3):
            mock_conn = MockSocket()
            address = (f"192.168.1.{100+i}", 12345)
            agent_info = {
                "hostname": f"test-host-{i}",
                "username": "test-user",
                "os_type": "Windows",
                "os_version": "10",
                "ip_address": address[0],
                "mac_address": f"00:11:22:33:44:{i:02d}"
            }
            agent_id = self.server._register_agent(mock_conn, address, agent_info)
            agent_ids.append(agent_id)
        
        # Broadcast command
        command = {"plugin": "test", "action": "test_action"}
        results = self.server.broadcast_command(command)
        
        # Verify command was queued for all agents
        self.assertEqual(len(results), 3)
        for agent_id in agent_ids:
            self.assertEqual(results[agent_id], "queued")
            self.assertEqual(self.server.resource_limiter.get_queue_size(agent_id), 1)
    
    def test_broadcast_command_specific_agents(self):
        """Test broadcasting command to specific agents"""
        # Register multiple agents
        agent_ids = []
        for i in range(3):
            mock_conn = MockSocket()
            address = (f"192.168.1.{100+i}", 12345)
            agent_info = {
                "hostname": f"test-host-{i}",
                "username": "test-user",
                "os_type": "Windows",
                "os_version": "10",
                "ip_address": address[0],
                "mac_address": f"00:11:22:33:44:{i:02d}"
            }
            agent_id = self.server._register_agent(mock_conn, address, agent_info)
            agent_ids.append(agent_id)
        
        # Broadcast command to first two agents only
        command = {"plugin": "test", "action": "test_action"}
        target_agents = agent_ids[:2]
        results = self.server.broadcast_command(command, target_agents)
        
        # Verify command was queued for target agents only
        self.assertEqual(len(results), 2)
        for agent_id in target_agents:
            self.assertEqual(results[agent_id], "queued")
            self.assertEqual(self.server.resource_limiter.get_queue_size(agent_id), 1)
        
        # Verify third agent did not receive command
        self.assertEqual(self.server.resource_limiter.get_queue_size(agent_ids[2]), 0)
    
    def test_get_active_agents(self):
        """Test getting list of active agents"""
        # Register agents
        for i in range(2):
            mock_conn = MockSocket()
            address = (f"192.168.1.{100+i}", 12345)
            agent_info = {
                "hostname": f"test-host-{i}",
                "username": "test-user",
                "os_type": "Windows",
                "os_version": "10",
                "ip_address": address[0],
                "mac_address": f"00:11:22:33:44:{i:02d}"
            }
            self.server._register_agent(mock_conn, address, agent_info)
        
        # Get active agents
        active_agents = self.server.get_active_agents()
        
        # Verify we get the registered agents
        self.assertEqual(len(active_agents), 2)
        for agent in active_agents:
            self.assertIn("agent_id", agent)
            self.assertIn("hostname", agent)
            self.assertEqual(agent["status"], "online")
    
    def test_send_message(self):
        """Test sending JSON message"""
        mock_conn = MockSocket()
        message = {"type": "TEST", "data": "test_data"}
        
        self.server._send_message(mock_conn, message)
        
        # Verify message was sent with length prefix
        self.assertEqual(len(mock_conn.sent_data), 2)
        
        # Verify length prefix
        length_bytes = mock_conn.sent_data[0]
        length = int.from_bytes(length_bytes, byteorder='big')
        
        # Verify message data
        message_bytes = mock_conn.sent_data[1]
        self.assertEqual(len(message_bytes), length)
        received_message = json.loads(message_bytes.decode('utf-8'))
        self.assertEqual(received_message, message)
    
    def test_receive_message(self):
        """Test receiving JSON message"""
        mock_conn = MockSocket()
        message = {"type": "TEST", "data": "test_data"}
        
        # Prepare mock data
        message_bytes = json.dumps(message).encode('utf-8')
        length = len(message_bytes)
        length_bytes = length.to_bytes(4, byteorder='big')
        
        # Add data to mock socket
        mock_conn.add_recv_data(length_bytes)
        mock_conn.add_recv_data(message_bytes)
        
        # Receive message
        received_message = self.server._receive_message(mock_conn)
        
        # Verify message
        self.assertEqual(received_message, message)
    
    def test_get_next_command(self):
        """Test getting next command from queue"""
        # Register agent
        mock_conn = MockSocket()
        address = ("192.168.1.100", 12345)
        agent_info = {
            "hostname": "test-host",
            "username": "test-user",
            "os_type": "Windows",
            "os_version": "10",
            "ip_address": "192.168.1.100",
            "mac_address": "00:11:22:33:44:55"
        }
        agent_id = self.server._register_agent(mock_conn, address, agent_info)
        
        # Add commands to queue using resource_limiter
        command1 = {"plugin": "test", "action": "action1"}
        command2 = {"plugin": "test", "action": "action2"}
        self.server.resource_limiter.queue_command(agent_id, command1)
        self.server.resource_limiter.queue_command(agent_id, command2)
        
        # Get first command
        cmd = self.server._get_next_command(agent_id)
        self.assertEqual(cmd, command1)
        
        # Get second command
        cmd = self.server._get_next_command(agent_id)
        self.assertEqual(cmd, command2)
        
        # Queue should be empty now
        cmd = self.server._get_next_command(agent_id)
        self.assertIsNone(cmd)
    
    def test_authentication_flow_valid_token(self):
        """Test authentication flow with valid token"""
        # Generate valid token
        auth_module = AuthenticationModule("test_secret_key")
        token = auth_module.generate_token("test_agent", {"test": "metadata"})
        
        # Validate token
        validation = auth_module.validate_token(token)
        
        self.assertTrue(validation.valid)
        self.assertEqual(validation.agent_id, "test_agent")
        self.assertIsNone(validation.error)
    
    def test_authentication_flow_invalid_token(self):
        """Test authentication flow with invalid token"""
        auth_module = AuthenticationModule("test_secret_key")
        
        # Validate invalid token
        validation = auth_module.validate_token("invalid_token")
        
        self.assertFalse(validation.valid)
        self.assertIsNotNone(validation.error)
    
    def test_authentication_flow_expired_token(self):
        """Test authentication flow with expired token"""
        # Create auth module with 1 second expiry
        auth_module = AuthenticationModule("test_secret_key", token_expiry=1)
        token = auth_module.generate_token("test_agent")
        
        # Wait for token to expire
        time.sleep(2)
        
        # Validate expired token
        validation = auth_module.validate_token(token)
        
        self.assertFalse(validation.valid)
        self.assertIn("expired", validation.error.lower())
    
    def test_heartbeat_mechanism(self):
        """Test heartbeat mechanism updates agent status"""
        # Register agent
        mock_conn = MockSocket()
        address = ("192.168.1.100", 12345)
        agent_info = {
            "hostname": "test-host",
            "username": "test-user",
            "os_type": "Windows",
            "os_version": "10",
            "ip_address": "192.168.1.100",
            "mac_address": "00:11:22:33:44:55"
        }
        agent_id = self.server._register_agent(mock_conn, address, agent_info)
        
        # Verify agent is online
        agents = self.server.get_active_agents()
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["status"], "online")
        
        # Update agent status to offline
        self.server.db_manager.update_agent_status(agent_id, "offline")
        
        # Verify status changed
        agent = self.server.db_manager.get_agent_by_id(agent_id)
        self.assertEqual(agent["status"], "offline")
    
    def test_command_queue_isolation(self):
        """Test that command queues are isolated per agent"""
        # Register two agents
        agent_ids = []
        for i in range(2):
            mock_conn = MockSocket()
            address = (f"192.168.1.{100+i}", 12345)
            agent_info = {
                "hostname": f"test-host-{i}",
                "username": "test-user",
                "os_type": "Windows",
                "os_version": "10",
                "ip_address": address[0],
                "mac_address": f"00:11:22:33:44:{i:02d}"
            }
            agent_id = self.server._register_agent(mock_conn, address, agent_info)
            agent_ids.append(agent_id)
        
        # Add command to first agent only using resource_limiter
        command = {"plugin": "test", "action": "test_action"}
        self.server.resource_limiter.queue_command(agent_ids[0], command)
        
        # Verify first agent has command
        self.assertEqual(self.server.resource_limiter.get_queue_size(agent_ids[0]), 1)
        
        # Verify second agent has no commands
        self.assertEqual(self.server.resource_limiter.get_queue_size(agent_ids[1]), 0)
    
    def test_concurrent_agent_registration(self):
        """Test concurrent agent registration is thread-safe"""
        registered_agents = []
        
        def register_agent(index):
            mock_conn = MockSocket()
            address = (f"192.168.1.{100+index}", 12345)
            agent_info = {
                "hostname": f"test-host-{index}",
                "username": "test-user",
                "os_type": "Windows",
                "os_version": "10",
                "ip_address": address[0],
                "mac_address": f"00:11:22:33:44:{index:02d}"
            }
            agent_id = self.server._register_agent(mock_conn, address, agent_info)
            registered_agents.append(agent_id)
        
        # Register agents concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_agent, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all agents registered
        self.assertEqual(len(registered_agents), 10)
        self.assertEqual(len(self.server.active_agents), 10)
        
        # Verify all agent IDs are unique
        self.assertEqual(len(set(registered_agents)), 10)


class TestAgentConnection(unittest.TestCase):
    """Test cases for AgentConnection class"""
    
    def test_agent_connection_initialization(self):
        """Test AgentConnection initializes correctly"""
        mock_conn = MockSocket()
        address = ("192.168.1.100", 12345)
        agent_info = {
            "hostname": "test-host",
            "username": "test-user"
        }
        
        agent_conn = AgentConnection("test_id", mock_conn, address, agent_info)
        
        self.assertEqual(agent_conn.agent_id, "test_id")
        self.assertEqual(agent_conn.connection, mock_conn)
        self.assertEqual(agent_conn.address, address)
        self.assertEqual(agent_conn.agent_info, agent_info)
        self.assertIsNotNone(agent_conn.last_heartbeat)
        self.assertIsNotNone(agent_conn.lock)


if __name__ == "__main__":
    unittest.main()
