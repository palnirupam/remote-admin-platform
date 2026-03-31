"""
Integration Tests for Internet Deployment Support

Tests various server address formats for internet connectivity:
- Ngrok tunnel URLs
- Dynamic DNS domain names
- Public IP addresses with port forwarding
- Cloud VPS deployment configurations
- Connection retry with exponential backoff
- TLS encryption over internet connections
- DNS resolution for domain names

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
"""

import unittest
import socket
import ssl
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from remote_system.builder.enhanced_builder import EnhancedBuilder
from remote_system.enhanced_agent.enhanced_agent import EnhancedAgent
from remote_system.enhanced_agent.config_manager import ConfigManager
from remote_system.enhanced_agent.tls_wrapper import TLSAgentWrapper, connect_with_tls


class TestInternetDeployment(unittest.TestCase):
    """Test suite for internet deployment scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.token = "test_token_123"
    
    def test_builder_with_ngrok_url(self):
        """
        Test builder with Ngrok tunnel URL
        
        Requirements: 14.2
        """
        ngrok_url = "https://abc123.ngrok.io"
        
        builder = EnhancedBuilder(
            server_address=ngrok_url,
            token=self.token
        )
        
        self.assertEqual(builder.server_ip, "abc123.ngrok.io")
        self.assertEqual(builder.server_port, 443)
        self.assertEqual(builder.server_address, ngrok_url)
    
    def test_builder_with_dynamic_dns(self):
        """
        Test builder with dynamic DNS domain
        
        Requirements: 14.4
        """
        ddns_address = "myserver.ddns.net:9999"
        
        builder = EnhancedBuilder(
            server_address=ddns_address,
            token=self.token
        )
        
        self.assertEqual(builder.server_ip, "myserver.ddns.net")
        self.assertEqual(builder.server_port, 9999)
    
    def test_builder_with_public_ip_port_forwarding(self):
        """
        Test builder with public IP and port forwarding
        
        Requirements: 14.3
        """
        public_ip_address = "203.0.113.42:9999"
        
        builder = EnhancedBuilder(
            server_address=public_ip_address,
            token=self.token
        )
        
        self.assertEqual(builder.server_ip, "203.0.113.42")
        self.assertEqual(builder.server_port, 9999)
    
    def test_builder_with_cloud_vps(self):
        """
        Test builder with cloud VPS public IP
        
        Requirements: 14.5
        """
        vps_address = "https://vps.example.com:9999"
        
        builder = EnhancedBuilder(
            server_address=vps_address,
            token=self.token
        )
        
        self.assertEqual(builder.server_ip, "vps.example.com")
        self.assertEqual(builder.server_port, 9999)
    
    def test_agent_with_ngrok_url(self):
        """
        Test agent initialization with Ngrok URL
        
        Requirements: 14.2, 14.6
        """
        ngrok_url = "https://xyz789.ngrok.io"
        
        agent = EnhancedAgent(
            server_address=ngrok_url,
            token=self.token,
            use_tls=True
        )
        
        self.assertEqual(agent.server_ip, "xyz789.ngrok.io")
        self.assertEqual(agent.server_port, 443)
        self.assertTrue(agent.use_tls)
    
    def test_agent_with_dynamic_dns(self):
        """
        Test agent initialization with dynamic DNS
        
        Requirements: 14.4, 14.6
        """
        ddns_address = "remote.dyndns.org:9999"
        
        agent = EnhancedAgent(
            server_address=ddns_address,
            token=self.token,
            use_tls=True
        )
        
        self.assertEqual(agent.server_ip, "remote.dyndns.org")
        self.assertEqual(agent.server_port, 9999)
    
    def test_agent_with_public_ip(self):
        """
        Test agent initialization with public IP
        
        Requirements: 14.3, 14.6
        """
        public_ip = "198.51.100.10:9999"
        
        agent = EnhancedAgent(
            server_address=public_ip,
            token=self.token,
            use_tls=True
        )
        
        self.assertEqual(agent.server_ip, "198.51.100.10")
        self.assertEqual(agent.server_port, 9999)
    
    def test_config_manager_with_server_address(self):
        """
        Test config manager with server_address field
        
        Requirements: 14.2, 14.3, 14.4, 14.5
        """
        config_manager = ConfigManager()
        
        # Test with Ngrok URL
        config_manager.config.server_address = "https://test123.ngrok.io"
        config_manager.validate_config()
        
        self.assertEqual(config_manager.config.server_ip, "test123.ngrok.io")
        self.assertEqual(config_manager.config.server_port, 443)
        
        # Test with dynamic DNS
        config_manager.config.server_address = "myserver.ddns.net:8080"
        config_manager.validate_config()
        
        self.assertEqual(config_manager.config.server_ip, "myserver.ddns.net")
        self.assertEqual(config_manager.config.server_port, 8080)
        
        # Test with public IP
        config_manager.config.server_address = "192.0.2.1:9999"
        config_manager.validate_config()
        
        self.assertEqual(config_manager.config.server_ip, "192.0.2.1")
        self.assertEqual(config_manager.config.server_port, 9999)
    
    def test_config_manager_backward_compatibility(self):
        """
        Test config manager backward compatibility with server_ip/server_port
        
        Requirements: 14.1
        """
        config_manager = ConfigManager()
        
        # Test legacy format still works
        config_manager.config.server_ip = "192.168.1.100"
        config_manager.config.server_port = 9999
        config_manager.config.server_address = None
        
        config_manager.validate_config()
        
        self.assertEqual(config_manager.config.server_ip, "192.168.1.100")
        self.assertEqual(config_manager.config.server_port, 9999)
    
    def test_various_url_formats(self):
        """
        Test parsing of various URL formats
        
        Requirements: 14.2, 14.3, 14.4, 14.5
        """
        test_cases = [
            # (input_address, expected_host, expected_port)
            ("https://example.com", "example.com", 443),
            ("http://example.com", "example.com", 80),
            ("https://example.com:8443", "example.com", 8443),
            ("http://example.com:8080", "example.com", 8080),
            ("192.168.1.1:9999", "192.168.1.1", 9999),
            ("subdomain.example.com:9999", "subdomain.example.com", 9999),
            ("https://a1b2c3.ngrok.io", "a1b2c3.ngrok.io", 443),
        ]
        
        for address, expected_host, expected_port in test_cases:
            with self.subTest(address=address):
                builder = EnhancedBuilder(
                    server_address=address,
                    token=self.token
                )
                
                self.assertEqual(builder.server_ip, expected_host,
                               f"Failed for address: {address}")
                self.assertEqual(builder.server_port, expected_port,
                               f"Failed for address: {address}")
    
    def test_invalid_address_formats(self):
        """
        Test that invalid address formats raise appropriate errors
        
        Requirements: 14.2, 14.3, 14.4
        """
        invalid_addresses = [
            "invalid_format",
            "ftp://example.com",  # Unsupported scheme
            "example.com",  # Missing port
            "192.168.1.1",  # Missing port
            "",  # Empty
        ]
        
        for address in invalid_addresses:
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    EnhancedBuilder(
                        server_address=address,
                        token=self.token
                    )


class TestConnectionRetry(unittest.TestCase):
    """Test suite for connection retry with exponential backoff"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.token = "test_token_retry"
        self.server_address = "192.168.1.100:9999"
    
    @patch('socket.socket')
    def test_exponential_backoff_timing(self, mock_socket_class):
        """
        Test that connection retry uses exponential backoff
        
        Verifies: 5s, 10s, 20s, 40s, 60s (max) intervals
        
        Requirements: 14.6, 20.5
        """
        # Mock socket to always fail connection
        mock_socket = Mock()
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_socket_class.return_value = mock_socket
        
        agent = EnhancedAgent(
            server_address=self.server_address,
            token=self.token,
            use_tls=False
        )
        
        # Verify initial reconnect delay is 5 seconds
        self.assertEqual(agent.reconnect_delay, 5)
        
        # Simulate failed reconnection attempts
        with patch('time.sleep') as mock_sleep:
            # First attempt - should wait 5 seconds
            result = agent._reconnect()
            self.assertFalse(result)
            mock_sleep.assert_called_with(5)
            self.assertEqual(agent.reconnect_delay, 10)  # Doubled
            
            # Second attempt - should wait 10 seconds
            result = agent._reconnect()
            self.assertFalse(result)
            mock_sleep.assert_called_with(10)
            self.assertEqual(agent.reconnect_delay, 20)  # Doubled
            
            # Third attempt - should wait 20 seconds
            result = agent._reconnect()
            self.assertFalse(result)
            mock_sleep.assert_called_with(20)
            self.assertEqual(agent.reconnect_delay, 40)  # Doubled
            
            # Fourth attempt - should wait 40 seconds
            result = agent._reconnect()
            self.assertFalse(result)
            mock_sleep.assert_called_with(40)
            self.assertEqual(agent.reconnect_delay, 60)  # Capped at max
            
            # Fifth attempt - should wait 60 seconds (max)
            result = agent._reconnect()
            self.assertFalse(result)
            mock_sleep.assert_called_with(60)
            self.assertEqual(agent.reconnect_delay, 60)  # Still at max
    
    @patch('socket.socket')
    def test_reconnect_resets_delay_on_success(self, mock_socket_class):
        """
        Test that successful reconnection resets the backoff delay
        
        Requirements: 14.6, 20.5
        """
        # First connection fails, second succeeds
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        agent = EnhancedAgent(
            server_address=self.server_address,
            token=self.token,
            use_tls=False
        )
        
        # Increase reconnect delay
        agent.reconnect_delay = 40
        
        # Mock successful connection
        with patch.object(agent, 'connect', return_value=True):
            with patch('time.sleep'):
                result = agent._reconnect()
                self.assertTrue(result)
                # Delay should be reset to initial value
                self.assertEqual(agent.reconnect_delay, 5)
    
    @patch('socket.socket')
    def test_connection_retry_on_network_failure(self, mock_socket_class):
        """
        Test that agent retries connection when network fails
        
        Requirements: 14.6, 20.6
        """
        mock_socket = Mock()
        mock_socket.connect.side_effect = [
            socket.timeout("Connection timeout"),
            socket.timeout("Connection timeout"),
            None  # Third attempt succeeds
        ]
        mock_socket_class.return_value = mock_socket
        
        agent = EnhancedAgent(
            server_address=self.server_address,
            token=self.token,
            use_tls=False
        )
        
        # Mock authentication flow for successful connection
        with patch.object(agent, '_receive_message') as mock_recv:
            with patch.object(agent, '_send_message'):
                with patch.object(agent, '_collect_system_info', return_value={}):
                    mock_recv.side_effect = [
                        {"type": "AUTH_REQUEST"},
                        {"type": "AUTH_SUCCESS", "agent_id": "test_agent"}
                    ]
                    
                    # First two attempts should fail, third should succeed
                    self.assertFalse(agent.connect())  # First attempt fails
                    self.assertFalse(agent.connect())  # Second attempt fails
                    self.assertTrue(agent.connect())   # Third attempt succeeds
    
    def test_max_reconnect_delay_cap(self):
        """
        Test that reconnect delay is capped at maximum value
        
        Requirements: 20.6
        """
        agent = EnhancedAgent(
            server_address=self.server_address,
            token=self.token,
            use_tls=False
        )
        
        # Verify max delay is 60 seconds
        self.assertEqual(agent.max_reconnect_delay, 60)
        
        # Simulate many failed attempts
        agent.reconnect_delay = 30
        agent.reconnect_delay = min(agent.reconnect_delay * 2, agent.max_reconnect_delay)
        self.assertEqual(agent.reconnect_delay, 60)
        
        # Further doubling should not exceed max
        agent.reconnect_delay = min(agent.reconnect_delay * 2, agent.max_reconnect_delay)
        self.assertEqual(agent.reconnect_delay, 60)


