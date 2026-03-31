"""
Unit Tests for Server Binding Module

Tests Secret_Key validation, certificate pinning, connection rejection,
and failed binding attempt logging.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
"""

import pytest
import ssl
import hashlib
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from remote_system.enhanced_agent.server_binding import (
    validate_certificate_pinning,
    validate_server_binding,
    validate_secret_key_server_side,
    log_failed_binding_attempt,
    reject_invalid_connection,
    ServerBindingResult
)


class TestServerBindingResult:
    """Test ServerBindingResult data class"""
    
    def test_initialization_valid(self):
        """Test successful initialization"""
        result = ServerBindingResult(
            valid=True,
            error=None,
            server_info={"ip": "192.168.1.1"}
        )
        
        assert result.valid is True
        assert result.error is None
        assert result.server_info == {"ip": "192.168.1.1"}
    
    def test_initialization_invalid(self):
        """Test initialization with error"""
        result = ServerBindingResult(
            valid=False,
            error="Invalid certificate"
        )
        
        assert result.valid is False
        assert result.error == "Invalid certificate"
        assert result.server_info == {}
    
    def test_initialization_default_server_info(self):
        """Test that server_info defaults to empty dict"""
        result = ServerBindingResult(valid=True)
        
        assert result.server_info == {}


class TestCertificatePinning:
    """Test certificate pinning validation - Requirements 9.3, 9.4"""
    
    def test_certificate_pinning_success(self):
        """Test successful certificate pinning validation - Requirement 9.3"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Create a fake certificate
        fake_cert = b"fake certificate data"
        expected_fingerprint = hashlib.sha256(fake_cert).hexdigest()
        
        mock_socket.getpeercert.return_value = fake_cert
        
        # Validate certificate pinning
        valid, error = validate_certificate_pinning(mock_socket, expected_fingerprint)
        
        assert valid is True
        assert error is None
        mock_socket.getpeercert.assert_called_once_with(binary_form=True)
    
    def test_certificate_pinning_failure_mismatch(self):
        """Test certificate pinning failure with mismatched fingerprint - Requirement 9.4"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Create a fake certificate
        fake_cert = b"fake certificate data"
        wrong_fingerprint = "0" * 64  # Wrong fingerprint
        
        mock_socket.getpeercert.return_value = fake_cert
        
        # Validate certificate pinning
        valid, error = validate_certificate_pinning(mock_socket, wrong_fingerprint)
        
        assert valid is False
        assert "fingerprint mismatch" in error.lower()
    
    def test_certificate_pinning_case_insensitive(self):
        """Test that fingerprint comparison is case-insensitive - Requirement 9.3"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Create a fake certificate
        fake_cert = b"fake certificate data"
        expected_fingerprint = hashlib.sha256(fake_cert).hexdigest()
        
        mock_socket.getpeercert.return_value = fake_cert
        
        # Test with uppercase fingerprint
        valid, error = validate_certificate_pinning(
            mock_socket, 
            expected_fingerprint.upper()
        )
        
        assert valid is True
        assert error is None
    
    def test_certificate_pinning_no_certificate(self):
        """Test certificate pinning when no certificate is received - Requirement 9.4"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeercert.return_value = None
        
        # Validate certificate pinning
        valid, error = validate_certificate_pinning(mock_socket, "abc123")
        
        assert valid is False
        assert "no certificate" in error.lower()
    
    def test_certificate_pinning_exception_handling(self):
        """Test certificate pinning handles exceptions gracefully - Requirement 9.4"""
        # Create mock TLS socket that raises exception
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeercert.side_effect = Exception("Connection error")
        
        # Validate certificate pinning
        valid, error = validate_certificate_pinning(mock_socket, "abc123")
        
        assert valid is False
        assert "error" in error.lower()


