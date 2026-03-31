"""
Authentication Module for Remote System Enhancement

This module provides JWT-based authentication for agent connections.
Handles token generation, validation, revocation, and refresh operations.

Requirements: 10.3, 10.4, 10.5, 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Set
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import time


class TokenValidation:
    """
    Result of token validation
    
    Attributes:
        valid: Whether the token is valid
        agent_id: Agent ID extracted from token (if valid)
        expires_at: Token expiration time (if valid)
        error: Error message (if invalid)
    """
    
    def __init__(self, valid: bool, agent_id: Optional[str] = None,
                 expires_at: Optional[datetime] = None, error: Optional[str] = None):
        self.valid = valid
        self.agent_id = agent_id
        self.expires_at = expires_at
        self.error = error


class AuthenticationModule:
    """
    Authentication Module for JWT-based agent authentication
    
    Provides token generation, validation, revocation, and refresh
    capabilities for secure agent-server communication.
    """
    
    def __init__(self, secret_key: str, token_expiry: int = 86400):
        """
        Initialize authentication module
        
        Args:
            secret_key: Secret key for JWT signing and verification
            token_expiry: Token expiration time in seconds (default: 86400 = 24 hours)
        
        Requirements: 10.4, 18.1
        """
        if not secret_key:
            raise ValueError("Secret key cannot be empty")
        
        if token_expiry <= 0:
            raise ValueError("Token expiry must be positive")
        
        self.secret_key = secret_key
        self.token_expiry = token_expiry
        self.revoked_tokens: Set[str] = set()  # Store revoked token JTIs
        self.algorithm = "HS256"  # HMAC with SHA-256
    
    def generate_token(self, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate JWT token for agent authentication
        
        Args:
            agent_id: Unique agent identifier
            metadata: Optional metadata to include in token payload
        
        Returns:
            JWT token string
        
        Requirements: 10.3, 18.2, 18.7
        """
        if not agent_id:
            raise ValueError("Agent ID cannot be empty")
        
        # Calculate expiration time using timezone-aware datetime
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.token_expiry)
        
        # Build JWT payload with high-precision timestamp for unique JTI
        payload = {
            'agent_id': agent_id,
            'iat': now,  # Issued at
            'exp': expires_at,  # Expiration time
            'jti': f"{agent_id}_{time.time_ns()}"  # JWT ID for revocation (nanosecond precision)
        }
        
        # Add metadata if provided
        if metadata:
            payload['metadata'] = metadata
        
        # Encode JWT token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return token
    
    def validate_token(self, token: str) -> TokenValidation:
        """
        Validate JWT token with signature verification and expiration check
        
        Args:
            token: JWT token string to validate
        
        Returns:
            TokenValidation object with validation result
        
        Requirements: 10.5, 18.3, 18.4, 18.5
        """
        if not token:
            return TokenValidation(valid=False, error="Token is empty")
        
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'require': ['agent_id', 'exp', 'jti']
                }
            )
            
            # Check if token is revoked
            jti = payload.get('jti')
            if jti in self.revoked_tokens:
                return TokenValidation(valid=False, error="Token has been revoked")
            
            # Extract agent_id and expiration
            agent_id = payload.get('agent_id')
            exp_timestamp = payload.get('exp')
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) if exp_timestamp else None
            
            return TokenValidation(
                valid=True,
                agent_id=agent_id,
                expires_at=expires_at,
                error=None
            )
        
        except ExpiredSignatureError:
            return TokenValidation(valid=False, error="Token has expired")
        
        except InvalidTokenError as e:
            return TokenValidation(valid=False, error=f"Invalid token: {str(e)}")
        
        except Exception as e:
            return TokenValidation(valid=False, error=f"Token validation error: {str(e)}")
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token to prevent further use
        
        Args:
            token: JWT token string to revoke
        
        Returns:
            True if token was successfully revoked, False otherwise
        
        Requirements: 18.6
        """
        if not token:
            return False
        
        try:
            # Decode token without verification to get JTI
            # We need to extract JTI even if token is expired
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    'verify_signature': True,
                    'verify_exp': False  # Don't verify expiration for revocation
                }
            )
            
            jti = payload.get('jti')
            if jti:
                self.revoked_tokens.add(jti)
                return True
            
            return False
        
        except Exception:
            # If we can't decode the token, we can't revoke it
            return False
    
    def refresh_token(self, old_token: str) -> str:
        """
        Refresh an existing token by generating a new one
        
        Args:
            old_token: Existing JWT token to refresh
        
        Returns:
            New JWT token string
        
        Raises:
            ValueError: If old token is invalid or expired
        
        Requirements: 18.2
        """
        if not old_token:
            raise ValueError("Old token cannot be empty")
        
        # Validate the old token
        validation = self.validate_token(old_token)
        
        if not validation.valid:
            raise ValueError(f"Cannot refresh invalid token: {validation.error}")
        
        # Extract metadata from old token
        try:
            old_payload = jwt.decode(
                old_token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_exp': False}
            )
            metadata = old_payload.get('metadata')
        except Exception:
            metadata = None
        
        # Revoke the old token
        self.revoke_token(old_token)
        
        # Generate new token with same agent_id
        new_token = self.generate_token(validation.agent_id, metadata)
        
        return new_token
    
    def clear_revoked_tokens(self) -> None:
        """
        Clear the revoked tokens list
        
        This should be called periodically to prevent memory growth,
        especially for expired tokens that no longer need to be tracked.
        """
        self.revoked_tokens.clear()
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get information from a token without full validation
        
        Args:
            token: JWT token string
        
        Returns:
            Dictionary with token information or None if token is invalid
        """
        if not token:
            return None
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_exp': False}
            )
            
            # Convert timestamps to timezone-aware datetimes
            issued_at = None
            if payload.get('iat'):
                issued_at = datetime.fromtimestamp(payload.get('iat'), tz=timezone.utc)
            
            expires_at = None
            if payload.get('exp'):
                expires_at = datetime.fromtimestamp(payload.get('exp'), tz=timezone.utc)
            
            return {
                'agent_id': payload.get('agent_id'),
                'issued_at': issued_at,
                'expires_at': expires_at,
                'jti': payload.get('jti'),
                'metadata': payload.get('metadata'),
                'is_revoked': payload.get('jti') in self.revoked_tokens
            }
        
        except Exception:
            return None