class TestTLSOverInternet(unittest.TestCase):
    """Test suite for TLS encryption over internet connections"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.token = "test_token_tls"
    
    def test_tls_enabled_for_ngrok_url(self):
        """
        Test that TLS is properly configured for Ngrok URLs
        
        Requirements: 14.2, 14.7
        """
        ngrok_url = "https://abc123.ngrok.io"
        
        agent = EnhancedAgent(
            server_address=ngrok_url,
            token=self.token,
            use_tls=True
        )
        
        self.assertTrue(agent.use_tls)
        self.assertEqual(agent.server_ip, "abc123.ngrok.io")
        self.assertEqual(agent.server_port, 443)
    
    def test_tls_enabled_for_public_ip(self):
        """
        Test that TLS can be enabled for public IP connections
        
        Requirements: 14.3, 14.7
        """
        public_ip = "203.0.113.42:9999"
        
        agent = EnhancedAgent(
            server_address=public_ip,
            token=self.token,
            use_tls=True
        )
        
        self.assertTrue(agent.use_tls)
        self.assertEqual(agent.server_ip, "203.0.113.42")
        self.assertEqual(agent.server_port, 9999)
    
    def test_tls_enabled_for_dynamic_dns(self):
        """
        Test that TLS works with dynamic DNS domains
        
        Requirements: 14.4, 14.7
        """
        ddns_address = "myserver.ddns.net:9999"
        
        agent = EnhancedAgent(
            server_address=ddns_address,
            token=self.token,
            use_tls=True
        )
        
        self.assertTrue(agent.use_tls)
        self.assertEqual(agent.server_ip, "myserver.ddns.net")
        self.assertEqual(agent.server_port, 9999)
    
    @patch('remote_system.enhanced_agent.enhanced_agent.TLSAgentWrapper')
    def test_tls_wrapper_initialization(self, mock_tls_wrapper_class):
        """
        Test that TLS wrapper is properly initialized for internet connections
        
        Requirements: 14.7
        """
        mock_tls_wrapper = Mock()
        mock_tls_socket = Mock(spec=ssl.SSLSocket)
        mock_tls_wrapper.connect.return_value = mock_tls_socket
        mock_tls_wrapper_class.return_value = mock_tls_wrapper
        
        agent = EnhancedAgent(
            server_address="https://example.com:9999",
            token=self.token,
            use_tls=True
        )
        
        # Mock authentication flow
        with patch.object(agent, '_receive_message') as mock_recv:
            with patch.object(agent, '_send_message'):
                with patch.object(agent, '_collect_system_info', return_value={}):
                    mock_recv.side_effect = [
                        {"type": "AUTH_REQUEST"},
                        {"type": "AUTH_SUCCESS", "agent_id": "test_agent"}
                    ]
                    
                    result = agent.connect()
                    
                    # Verify TLS wrapper was created with correct parameters
                    mock_tls_wrapper_class.assert_called_once_with(
                        server_ip="example.com",
                        server_port=9999,
                        expected_fingerprint=None,
                        verify_cert=False,
                        timeout=30
                    )
                    
                    # Verify TLS connection was established
                    mock_tls_wrapper.connect.assert_called_once()
                    self.assertTrue(result)
    
    @patch('socket.socket')
    @patch('ssl.SSLContext')
    def test_tls_connection_with_certificate_pinning(self, mock_ssl_context_class, mock_socket_class):
        """
        Test TLS connection with certificate pinning for internet security
        
        Requirements: 14.7, 9.3, 9.4
        """
        expected_fingerprint = "a" * 64  # Mock SHA256 fingerprint
        
        # Mock SSL context and socket
        mock_context = Mock()
        mock_ssl_context_class.return_value = mock_context
        
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        mock_tls_socket = Mock(spec=ssl.SSLSocket)
        mock_context.wrap_socket.return_value = mock_tls_socket
        
        # Mock certificate
        mock_cert = b"mock_certificate_data"
        mock_tls_socket.getpeercert.return_value = mock_cert
        
        # Mock hashlib to return expected fingerprint
        with patch('hashlib.sha256') as mock_sha256:
            mock_hash = Mock()
            mock_hash.hexdigest.return_value = expected_fingerprint
            mock_sha256.return_value = mock_hash
            
            # Test TLS connection with pinning
            tls_wrapper = TLSAgentWrapper(
                server_ip="example.com",
                server_port=9999,
                expected_fingerprint=expected_fingerprint,
                verify_cert=False
            )
            
            # This should succeed with matching fingerprint
            # Note: In real test, this would connect to actual server
            # Here we're just verifying the wrapper is configured correctly
            self.assertEqual(tls_wrapper.expected_fingerprint, expected_fingerprint)
            self.assertEqual(tls_wrapper.server_ip, "example.com")
            self.assertEqual(tls_wrapper.server_port, 9999)
    
    def test_tls_enforced_for_internet_connections(self):
        """
        Test that TLS is enforced for all internet connections
        
        Requirements: 14.7
        """
        internet_addresses = [
            "https://ngrok.io",
            "https://example.com:9999",
            "203.0.113.42:9999",
            "myserver.ddns.net:9999"
        ]
        
        for address in internet_addresses:
            with self.subTest(address=address):
                agent = EnhancedAgent(
                    server_address=address,
                    token=self.token,
                    use_tls=True
                )
                
                # Verify TLS is enabled
                self.assertTrue(agent.use_tls)


class TestDNSResolution(unittest.TestCase):
    """Test suite for DNS resolution of domain names"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.token = "test_token_dns"
    
    def test_domain_name_parsing(self):
        """
        Test that domain names are correctly parsed
        
        Requirements: 14.4
        """
        test_cases = [
            ("example.com:9999", "example.com", 9999),
            ("subdomain.example.com:8080", "subdomain.example.com", 8080),
            ("my-server.ddns.net:9999", "my-server.ddns.net", 9999),
            ("remote.dyndns.org:7777", "remote.dyndns.org", 7777),
        ]
        
        for address, expected_host, expected_port in test_cases:
            with self.subTest(address=address):
                agent = EnhancedAgent(
                    server_address=address,
                    token=self.token,
                    use_tls=False
                )
                
                self.assertEqual(agent.server_ip, expected_host)
                self.assertEqual(agent.server_port, expected_port)
    
    def test_https_domain_parsing(self):
        """
        Test that HTTPS domains are correctly parsed
        
        Requirements: 14.2, 14.4
        """
        test_cases = [
            ("https://example.com", "example.com", 443),
            ("https://example.com:8443", "example.com", 8443),
            ("https://subdomain.example.com", "subdomain.example.com", 443),
            ("https://my-server.ddns.net:9999", "my-server.ddns.net", 9999),
        ]
        
        for address, expected_host, expected_port in test_cases:
            with self.subTest(address=address):
                builder = EnhancedBuilder(
                    server_address=address,
                    token=self.token
                )
                
                self.assertEqual(builder.server_ip, expected_host)
                self.assertEqual(builder.server_port, expected_port)
    
    @patch('socket.socket')
    def test_dns_resolution_during_connection(self, mock_socket_class):
        """
        Test that DNS resolution occurs when connecting to domain names
        
        Requirements: 14.4
        """
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        agent = EnhancedAgent(
            server_address="example.com:9999",
            token=self.token,
            use_tls=False
        )
        
        # Mock authentication flow
        with patch.object(agent, '_receive_message') as mock_recv:
            with patch.object(agent, '_send_message'):
                with patch.object(agent, '_collect_system_info', return_value={}):
                    mock_recv.side_effect = [
                        {"type": "AUTH_REQUEST"},
                        {"type": "AUTH_SUCCESS", "agent_id": "test_agent"}
                    ]
                    
                    agent.connect()
                    
                    # Verify socket.connect was called with domain name
                    # (DNS resolution happens inside socket.connect)
                    mock_socket.connect.assert_called_once_with(("example.com", 9999))
    
    def test_ngrok_subdomain_resolution(self):
        """
        Test that Ngrok subdomains are correctly resolved
        
        Requirements: 14.2
        """
        ngrok_urls = [
            ("https://abc123.ngrok.io", "abc123.ngrok.io", 443),
            ("https://my-app.ngrok.io", "my-app.ngrok.io", 443),
            ("https://test-server.ngrok-free.app", "test-server.ngrok-free.app", 443),
        ]
        
        for url, expected_host, expected_port in ngrok_urls:
            with self.subTest(url=url):
                agent = EnhancedAgent(
                    server_address=url,
                    token=self.token,
                    use_tls=True
                )
                
                self.assertEqual(agent.server_ip, expected_host)
                self.assertEqual(agent.server_port, expected_port)


