"""
Unit tests for Configuration Manager (Server and Agent)

Tests configuration loading from files and environment, validation,
hot-reload functionality, and security level presets.

Requirements: 21.1-21.7
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# Import both server and agent config managers
from remote_system.enhanced_server.config_manager import (
    ConfigManager as ServerConfigManager,
    ServerConfig,
    SecurityLevel as ServerSecurityLevel
)
from remote_system.enhanced_agent.config_manager import (
    ConfigManager as AgentConfigManager,
    AgentConfig,
    SecurityLevel as AgentSecurityLevel
)


class TestServerConfigManager:
    """Test suite for server configuration manager"""
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config_manager = ServerConfigManager()
        config = config_manager.load_config()
        
        assert config.host == "0.0.0.0"
        assert config.port == 9999
        assert config.use_tls is True
        assert config.security_level == "medium"
        assert config.max_agents == 1000
        assert config.command_timeout == 300
    
    def test_load_from_json_file(self):
        """
        Test loading configuration from JSON file
        Requirements: 21.2
        """
        # Create temporary JSON config file
        config_data = {
            "host": "192.168.1.100",
            "port": 8888,
            "db_path": "/tmp/test.db",
            "use_tls": False,
            "max_agents": 500
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config_manager = ServerConfigManager(temp_path)
            config = config_manager.load_config()
            
            assert config.host == "192.168.1.100"
            assert config.port == 8888
            assert config.db_path == "/tmp/test.db"
            assert config.use_tls is False
            assert config.max_agents == 500
        finally:
            os.unlink(temp_path)
    
    def test_load_from_yaml_file(self):
        """
        Test loading configuration from YAML file
        Requirements: 21.2
        """
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")
        
        # Create temporary YAML config file
        config_data = """
