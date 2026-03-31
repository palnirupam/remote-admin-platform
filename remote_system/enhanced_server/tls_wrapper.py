"""
TLS Wrapper Module for Enhanced Server

This module provides TLS encryption for server-side socket connections.
Handles TLS socket wrapping, certificate generation, and secure communication.

Requirements: 10.1, 10.2, 14.7
"""

import ssl
import socket
import os
import ipaddress
from typing import Tuple, Optional
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate_self_signed_certificate(
    cert_path: str = "server.crt",
    key_path: str = "server.key",
    common_name: str = "localhost",
    validity_days: int = 365
) -> Tuple[str, str]:
    """
    Generate self-signed TLS certificate for development
    
    Args:
        cert_path: Path to save certificate file
        key_path: Path to save private key file
        common_name: Common name for certificate (hostname/IP)
        validity_days: Certificate validity period in days
    
    Returns:
        Tuple of (cert_path, key_path)
    
    Requirements: 10.1
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Create certificate subject and issuer (same for self-signed)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Remote System"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    # Build certificate
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=validity_days))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(common_name),
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    
    # Write private key to file
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )
    
    # Write certificate to file
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    return cert_path, key_path


def wrapSocketWithTLS(
    sock: socket.socket,
    cert_path: str = "server.crt",
    key_path: str = "server.key",
    require_client_cert: bool = False
) -> ssl.SSLSocket:
    """
    Wrap a server socket with TLS encryption
    
    Args:
        sock: Socket to wrap with TLS
        cert_path: Path to server certificate file
        key_path: Path to server private key file
        require_client_cert: Whether to require client certificate authentication
    
    Returns:
        TLS-wrapped SSLSocket
    
    Raises:
        FileNotFoundError: If certificate or key files don't exist
        ssl.SSLError: If TLS handshake fails
    
    Requirements: 10.1, 10.2, 14.7
    """
    # Verify certificate and key files exist
    if not os.path.exists(cert_path):
        raise FileNotFoundError(f"Certificate file not found: {cert_path}")
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Key file not found: {key_path}")
    
    # Create SSL context with TLS 1.3 or higher
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Set minimum TLS version to 1.3 (or 1.2 if 1.3 not available)
    try:
        context.minimum_version = ssl.TLSVersion.TLSv1_3
    except AttributeError:
        # Fallback to TLS 1.2 if 1.3 not available
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Load server certificate and private key
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    
    # Configure client certificate requirements
    if require_client_cert:
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context.verify_mode = ssl.CERT_NONE
    
    # Set secure cipher suites (prefer strong ciphers)
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
    
    # Wrap socket with TLS
    tls_socket = context.wrap_socket(sock, server_side=True)
    
    return tls_socket


def get_certificate_fingerprint(cert_path: str) -> str:
    """
    Get SHA256 fingerprint of certificate for pinning
    
    Args:
        cert_path: Path to certificate file
    
    Returns:
        Hex-encoded SHA256 fingerprint
    
    Requirements: 9.3
    """
    with open(cert_path, "rb") as f:
        cert_data = f.read()
    
    # Parse certificate
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    
    # Calculate SHA256 fingerprint
    fingerprint = cert.fingerprint(hashes.SHA256())
    
    return fingerprint.hex()


class TLSServerWrapper:
    """
    TLS Server Wrapper for managing TLS connections
    
    Provides high-level interface for TLS server operations including
    certificate management and secure socket wrapping.
    """
    
    def __init__(
        self,
        cert_path: str = "server.crt",
        key_path: str = "server.key",
        auto_generate: bool = True,
        common_name: str = "localhost"
    ):
        """
        Initialize TLS server wrapper
        
        Args:
            cert_path: Path to server certificate
            key_path: Path to server private key
            auto_generate: Automatically generate certificate if not found
            common_name: Common name for auto-generated certificate
        """
        self.cert_path = cert_path
        self.key_path = key_path
        self.common_name = common_name
        
        # Generate certificate if needed
        if auto_generate and (not os.path.exists(cert_path) or not os.path.exists(key_path)):
            self.generate_certificate()
    
    def generate_certificate(self, validity_days: int = 365) -> Tuple[str, str]:
        """
        Generate self-signed certificate
        
        Args:
            validity_days: Certificate validity period in days
        
        Returns:
            Tuple of (cert_path, key_path)
        """
        return generate_self_signed_certificate(
            cert_path=self.cert_path,
            key_path=self.key_path,
            common_name=self.common_name,
            validity_days=validity_days
        )
    
    def wrap_socket(self, sock: socket.socket, require_client_cert: bool = False) -> ssl.SSLSocket:
        """
        Wrap socket with TLS
        
        Args:
            sock: Socket to wrap
            require_client_cert: Whether to require client certificate
        
        Returns:
            TLS-wrapped socket
        """
        return wrapSocketWithTLS(
            sock=sock,
            cert_path=self.cert_path,
            key_path=self.key_path,
            require_client_cert=require_client_cert
        )
    
    def get_fingerprint(self) -> str:
        """
        Get certificate fingerprint for pinning
        
        Returns:
            Hex-encoded SHA256 fingerprint
        """
        return get_certificate_fingerprint(self.cert_path)
    
    def certificate_exists(self) -> bool:
        """
        Check if certificate and key files exist
        
        Returns:
            True if both files exist, False otherwise
        """
        return os.path.exists(self.cert_path) and os.path.exists(self.key_path)