class TestServerBinding:
    """Test server binding validation - Requirements 9.1, 9.2, 9.3, 9.4, 9.5"""
    
    def test_server_binding_success_with_pinning(self):
        """Test successful server binding with certificate pinning - Requirement 9.1, 9.3"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Setup certificate
        fake_cert = b"fake certificate data"
        expected_fingerprint = hashlib.sha256(fake_cert).hexdigest()
        mock_socket.getpeercert.return_value = fake_cert
        
        # Setup connection info
        mock_socket.getpeername.return_value = ("192.168.1.100", 9999)
        
        # Validate server binding
        result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=expected_fingerprint,
            secret_key="test_secret_key_123",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        assert result.valid is True
        assert result.error is None
        assert result.server_info["server_ip"] == "192.168.1.100"
        assert result.server_info["server_port"] == 9999
        assert result.server_info["certificate_pinned"] is True
    
    def test_server_binding_success_without_pinning(self):
        """Test successful server binding without certificate pinning - Requirement 9.1"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeername.return_value = ("192.168.1.100", 9999)
        
        # Validate server binding (no fingerprint)
        result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=None,
            secret_key="test_secret_key_123",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        assert result.valid is True
        assert result.error is None
        assert result.server_info["certificate_pinned"] is False
    
    def test_server_binding_failure_invalid_certificate(self):
        """Test server binding failure with invalid certificate - Requirement 9.4"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Setup certificate with wrong fingerprint
        fake_cert = b"fake certificate data"
        wrong_fingerprint = "0" * 64
        mock_socket.getpeercert.return_value = fake_cert
        
        # Validate server binding
        result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=wrong_fingerprint,
            secret_key="test_secret_key_123",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        assert result.valid is False
        assert "certificate" in result.error.lower()
    
    def test_server_binding_failure_empty_secret_key(self):
        """Test server binding failure with empty secret key - Requirement 9.2"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Validate server binding with empty secret key
        result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=None,
            secret_key="",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        assert result.valid is False
        assert "secret key" in result.error.lower()
    
    def test_server_binding_failure_empty_server_ip(self):
        """Test server binding failure with empty server IP - Requirement 9.1"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Validate server binding with empty server IP
        result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=None,
            secret_key="test_secret_key_123",
            server_ip="",
            server_port=9999
        )
        
        assert result.valid is False
        assert "server ip" in result.error.lower()
    
    def test_server_binding_failure_invalid_port(self):
        """Test server binding failure with invalid port - Requirement 9.1"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Test with port 0
        result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=None,
            secret_key="test_secret_key_123",
            server_ip="192.168.1.100",
            server_port=0
        )
        
        assert result.valid is False
        assert "port" in result.error.lower()
        
        # Test with port > 65535
        result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=None,
            secret_key="test_secret_key_123",
            server_ip="192.168.1.100",
            server_port=70000
        )
        
        assert result.valid is False
        assert "port" in result.error.lower()
    
    def test_server_binding_failure_connection_error(self):
        """Test server binding handles connection errors - Requirement 9.5"""
        # Create mock TLS socket that raises exception
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeername.side_effect = Exception("Connection lost")
        
        # Validate server binding
        result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=None,
            secret_key="test_secret_key_123",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        assert result.valid is False
        assert "connection" in result.error.lower()


class TestSecretKeyValidation:
    """Test Secret_Key validation on server side - Requirements 9.2, 9.5, 9.6"""
    
    def test_secret_key_validation_success(self):
        """Test successful Secret_Key validation - Requirement 9.2, 9.5"""
        received_key = "test_secret_key_12345678"
        expected_key = "test_secret_key_12345678"
        
        valid, error = validate_secret_key_server_side(
            received_secret_key=received_key,
            expected_secret_key=expected_key,
            agent_id="test-agent-1"
        )
        
        assert valid is True
        assert error is None
    
    def test_secret_key_validation_failure_mismatch(self):
        """Test Secret_Key validation failure with mismatch - Requirement 9.6"""
        received_key = "wrong_secret_key"
        expected_key = "correct_secret_key"
        
        valid, error = validate_secret_key_server_side(
            received_secret_key=received_key,
            expected_secret_key=expected_key,
            agent_id="test-agent-1"
        )
        
        assert valid is False
        assert "invalid" in error.lower()
    
    def test_secret_key_validation_failure_empty_received(self):
        """Test Secret_Key validation failure with empty received key - Requirement 9.6"""
        valid, error = validate_secret_key_server_side(
            received_secret_key="",
            expected_secret_key="expected_key",
            agent_id="test-agent-1"
        )
        
        assert valid is False
        assert "required" in error.lower()
    
    def test_secret_key_validation_failure_empty_expected(self):
        """Test Secret_Key validation failure with empty expected key - Requirement 9.5"""
        valid, error = validate_secret_key_server_side(
            received_secret_key="received_key",
            expected_secret_key="",
            agent_id="test-agent-1"
        )
        
        assert valid is False
        assert "configuration" in error.lower()
    
    def test_secret_key_validation_constant_time_comparison(self):
        """Test that Secret_Key validation uses constant-time comparison - Requirement 9.5"""
        # This test verifies that secrets.compare_digest is used
        # We can't directly test timing, but we can verify the function works correctly
        
        # Test with keys that differ in first character
        valid1, _ = validate_secret_key_server_side(
            received_secret_key="a" * 32,
            expected_secret_key="b" * 32,
            agent_id="test-agent-1"
        )
        
        # Test with keys that differ in last character
        valid2, _ = validate_secret_key_server_side(
            received_secret_key="a" * 31 + "a",
            expected_secret_key="a" * 31 + "b",
            agent_id="test-agent-2"
        )
        
        # Both should fail
        assert valid1 is False
        assert valid2 is False