host: 10.0.0.1
port: 7777
db_path: /var/lib/remote_system.db
use_tls: true
max_agents: 2000
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_data)
            temp_path = f.name
        
        try:
            config_manager = ServerConfigManager(temp_path)
            config = config_manager.load_config()
            
            assert config.host == "10.0.0.1"
            assert config.port == 7777
            assert config.db_path == "/var/lib/remote_system.db"
            assert config.use_tls is True
            assert config.max_agents == 2000
        finally:
            os.unlink(temp_path)
    
    def test_load_from_environment_variables(self):
        """
        Test loading configuration from environment variables
        Requirements: 21.2
        """
        env_vars = {
            "REMOTE_SYSTEM_HOST": "env.example.com",
            "REMOTE_SYSTEM_PORT": "5555",
            "REMOTE_SYSTEM_USE_TLS": "false",
            "REMOTE_SYSTEM_MAX_AGENTS": "100",
            "REMOTE_SYSTEM_LOG_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars):
            config_manager = ServerConfigManager()
            config = config_manager.load_config()
            
            assert config.host == "env.example.com"
            assert config.port == 5555
            assert config.use_tls is False
            assert config.max_agents == 100
            assert config.log_level == "DEBUG"
    
    def test_environment_overrides_file(self):
        """
        Test that environment variables override file configuration
        Requirements: 21.2
        """
        # Create config file
        config_data = {"host": "file.example.com", "port": 8888}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            env_vars = {
                "REMOTE_SYSTEM_HOST": "env.example.com",
                "REMOTE_SYSTEM_PORT": "9999"
            }
            
            with patch.dict(os.environ, env_vars):
                config_manager = ServerConfigManager(temp_path)
                config = config_manager.load_config()
                
                # Environment should override file
                assert config.host == "env.example.com"
                assert config.port == 9999
        finally:
            os.unlink(temp_path)
    
    def test_invalid_port_validation(self):
        """
        Test validation of invalid port numbers
        Requirements: 21.3
        """
        config_manager = ServerConfigManager()
        config_manager.config.port = 99999  # Invalid port
        
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config()
        
        assert "Invalid port number" in str(exc_info.value)
        assert "99999" in str(exc_info.value)
    
    def test_invalid_log_level_validation(self):
        """
        Test validation of invalid log level
        Requirements: 21.3
        """
        config_manager = ServerConfigManager()
        config_manager.config.log_level = "INVALID"
        
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config()
        
        assert "Invalid log_level" in str(exc_info.value)
    
    def test_invalid_max_agents_validation(self):
        """
        Test validation of invalid max_agents
        Requirements: 21.3
        """
        config_manager = ServerConfigManager()
        config_manager.config.max_agents = 0
        
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config()
        
        assert "Invalid max_agents" in str(exc_info.value)
    
    def test_missing_tls_certificate_validation(self):
        """
        Test validation when TLS is enabled but certificate is missing
        Requirements: 21.3
        """
        config_manager = ServerConfigManager()
        config_manager.config.use_tls = True
        config_manager.config.cert_file = "/nonexistent/cert.pem"
        
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config()
        
        assert "certificate file not found" in str(exc_info.value).lower()
    
    def test_multiple_validation_errors(self):
        """
        Test that multiple validation errors are reported
        Requirements: 21.3
        """
        config_manager = ServerConfigManager()
        config_manager.config.port = -1
        config_manager.config.max_agents = -10
        config_manager.config.log_level = "INVALID"
        
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config()
        
        error_message = str(exc_info.value)
        assert "Invalid port number" in error_message
        assert "Invalid max_agents" in error_message
        assert "Invalid log_level" in error_message
    
    def test_security_level_low_preset(self):
        """
        Test LOW security level preset
        Requirements: 21.7
        """
        config_manager = ServerConfigManager()
        config_manager.config.security_level = "low"
        config_manager._apply_security_preset()
        
        # Security preset should set token expiry
        assert config_manager.config.token_expiry == 3600  # 1 hour
    
    def test_security_level_medium_preset(self):
        """
        Test MEDIUM security level preset
        Requirements: 21.7
        """
        config_manager = ServerConfigManager()
        config_manager.config.security_level = "medium"
        config_manager._apply_security_preset()
        
        # Security preset should set token expiry
        assert config_manager.config.token_expiry == 86400  # 24 hours
    
    def test_security_level_high_preset(self):
        """
        Test HIGH security level preset
        Requirements: 21.7
        """
        config_manager = ServerConfigManager()
        config_manager.config.security_level = "high"
        config_manager._apply_security_preset()
        
        # Security preset should set token expiry
        assert config_manager.config.token_expiry == 3600  # 1 hour
    
    def test_hot_reload_functionality(self):
        """
        Test hot-reload of non-critical settings
        Requirements: 21.4
        """
        # Create initial config file
        config_data = {"log_level": "INFO", "max_agents": 1000}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config_manager = ServerConfigManager(temp_path)
            config = config_manager.load_config()
            
            assert config.log_level == "INFO"
            assert config.max_agents == 1000
            
            # Update config file
            updated_data = {"log_level": "DEBUG", "max_agents": 500}
            with open(temp_path, 'w') as f:
                json.dump(updated_data, f)
            
            # Reload config
            config = config_manager.reload_config()
            
            # Hot-reloadable setting should update
            assert config.log_level == "DEBUG"
            # max_agents is also hot-reloadable
            assert config.max_agents == 500
        finally:
            os.unlink(temp_path)
    
    def test_hot_reload_preserves_critical_settings(self):
        """
        Test that hot-reload preserves critical settings
        Requirements: 21.4
        """
        # Create initial config
        config_data = {"host": "original.com", "port": 9999, "log_level": "INFO"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config_manager = ServerConfigManager(temp_path)
            config = config_manager.load_config()
            
            original_host = config.host
            original_port = config.port
            
            # Update config file with different host/port
            updated_data = {"host": "new.com", "port": 8888, "log_level": "DEBUG"}
            with open(temp_path, 'w') as f:
                json.dump(updated_data, f)
            
            # Reload config
            config = config_manager.reload_config()
            
            # Critical settings should NOT change
            assert config.host == original_host
            assert config.port == original_port
            # But hot-reloadable settings should change
            assert config.log_level == "DEBUG"
        finally:
            os.unlink(temp_path)
    
    def test_save_config_json(self):
        """Test saving configuration to JSON file"""
        config_manager = ServerConfigManager()
        config_manager.config.host = "test.example.com"
        config_manager.config.port = 7777
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config_manager.save_config(temp_path, format='json')
            
            # Load and verify
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['host'] == "test.example.com"
            assert saved_data['port'] == 7777
        finally:
            os.unlink(temp_path)
    
    def test_create_template(self):
        """
        Test creating configuration template for batch builds
        Requirements: 21.5
        """
        config_manager = ServerConfigManager()
        
        template = config_manager.create_template(
            "production_template",
            {"host": "prod.example.com", "max_agents": 5000}
        )
        
        assert template['template_name'] == "production_template"
        assert template['host'] == "prod.example.com"
        assert template['max_agents'] == 5000
    
    def test_file_not_found_error(self):
        """Test error handling for missing config file"""
        config_manager = ServerConfigManager("/nonexistent/config.json")
        
        with pytest.raises(FileNotFoundError) as exc_info:
            config_manager.load_config()
        
        assert "Configuration file not found" in str(exc_info.value)
    
    def test_invalid_json_format(self):
        """Test error handling for invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            config_manager = ServerConfigManager(temp_path)
            
            with pytest.raises(ValueError) as exc_info:
                config_manager.load_config()
            
            assert "Invalid JSON" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestAgentConfigManager:
    """Test suite for agent configuration manager"""
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config_manager = AgentConfigManager()
        config = config_manager.load_config()
        
        assert config.server_ip == "127.0.0.1"
        assert config.server_port == 9999
        assert config.use_tls is True
        assert config.security_level == "medium"
        assert config.reconnect_enabled is True
    
    def test_load_from_json_file(self):
        """
        Test loading configuration from JSON file
        Requirements: 21.2
        """
        config_data = {
            "server_ip": "192.168.1.100",
            "server_port": 8888,
            "use_tls": False,
            "persistence_enabled": True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config_manager = AgentConfigManager(temp_path)
            config = config_manager.load_config()
            
            assert config.server_ip == "192.168.1.100"
            assert config.server_port == 8888
            assert config.use_tls is False
            assert config.persistence_enabled is True
        finally:
            os.unlink(temp_path)
    
    def test_load_from_environment_variables(self):
        """
        Test loading configuration from environment variables
        Requirements: 21.2
        """
        env_vars = {
            "REMOTE_AGENT_SERVER_IP": "env.example.com",
            "REMOTE_AGENT_SERVER_PORT": "5555",
            "REMOTE_AGENT_USE_TLS": "false",
            "REMOTE_AGENT_PERSISTENCE_ENABLED": "true",
            "REMOTE_AGENT_LOG_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars):
            config_manager = AgentConfigManager()
            config = config_manager.load_config()
            
            assert config.server_ip == "env.example.com"
            assert config.server_port == 5555
            assert config.use_tls is False
            assert config.persistence_enabled is True
            assert config.log_level == "DEBUG"
    
    def test_invalid_server_port_validation(self):
        """
        Test validation of invalid server port
        Requirements: 21.3
        """
        config_manager = AgentConfigManager()
        config_manager.config.server_port = 99999
        
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config()
        
        assert "Invalid server_port" in str(exc_info.value)
    
    def test_empty_server_ip_validation(self):
        """
        Test validation of empty server IP
        Requirements: 21.3
        """
        config_manager = AgentConfigManager()
        config_manager.config.server_ip = ""
        
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config()
        
        assert "server_ip cannot be empty" in str(exc_info.value)
    
    def test_invalid_persistence_method_validation(self):
        """
        Test validation of invalid persistence method
        Requirements: 21.3, 21.6
        """
        config_manager = AgentConfigManager()
        config_manager.config.persistence_enabled = True
        config_manager.config.persistence_methods = ["invalid_method"]
        
        with pytest.raises(ValueError) as exc_info:
            config_manager.validate_config()
        
        assert "Invalid persistence method" in str(exc_info.value)
    
    def test_security_level_presets(self):
        """
        Test security level presets for agent
        Requirements: 21.7
        """
        # Test LOW
        config_manager = AgentConfigManager()
        config_manager.config.security_level = "low"
        config_manager._apply_security_preset()
        # Security preset is applied but doesn't override explicit settings
        
        # Test MEDIUM
        config_manager = AgentConfigManager()
        config_manager.config.security_level = "medium"
        config_manager._apply_security_preset()
        # Security preset is applied
        
        # Test HIGH
        config_manager = AgentConfigManager()
        config_manager.config.security_level = "high"
        config_manager._apply_security_preset()
        # Security preset is applied
    
    def test_hot_reload_functionality(self):
        """
        Test hot-reload of non-critical settings
        Requirements: 21.4
        """
        config_data = {"log_level": "INFO", "command_timeout": 300}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config_manager = AgentConfigManager(temp_path)
            config = config_manager.load_config()
            
            assert config.log_level == "INFO"
            assert config.command_timeout == 300
            
            # Update config file
            updated_data = {"log_level": "DEBUG", "command_timeout": 600}
            with open(temp_path, 'w') as f:
                json.dump(updated_data, f)
            
            # Reload config
            config = config_manager.reload_config()
            
            assert config.log_level == "DEBUG"
            assert config.command_timeout == 600
        finally:
            os.unlink(temp_path)
    
    def test_persistence_methods_configuration(self):
        """
        Test configuring persistence methods
        Requirements: 21.6
        """
        config_manager = AgentConfigManager()
        config_manager.config.persistence_enabled = True
        config_manager.config.persistence_methods = ["registry", "startup", "scheduled_task"]
        
        # Should validate successfully
        config_manager.validate_config()
        
        assert "registry" in config_manager.config.persistence_methods
        assert "startup" in config_manager.config.persistence_methods
        assert "scheduled_task" in config_manager.config.persistence_methods
    
    def test_list_environment_variables(self):
        """Test loading list-type configuration from environment"""
        env_vars = {
            "REMOTE_AGENT_ENABLED_PLUGINS": "file_transfer,screenshot,keylogger",
            "REMOTE_AGENT_DISABLED_PLUGINS": "persistence",
            "REMOTE_AGENT_PERSISTENCE_METHODS": "registry,startup"
        }
        
        with patch.dict(os.environ, env_vars):
            config_manager = AgentConfigManager()
            config = config_manager.load_config()
            
            assert config.enabled_plugins == ["file_transfer", "screenshot", "keylogger"]
            assert config.disabled_plugins == ["persistence"]
            assert config.persistence_methods == ["registry", "startup"]
    
    def test_create_template(self):
        """
        Test creating configuration template for batch builds
        Requirements: 21.5
        """
        config_manager = AgentConfigManager()
        
        template = config_manager.create_template(
            "field_agent_template",
            {"server_ip": "field.example.com", "persistence_enabled": True}
        )
        
        assert template['template_name'] == "field_agent_template"
        assert template['server_ip'] == "field.example.com"
        assert template['persistence_enabled'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
