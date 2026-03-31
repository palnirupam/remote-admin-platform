"""
Configuration Manager for Enhanced Agent

This module provides flexible configuration management for the enhanced agent,
supporting loading from JSON/YAML files, environment variables, validation,
hot-reload, and security level presets.

Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from urllib.parse import urlparse

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
class AgentConfig:
    """Agent configuration data class"""
    # Server connection settings
    server_address: Optional[str] = None  # New: unified address format
    server_ip: str = "127.0.0.1"  # Deprecated: kept for backward compatibility
    server_port: int = 9999  # Deprecated: kept for backward compatibility
    
    # Authentication settings
    token: Optional[str] = None
    secret_key: Optional[str] = None
    
    # Security settings
    use_tls: bool = True
    cert_pinning_enabled: bool = True
    cert_fingerprint: Optional[str] = None
    
    # Plugin settings
    plugin_dir: str = "./plugins"
    enabled_plugins: List[str] = field(default_factory=lambda: [])
    disabled_plugins: List[str] = field(default_factory=lambda: [])
    
    # Persistence settings
    persistence_enabled: bool = False
    persistence_methods: List[str] = field(default_factory=lambda: ["auto"])
    
    # Reconnection settings
    reconnect_enabled: bool = True
    reconnect_delay_base: int = 5
    reconnect_delay_max: int = 60
    reconnect_attempts: int = -1  # -1 = infinite
    
    # Performance settings
    command_timeout: int = 300
    heartbeat_timeout: int = 10
    buffer_size: int = 4096
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Security level preset
    security_level: str = "medium"
    
    # Hot-reload settings (non-critical settings that can be reloaded)
    hot_reload_enabled: bool = True
    hot_reloadable_keys: List[str] = field(default_factory=lambda: [
        "log_level", "command_timeout", "heartbeat_timeout",
        "reconnect_delay_base", "reconnect_delay_max"
    ])


class ConfigManager:
    """
    Configuration manager for enhanced agent
    
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
        self.config = AgentConfig()
        self._loaded = False
    
    @staticmethod
    def _parse_server_address(address: str) -> Tuple[str, int]:
        """
        Parse server address in various formats and extract host and port
        
        Supports:
        - IP:PORT (e.g., "192.168.1.100:9999")
        - Domain:PORT (e.g., "myserver.ddns.net:9999")
        - Ngrok URL (e.g., "https://abc123.ngrok.io")
        - HTTP/HTTPS URL with port (e.g., "https://example.com:9999")
        
        Args:
            address: Server address in any supported format
        
        Returns:
            Tuple of (host, port)
        
        Raises:
            ValueError: If address format is invalid
        
        Requirements: 14.2, 14.3, 14.4, 14.5
        """
        # Try parsing as URL first (handles Ngrok, HTTPS, HTTP)
        if address.startswith(('http://', 'https://')):
            try:
                parsed = urlparse(address)
                host = parsed.hostname
                port = parsed.port
                
                if not host:
                    raise ValueError(f"Invalid URL: no hostname found in {address}")
                
                # Default ports for HTTP/HTTPS
                if port is None:
                    if parsed.scheme == 'https':
                        port = 443
                    elif parsed.scheme == 'http':
                        port = 80
                    else:
                        raise ValueError(f"Unknown scheme: {parsed.scheme}")
                
                logger.debug(f"Parsed URL: {address} -> {host}:{port}")
                return host, port
            except Exception as e:
                raise ValueError(f"Invalid URL format: {address}. Error: {e}")
        
        # Try parsing as IP:PORT or Domain:PORT
        if ':' in address:
            parts = address.rsplit(':', 1)  # Split from right to handle IPv6
            if len(parts) == 2:
                host, port_str = parts
                try:
                    port = int(port_str)
                    if port <= 0 or port > 65535:
                        raise ValueError(f"Port must be between 1 and 65535, got {port}")
                    
                    # Validate host (IP or domain)
                    if not host:
                        raise ValueError("Host cannot be empty")
                    
                    logger.debug(f"Parsed address: {address} -> {host}:{port}")
                    return host, port
                except ValueError as e:
                    raise ValueError(f"Invalid port in address {address}: {e}")
        
        # If no format matches, raise error
        raise ValueError(
            f"Invalid server address format: {address}. "
            "Supported formats: IP:PORT, Domain:PORT, https://domain, https://domain:port"
        )
        
    def load_config(self, config_path: Optional[str] = None) -> AgentConfig:
        """
        Load configuration from file and environment variables
        
        Priority (highest to lowest):
        1. Environment variables
        2. Configuration file
        3. Default values
        
        Args:
            config_path: Path to configuration file (overrides init path)
            
        Returns:
            AgentConfig object
            
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
        
        Environment variables should be prefixed with 'REMOTE_AGENT_'
        Example: REMOTE_AGENT_SERVER_IP, REMOTE_AGENT_SERVER_PORT
        """
        prefix = "REMOTE_AGENT_"
        
        # Map environment variable names to config attributes
        env_mappings = {
            f"{prefix}SERVER_ADDRESS": "server_address",  # New unified format
            f"{prefix}SERVER_IP": "server_ip",  # Legacy
            f"{prefix}SERVER_PORT": ("server_port", int),  # Legacy
            f"{prefix}TOKEN": "token",
            f"{prefix}SECRET_KEY": "secret_key",
            f"{prefix}USE_TLS": ("use_tls", lambda x: x.lower() in ['true', '1', 'yes']),
            f"{prefix}CERT_PINNING_ENABLED": ("cert_pinning_enabled", lambda x: x.lower() in ['true', '1', 'yes']),
            f"{prefix}CERT_FINGERPRINT": "cert_fingerprint",
            f"{prefix}PLUGIN_DIR": "plugin_dir",
            f"{prefix}PERSISTENCE_ENABLED": ("persistence_enabled", lambda x: x.lower() in ['true', '1', 'yes']),
            f"{prefix}RECONNECT_ENABLED": ("reconnect_enabled", lambda x: x.lower() in ['true', '1', 'yes']),
            f"{prefix}RECONNECT_DELAY_BASE": ("reconnect_delay_base", int),
            f"{prefix}RECONNECT_DELAY_MAX": ("reconnect_delay_max", int),
            f"{prefix}RECONNECT_ATTEMPTS": ("reconnect_attempts", int),
            f"{prefix}COMMAND_TIMEOUT": ("command_timeout", int),
            f"{prefix}HEARTBEAT_TIMEOUT": ("heartbeat_timeout", int),
            f"{prefix}BUFFER_SIZE": ("buffer_size", int),
            f"{prefix}LOG_LEVEL": "log_level",
            f"{prefix}LOG_FILE": "log_file",
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
        
        # Handle list-type environment variables
        enabled_plugins = os.environ.get(f"{prefix}ENABLED_PLUGINS")
        if enabled_plugins:
            self.config.enabled_plugins = [p.strip() for p in enabled_plugins.split(',')]
        
        disabled_plugins = os.environ.get(f"{prefix}DISABLED_PLUGINS")
        if disabled_plugins:
            self.config.disabled_plugins = [p.strip() for p in disabled_plugins.split(',')]
        
        persistence_methods = os.environ.get(f"{prefix}PERSISTENCE_METHODS")
        if persistence_methods:
            self.config.persistence_methods = [m.strip() for m in persistence_methods.split(',')]
    
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
            # Low security preset
            logger.warning("Security level set to LOW - not recommended for production")
            
        elif level == SecurityLevel.MEDIUM.value:
            # Medium security preset
            logger.info("Security level set to MEDIUM")
            
        elif level == SecurityLevel.HIGH.value:
            # High security preset
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
        
        # Validate server connection settings
        # Support both new server_address and legacy server_ip/server_port
        if self.config.server_address:
            # New format: validate and parse server_address
            try:
                host, port = self._parse_server_address(self.config.server_address)
                # Update server_ip and server_port for backward compatibility
                self.config.server_ip = host
                self.config.server_port = port
                logger.info(f"Using server_address: {self.config.server_address} -> {host}:{port}")
            except ValueError as e:
                errors.append(str(e))
        else:
            # Legacy format: validate server_ip and server_port
            if not self.config.server_ip:
                errors.append("server_ip cannot be empty (or provide server_address)")
            
            if not isinstance(self.config.server_port, int) or not (1 <= self.config.server_port <= 65535):
                errors.append(f"Invalid server_port: {self.config.server_port}. Must be between 1 and 65535")
        
        # Validate TLS settings
        if self.config.use_tls and self.config.cert_pinning_enabled:
            if not self.config.cert_fingerprint:
                logger.warning("Certificate pinning enabled but no fingerprint provided. Pinning will be skipped.")
        
        # Validate plugin settings
        if self.config.plugin_dir and not Path(self.config.plugin_dir).exists():
            logger.warning(f"Plugin directory does not exist: {self.config.plugin_dir}")
        
        # Validate persistence settings
        if self.config.persistence_enabled:
            valid_methods = ['auto', 'registry', 'startup', 'scheduled_task', 'cron', 'systemd', 'launchd']
            for method in self.config.persistence_methods:
                if method not in valid_methods:
                    errors.append(f"Invalid persistence method: {method}. Must be one of {valid_methods}")
        
        # Validate reconnection settings
        if self.config.reconnect_delay_base < 1:
            errors.append(f"Invalid reconnect_delay_base: {self.config.reconnect_delay_base}. Must be at least 1 second")
        
        if self.config.reconnect_delay_max < self.config.reconnect_delay_base:
            errors.append(f"reconnect_delay_max ({self.config.reconnect_delay_max}) must be >= reconnect_delay_base ({self.config.reconnect_delay_base})")
        
        if self.config.reconnect_attempts < -1:
            errors.append(f"Invalid reconnect_attempts: {self.config.reconnect_attempts}. Must be -1 (infinite) or >= 0")
        
        # Validate performance settings
        if self.config.command_timeout < 1:
            errors.append(f"Invalid command_timeout: {self.config.command_timeout}. Must be at least 1 second")
        
        if self.config.heartbeat_timeout < 1:
            errors.append(f"Invalid heartbeat_timeout: {self.config.heartbeat_timeout}. Must be at least 1 second")
        
        if self.config.buffer_size < 1024:
            errors.append(f"Invalid buffer_size: {self.config.buffer_size}. Must be at least 1024 bytes")
        
        # Validate logging settings
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.log_level.upper() not in valid_log_levels:
            errors.append(f"Invalid log_level: {self.config.log_level}. Must be one of {valid_log_levels}")
        
        # Validate security level
        valid_security_levels = [level.value for level in SecurityLevel]
        if self.config.security_level.lower() not in valid_security_levels:
            errors.append(f"Invalid security_level: {self.config.security_level}. Must be one of {valid_security_levels}")
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_message)
    
    def reload_config(self, config_path: Optional[str] = None) -> AgentConfig:
        """
        Reload configuration (hot-reload for non-critical settings)
        
        Only reloads settings marked as hot-reloadable to avoid disrupting
        active connections.
        
        Args:
            config_path: Path to configuration file (optional)
            
        Returns:
            Updated AgentConfig object
            
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
    
    def get_config(self) -> AgentConfig:
        """
        Get current configuration
        
        Returns:
            AgentConfig object
        """
        return self.config
