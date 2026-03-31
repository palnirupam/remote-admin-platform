"""
Unit tests for AuthenticationModule

Tests token generation, validation, revocation, and refresh operations.

Requirements: 10.3, 10.4, 10.5, 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7
"""

import pytest
import time
import string
from datetime import datetime, timedelta, timezone
from hypothesis import given, strategies as st, settings, assume
from remote_system.enhanced_server.auth_module import (
    AuthenticationModule,
    TokenValidation
)


@pytest.fixture
def auth_module():
    """Create an AuthenticationModule instance for testing"""
    return AuthenticationModule(secret_key="test_secret_key_12345", token_expiry=3600)


@pytest.fixture
def short_expiry_auth():
    """Create an AuthenticationModule with short expiry for testing"""
    return AuthenticationModule(secret_key="test_secret_key_12345", token_expiry=1)


class TestAuthenticationModuleInitialization:
    """Test authentication module initialization"""
    
    def test_initialization_with_valid_params(self):
        """Test successful initialization with valid parameters"""
        auth = AuthenticationModule(secret_key="my_secret", token_expiry=86400)
        assert auth.secret_key == "my_secret"
        assert auth.token_expiry == 86400
        assert auth.algorithm == "HS256"
        assert len(auth.revoked_tokens) == 0
    
    def test_initialization_with_empty_secret_key(self):
        """Test that empty secret key raises ValueError"""
        with pytest.raises(ValueError, match="Secret key cannot be empty"):
            AuthenticationModule(secret_key="", token_expiry=3600)
    
    def test_initialization_with_negative_expiry(self):
        """Test that negative expiry raises ValueError"""
        with pytest.raises(ValueError, match="Token expiry must be positive"):
            AuthenticationModule(secret_key="test_key", token_expiry=-100)
    
    def test_initialization_with_zero_expiry(self):
        """Test that zero expiry raises ValueError"""
        with pytest.raises(ValueError, match="Token expiry must be positive"):
            AuthenticationModule(secret_key="test_key", token_expiry=0)
    
    def test_default_token_expiry(self):
        """Test default token expiry is 24 hours (86400 seconds)"""
        auth = AuthenticationModule(secret_key="test_key")
        assert auth.token_expiry == 86400