class TestErrorHandling(unittest.TestCase):
    """Test suite for error handling in internet connections"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.token = "test_token_error"
    
    @patch('socket.socket')
    def test_connection_timeout_handling(self, mock_socket_class):
        """
        Test that connection timeouts are properly handled
        
        Requirements: 14.6, 15.4
        """
        mock_socket = Mock()
        mock_socket.connect.side_effect = socket.timeout("Connection timeout")
        mock_socket_class.return_value = mock_socket
        
        agent = EnhancedAgent(
            server_address="192.168.1.100:9999",
            token=self.token,
            use_tls=False
        )
        
        # Connection should fail gracefully
        result = agent.connect()
        self.assertFalse(result)
        self.assertFalse(agent.connected)
    
    @patch('socket.socket')
    def test_connection_refused_handling(self, mock_socket_class):
        """
        Test that connection refused errors are properly handled
        
        Requirements: 14.6, 15.1
        """
        mock_socket = Mock()
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_socket_class.return_value = mock_socket
        
        agent = EnhancedAgent(
            server_address="192.168.1.100:9999",
            token=self.token,
            use_tls=False
        )
        
        # Connection should fail gracefully without crashing
        result = agent.connect()
        self.assertFalse(result)
        self.assertFalse(agent.connected)
    
    def test_invalid_port_error(self):
        """
        Test that invalid port numbers raise appropriate errors
        
        Requirements: 14.2, 14.3
        """
        invalid_addresses = [
            "192.168.1.1:0",      # Port 0
            "192.168.1.1:65536",  # Port > 65535
            "192.168.1.1:-1",     # Negative port
        ]
        
        for address in invalid_addresses:
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    EnhancedAgent(
                        server_address=address,
                        token=self.token,
                        use_tls=False
                    )
    
    def test_empty_hostname_error(self):
        """
        Test that empty hostnames raise appropriate errors
        
        Requirements: 14.2, 14.4
        """
        with self.assertRaises(ValueError):
            EnhancedAgent(
                server_address=":9999",
                token=self.token,
                use_tls=False
            )
    
    @patch('socket.socket')
    def test_network_unreachable_handling(self, mock_socket_class):
        """
        Test that network unreachable errors are properly handled
        
        Requirements: 14.6, 15.1
        """
        mock_socket = Mock()
        mock_socket.connect.side_effect = OSError("Network is unreachable")
        mock_socket_class.return_value = mock_socket
        
        agent = EnhancedAgent(
            server_address="203.0.113.42:9999",
            token=self.token,
            use_tls=False
        )
        
        # Should handle error gracefully
        result = agent.connect()
        self.assertFalse(result)
        self.assertFalse(agent.connected)


if __name__ == "__main__":
    unittest.main()
