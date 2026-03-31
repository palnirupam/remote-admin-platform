"""
TLS Wrapper Module for Enhanced Agent

This module provides TLS encryption for agent-side connections with
certificate pinning validation for secure server authentication.

Requirements: 9.3, 9.4, 10.1, 10.2, 14.7
"""

import ssl
import socket
from typing import Optional
import hashlib


def validate_certificate_pinning(
    sock: ssl.SSLSocket,
    expected_fingerprint: str
) -> bool:
    """
    Validate server certificate using certificate pinning
    
    Args:
        sock: TLS socket with established connection
        expected_fingerprint: Expected SHA256 fingerprint (hex-encoded)
    
    Returns:
        True if certificate matches expected fingerprint, False otherwise
    
    Requirements: 9.3, 9.4
    """
    try:
        # Get peer certificate in DER format
        cert_der = sock.getpeercert(binary_form=True)
        
        if not cert_der:
            return False
        
        # Calculate SHA256 fingerprint
        fingerprint = hashlib.sha256(cert_der).hexdigest()
        
        # Compare with expected fingerprint (case-insensitive)
        return fingerprint.lower() == expected_fingerprint.lower()
    
    except Exception:
        return False


def connect_with_tls(
    server_ip: str,
    server_port: int,
    expected_fingerprint: Optional[str] = None,
    verify_cert: bool = True,
    timeout: int = 30
) -> ssl.SSLSocket:
    """
    Connect to server with TLS encryption and optional certificate pinning
    
    Args:
        server_ip: Server IP address or hostname
        server_port: Server port number
        expected_fingerprint: Expected certificate fingerprint for pinning (optional)
        verify_cert: Whether to verify server certificate
        timeout: Connection timeout in seconds
    
    Returns:
        TLS-wrapped socket connected to server
    
    Raises:
        ConnectionError: If connection fails
        ssl.SSLError: If TLS handshake fails
        ValueError: If certificate pinning validation fails
    
    Requirements: 9.3, 9.4, 10.1, 10.2, 14.7
    """
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        # Create SSL context for client
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        
        # Set minimum TLS version to 1.3 (or 1.2 if 1.3 not available)
        try:
            context.minimum_version = ssl.TLSVersion.TLSv1_3
        except AttributeError:
            # Fallback to TLS 1.2 if 1.3 not available
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Configure certificate verification
        if verify_cert:
            # For production: verify against system CA certificates
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_default_certs()
        else:
            # For development: allow self-signed certificates
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        
        # Set secure cipher suites
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        # Connect to server
        sock.connect((server_ip, server_port))
        
        # Wrap socket with TLS
        tls_socket = context.wrap_socket(sock, server_hostname=server_ip if verify_cert else None)
        
        # Perform certificate pinning validation if fingerprint provided
        if expected_fingerprint:
            if not validate_certificate_pinning(tls_socket, expected_fingerprint):
                tls_socket.close()
                raise ValueError("Certificate pinning validation failed: fingerprint mismatch")
        
        return tls_socket
    
    except Exception as e:
        sock.close()
        raise e


def get_server_certificate_fingerprint(
    server_ip: str,
    server_port: int,
    timeout: int = 10
) -> str:
    """
    Get server certificate fingerprint without validation
    
    This is useful for initial setup to retrieve the server's certificate
    fingerprint for pinning configuration.
    
    Args:
        server_ip: Server IP address or hostname
        server_port: Server port number
        timeout: Connection timeout in seconds
    
    Returns:
        Hex-encoded SHA256 fingerprint of server certificate
    
    Raises:
        ConnectionError: If connection fails
        ssl.SSLError: If TLS handshake fails
    
    Requirements: 9.3
    """
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        # Create SSL context without verification
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Connect to server
        sock.connect((server_ip, server_port))
        
        # Wrap socket with TLS
        tls_socket = context.wrap_socket(sock)
        
        # Get certificate in DER format
        cert_der = tls_socket.getpeercert(binary_form=True)
        
        if not cert_der:
            raise ValueError("Could not retrieve server certificate")
        
        # Calculate SHA256 fingerprint
        fingerprint = hashlib.sha256(cert_der).hexdigest()
        
        tls_socket.close()
        
        return fingerprint
    
    except Exception as e:
        sock.close()
        raise e


class TLSAgentWrapper:
    """
    TLS Agent Wrapper for managing TLS client connections
    
    Provides high-level interface for TLS client operations including
    certificate pinning and secure connection establishment.
    """
    
    def __init__(
        self,
        server_ip: str,
        server_port: int,
        expected_fingerprint: Optional[str] = None,
        verify_cert: bool = False,
        timeout: int = 30
    ):
        """
        Initialize TLS agent wrapper
        
        Args:
            server_ip: Server IP address or hostname
            server_port: Server port number
            expected_fingerprint: Expected certificate fingerprint for pinning
            verify_cert: Whether to verify server certificate against CA
            timeout: Connection timeout in seconds
        """
        self.server_ip = server_ip
        self.server_port = server_port
        self.expected_fingerprint = expected_fingerprint
        self.verify_cert = verify_cert
        self.timeout = timeout
        self.connection: Optional[ssl.SSLSocket] = None
    
    def connect(self) -> ssl.SSLSocket:
        """
        Connect to server with TLS
        
        Returns:
            TLS-wrapped socket connected to server
        
        Raises:
            ConnectionError: If connection fails
            ValueError: If certificate pinning validation fails
        
        Requirements: 9.3, 9.4, 10.1, 10.2
        """
        self.connection = connect_with_tls(
            server_ip=self.server_ip,
            server_port=self.server_port,
            expected_fingerprint=self.expected_fingerprint,
            verify_cert=self.verify_cert,
            timeout=self.timeout
        )
        return self.connection
    
    def disconnect(self) -> None:
        """
        Disconnect from server
        """
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            finally:
                self.connection = None
    
    def is_connected(self) -> bool:
        """
        Check if connected to server
        
        Returns:
            True if connected, False otherwise
        """
        return self.connection is not None
    
    def send(self, data: bytes) -> int:
        """
        Send data over TLS connection
        
        Args:
            data: Data to send
        
        Returns:
            Number of bytes sent
        
        Raises:
            ConnectionError: If not connected
        
        Requirements: 10.2
        """
        if not self.connection:
            raise ConnectionError("Not connected to server")
        
        return self.connection.send(data)
    
    def recv(self, buffer_size: int = 4096) -> bytes:
        """
        Receive data over TLS connection
        
        Args:
            buffer_size: Maximum number of bytes to receive
        
        Returns:
            Received data
        
        Raises:
            ConnectionError: If not connected
        
        Requirements: 10.2
        """
        if not self.connection:
            raise ConnectionError("Not connected to server")
        
        return self.connection.recv(buffer_size)
    
    def get_server_fingerprint(self) -> str:
        """
        Get server certificate fingerprint
        
        Returns:
            Hex-encoded SHA256 fingerprint
        
        Requirements: 9.3
        """
        return get_server_certificate_fingerprint(
            server_ip=self.server_ip,
            server_port=self.server_port,
            timeout=self.timeout
        )
    
    def validate_pinning(self) -> bool:
        """
        Validate certificate pinning for current connection
        
        Returns:
            True if pinning is valid, False otherwise
        
        Requirements: 9.3, 9.4
        """
        if not self.connection or not self.expected_fingerprint:
            return False
        
        return validate_certificate_pinning(self.connection, self.expected_fingerprint)