class TestTokenGeneration:
    """Test token generation functionality"""
    
    def test_generate_token_basic(self, auth_module):
        """Test basic token generation - Requirement 10.3, 18.2"""
        agent_id = "test-agent-001"
        token = auth_module.generate_token(agent_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_generate_token_with_metadata(self, auth_module):
        """Test token generation with metadata - Requirement 18.7"""
        agent_id = "test-agent-002"
        metadata = {
            'hostname': 'test-host',
            'os_type': 'Windows',
            'version': '1.0.0'
        }
        
        token = auth_module.generate_token(agent_id, metadata)
        
        assert token is not None
        # Verify metadata is included by getting token info
        info = auth_module.get_token_info(token)
        assert info is not None
        assert info['metadata'] == metadata
    
    def test_generate_token_with_empty_agent_id(self, auth_module):
        """Test that empty agent_id raises ValueError"""
        with pytest.raises(ValueError, match="Agent ID cannot be empty"):
            auth_module.generate_token("")
    
    def test_generate_token_unique_jti(self, auth_module):
        """Test that each token has a unique JTI"""
        agent_id = "test-agent-003"
        
        token1 = auth_module.generate_token(agent_id)
        time.sleep(0.01)  # Small delay to ensure different timestamp
        token2 = auth_module.generate_token(agent_id)
        
        info1 = auth_module.get_token_info(token1)
        info2 = auth_module.get_token_info(token2)
        
        assert info1['jti'] != info2['jti']
    
    def test_generate_token_contains_required_claims(self, auth_module):
        """Test that generated token contains all required claims"""
        agent_id = "test-agent-004"
        token = auth_module.generate_token(agent_id)
        
        info = auth_module.get_token_info(token)
        
        assert info is not None
        assert info['agent_id'] == agent_id
        assert info['issued_at'] is not None
        assert info['expires_at'] is not None
        assert info['jti'] is not None


class TestTokenValidation:
    """Test token validation functionality"""
    
    def test_validate_valid_token(self, auth_module):
        """Test validation of valid token - Requirement 18.3, 18.4"""
        agent_id = "test-agent-005"
        token = auth_module.generate_token(agent_id)
        
        validation = auth_module.validate_token(token)
        
        assert validation.valid is True
        assert validation.agent_id == agent_id
        assert validation.expires_at is not None
        assert validation.error is None
    
    def test_validate_empty_token(self, auth_module):
        """Test validation of empty token"""
        validation = auth_module.validate_token("")
        
        assert validation.valid is False
        assert validation.error == "Token is empty"
    
    def test_validate_expired_token(self, short_expiry_auth):
        """Test validation of expired token - Requirement 10.5, 18.4"""
        agent_id = "test-agent-006"
        token = short_expiry_auth.generate_token(agent_id)
        
        # Wait for token to expire
        time.sleep(2)
        
        validation = short_expiry_auth.validate_token(token)
        
        assert validation.valid is False
        assert "expired" in validation.error.lower()
    
    def test_validate_token_with_wrong_secret(self, auth_module):
        """Test validation fails with wrong secret key"""
        agent_id = "test-agent-007"
        token = auth_module.generate_token(agent_id)
        
        # Create new auth module with different secret
        wrong_auth = AuthenticationModule(secret_key="wrong_secret", token_expiry=3600)
        validation = wrong_auth.validate_token(token)
        
        assert validation.valid is False
        assert "Invalid token" in validation.error
    
    def test_validate_malformed_token(self, auth_module):
        """Test validation of malformed token"""
        malformed_token = "this.is.not.a.valid.jwt.token"
        
        validation = auth_module.validate_token(malformed_token)
        
        assert validation.valid is False
        assert validation.error is not None
    
    def test_validate_revoked_token(self, auth_module):
        """Test validation of revoked token - Requirement 18.6"""
        agent_id = "test-agent-008"
        token = auth_module.generate_token(agent_id)
        
        # Revoke the token
        auth_module.revoke_token(token)
        
        # Try to validate
        validation = auth_module.validate_token(token)
        
        assert validation.valid is False
        assert "revoked" in validation.error.lower()
    
    def test_validate_token_signature_verification(self, auth_module):
        """Test that signature verification is enforced - Requirement 18.3"""
        agent_id = "test-agent-009"
        token = auth_module.generate_token(agent_id)
        
        # Tamper with token by modifying a character
        tampered_token = token[:-5] + "XXXXX"
        
        validation = auth_module.validate_token(tampered_token)
        
        assert validation.valid is False


class TestTokenRevocation:
    """Test token revocation functionality"""
    
    def test_revoke_valid_token(self, auth_module):
        """Test revoking a valid token - Requirement 18.6"""
        agent_id = "test-agent-010"
        token = auth_module.generate_token(agent_id)
        
        result = auth_module.revoke_token(token)
        
        assert result is True
        
        # Verify token is now invalid
        validation = auth_module.validate_token(token)
        assert validation.valid is False
    
    def test_revoke_empty_token(self, auth_module):
        """Test revoking empty token returns False"""
        result = auth_module.revoke_token("")
        assert result is False
    
    def test_revoke_expired_token(self, short_expiry_auth):
        """Test revoking an expired token"""
        agent_id = "test-agent-011"
        token = short_expiry_auth.generate_token(agent_id)
        
        # Wait for expiration
        time.sleep(2)
        
        # Should still be able to revoke expired token
        result = short_expiry_auth.revoke_token(token)
        assert result is True
    
    def test_revoke_malformed_token(self, auth_module):
        """Test revoking malformed token returns False"""
        result = auth_module.revoke_token("not.a.valid.token")
        assert result is False
    
    def test_revoke_token_twice(self, auth_module):
        """Test revoking the same token twice"""
        agent_id = "test-agent-012"
        token = auth_module.generate_token(agent_id)
        
        result1 = auth_module.revoke_token(token)
        result2 = auth_module.revoke_token(token)
        
        assert result1 is True
        assert result2 is True  # Should still return True


class TestTokenRefresh:
    """Test token refresh functionality"""
    
    def test_refresh_valid_token(self, auth_module):
        """Test refreshing a valid token - Requirement 18.2"""
        agent_id = "test-agent-013"
        old_token = auth_module.generate_token(agent_id)
        
        new_token = auth_module.refresh_token(old_token)
        
        assert new_token is not None
        assert new_token != old_token
        
        # Old token should be revoked
        old_validation = auth_module.validate_token(old_token)
        assert old_validation.valid is False
        
        # New token should be valid
        new_validation = auth_module.validate_token(new_token)
        assert new_validation.valid is True
        assert new_validation.agent_id == agent_id
    
    def test_refresh_token_preserves_metadata(self, auth_module):
        """Test that refresh preserves metadata"""
        agent_id = "test-agent-014"
        metadata = {'key': 'value', 'number': 42}
        old_token = auth_module.generate_token(agent_id, metadata)
        
        new_token = auth_module.refresh_token(old_token)
        
        new_info = auth_module.get_token_info(new_token)
        assert new_info['metadata'] == metadata
    
    def test_refresh_empty_token(self, auth_module):
        """Test refreshing empty token raises ValueError"""
        with pytest.raises(ValueError, match="Old token cannot be empty"):
            auth_module.refresh_token("")
    
    def test_refresh_expired_token(self, short_expiry_auth):
        """Test refreshing expired token raises ValueError"""
        agent_id = "test-agent-015"
        token = short_expiry_auth.generate_token(agent_id)
        
        # Wait for expiration
        time.sleep(2)
        
        with pytest.raises(ValueError, match="Cannot refresh invalid token"):
            short_expiry_auth.refresh_token(token)
    
    def test_refresh_revoked_token(self, auth_module):
        """Test refreshing revoked token raises ValueError"""
        agent_id = "test-agent-016"
        token = auth_module.generate_token(agent_id)
        
        auth_module.revoke_token(token)
        
        with pytest.raises(ValueError, match="Cannot refresh invalid token"):
            auth_module.refresh_token(token)
    
    def test_refresh_malformed_token(self, auth_module):
        """Test refreshing malformed token raises ValueError"""
        with pytest.raises(ValueError, match="Cannot refresh invalid token"):
            auth_module.refresh_token("not.a.valid.token")


class TestTokenInfo:
    """Test token information retrieval"""
    
    def test_get_token_info_valid_token(self, auth_module):
        """Test getting info from valid token"""
        agent_id = "test-agent-017"
        metadata = {'test': 'data'}
        token = auth_module.generate_token(agent_id, metadata)
        
        info = auth_module.get_token_info(token)
        
        assert info is not None
        assert info['agent_id'] == agent_id
        assert info['metadata'] == metadata
        assert info['issued_at'] is not None
        assert info['expires_at'] is not None
        assert info['jti'] is not None
        assert info['is_revoked'] is False
    
    def test_get_token_info_revoked_token(self, auth_module):
        """Test getting info from revoked token"""
        agent_id = "test-agent-018"
        token = auth_module.generate_token(agent_id)
        auth_module.revoke_token(token)
        
        info = auth_module.get_token_info(token)
        
        assert info is not None
        assert info['is_revoked'] is True
    
    def test_get_token_info_empty_token(self, auth_module):
        """Test getting info from empty token returns None"""
        info = auth_module.get_token_info("")
        assert info is None
    
    def test_get_token_info_malformed_token(self, auth_module):
        """Test getting info from malformed token returns None"""
        info = auth_module.get_token_info("not.a.valid.token")
        assert info is None
    
    def test_get_token_info_expired_token(self, short_expiry_auth):
        """Test getting info from expired token (should still work)"""
        agent_id = "test-agent-019"
        token = short_expiry_auth.generate_token(agent_id)
        
        time.sleep(2)
        
        # get_token_info should work even for expired tokens
        info = short_expiry_auth.get_token_info(token)
        assert info is not None
        assert info['agent_id'] == agent_id


class TestClearRevokedTokens:
    """Test clearing revoked tokens list"""
    
    def test_clear_revoked_tokens(self, auth_module):
        """Test clearing revoked tokens list"""
        # Revoke multiple tokens
        for i in range(5):
            token = auth_module.generate_token(f"agent-{i}")
            auth_module.revoke_token(token)
        
        assert len(auth_module.revoked_tokens) == 5
        
        auth_module.clear_revoked_tokens()
        
        assert len(auth_module.revoked_tokens) == 0
    
    def test_tokens_valid_after_clear(self, auth_module):
        """Test that tokens become valid again after clearing revocation list"""
        agent_id = "test-agent-020"
        token = auth_module.generate_token(agent_id)
        
        # Revoke token
        auth_module.revoke_token(token)
        validation1 = auth_module.validate_token(token)
        assert validation1.valid is False
        
        # Clear revoked tokens
        auth_module.clear_revoked_tokens()
        
        # Token should now be valid again (if not expired)
        validation2 = auth_module.validate_token(token)
        assert validation2.valid is True


class TestTokenExpiry:
    """Test token expiration behavior"""
    
    def test_token_expiry_time_correct(self, auth_module):
        """Test that token expiry time is set correctly - Requirement 10.4"""
        agent_id = "test-agent-021"
        before_generation = datetime.now(timezone.utc)
        token = auth_module.generate_token(agent_id)
        after_generation = datetime.now(timezone.utc)
        
        info = auth_module.get_token_info(token)
        
        # Expiry should be approximately token_expiry seconds from now
        # Note: JWT stores timestamps as integers, so we lose microsecond precision
        expected_expiry_min = before_generation + timedelta(seconds=auth_module.token_expiry)
        expected_expiry_max = after_generation + timedelta(seconds=auth_module.token_expiry)
        
        # Allow 2 second tolerance for timestamp precision loss
        assert (expected_expiry_min - timedelta(seconds=2)) <= info['expires_at'] <= (expected_expiry_max + timedelta(seconds=2))
    
    def test_custom_token_expiry(self):
        """Test custom token expiry configuration"""
        custom_expiry = 7200  # 2 hours
        auth = AuthenticationModule(secret_key="test_key", token_expiry=custom_expiry)
        
        agent_id = "test-agent-022"
        token = auth.generate_token(agent_id)
        
        info = auth.get_token_info(token)
        issued_at = info['issued_at']
        expires_at = info['expires_at']
        
        actual_expiry = (expires_at - issued_at).total_seconds()
        
        # Should be approximately custom_expiry seconds
        assert abs(actual_expiry - custom_expiry) < 1  # Allow 1 second tolerance


class TestTokenValidationObject:
    """Test TokenValidation object"""
    
    def test_token_validation_success(self):
        """Test TokenValidation object for successful validation"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        validation = TokenValidation(
            valid=True,
            agent_id="test-agent",
            expires_at=expires_at,
            error=None
        )
        
        assert validation.valid is True
        assert validation.agent_id == "test-agent"
        assert validation.expires_at == expires_at
        assert validation.error is None
    
    def test_token_validation_failure(self):
        """Test TokenValidation object for failed validation"""
        validation = TokenValidation(
            valid=False,
            agent_id=None,
            expires_at=None,
            error="Token expired"
        )
        
        assert validation.valid is False
        assert validation.agent_id is None
        assert validation.expires_at is None
        assert validation.error == "Token expired"


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    def test_full_token_lifecycle(self, auth_module):
        """Test complete token lifecycle: generate, validate, refresh, revoke"""
        agent_id = "test-agent-023"
        metadata = {'hostname': 'test-host'}
        
        # Generate token
        token1 = auth_module.generate_token(agent_id, metadata)
        
        # Validate token
        validation1 = auth_module.validate_token(token1)
        assert validation1.valid is True
        
        # Refresh token
        token2 = auth_module.refresh_token(token1)
        
        # Old token should be invalid
        validation2 = auth_module.validate_token(token1)
        assert validation2.valid is False
        
        # New token should be valid
        validation3 = auth_module.validate_token(token2)
        assert validation3.valid is True
        
        # Revoke new token
        auth_module.revoke_token(token2)
        
        # New token should now be invalid
        validation4 = auth_module.validate_token(token2)
        assert validation4.valid is False
    
    def test_multiple_agents_tokens(self, auth_module):
        """Test managing tokens for multiple agents"""
        agents = [f"agent-{i:03d}" for i in range(10)]
        tokens = {}
        
        # Generate tokens for all agents
        for agent_id in agents:
            tokens[agent_id] = auth_module.generate_token(agent_id)
        
        # Validate all tokens
        for agent_id, token in tokens.items():
            validation = auth_module.validate_token(token)
            assert validation.valid is True
            assert validation.agent_id == agent_id
        
        # Revoke some tokens
        for i in range(0, 10, 2):  # Revoke even-numbered agents
            auth_module.revoke_token(tokens[agents[i]])
        
        # Verify revoked tokens are invalid
        for i in range(0, 10, 2):
            validation = auth_module.validate_token(tokens[agents[i]])
            assert validation.valid is False
        
        # Verify non-revoked tokens are still valid
        for i in range(1, 10, 2):
            validation = auth_module.validate_token(tokens[agents[i]])
            assert validation.valid is True



class TestPropertyBasedTokenAuthentication:
    """
    Property-Based Tests for Token Generation and Validation
    
    Property 1: Authentication Integrity - Any generated token must validate successfully before expiration
    Validates: Requirements 10.3, 10.4, 18.3, 18.4
    """
    
    @given(
        agent_id=st.text(
            alphabet=string.ascii_letters + string.digits + '-_',
            min_size=1,
            max_size=50
        ),
        metadata_keys=st.lists(
            st.text(alphabet=string.ascii_letters, min_size=1, max_size=10),
            min_size=0,
            max_size=5,
            unique=True
        ),
        metadata_values=st.lists(
            st.one_of(
                st.text(max_size=50),
                st.integers(min_value=-1000, max_value=1000),
                st.booleans()
            ),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=20, deadline=500)
    def test_property_generated_token_validates_before_expiration(
        self, agent_id, metadata_keys, metadata_values
    ):
        """
        Property 1: Authentication Integrity
        
        For all valid agent_ids and metadata:
        - A generated token MUST validate successfully
        - The validated agent_id MUST match the original
        - The token MUST be valid before expiration
        - The token MUST have a valid expiration time
        
        Requirements: 10.3, 10.4, 18.3, 18.4
        """
        # Ensure metadata keys and values have same length
        metadata_values = metadata_values[:len(metadata_keys)]
        metadata = dict(zip(metadata_keys, metadata_values)) if metadata_keys else {}
        
        # Create auth module with reasonable expiry
        auth_module = AuthenticationModule(
            secret_key="property_test_secret_key",
            token_expiry=3600
        )
        
        # Generate token
        token = auth_module.generate_token(agent_id, metadata)
        
        # Property assertions
        assert token is not None, "Generated token must not be None"
        assert isinstance(token, str), "Generated token must be a string"
        assert len(token) > 0, "Generated token must not be empty"
        
        # Validate token immediately (before expiration)
        validation = auth_module.validate_token(token)
        
        # Core property: Generated token MUST validate successfully
        assert validation.valid is True, \
            f"Generated token must validate successfully. Error: {validation.error}"
        
        # Agent ID must match
        assert validation.agent_id == agent_id, \
            f"Validated agent_id must match original. Expected: {agent_id}, Got: {validation.agent_id}"
        
        # Expiration time must be set and in the future
        assert validation.expires_at is not None, "Token must have expiration time"
        assert validation.expires_at > datetime.now(timezone.utc), \
            "Token expiration must be in the future"
        
        # No error should be present for valid token
        assert validation.error is None, \
            f"Valid token must not have error. Got: {validation.error}"
        
        # Verify metadata is preserved
        token_info = auth_module.get_token_info(token)
        assert token_info is not None, "Token info must be retrievable"
        assert token_info['agent_id'] == agent_id, "Token info must contain correct agent_id"
        # Metadata might be None if empty dict was passed
        expected_metadata = metadata if metadata else None
        assert token_info['metadata'] == expected_metadata, \
            f"Token info must preserve metadata. Expected: {expected_metadata}, Got: {token_info['metadata']}"
    
    @given(
        agent_id=st.text(
            alphabet=string.ascii_letters + string.digits + '-_',
            min_size=1,
            max_size=30
        ),
        expiry_seconds=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=10, deadline=10000)
    def test_property_token_expires_after_expiry_time(self, agent_id, expiry_seconds):
        """
        Property: Token Expiration Behavior
        
        For all valid agent_ids and expiry times:
        - A token MUST be valid before expiration
        - A token MUST be invalid after expiration
        - Expired tokens MUST return appropriate error
        
        Requirements: 10.4, 10.5, 18.4
        """
        # Create auth module with short expiry
        auth_module = AuthenticationModule(
            secret_key="expiry_test_secret_key",
            token_expiry=expiry_seconds
        )
        
        # Generate token
        token = auth_module.generate_token(agent_id)
        
        # Token must be valid immediately after generation
        validation_before = auth_module.validate_token(token)
        assert validation_before.valid is True, \
            "Token must be valid immediately after generation"
        assert validation_before.agent_id == agent_id, \
            "Agent ID must match before expiration"
        
        # Wait for token to expire (add 1 second buffer)
        time.sleep(expiry_seconds + 1)
        
        # Token must be invalid after expiration
        validation_after = auth_module.validate_token(token)
        assert validation_after.valid is False, \
            "Token must be invalid after expiration time"
        assert validation_after.error is not None, \
            "Expired token must have error message"
        assert "expired" in validation_after.error.lower(), \
            f"Error message must indicate expiration. Got: {validation_after.error}"
    
    @given(
        agent_id=st.text(
            alphabet=string.ascii_letters + string.digits + '-_',
            min_size=1,
            max_size=30
        ),
        num_tokens=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=15, deadline=1000)
    def test_property_revoked_tokens_always_invalid(self, agent_id, num_tokens):
        """
        Property: Token Revocation Behavior
        
        For all valid agent_ids and any number of tokens:
        - A revoked token MUST always be invalid
        - Revocation MUST succeed for valid tokens
        - Validation of revoked token MUST return appropriate error
        
        Requirements: 18.6
        """
        auth_module = AuthenticationModule(
            secret_key="revocation_test_secret_key",
            token_expiry=3600
        )
        
        # Generate multiple tokens
        tokens = []
        for i in range(num_tokens):
            token = auth_module.generate_token(f"{agent_id}-{i}")
            tokens.append(token)
            
            # Verify token is valid before revocation
            validation = auth_module.validate_token(token)
            assert validation.valid is True, \
                f"Token {i} must be valid before revocation"
        
        # Revoke all tokens
        for i, token in enumerate(tokens):
            revoke_result = auth_module.revoke_token(token)
            assert revoke_result is True, \
                f"Revocation must succeed for token {i}"
            
            # Verify token is now invalid
            validation = auth_module.validate_token(token)
            assert validation.valid is False, \
                f"Token {i} must be invalid after revocation"
            assert validation.error is not None, \
                f"Revoked token {i} must have error message"
            assert "revoked" in validation.error.lower(), \
                f"Error must indicate revocation for token {i}. Got: {validation.error}"
    
    @given(
        agent_ids=st.lists(
            st.text(
                alphabet=string.ascii_letters + string.digits + '-_',
                min_size=1,
                max_size=30
            ),
            min_size=1,
            max_size=20,
            unique=True
        )
    )
    @settings(max_examples=15, deadline=1000)
    def test_property_unique_tokens_for_different_agents(self, agent_ids):
        """
        Property: Token Uniqueness
        
        For all sets of unique agent_ids:
        - Each agent MUST receive a unique token
        - Each token MUST validate to the correct agent_id
        - Tokens MUST not be interchangeable between agents
        
        Requirements: 10.3, 18.3
        """
        auth_module = AuthenticationModule(
            secret_key="uniqueness_test_secret_key",
            token_expiry=3600
        )
        
        # Generate tokens for all agents
        agent_tokens = {}
        for agent_id in agent_ids:
            token = auth_module.generate_token(agent_id)
            agent_tokens[agent_id] = token
        
        # Verify all tokens are unique
        all_tokens = list(agent_tokens.values())
        assert len(all_tokens) == len(set(all_tokens)), \
            "All generated tokens must be unique"
        
        # Verify each token validates to correct agent
        for agent_id, token in agent_tokens.items():
            validation = auth_module.validate_token(token)
            assert validation.valid is True, \
                f"Token for agent {agent_id} must be valid"
            assert validation.agent_id == agent_id, \
                f"Token must validate to correct agent. Expected: {agent_id}, Got: {validation.agent_id}"
    
    @given(
        agent_id=st.text(
            alphabet=string.ascii_letters + string.digits + '-_',
            min_size=1,
            max_size=30
        ),
        secret_key1=st.text(min_size=10, max_size=50),
        secret_key2=st.text(min_size=10, max_size=50)
    )
    @settings(max_examples=20, deadline=500)
    def test_property_tokens_not_valid_across_different_secrets(
        self, agent_id, secret_key1, secret_key2
    ):
        """
        Property: Secret Key Isolation
        
        For all agent_ids and different secret keys:
        - A token generated with one secret MUST NOT validate with a different secret
        - Token validation MUST enforce signature verification
        
        Requirements: 18.3
        """
        # Ensure secret keys are different
        assume(secret_key1 != secret_key2)
        
        # Create two auth modules with different secrets
        auth_module1 = AuthenticationModule(
            secret_key=secret_key1,
            token_expiry=3600
        )
        auth_module2 = AuthenticationModule(
            secret_key=secret_key2,
            token_expiry=3600
        )
        
        # Generate token with first secret
        token = auth_module1.generate_token(agent_id)
        
        # Token must be valid with first auth module
        validation1 = auth_module1.validate_token(token)
        assert validation1.valid is True, \
            "Token must be valid with original secret key"
        
        # Token must NOT be valid with second auth module
        validation2 = auth_module2.validate_token(token)
        assert validation2.valid is False, \
            "Token must NOT be valid with different secret key"
        assert validation2.error is not None, \
            "Invalid token must have error message"
    
    @given(
        agent_id=st.text(
            alphabet=string.ascii_letters + string.digits + '-_',
            min_size=1,
            max_size=30
        ),
        num_refreshes=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=15, deadline=1000)
    def test_property_token_refresh_maintains_validity(self, agent_id, num_refreshes):
        """
        Property: Token Refresh Chain
        
        For all agent_ids and refresh counts:
        - Refreshed tokens MUST be valid
        - Old tokens MUST be revoked after refresh
        - Refresh chain MUST maintain agent_id consistency
        
        Requirements: 18.2, 18.6
        """
        auth_module = AuthenticationModule(
            secret_key="refresh_test_secret_key",
            token_expiry=3600
        )
        
        # Generate initial token
        current_token = auth_module.generate_token(agent_id, {'initial': True})
        
        # Perform multiple refreshes
        for i in range(num_refreshes):
            # Current token must be valid before refresh
            validation_before = auth_module.validate_token(current_token)
            assert validation_before.valid is True, \
                f"Token must be valid before refresh {i}"
            assert validation_before.agent_id == agent_id, \
                f"Agent ID must be consistent before refresh {i}"
            
            # Refresh token
            new_token = auth_module.refresh_token(current_token)
            
            # New token must be different
            assert new_token != current_token, \
                f"Refreshed token must be different at iteration {i}"
            
            # Old token must now be invalid (revoked)
            validation_old = auth_module.validate_token(current_token)
            assert validation_old.valid is False, \
                f"Old token must be invalid after refresh {i}"
            
            # New token must be valid
            validation_new = auth_module.validate_token(new_token)
            assert validation_new.valid is True, \
                f"New token must be valid after refresh {i}"
            assert validation_new.agent_id == agent_id, \
                f"Agent ID must be preserved after refresh {i}"
            
            # Update current token for next iteration
            current_token = new_token
    
    @given(
        agent_id=st.text(
            alphabet=string.ascii_letters + string.digits + '-_',
            min_size=1,
            max_size=30
        ),
        token_expiry=st.integers(min_value=60, max_value=3600)
    )
    @settings(max_examples=20, deadline=500)
    def test_property_token_expiry_time_accuracy(self, agent_id, token_expiry):
        """
        Property: Token Expiry Time Accuracy
        
        For all agent_ids and expiry times:
        - Token expiry time MUST be approximately token_expiry seconds from generation
        - Expiry time MUST be in the future at generation time
        
        Requirements: 10.4
        """
        auth_module = AuthenticationModule(
            secret_key="expiry_accuracy_test_key",
            token_expiry=token_expiry
        )
        
        # Record time before and after generation
        time_before = datetime.now(timezone.utc)
        token = auth_module.generate_token(agent_id)
        time_after = datetime.now(timezone.utc)
        
        # Get token info
        token_info = auth_module.get_token_info(token)
        assert token_info is not None, "Token info must be retrievable"
        
        expires_at = token_info['expires_at']
        issued_at = token_info['issued_at']
        
        # Expiry must be in the future
        assert expires_at > time_before, \
            "Token expiry must be in the future"
        
        # Calculate expected expiry range
        expected_expiry_min = time_before + timedelta(seconds=token_expiry)
        expected_expiry_max = time_after + timedelta(seconds=token_expiry)
        
        # Expiry should be within expected range (allow 2 second tolerance)
        tolerance = timedelta(seconds=2)
        assert (expected_expiry_min - tolerance) <= expires_at <= (expected_expiry_max + tolerance), \
            f"Token expiry time must be accurate. Expected: {token_expiry}s from generation, " \
            f"Got: {(expires_at - issued_at).total_seconds()}s"
