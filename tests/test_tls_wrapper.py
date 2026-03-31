"""
Unit Tests for TLS Wrapper Modules

Tests TLS encryption functionality for both server and agent sides,
including certificate generation, TLS handshake, certificate pinning,
and encrypted data transmission.

Requirements: 10.1, 10.2, 9.3, 9.4
"""

import unittest
import socket
import ssl
import os
import tempfile
import threading
import time
from pathlib import Path

# Import server-side TLS wrapper
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from remote_system.enhanced_server.tls_wrapper import (
    generate_self_signed_certificate,
    wrapSocketWithTLS,
    get_certificate_fingerprint,
    TLSServerWrapper
)

from remote_system.enhanced_agent.tls_wrapper import (
    connect_with_tls,
    validate_certificate_pinning,
    get_server_certificate_fingerprint,
    TLSAgentWrapper
)


class TestCertificateGeneration(unittest.TestCase):
    """Test certificate generation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cert_path = os.path.join(self.temp_dir, "test_server.crt")
        self.key_path = os.path.join(self.temp_dir, "test_server.key")
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.cert_path):
            os.remove(self.cert_path)
        if os.path.exists(self.key_path):
            os.remove(self.key_path)
        os.rmdir(self.temp_dir)
    
    def test_generate_self_signed_certificate(self):
        """Test self-signed certificate generation"""
        # Generate certificate
        cert_path, key_path = generate_self_signed_certificate(
            cert_path=self.cert_path,
            key_path=self.key_path,
            common_name="test.localhost"
        )
        
        # Verify files were created
        self.assertTrue(os.path.exists(cert_path))
        self.assertTrue(os.path.exists(key_path))
        
        # Verify files are not empty
        self.assertGreater(os.path.getsize(cert_path), 0)
        self.assertGreater(os.path.getsize(key_path), 0)
    
    def test_get_certificate_fingerprint(self):
        """Test certificate fingerprint calculation"""
        # Generate certificate
        generate_self_signed_certificate(
            cert_path=self.cert_path,
            key_path=self.key_path
        )
        
        # Get fingerprint
        fingerprint = get_certificate_fingerprint(self.cert_path)
        
        # Verify fingerprint format (64 hex characters for SHA256)
        self.assertEqual(len(fingerprint), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in fingerprint))
    
    def test_fingerprint_consistency(self):
        """Test that fingerprint is consistent for same certificate"""
        # Generate certificate
        generate_self_signed_certificate(
            cert_path=self.cert_path,
            key_path=self.key_path
        )
        
        # Get fingerprint twice
        fingerprint1 = get_certificate_fingerprint(self.cert_path)
        fingerprint2 = get_certificate_fingerprint(self.cert_path)
        
        # Verify they match
        self.assertEqual(fingerprint1, fingerprint2)


class TestTLSServerWrapper(unittest.TestCase):
    """Test TLS server wrapper functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cert_path = os.path.join(self.temp_dir, "server.crt")
        self.key_path = os.path.join(self.temp_dir, "server.key")
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.cert_path):
            os.remove(self.cert_path)
        if os.path.exists(self.key_path):
            os.remove(self.key_path)
        os.rmdir(self.temp_dir)
    
    def test_tls_server_wrapper_auto_generate(self):
        """Test TLS server wrapper with auto-generation"""
        wrapper = TLSServerWrapper(
            cert_path=self.cert_path,
            key_path=self.key_path,
            auto_generate=True
        )
        
        # Verify certificate was generated
        self.assertTrue(wrapper.certificate_exists())
        self.assertTrue(os.path.exists(self.cert_path))
        self.assertTrue(os.path.exists(self.key_path))
    
    def test_tls_server_wrapper_fingerprint(self):
        """Test getting fingerprint from wrapper"""
        wrapper = TLSServerWrapper(
            cert_path=self.cert_path,
            key_path=self.key_path,
            auto_generate=True
        )
        
        fingerprint = wrapper.get_fingerprint()
        
        # Verify fingerprint format
        self.assertEqual(len(fingerprint), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in fingerprint))


