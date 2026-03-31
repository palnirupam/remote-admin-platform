"""
Configuration Manager for Enhanced Server

This module provides flexible configuration management for the enhanced server,
supporting loading from JSON/YAML files, environment variables, validation,
hot-reload, and security level presets.

Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security level presets"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ServerConfig:
    """Server configuration data class"""
    # Network settings
    host: str = "0.0.0.0"
    port: int = 9999
    
    # Database settings
    db_path: str = "./data/remote_system.db"
    db_type: str = "sqlite"
    
    # Security settings
    use_tls: bool = True
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    secret_key: Optional[str] = None
    token_expiry: int = 86400  # 24 hours
    
    # Performance settings
    max_agents: int = 1000
    command_timeout: int = 300
    heartbeat_interval: int = 60
    heartbeat_timeout: int = 10
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Web UI settings
    web_ui_enabled: bool = True
    web_ui_port: int = 8080
    web_ui_username: str = "admin"
    web_ui_password: str = "admin"
    
    # Security level preset
    security_level: str = "medium"
    
    # Hot-reload settings (non-critical settings that can be reloaded)
    hot_reload_enabled: bool = True
    hot_reloadable_keys: List[str] = field(default_factory=lambda: [
        "log_level", "heartbeat_interval", "heartbeat_timeout",
        "command_timeout", "max_agents"
    ])


class ConfigManager:
    """
    Configuration manager for enhanced server
    
    Supports:
    - Loading from JSON/YAML files
    - Loading from environment variables
    - Configuration validation
    - Hot-reload for non-critical settings
    - Security level presets
    - Configuration templates
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to configuration file (JSON or YAML)
        """
        self.config_path = config_path
        self.config = ServerConfig()
        self._loaded = False
        
    def load_config(self, config_path: Optional[str] = None) -> ServerConfig:
        """
        Load configuration from file and environment variables
        
        Priority (highest to lowest):
        1. Environment variables
        2. Configuration file
        3. Default values
        
        Args:
            config_path: Path to configuration file (overrides init path)
            
        Returns:
            ServerConfig object
            
        Raises:
            ValueError: If configuration is invalid
            FileNotFoundError: If config file doesn't exist
        """
        if config_path:
            self.config_path = config_path
            
        # Load from file if provided
        if self.config_path:
            self._load_from_file(self.config_path)
            
        # Override with environment variables
        self._load_from_env()
        
        # Apply security level preset
        self._apply_security_preset()
        
        # Validate configuration
        self.validate_config()
        
        self._loaded = True
        logger.info("Configuration loaded successfully")
        return self.config
    
    def _load_from_file(self, config_path: str) -> None:
        """
        Load configuration from JSON or YAML file
        
        Args:
            config_path: Path to configuration file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Determine file format
        suffix = path.suffix.lower()
        
        try:
            with open(path, 'r') as f:
                if suffix == '.json':
                    data = json.load(f)
                elif suffix in ['.yaml', '.yml']:
                    if not YAML_AVAILABLE:
                        raise ValueError("YAML support not available. Install PyYAML: pip install pyyaml")
                    data = yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported configuration file format: {suffix}. Use .json, .yaml, or .yml")
            
            # Update config with loaded data
            self._update_config_from_dict(data)
            logger.info(f"Configuration loaded from file: {config_path}")
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables
        
        Environment variables should be prefixed with 'REMOTE_SYSTEM_'
        Example: REMOTE_SYSTEM_HOST, REMOTE_SYSTEM_PORT
        """
        prefix = "REMOTE_SYSTEM_"
        
        # Map environment variable names to config attributes
        env_mappings = {
            f"{prefix}HOST": "host",
            f"{prefix}PORT": ("port", int),
            f"{prefix}DB_PATH": "db_path",
            f"{prefix}DB_TYPE": "db_type",
            f"{prefix}USE_TLS": ("use_tls", lambda x: x.lower() in ['true', '1', 'yes']),
            f"{prefix}CERT_FILE": "cert_file",
            f"{prefix}KEY_FILE": "key_file",
            f"{prefix}SECRET_KEY": "secret_key",
            f"{prefix}TOKEN_EXPIRY": ("token_expiry", int),
            f"{prefix}MAX_AGENTS": ("max_agents", int),
            f"{prefix}COMMAND_TIMEOUT": ("command_timeout", int),
            f"{prefix}HEARTBEAT_INTERVAL": ("heartbeat_interval", int),
            f"{prefix}HEARTBEAT_TIMEOUT": ("heartbeat_timeout", int),
            f"{prefix}LOG_LEVEL": "log_level",
            f"{prefix}LOG_FILE": "log_file",
            f"{prefix}WEB_UI_ENABLED": ("web_ui_enabled", lambda x: x.lower() in ['true', '1', 'yes']),
            f"{prefix}WEB_UI_PORT": ("web_ui_port", int),
            f"{prefix}WEB_UI_USERNAME": "web_ui_username",
            f"{prefix}WEB_UI_PASSWORD": "web_ui_password",
            f"{prefix}SECURITY_LEVEL": "security_level",
        }
        
        for env_var, mapping in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                if isinstance(mapping, tuple):
                    attr_name, converter = mapping
                    try:
                        setattr(self.config, attr_name, converter(value))
                        logger.debug(f"Loaded {attr_name} from environment variable")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid value for {env_var}: {e}")
                else:
                    setattr(self.config, mapping, value)
                    logger.debug(f"Loaded {mapping} from environment variable")
    
    def _update_config_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update configuration from dictionary
        
        Args:
            data: Dictionary with configuration values
        """
        for key, value in data.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                logger.warning(f"Unknown configuration key: {key}")
    
    def _apply_security_preset(self) -> None:
        """
        Apply security level preset
        
        Security levels:
        - LOW: Minimal security, suitable for testing
        - MEDIUM: Balanced security (default)
        - HIGH: Maximum security, suitable for production
        
        Note: Only applies defaults if not explicitly configured
        """
        level = self.config.security_level.lower()
        
        if level == SecurityLevel.LOW.value:
            # Low security: short token expiry
            self.config.token_expiry = 3600  # 1 hour
            logger.warning("Security level set to LOW - not recommended for production")
            
        elif level == SecurityLevel.MEDIUM.value:
            # Medium security: standard token expiry
            self.config.token_expiry = 86400  # 24 hours
            logger.info("Security level set to MEDIUM")
            
        elif level == SecurityLevel.HIGH.value:
            # High security: short token expiry
            self.config.token_expiry = 3600  # 1 hour
            logger.info("Security level set to HIGH")
            
        else:
            logger.warning(f"Unknown security level: {level}. Using MEDIUM")
            self.config.security_level = SecurityLevel.MEDIUM.value
    
    def validate_config(self) -> None:
        """
        Validate configuration
        
        Raises:
            ValueError: If configuration is invalid with specific error message
        """
        errors = []
        
        # Validate network settings
        if not isinstance(self.config.port, int) or not (1 <= self.config.port <= 65535):
            errors.append(f"Invalid port number: {self.config.port}. Must be between 1 and 65535")
        
        if not self.config.host:
            errors.append("Host cannot be empty")
        
        # Validate TLS settings
        if self.config.use_tls:
            if self.config.cert_file and not Path(self.config.cert_file).exists():
                errors.append(f"TLS certificate file not found: {self.config.cert_file}")
            if self.config.key_file and not Path(self.config.key_file).exists():
                errors.append(f"TLS key file not found: {self.config.key_file}")
        
        # Validate database settings
        if self.config.db_type not in ['sqlite', 'postgresql']:
            errors.append(f"Invalid database type: {self.config.db_type}. Must be 'sqlite' or 'postgresql'")
        
        # Validate performance settings
        if self.config.max_agents < 1:
            errors.append(f"Invalid max_agents: {self.config.max_agents}. Must be at least 1")
        
        if self.config.command_timeout < 1:
            errors.append(f"Invalid command_timeout: {self.config.command_timeout}. Must be at least 1 second")
        
        if self.config.heartbeat_interval < 1:
            errors.append(f"Invalid heartbeat_interval: {self.config.heartbeat_interval}. Must be at least 1 second")
        
        if self.config.heartbeat_timeout < 1:
            errors.append(f"Invalid heartbeat_timeout: {self.config.heartbeat_timeout}. Must be at least 1 second")
        
        if self.config.token_expiry < 60:
            errors.append(f"Invalid token_expiry: {self.config.token_expiry}. Must be at least 60 seconds")
        
        # Validate logging settings
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.log_level.upper() not in valid_log_levels:
            errors.append(f"Invalid log_level: {self.config.log_level}. Must be one of {valid_log_levels}")
        
        # Validate web UI settings
        if self.config.web_ui_enabled:
            if not isinstance(self.config.web_ui_port, int) or not (1 <= self.config.web_ui_port <= 65535):
                errors.append(f"Invalid web_ui_port: {self.config.web_ui_port}. Must be between 1 and 65535")
            
            if not self.config.web_ui_username:
                errors.append("web_ui_username cannot be empty when web UI is enabled")
            
            if not self.config.web_ui_password:
                errors.append("web_ui_password cannot be empty when web UI is enabled")
        
        # Validate security level
        valid_security_levels = [level.value for level in SecurityLevel]
        if self.config.security_level.lower() not in valid_security_levels:
            errors.append(f"Invalid security_level: {self.config.security_level}. Must be one of {valid_security_levels}")
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_message)
    
    def reload_config(self, config_path: Optional[str] = None) -> ServerConfig:
        """
        Reload configuration (hot-reload for non-critical settings)
        
        Only reloads settings marked as hot-reloadable to avoid disrupting
        active connections.
        
        Args:
            config_path: Path to configuration file (optional)
            
        Returns:
            Updated ServerConfig object
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.hot_reload_enabled:
            logger.warning("Hot-reload is disabled")
            return self.config
        
        # Save current config
        old_config = asdict(self.config)
        
        # Load new config
        try:
            self.load_config(config_path)
            
            # Restore non-reloadable settings
            for key in old_config:
                if key not in self.config.hot_reloadable_keys:
                    setattr(self.config, key, old_config[key])
            
            logger.info("Configuration reloaded successfully (hot-reload)")
            return self.config
            
        except Exception as e:
            # Restore old config on error
            self._update_config_from_dict(old_config)
            logger.error(f"Failed to reload configuration: {e}")
            raise
    
    def save_config(self, output_path: str, format: str = 'json') -> None:
        """
        Save current configuration to file
        
        Args:
            output_path: Path to save configuration
            format: File format ('json' or 'yaml')
            
        Raises:
            ValueError: If format is invalid
        """
        if format not in ['json', 'yaml']:
            raise ValueError(f"Invalid format: {format}. Must be 'json' or 'yaml'")
        
        if format == 'yaml' and not YAML_AVAILABLE:
            raise ValueError("YAML support not available. Install PyYAML: pip install pyyaml")
        
        config_dict = asdict(self.config)
        
        with open(output_path, 'w') as f:
            if format == 'json':
                json.dump(config_dict, f, indent=2)
            else:
                yaml.dump(config_dict, f, default_flow_style=False)
        
        logger.info(f"Configuration saved to: {output_path}")
    
    def create_template(self, template_name: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create configuration template for batch builds
        
        Args:
            template_name: Name of the template
            overrides: Dictionary of values to override in default config
            
        Returns:
            Configuration dictionary
        """
        template = asdict(self.config)
        template['template_name'] = template_name
        template.update(overrides)
        
        logger.info(f"Created configuration template: {template_name}")
        return template
    
    def get_config(self) -> ServerConfig:
        """
        Get current configuration
        
        Returns:
            ServerConfig object
        """
        return self.config