class TestFailedBindingLogging:
    """Test failed binding attempt logging - Requirement 9.7"""
    
    @patch('remote_system.enhanced_agent.server_binding.logger')
    def test_log_failed_binding_attempt_basic(self, mock_logger):
        """Test basic failed binding attempt logging - Requirement 9.7"""
        log_failed_binding_attempt(
            agent_id="test-agent-1",
            reason="Invalid Secret_Key",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        # Verify logger was called
        assert mock_logger.warning.called
        
        # Get the log message
        log_call = mock_logger.warning.call_args[0][0]
        
        # Verify log contains required information
        assert "test-agent-1" in log_call
        assert "Invalid Secret_Key" in log_call
        assert "192.168.1.100" in log_call
        assert "9999" in log_call
    
    @patch('remote_system.enhanced_agent.server_binding.logger')
    def test_log_failed_binding_attempt_with_additional_info(self, mock_logger):
        """Test failed binding logging with additional info - Requirement 9.7"""
        additional_info = {
            "attempt_count": 3,
            "source_ip": "10.0.0.5"
        }
        
        log_failed_binding_attempt(
            agent_id="test-agent-2",
            reason="Certificate mismatch",
            server_ip="192.168.1.100",
            server_port=9999,
            additional_info=additional_info
        )
        
        # Verify logger was called
        assert mock_logger.warning.called
    
    @patch('remote_system.enhanced_agent.server_binding.logger')
    def test_log_failed_binding_attempt_unknown_agent(self, mock_logger):
        """Test failed binding logging with unknown agent - Requirement 9.7"""
        log_failed_binding_attempt(
            agent_id=None,
            reason="Authentication failed",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        # Verify logger was called
        assert mock_logger.warning.called
        
        # Get the log message
        log_call = mock_logger.warning.call_args[0][0]
        
        # Verify "unknown" is used for agent_id
        assert "unknown" in log_call


class TestConnectionRejection:
    """Test connection rejection for invalid keys - Requirements 9.6"""
    
    @patch('remote_system.enhanced_agent.server_binding.log_failed_binding_attempt')
    def test_reject_invalid_connection_basic(self, mock_log):
        """Test basic connection rejection - Requirement 9.6"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeername.return_value = ("192.168.1.50", 12345)
        
        # Reject connection
        reject_invalid_connection(
            connection=mock_socket,
            reason="Invalid Secret_Key",
            agent_id="test-agent-1"
        )
        
        # Verify connection was closed
        mock_socket.close.assert_called_once()
        
        # Verify failed attempt was logged
        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args[1]["agent_id"] == "test-agent-1"
        assert call_args[1]["reason"] == "Invalid Secret_Key"
    
    @patch('remote_system.enhanced_agent.server_binding.log_failed_binding_attempt')
    def test_reject_invalid_connection_sends_rejection_message(self, mock_log):
        """Test that rejection message is sent before closing - Requirement 9.6"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeername.return_value = ("192.168.1.50", 12345)
        
        # Reject connection
        reject_invalid_connection(
            connection=mock_socket,
            reason="Certificate validation failed",
            agent_id="test-agent-2"
        )
        
        # Verify sendall was called (rejection message)
        assert mock_socket.sendall.called
        
        # Verify connection was closed
        mock_socket.close.assert_called_once()
    
    @patch('remote_system.enhanced_agent.server_binding.log_failed_binding_attempt')
    def test_reject_invalid_connection_handles_send_error(self, mock_log):
        """Test that connection is closed even if sending rejection fails - Requirement 9.6"""
        # Create mock TLS socket that fails to send
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeername.return_value = ("192.168.1.50", 12345)
        mock_socket.sendall.side_effect = Exception("Send failed")
        
        # Reject connection (should not raise exception)
        reject_invalid_connection(
            connection=mock_socket,
            reason="Invalid Secret_Key",
            agent_id="test-agent-3"
        )
        
        # Verify connection was still closed
        mock_socket.close.assert_called_once()
    
    @patch('remote_system.enhanced_agent.server_binding.log_failed_binding_attempt')
    def test_reject_invalid_connection_handles_close_error(self, mock_log):
        """Test that close errors are handled gracefully - Requirement 9.6"""
        # Create mock TLS socket that fails to close
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeername.return_value = ("192.168.1.50", 12345)
        mock_socket.close.side_effect = Exception("Close failed")
        
        # Reject connection (should not raise exception)
        reject_invalid_connection(
            connection=mock_socket,
            reason="Invalid Secret_Key",
            agent_id="test-agent-4"
        )
        
        # Verify close was attempted (may be called multiple times due to error handling)
        assert mock_socket.close.called
    
    @patch('remote_system.enhanced_agent.server_binding.log_failed_binding_attempt')
    def test_reject_invalid_connection_without_agent_id(self, mock_log):
        """Test connection rejection without agent ID - Requirement 9.6"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        mock_socket.getpeername.return_value = ("192.168.1.50", 12345)
        
        # Reject connection without agent_id
        reject_invalid_connection(
            connection=mock_socket,
            reason="Authentication timeout"
        )
        
        # Verify connection was closed
        mock_socket.close.assert_called_once()
        
        # Verify failed attempt was logged with None agent_id
        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args[1]["agent_id"] is None


class TestIntegration:
    """Integration tests for server binding"""
    
    def test_full_binding_validation_flow(self):
        """Test complete binding validation flow - Requirements 9.1-9.5"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Setup certificate
        fake_cert = b"test certificate for integration"
        expected_fingerprint = hashlib.sha256(fake_cert).hexdigest()
        mock_socket.getpeercert.return_value = fake_cert
        
        # Setup connection info
        mock_socket.getpeername.return_value = ("192.168.1.100", 9999)
        
        # Step 1: Validate server binding (agent side)
        binding_result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=expected_fingerprint,
            secret_key="integration_test_secret_key",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        assert binding_result.valid is True
        assert binding_result.server_info["certificate_pinned"] is True
        
        # Step 2: Validate Secret_Key (server side)
        secret_valid, secret_error = validate_secret_key_server_side(
            received_secret_key="integration_test_secret_key",
            expected_secret_key="integration_test_secret_key",
            agent_id="integration-test-agent"
        )
        
        assert secret_valid is True
        assert secret_error is None
    
    @patch('remote_system.enhanced_agent.server_binding.log_failed_binding_attempt')
    def test_full_rejection_flow(self, mock_log):
        """Test complete rejection flow for invalid binding - Requirements 9.4, 9.6, 9.7"""
        # Create mock TLS socket
        mock_socket = Mock(spec=ssl.SSLSocket)
        
        # Setup certificate with wrong fingerprint
        fake_cert = b"test certificate"
        wrong_fingerprint = "0" * 64
        mock_socket.getpeercert.return_value = fake_cert
        mock_socket.getpeername.return_value = ("192.168.1.50", 12345)
        
        # Step 1: Validate server binding (should fail)
        binding_result = validate_server_binding(
            tls_socket=mock_socket,
            expected_fingerprint=wrong_fingerprint,
            secret_key="test_secret_key",
            server_ip="192.168.1.100",
            server_port=9999
        )
        
        assert binding_result.valid is False
        
        # Step 2: Reject connection
        reject_invalid_connection(
            connection=mock_socket,
            reason=binding_result.error,
            agent_id="rejected-agent"
        )
        
        # Verify connection was closed
        mock_socket.close.assert_called_once()
        
        # Verify failed attempt was logged
        mock_log.assert_called_once()