class TestTLSHandshake(unittest.TestCase):
    """Test TLS handshake between server and agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cert_path = os.path.join(self.temp_dir, "server.crt")
        self.key_path = os.path.join(self.temp_dir, "server.key")
        self.server_port = 19999  # Use different port for testing
        self.server_socket = None
        self.server_thread = None
        self.server_running = False
        
        # Generate certificate
        generate_self_signed_certificate(
            cert_path=self.cert_path,
            key_path=self.key_path,
            common_name="localhost"
        )
        
        self.fingerprint = get_certificate_fingerprint(self.cert_path)
    
    def tearDown(self):
        """Clean up test resources"""
        self.server_running = False
        
        if self.server_thread:
            self.server_thread.join(timeout=2)
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        
        if os.path.exists(self.cert_path):
            os.remove(self.cert_path)
        if os.path.exists(self.key_path):
            os.remove(self.key_path)
        os.rmdir(self.temp_dir)
    
    def start_test_server(self):
        """Start a test TLS server"""
        def server_loop():
            try:
                # Create server socket
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(("127.0.0.1", self.server_port))
                self.server_socket.listen(1)
                self.server_socket.settimeout(1.0)
                
                self.server_running = True
                
                while self.server_running:
                    try:
                        conn, addr = self.server_socket.accept()
                        
                        # Wrap with TLS
                        tls_conn = wrapSocketWithTLS(
                            conn,
                            cert_path=self.cert_path,
                            key_path=self.key_path
                        )
                        
                        # Echo server: receive and send back multiple messages
                        tls_conn.settimeout(2.0)
                        while self.server_running:
                            try:
                                data = tls_conn.recv(1024)
                                if not data:
                                    break
                                tls_conn.send(data)
                            except socket.timeout:
                                break
                            except Exception:
                                break
                        
                        tls_conn.close()
                    except socket.timeout:
                        continue
                    except Exception:
                        break
            except Exception:
                pass
        
        self.server_thread = threading.Thread(target=server_loop, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
    
    def test_tls_handshake_success(self):
        """Test successful TLS handshake"""
        self.start_test_server()
        
        # Connect with TLS (without certificate verification for self-signed)
        tls_socket = connect_with_tls(
            server_ip="127.0.0.1",
            server_port=self.server_port,
            verify_cert=False,
            timeout=5
        )
        
        # Verify connection is established
        self.assertIsNotNone(tls_socket)
        self.assertIsInstance(tls_socket, ssl.SSLSocket)
        
        # Test data transmission
        test_data = b"Hello TLS Server"
        tls_socket.send(test_data)
        response = tls_socket.recv(1024)
        
        self.assertEqual(response, test_data)
        
        tls_socket.close()
    
    def test_tls_handshake_with_certificate_pinning_success(self):
        """Test TLS handshake with valid certificate pinning"""
        self.start_test_server()
        
        # Connect with certificate pinning
        tls_socket = connect_with_tls(
            server_ip="127.0.0.1",
            server_port=self.server_port,
            expected_fingerprint=self.fingerprint,
            verify_cert=False,
            timeout=5
        )
        
        # Verify connection is established
        self.assertIsNotNone(tls_socket)
        
        tls_socket.close()
    
    def test_tls_handshake_with_certificate_pinning_failure(self):
        """Test TLS handshake with invalid certificate pinning"""
        self.start_test_server()
        
        # Try to connect with wrong fingerprint
        wrong_fingerprint = "0" * 64
        
        with self.assertRaises(ValueError) as context:
            connect_with_tls(
                server_ip="127.0.0.1",
                server_port=self.server_port,
                expected_fingerprint=wrong_fingerprint,
                verify_cert=False,
                timeout=5
            )
        
        self.assertIn("Certificate pinning validation failed", str(context.exception))
    
    def test_encrypted_data_transmission(self):
        """Test encrypted data transmission over TLS"""
        self.start_test_server()
        
        # Connect with TLS
        tls_socket = connect_with_tls(
            server_ip="127.0.0.1",
            server_port=self.server_port,
            verify_cert=False,
            timeout=5
        )
        
        # Send multiple messages
        test_messages = [
            b"Message 1",
            b"Message 2 with more data",
            b"Message 3: Special chars !@#$%"
        ]
        
        for msg in test_messages:
            tls_socket.send(msg)
            response = tls_socket.recv(1024)
            self.assertEqual(response, msg)
        
        tls_socket.close()


class TestTLSAgentWrapper(unittest.TestCase):
    """Test TLS agent wrapper functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cert_path = os.path.join(self.temp_dir, "server.crt")
        self.key_path = os.path.join(self.temp_dir, "server.key")
        self.server_port = 19998
        self.server_socket = None
        self.server_thread = None
        self.server_running = False
        
        # Generate certificate
        generate_self_signed_certificate(
            cert_path=self.cert_path,
            key_path=self.key_path,
            common_name="localhost"
        )
        
        self.fingerprint = get_certificate_fingerprint(self.cert_path)
    
    def tearDown(self):
        """Clean up test resources"""
        self.server_running = False
        
        if self.server_thread:
            self.server_thread.join(timeout=2)
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        
        if os.path.exists(self.cert_path):
            os.remove(self.cert_path)
        if os.path.exists(self.key_path):
            os.remove(self.key_path)
        os.rmdir(self.temp_dir)
    
    def start_test_server(self):
        """Start a test TLS server"""
        def server_loop():
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(("127.0.0.1", self.server_port))
                self.server_socket.listen(1)
                self.server_socket.settimeout(1.0)
                
                self.server_running = True
                
                while self.server_running:
                    try:
                        conn, addr = self.server_socket.accept()
                        tls_conn = wrapSocketWithTLS(
                            conn,
                            cert_path=self.cert_path,
                            key_path=self.key_path
                        )
                        
                        data = tls_conn.recv(1024)
                        if data:
                            tls_conn.send(data)
                        
                        tls_conn.close()
                    except socket.timeout:
                        continue
                    except Exception:
                        break
            except Exception:
                pass
        
        self.server_thread = threading.Thread(target=server_loop, daemon=True)
        self.server_thread.start()
        time.sleep(0.5)
    
    def test_agent_wrapper_connect(self):
        """Test agent wrapper connection"""
        self.start_test_server()
        
        wrapper = TLSAgentWrapper(
            server_ip="127.0.0.1",
            server_port=self.server_port,
            verify_cert=False
        )
        
        # Connect
        connection = wrapper.connect()
        
        self.assertIsNotNone(connection)
        self.assertTrue(wrapper.is_connected())
        
        wrapper.disconnect()
        self.assertFalse(wrapper.is_connected())
    
    def test_agent_wrapper_send_recv(self):
        """Test agent wrapper send and receive"""
        self.start_test_server()
        
        wrapper = TLSAgentWrapper(
            server_ip="127.0.0.1",
            server_port=self.server_port,
            verify_cert=False
        )
        
        wrapper.connect()
        
        # Send and receive data
        test_data = b"Test message"
        wrapper.send(test_data)
        response = wrapper.recv(1024)
        
        self.assertEqual(response, test_data)
        
        wrapper.disconnect()
    
    def test_agent_wrapper_with_pinning(self):
        """Test agent wrapper with certificate pinning"""
        self.start_test_server()
        
        wrapper = TLSAgentWrapper(
            server_ip="127.0.0.1",
            server_port=self.server_port,
            expected_fingerprint=self.fingerprint,
            verify_cert=False
        )
        
        # Connect with pinning
        wrapper.connect()
        
        # Validate pinning
        self.assertTrue(wrapper.validate_pinning())
        
        wrapper.disconnect()


