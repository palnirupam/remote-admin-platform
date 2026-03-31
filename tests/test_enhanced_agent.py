"""
Unit Tests for Enhanced Agent

Tests connection, authentication, command execution, heartbeat,
reconnection logic, and result buffering.

Requirements: 4.1, 14.6, 19.2, 20.5
"""

import unittest
import socket
import threading
import time
import json
from unittest.mock import Mock, MagicMock, patch, call
import ssl

from remote_system.enhanced_agent.enhanced_agent import EnhancedAgent
from remote_system.enhanced_agent.plugin_manager import PluginResult


class MockSocket:
    """Mock socket for testing"""
    
    def __init__(self):
        self.sent_data = []
        self.receive_queue = []
        self.closed = False
        self.timeout_value = None
    
    def sendall(self, data):
        if self.closed:
            raise Exception("Socket is closed")
        self.sent_data.append(data)
    
    def recv(self, buffer_size):
        if self.closed:
            raise Exception("Socket is closed")
        if not self.receive_queue:
            raise socket.timeout("No data available")
        return self.receive_queue.pop(0)
    
    def close(self):
        self.closed = True
    
    def settimeout(self, timeout):
        self.timeout_value = timeout
    
    def connect(self, address):
        pass


class TestEnhancedAgent(unittest.TestCase):
    """Test suite for EnhancedAgent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server_ip = "127.0.0.1"
        self.server_port = 9999
        self.server_address = f"{self.server_ip}:{self.server_port}"
        self.token = "test_token_12345"
        self.plugin_dir = "./test_plugins"
    
    def test_initialization(self):
        """Test agent initialization with valid parameters"""
        agent = EnhancedAgent(
            server_address=self.server_address,
            token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        self.assertEqual(agent.server_ip, self.server_ip)
        self.assertEqual(agent.server_port, self.server_port)
        self.assertEqual(agent.token, self.token)
        self.assertFalse(agent.use_tls)
        self.assertEqual(agent.plugin_dir, self.plugin_dir)
        self.assertFalse(agent.connected)
        self.assertIsNotNone(agent.plugin_manager)
    
    def test_initialization_parse_ip_port(self):
        """Test agent initialization with IP:PORT format"""
        agent = EnhancedAgent(
            server_address="192.168.1.100:9999",
            token=self.token,
            use_tls=False
        )
        
        self.assertEqual(agent.server_ip, "192.168.1.100")
        self.assertEqual(agent.server_port, 9999)
    
    def test_initialization_parse_domain_port(self):
        """Test agent initialization with Domain:PORT format (dynamic DNS)"""
        agent = EnhancedAgent(
            server_address="myserver.ddns.net:9999",
            token=self.token,
            use_tls=False
        )
        
        self.assertEqual(agent.server_ip, "myserver.ddns.net")
        self.assertEqual(agent.server_port, 9999)
    
    def test_initialization_parse_ngrok_url(self):
        """Test agent initialization with Ngrok URL"""
        agent = EnhancedAgent(
            server_address="https://abc123.ngrok.io",
            token=self.token,
            use_tls=True
        )
        
        self.assertEqual(agent.server_ip, "abc123.ngrok.io")
        self.assertEqual(agent.server_port, 443)
    
    def test_initialization_parse_https_url_with_port(self):
        """Test agent initialization with HTTPS URL and custom port"""
        agent = EnhancedAgent(
            server_address="https://example.com:9999",
            token=self.token,
            use_tls=True
        )
        
        self.assertEqual(agent.server_ip, "example.com")
        self.assertEqual(agent.server_port, 9999)
    
    def test_initialization_invalid_parameters(self):
        """Test agent initialization with invalid parameters"""
        # Empty server address
        with self.assertRaises(ValueError):
            EnhancedAgent("", self.token)
        
        # Empty token
        with self.assertRaises(ValueError):
            EnhancedAgent(self.server_address, "")
        
        # Invalid address format
        with self.assertRaises(ValueError):
            EnhancedAgent("invalid_format", self.token)
        
        # Invalid port in address
        with self.assertRaises(ValueError):
            EnhancedAgent("192.168.1.100:0", self.token)
        
        with self.assertRaises(ValueError):
            EnhancedAgent("192.168.1.100:70000", self.token)
    
    @patch('socket.socket')
    def test_connect_success_without_tls(self, mock_socket_class):
        """Test successful connection without TLS"""
        # Create mock socket
        mock_sock = MockSocket()
        mock_socket_class.return_value = mock_sock
        
        # Prepare authentication flow
        auth_request = {"type": "AUTH_REQUEST"}
        auth_success = {"type": "AUTH_SUCCESS", "agent_id": "test_agent_123"}
        
        # Queue messages for receive
        self._queue_message(mock_sock, auth_request)
        self._queue_message(mock_sock, auth_success)
        
        # Create agent and connect
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        result = agent.connect()
        
        # Verify connection success
        self.assertTrue(result)
        self.assertTrue(agent.connected)
        self.assertEqual(agent.agent_id, "test_agent_123")
        
        # Verify authentication message was sent
        self.assertEqual(len(mock_sock.sent_data), 2)  # Length prefix + data
    
    @patch('socket.socket')
    def test_connect_authentication_failure(self, mock_socket_class):
        """Test connection with authentication failure"""
        # Create mock socket
        mock_sock = MockSocket()
        mock_socket_class.return_value = mock_sock
        
        # Prepare authentication flow with failure
        auth_request = {"type": "AUTH_REQUEST"}
        auth_failed = {"type": "AUTH_FAILED", "error": "Invalid token"}
        
        # Queue messages for receive
        self._queue_message(mock_sock, auth_request)
        self._queue_message(mock_sock, auth_failed)
        
        # Create agent and connect
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        result = agent.connect()
        
        # Verify connection failed
        self.assertFalse(result)
        self.assertFalse(agent.connected)
        self.assertIsNone(agent.agent_id)
    
    def test_handle_heartbeat(self):
        """Test heartbeat response mechanism"""
        # Create agent with mock connection
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Set up mock connection
        mock_sock = MockSocket()
        agent.connection = mock_sock
        agent.connected = True
        
        # Handle heartbeat
        agent._handle_heartbeat()
        
        # Verify heartbeat acknowledgment was sent
        self.assertEqual(len(mock_sock.sent_data), 2)  # Length prefix + data
        
        # Decode and verify message
        length = int.from_bytes(mock_sock.sent_data[0], byteorder='big')
        message_data = mock_sock.sent_data[1]
        message = json.loads(message_data.decode('utf-8'))
        
        self.assertEqual(message["type"], "HEARTBEAT_ACK")
    
    def test_handle_command_success(self):
        """Test command execution via plugin manager"""
        # Create agent with mock connection
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Set up mock connection
        mock_sock = MockSocket()
        agent.connection = mock_sock
        agent.connected = True
        
        # Mock plugin manager
        mock_plugin_result = PluginResult(
            success=True,
            data={"output": "command executed"},
            error=None,
            metadata={"execution_time": 0.5}
        )
        agent.plugin_manager.execute_plugin = Mock(return_value=mock_plugin_result)
        
        # Handle command
        command = {
            "plugin": "test_plugin",
            "args": {"arg1": "value1"}
        }
        agent._handle_command(command)
        
        # Verify plugin was executed
        agent.plugin_manager.execute_plugin.assert_called_once_with("test_plugin", {"arg1": "value1"})
        
        # Verify result was sent
        self.assertEqual(len(mock_sock.sent_data), 2)  # Length prefix + data
        
        # Decode and verify result message
        length = int.from_bytes(mock_sock.sent_data[0], byteorder='big')
        message_data = mock_sock.sent_data[1]
        message = json.loads(message_data.decode('utf-8'))
        
        self.assertEqual(message["type"], "COMMAND_RESULT")
        self.assertTrue(message["result"]["success"])
        self.assertEqual(message["result"]["data"], {"output": "command executed"})
    
    def test_handle_command_plugin_failure(self):
        """Test command execution with plugin failure"""
        # Create agent with mock connection
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Set up mock connection
        mock_sock = MockSocket()
        agent.connection = mock_sock
        agent.connected = True
        
        # Mock plugin manager with failure
        mock_plugin_result = PluginResult(
            success=False,
            data=None,
            error="Plugin execution failed",
            metadata={}
        )
        agent.plugin_manager.execute_plugin = Mock(return_value=mock_plugin_result)
        
        # Handle command
        command = {
            "plugin": "test_plugin",
            "args": {}
        }
        agent._handle_command(command)
        
        # Verify result was sent with error
        self.assertEqual(len(mock_sock.sent_data), 2)
        
        # Decode and verify result message
        length = int.from_bytes(mock_sock.sent_data[0], byteorder='big')
        message_data = mock_sock.sent_data[1]
        message = json.loads(message_data.decode('utf-8'))
        
        self.assertEqual(message["type"], "COMMAND_RESULT")
        self.assertFalse(message["result"]["success"])
        self.assertEqual(message["result"]["error"], "Plugin execution failed")
    
    def test_result_buffering_when_offline(self):
        """Test result buffering when connection is lost"""
        # Create agent
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Agent is offline
        agent.connected = False
        agent.connection = None
        
        # Mock plugin manager
        mock_plugin_result = PluginResult(
            success=True,
            data={"output": "test"},
            error=None,
            metadata={}
        )
        agent.plugin_manager.execute_plugin = Mock(return_value=mock_plugin_result)
        
        # Handle command while offline
        command = {
            "plugin": "test_plugin",
            "args": {}
        }
        agent._handle_command(command)
        
        # Verify result was buffered
        self.assertEqual(len(agent.result_buffer), 1)
        self.assertEqual(agent.result_buffer[0]["type"], "COMMAND_RESULT")
    
    def test_send_buffered_results_on_reconnect(self):
        """Test sending buffered results after reconnection"""
        # Create agent with mock connection
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Add buffered results
        agent.result_buffer = [
            {"type": "COMMAND_RESULT", "result": {"success": True, "data": "result1"}},
            {"type": "COMMAND_RESULT", "result": {"success": True, "data": "result2"}}
        ]
        
        # Set up mock connection
        mock_sock = MockSocket()
        agent.connection = mock_sock
        agent.connected = True
        
        # Send buffered results
        agent._send_buffered_results()
        
        # Verify all results were sent
        self.assertEqual(len(mock_sock.sent_data), 4)  # 2 messages * 2 (length + data)
        
        # Verify buffer was cleared
        self.assertEqual(len(agent.result_buffer), 0)
    
    def test_reconnection_exponential_backoff(self):
        """Test reconnection logic with exponential backoff"""
        # Create agent
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Mock connect method to fail
        agent.connect = Mock(return_value=False)
        
        # Test exponential backoff progression
        initial_delay = agent.reconnect_delay
        self.assertEqual(initial_delay, 5)
        
        # First reconnect attempt
        with patch('time.sleep'):
            result = agent._reconnect()
        self.assertFalse(result)
        self.assertEqual(agent.reconnect_delay, 10)  # 5 * 2
        
        # Second reconnect attempt
        with patch('time.sleep'):
            result = agent._reconnect()
        self.assertFalse(result)
        self.assertEqual(agent.reconnect_delay, 20)  # 10 * 2
        
        # Third reconnect attempt
        with patch('time.sleep'):
            result = agent._reconnect()
        self.assertFalse(result)
        self.assertEqual(agent.reconnect_delay, 40)  # 20 * 2
        
        # Fourth reconnect attempt
        with patch('time.sleep'):
            result = agent._reconnect()
        self.assertFalse(result)
        self.assertEqual(agent.reconnect_delay, 60)  # 40 * 2, capped at max
        
        # Fifth reconnect attempt (should stay at max)
        with patch('time.sleep'):
            result = agent._reconnect()
        self.assertFalse(result)
        self.assertEqual(agent.reconnect_delay, 60)  # Stays at max
    
    def test_reconnection_resets_delay_on_success(self):
        """Test that reconnection delay resets on successful connection"""
        # Create agent
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Set high reconnection delay
        agent.reconnect_delay = 40
        
        # Mock connect method to succeed
        agent.connect = Mock(return_value=True)
        
        # Reconnect successfully
        with patch('time.sleep'):
            result = agent._reconnect()
        
        self.assertTrue(result)
        self.assertEqual(agent.reconnect_delay, 5)  # Reset to initial value
    
    def test_collect_system_info(self):
        """Test system information collection"""
        # Create agent
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Mock plugin manager to return test plugins
        agent.plugin_manager.list_plugins = Mock(return_value=["plugin1", "plugin2"])
        
        # Collect system info
        info = agent._collect_system_info()
        
        # Verify required fields are present
        self.assertIn("hostname", info)
        self.assertIn("username", info)
        self.assertIn("os_type", info)
        self.assertIn("os_version", info)
        self.assertIn("mac_address", info)
        self.assertIn("capabilities", info)
        self.assertIn("metadata", info)
        
        # Verify capabilities include plugins
        self.assertEqual(info["capabilities"], ["plugin1", "plugin2"])
    
    def test_send_and_receive_message(self):
        """Test message sending and receiving with length prefix"""
        # Create agent with mock connection
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        # Set up mock connection
        mock_sock = MockSocket()
        agent.connection = mock_sock
        
        # Send message
        test_message = {"type": "TEST", "data": "hello"}
        agent._send_message(test_message)
        
        # Verify message was sent with length prefix
        self.assertEqual(len(mock_sock.sent_data), 2)
        
        # Decode sent message
        length = int.from_bytes(mock_sock.sent_data[0], byteorder='big')
        message_data = mock_sock.sent_data[1]
        
        self.assertEqual(len(message_data), length)
        decoded_message = json.loads(message_data.decode('utf-8'))
        self.assertEqual(decoded_message, test_message)
        
        # Test receiving message
        self._queue_message(mock_sock, test_message)
        received_message = agent._receive_message()
        
        self.assertEqual(received_message, test_message)
    
    def test_stop_agent(self):
        """Test stopping the agent"""
        # Create agent
        agent = EnhancedAgent(
            server_address=self.server_address, token=self.token,
            use_tls=False,
            plugin_dir=self.plugin_dir
        )
        
        agent.running = True
        agent.stop()
        
        self.assertFalse(agent.running)
    
    # Helper methods
    
    def _queue_message(self, mock_sock, message):
        """Queue a message for the mock socket to receive"""
        data = json.dumps(message).encode('utf-8')
        length = len(data)
        
        # Queue length prefix
        mock_sock.receive_queue.append(length.to_bytes(4, byteorder='big'))
        
        # Queue message data
        mock_sock.receive_queue.append(data)


if __name__ == "__main__":
    unittest.main()
