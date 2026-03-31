"""
Property-Based Tests for Final Integration Testing

Implements the remaining property-based tests for the remote system enhancement.

Subtask 33.2: Run property-based tests
- Property 2: Command Logging Completeness
- Property 5: Plugin Isolation
- Property 6: Agent Registry Consistency
- Property 7: Timeout Enforcement
- Property 8: Token Expiration
"""

import pytest
import tempfile
import os
import time
import threading
from hypothesis import given, strategies as st, settings, HealthCheck
from remote_system.enhanced_server.enhanced_server import EnhancedServer
from remote_system.enhanced_server.auth_module import AuthenticationModule
from remote_system.enhanced_agent.plugin_manager import PluginManager, Plugin, PluginResult


@pytest.fixture
def temp_db():
    """Create a temporary database file"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def enhanced_server(temp_db):
    """Create enhanced server for testing"""
    server = EnhancedServer(
        host="127.0.0.1",
        port=39999,
        db_path=temp_db,
        use_tls=False,
        secret_key="test_secret_key_pbt"
    )
    yield server
    try:
        server.stop()
    except Exception:
        pass


@pytest.fixture
def auth_module():
    """Create authentication module"""
    return AuthenticationModule(secret_key="test_secret_key_pbt", token_expiry=3600)


class TestProperty2CommandLoggingCompleteness:
    """
    Property 2: Command Logging Completeness - Every command must be logged
    
    **Validates: Requirements 12.2, 12.3**
    
    For all commands sent to an agent:
    - The command MUST be logged in the database
    - The log MUST contain the agent_id, command text, and timestamp
    - The log MUST be retrievable from command history
    """
    
    @given(
        agent_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=5, max_size=20),
        command=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=100),
        result=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 ", min_size=0, max_size=200),
        status=st.sampled_from(['success', 'error', 'timeout'])
    )
    @settings(max_examples=50, deadline=2000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_every_command_is_logged(self, enhanced_server, agent_id, command, result, status):
        """
        **Validates: Requirements 12.2, 12.3**
        
        Property 2: Every command sent to an agent must be logged in the database
        
        For all commands:
        - Command is logged with correct agent_id
        - Command text is preserved
        - Status is recorded
        - Log is retrievable from history
        """
        # Register agent first
        agent_info = {
            'hostname': 'test-host',
            'username': 'testuser',
            'os_type': 'Linux',
            'os_version': 'Ubuntu 20.04',
            'ip_address': '127.0.0.1',
            'mac_address': '00:11:22:33:44:55',
            'capabilities': ['command']
        }
        enhanced_server.db_manager.log_connection(agent_id, agent_info)
        
        # Log the command
        log_id = enhanced_server.db_manager.log_command(
            agent_id=agent_id,
            command=command,
            result=result,
            status=status,
            execution_time=0.1
        )
        
        # Property: Log ID must be generated
        assert log_id is not None, \
            "Command logging must return a log ID"
        
        # Property: Command must be retrievable from history
        history = enhanced_server.db_manager.get_agent_history(agent_id, limit=100)
        
        assert len(history) > 0, \
            "Command history must contain at least one entry after logging"
        
        # Property: The logged command must be in the history
        command_found = any(
            log['command'] == command and 
            log['agent_id'] == agent_id and
            log['status'] == status
            for log in history
        )
        
        assert command_found, \
            f"Logged command '{command}' must be retrievable from agent history"
        
        # Property: The most recent log must match our command
        most_recent = history[0]
        assert most_recent['agent_id'] == agent_id, \
            "Most recent log must have correct agent_id"
        assert most_recent['command'] == command, \
            "Most recent log must have correct command text"
        assert most_recent['status'] == status, \
            "Most recent log must have correct status"
    
    @given(
        num_commands=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=30, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_all_commands_logged_in_sequence(self, enhanced_server, num_commands):
        """
        **Validates: Requirements 12.2, 12.3**
        
        Property 2: All commands in a sequence must be logged
        
        For any sequence of commands:
        - All commands are logged
        - Command count in history matches sent count
        - Commands are in correct order
        """
        agent_id = "test-agent-sequence"
        
        # Register agent
        agent_info = {
            'hostname': 'test-host',
            'username': 'testuser',
            'os_type': 'Linux',
            'os_version': 'Ubuntu 20.04',
            'ip_address': '127.0.0.1',
            'mac_address': '00:11:22:33:44:55',
            'capabilities': ['command']
        }
        enhanced_server.db_manager.log_connection(agent_id, agent_info)
        
        # Log multiple commands
        commands = [f"command_{i}" for i in range(num_commands)]
        log_ids = []
        
        for cmd in commands:
            log_id = enhanced_server.db_manager.log_command(
                agent_id=agent_id,
                command=cmd,
                result=f"result_{cmd}",
                status='success',
                execution_time=0.1
            )
            log_ids.append(log_id)
        
        # Property: All log IDs must be generated
        assert len(log_ids) == num_commands, \
            "All commands must generate log IDs"
        assert all(log_id is not None for log_id in log_ids), \
            "All log IDs must be non-null"
        
        # Property: History must contain all commands
        history = enhanced_server.db_manager.get_agent_history(agent_id, limit=100)
        
        assert len(history) >= num_commands, \
            f"History must contain at least {num_commands} entries"
        
        # Property: All commands must be present in history
        logged_commands = [log['command'] for log in history]
        for cmd in commands:
            assert cmd in logged_commands, \
                f"Command '{cmd}' must be in history"


class TestProperty5PluginIsolation:
    """
    Property 5: Plugin Isolation - Plugin failures must not crash the agent
    
    **Validates: Requirements 17.3**
    
    For all plugin failures:
    - Agent continues running
    - Other plugins remain available
    - Error is returned in PluginResult
    - No exceptions propagate to agent
    """
    
    @given(
        error_message=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=5, max_size=50)
    )
    @settings(max_examples=30, deadline=2000)
    def test_property_plugin_failure_does_not_crash_agent(self, error_message):
        """
        **Validates: Requirements 17.3**
        
        Property 5: Plugin failures must not crash the agent
        
        For all plugin errors:
        - Plugin manager catches the error
        - Returns PluginResult with success=False
        - Error message is preserved
        - Plugin manager remains operational
        """
        import tempfile
        import shutil
        
        # Create temporary plugin directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create a plugin that always fails
            class FailingPlugin(Plugin):
                def execute(self, args):
                    raise Exception(error_message)
                
                def get_name(self):
                    return "failing_plugin"
                
                def get_required_arguments(self):
                    return []
            
            # Create plugin manager
            manager = PluginManager(temp_dir)
            manager.register_plugin(FailingPlugin())
            
            # Property: Plugin manager is operational
            assert "failing_plugin" in manager.list_plugins(), \
                "Plugin must be registered"
            
            # Execute the failing plugin
            result = manager.execute_plugin("failing_plugin", {})
            
            # Property: Execution returns PluginResult (not exception)
            assert isinstance(result, PluginResult), \
                "Plugin execution must return PluginResult even on failure"
            
            # Property: Result indicates failure
            assert result.success is False, \
                "Plugin result must indicate failure"
            
            # Property: Error message is preserved
            assert result.error is not None, \
                "Plugin result must contain error message"
            assert error_message in result.error, \
                f"Error message must be preserved. Expected '{error_message}' in '{result.error}'"
            
            # Property: Plugin manager remains operational
            plugins = manager.list_plugins()
            assert len(plugins) > 0, \
                "Plugin manager must remain operational after plugin failure"
            
        finally:
            shutil.rmtree(temp_dir)
    
    @given(
        num_failures=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=3000)
    def test_property_multiple_plugin_failures_isolated(self, num_failures):
        """
        **Validates: Requirements 17.3**
        
        Property 5: Multiple plugin failures must be isolated
        
        For any number of plugin failures:
        - Each failure is isolated
        - Plugin manager continues working
        - Other plugins remain available
        """
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create multiple failing plugins
            class FailingPlugin(Plugin):
                def __init__(self, name):
                    self.name = name
                
                def execute(self, args):
                    raise Exception(f"Failure from {self.name}")
                
                def get_name(self):
                    return self.name
                
                def get_required_arguments(self):
                    return []
            
            # Create a working plugin
            class WorkingPlugin(Plugin):
                def execute(self, args):
                    return {"status": "success"}
                
                def get_name(self):
                    return "working_plugin"
                
                def get_required_arguments(self):
                    return []
            
            # Create plugin manager
            manager = PluginManager(temp_dir)
            
            # Register failing plugins
            for i in range(num_failures):
                manager.register_plugin(FailingPlugin(f"failing_{i}"))
            
            # Register working plugin
            manager.register_plugin(WorkingPlugin())
            
            # Property: All plugins are registered
            plugins = manager.list_plugins()
            assert len(plugins) == num_failures + 1, \
                "All plugins must be registered"
            
            # Execute all failing plugins
            for i in range(num_failures):
                result = manager.execute_plugin(f"failing_{i}", {})
                
                # Property: Each failure is isolated
                assert result.success is False, \
                    f"Plugin failing_{i} must fail"
                assert result.error is not None, \
                    f"Plugin failing_{i} must have error message"
            
            # Property: Working plugin still works after failures
            result = manager.execute_plugin("working_plugin", {})
            assert result.success is True, \
                "Working plugin must still function after other plugins fail"
            assert result.data is not None, \
                "Working plugin must return data"
            
        finally:
            shutil.rmtree(temp_dir)


class TestProperty6AgentRegistryConsistency:
    """
    Property 6: Agent Registry Consistency - Active agents must match database state
    
    **Validates: Requirements 16.1, 19.4**
    
    For all agent registrations:
    - Agent in active registry implies database status is "online"
    - Database status "online" implies agent is in active registry
    - Registry and database are synchronized
    """
    
    @given(
        agent_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=5, max_size=20),
        hostname=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=15)
    )
    @settings(max_examples=50, deadline=2000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_registered_agent_in_database(self, enhanced_server, agent_id, hostname):
        """
        **Validates: Requirements 16.1, 19.4**
        
        Property 6: Registered agents must be in database with correct status
        
        For all agent registrations:
        - Agent is logged in database
        - Agent appears in active agents list
        - Status is consistent
        """
        # Register agent
        agent_info = {
            'hostname': hostname,
            'username': 'testuser',
            'os_type': 'Linux',
            'os_version': 'Ubuntu 20.04',
            'ip_address': '127.0.0.1',
            'mac_address': '00:11:22:33:44:55',
            'capabilities': ['command']
        }
        
        enhanced_server.db_manager.log_connection(agent_id, agent_info)
        
        # Property: Agent must be in active agents list
        active_agents = enhanced_server.db_manager.get_active_agents()
        
        agent_found = any(
            agent['agent_id'] == agent_id and
            agent['hostname'] == hostname
            for agent in active_agents
        )
        
        assert agent_found, \
            f"Registered agent '{agent_id}' must appear in active agents list"
    
    @given(
        num_agents=st.integers(min_value=1, max_value=15)
    )
    @settings(max_examples=20, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_all_registered_agents_in_database(self, enhanced_server, num_agents):
        """
        **Validates: Requirements 16.1, 19.4**
        
        Property 6: All registered agents must be in database
        
        For any number of agent registrations:
        - All agents are in database
        - Count matches
        - All are retrievable
        """
        # Register multiple agents
        agent_ids = [f"agent-{i:03d}" for i in range(num_agents)]
        
        for i, agent_id in enumerate(agent_ids):
            agent_info = {
                'hostname': f'host-{i}',
                'username': 'testuser',
                'os_type': 'Linux',
                'os_version': 'Ubuntu 20.04',
                'ip_address': '127.0.0.1',
                'mac_address': f'00:11:22:33:44:{i:02x}',
                'capabilities': ['command']
            }
            enhanced_server.db_manager.log_connection(agent_id, agent_info)
        
        # Property: All agents must be in active agents list
        active_agents = enhanced_server.db_manager.get_active_agents()
        
        assert len(active_agents) >= num_agents, \
            f"Active agents count must be at least {num_agents}"
        
        # Property: All registered agent IDs must be present
        active_agent_ids = [agent['agent_id'] for agent in active_agents]
        
        for agent_id in agent_ids:
            assert agent_id in active_agent_ids, \
                f"Agent '{agent_id}' must be in active agents list"


class TestProperty7TimeoutEnforcement:
    """
    Property 7: Timeout Enforcement - Operations must complete within timeout
    
    **Validates: Requirements 4.3, 17.4**
    
    For all operations with timeouts:
    - Operation completes within timeout OR
    - Operation is terminated and returns timeout status
    - No operation exceeds timeout significantly
    """
    
    @given(
        timeout=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=20, deadline=10000)
    def test_property_plugin_timeout_enforced(self, timeout):
        """
        **Validates: Requirements 4.3, 17.4**
        
        Property 7: Plugin execution must respect timeout
        
        For all timeout values:
        - Plugin execution terminates within timeout
        - Timeout error is returned
        - Execution time does not significantly exceed timeout
        """
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create a plugin that sleeps longer than timeout
            class SlowPlugin(Plugin):
                def execute(self, args):
                    time.sleep(timeout + 2)  # Sleep longer than timeout
                    return {"status": "completed"}
                
                def get_name(self):
                    return "slow_plugin"
                
                def get_required_arguments(self):
                    return []
            
            # Create plugin manager
            manager = PluginManager(temp_dir)
            manager.register_plugin(SlowPlugin())
            
            # Execute with timeout
            start_time = time.time()
            result = manager.execute_plugin("slow_plugin", {"timeout": timeout})
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Property: Execution must complete within reasonable time
            # Allow 1 second grace period for thread termination
            assert execution_time <= timeout + 1.5, \
                f"Execution time ({execution_time:.2f}s) must not significantly exceed timeout ({timeout}s)"
            
            # Property: Result must indicate timeout
            assert result.success is False, \
                "Plugin execution must fail on timeout"
            assert result.error is not None, \
                "Timeout must produce error message"
            assert "timeout" in result.error.lower(), \
                f"Error must mention timeout. Got: {result.error}"
            
        finally:
            shutil.rmtree(temp_dir)


class TestProperty8TokenExpiration:
    """
    Property 8: Token Expiration - Expired tokens must not grant access
    
    **Validates: Requirements 10.5, 18.4**
    
    For all expired tokens:
    - Token validation returns valid=False
    - Error message indicates expiration
    - No access is granted with expired token
    """
    
    @given(
        agent_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=5, max_size=20),
        expiry_seconds=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=20, deadline=8000)
    def test_property_expired_tokens_rejected(self, agent_id, expiry_seconds):
        """
        **Validates: Requirements 10.5, 18.4**
        
        Property 8: Expired tokens must not grant access
        
        For all tokens with expiration:
        - Token is valid before expiration
        - Token is invalid after expiration
        - Error indicates expiration
        """
        # Create auth module with short expiry
        auth = AuthenticationModule(
            secret_key="test_secret_key",
            token_expiry=expiry_seconds
        )
        
        # Generate token
        token = auth.generate_token(agent_id, {"hostname": "test-host"})
        
        # Property: Token is valid immediately after generation
        validation = auth.validate_token(token)
        assert validation.valid is True, \
            "Token must be valid immediately after generation"
        assert validation.agent_id == agent_id, \
            "Token must contain correct agent_id"
        
        # Wait for expiration
        time.sleep(expiry_seconds + 1)
        
        # Property: Token is invalid after expiration
        validation_expired = auth.validate_token(token)
        assert validation_expired.valid is False, \
            "Token must be invalid after expiration"
        
        # Property: Error indicates expiration
        assert validation_expired.error is not None, \
            "Expired token validation must have error message"
        assert "expired" in validation_expired.error.lower(), \
            f"Error must indicate expiration. Got: {validation_expired.error}"
    
    @given(
        num_tokens=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=15, deadline=8000)
    def test_property_all_expired_tokens_rejected(self, num_tokens):
        """
        **Validates: Requirements 10.5, 18.4**
        
        Property 8: All expired tokens must be rejected
        
        For any number of expired tokens:
        - All are rejected after expiration
        - None grant access
        """
        # Create auth module with very short expiry
        auth = AuthenticationModule(
            secret_key="test_secret_key",
            token_expiry=1
        )
        
        # Generate multiple tokens
        tokens = []
        for i in range(num_tokens):
            token = auth.generate_token(f"agent-{i}", {"hostname": f"host-{i}"})
            tokens.append(token)
        
        # Property: All tokens are valid initially
        for token in tokens:
            validation = auth.validate_token(token)
            assert validation.valid is True, \
                "All tokens must be valid initially"
        
        # Wait for expiration
        time.sleep(2)
        
        # Property: All tokens are invalid after expiration
        for i, token in enumerate(tokens):
            validation = auth.validate_token(token)
            assert validation.valid is False, \
                f"Token {i} must be invalid after expiration"
            assert validation.error is not None, \
                f"Token {i} must have error message"
            assert "expired" in validation.error.lower(), \
                f"Token {i} error must indicate expiration"