class TestTLSErrorHandling(unittest.TestCase):
    """Test TLS error handling"""
    
    def test_connection_to_nonexistent_server(self):
        """Test connection failure to nonexistent server"""
        with self.assertRaises(Exception):
            connect_with_tls(
                server_ip="127.0.0.1",
                server_port=19997,  # No server listening
                verify_cert=False,
                timeout=2
            )
    
    def test_missing_certificate_files(self):
        """Test error when certificate files are missing"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        with self.assertRaises(FileNotFoundError):
            wrapSocketWithTLS(
                sock,
                cert_path="nonexistent.crt",
                key_path="nonexistent.key"
            )
        
        sock.close()
    
    def test_agent_wrapper_send_without_connection(self):
        """Test sending data without connection"""
        wrapper = TLSAgentWrapper(
            server_ip="127.0.0.1",
            server_port=19996,
            verify_cert=False
        )
        
        with self.assertRaises(ConnectionError):
            wrapper.send(b"test")
    
    def test_agent_wrapper_recv_without_connection(self):
        """Test receiving data without connection"""
        wrapper = TLSAgentWrapper(
            server_ip="127.0.0.1",
            server_port=19996,
            verify_cert=False
        )
        
        with self.assertRaises(ConnectionError):
            wrapper.recv(1024)


if __name__ == '__main__':
    unittest.main()
