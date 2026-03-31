"""
Demonstration of Configuration Manager Usage

This script demonstrates how to use the configuration manager for both
server and agent components.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from remote_system.enhanced_server.config_manager import ConfigManager as ServerConfigManager
from remote_system.enhanced_agent.config_manager import ConfigManager as AgentConfigManager


def demo_server_config():
    """Demonstrate server configuration management"""
    print("=" * 60)
    print("SERVER CONFIGURATION DEMO")
    print("=" * 60)
    
    # Example 1: Load from default values
    print("\n1. Loading default configuration:")
    config_manager = ServerConfigManager()
    config = config_manager.load_config()
    print(f"   Host: {config.host}")
    print(f"   Port: {config.port}")
    print(f"   TLS Enabled: {config.use_tls}")
    print(f"   Security Level: {config.security_level}")
    
    # Example 2: Load from JSON file
    print("\n2. Loading from JSON file:")
    json_path = Path(__file__).parent / "server_config.json"
    if json_path.exists():
        config_manager = ServerConfigManager(str(json_path))
        config = config_manager.load_config()
        print(f"   Host: {config.host}")
        print(f"   Port: {config.port}")
        print(f"   Max Agents: {config.max_agents}")
    else:
        print("   (server_config.json not found)")
    
    # Example 3: Load from environment variables
    print("\n3. Loading from environment variables:")
    os.environ["REMOTE_SYSTEM_HOST"] = "env.example.com"
    os.environ["REMOTE_SYSTEM_PORT"] = "7777"
    os.environ["REMOTE_SYSTEM_LOG_LEVEL"] = "DEBUG"
    
    config_manager = ServerConfigManager()
    config = config_manager.load_config()
    print(f"   Host: {config.host}")
    print(f"   Port: {config.port}")
    print(f"   Log Level: {config.log_level}")
    
    # Clean up environment
    del os.environ["REMOTE_SYSTEM_HOST"]
    del os.environ["REMOTE_SYSTEM_PORT"]
    del os.environ["REMOTE_SYSTEM_LOG_LEVEL"]
    
    # Example 4: Validation
    print("\n4. Configuration validation:")
    config_manager = ServerConfigManager()
    config_manager.config.port = 99999  # Invalid port
    try:
        config_manager.validate_config()
        print("   Validation passed")
    except ValueError as e:
        print(f"   Validation failed (expected):")
        print(f"   {str(e)[:100]}...")
    
    # Example 5: Security level presets
    print("\n5. Security level presets:")
    for level in ["low", "medium", "high"]:
        config_manager = ServerConfigManager()
        config_manager.config.security_level = level
        config_manager._apply_security_preset()
        print(f"   {level.upper()}: token_expiry={config_manager.config.token_expiry}s")
    
    # Example 6: Create template
    print("\n6. Creating configuration template:")
    config_manager = ServerConfigManager()
    config_manager.load_config()
    template = config_manager.create_template(
        "production_template",
        {"host": "prod.example.com", "max_agents": 5000}
    )
    print(f"   Template: {template['template_name']}")
    print(f"   Host: {template['host']}")
    print(f"   Max Agents: {template['max_agents']}")


def demo_agent_config():
    """Demonstrate agent configuration management"""
    print("\n" + "=" * 60)
    print("AGENT CONFIGURATION DEMO")
    print("=" * 60)
    
    # Example 1: Load from default values
    print("\n1. Loading default configuration:")
    config_manager = AgentConfigManager()
    config = config_manager.load_config()
    print(f"   Server IP: {config.server_ip}")
    print(f"   Server Port: {config.server_port}")
    print(f"   TLS Enabled: {config.use_tls}")
    print(f"   Reconnect Enabled: {config.reconnect_enabled}")
    
    # Example 2: Load from JSON file
    print("\n2. Loading from JSON file:")
    json_path = Path(__file__).parent / "agent_config.json"
    if json_path.exists():
        config_manager = AgentConfigManager(str(json_path))
        config = config_manager.load_config()
        print(f"   Server IP: {config.server_ip}")
        print(f"   Server Port: {config.server_port}")
        print(f"   Persistence Enabled: {config.persistence_enabled}")
    else:
        print("   (agent_config.json not found)")
    
    # Example 3: Load from environment variables
    print("\n3. Loading from environment variables:")
    os.environ["REMOTE_AGENT_SERVER_IP"] = "192.168.1.100"
    os.environ["REMOTE_AGENT_SERVER_PORT"] = "8888"
    os.environ["REMOTE_AGENT_PERSISTENCE_ENABLED"] = "true"
    
    config_manager = AgentConfigManager()
    config = config_manager.load_config()
    print(f"   Server IP: {config.server_ip}")
    print(f"   Server Port: {config.server_port}")
    print(f"   Persistence Enabled: {config.persistence_enabled}")
    
    # Clean up environment
    del os.environ["REMOTE_AGENT_SERVER_IP"]
    del os.environ["REMOTE_AGENT_SERVER_PORT"]
    del os.environ["REMOTE_AGENT_PERSISTENCE_ENABLED"]
    
    # Example 4: Persistence methods configuration
    print("\n4. Persistence methods configuration:")
    config_manager = AgentConfigManager()
    config_manager.config.persistence_enabled = True
    config_manager.config.persistence_methods = ["registry", "startup"]
    config_manager.validate_config()
    print(f"   Methods: {', '.join(config_manager.config.persistence_methods)}")
    
    # Example 5: Plugin configuration
    print("\n5. Plugin configuration:")
    config_manager = AgentConfigManager()
    config_manager.config.enabled_plugins = ["file_transfer", "screenshot"]
    config_manager.config.disabled_plugins = ["keylogger"]
    print(f"   Enabled: {', '.join(config_manager.config.enabled_plugins)}")
    print(f"   Disabled: {', '.join(config_manager.config.disabled_plugins)}")


def demo_hot_reload():
    """Demonstrate hot-reload functionality"""
    print("\n" + "=" * 60)
    print("HOT-RELOAD DEMO")
    print("=" * 60)
    
    print("\n1. Server hot-reload:")
    config_manager = ServerConfigManager()
    config = config_manager.load_config()
    print(f"   Initial log_level: {config.log_level}")
    
    # Simulate config change
    config_manager.config.log_level = "DEBUG"
    print(f"   Updated log_level: {config_manager.config.log_level}")
    print(f"   Hot-reloadable keys: {', '.join(config.hot_reloadable_keys[:3])}...")
    
    print("\n2. Agent hot-reload:")
    config_manager = AgentConfigManager()
    config = config_manager.load_config()
    print(f"   Initial command_timeout: {config.command_timeout}")
    
    # Simulate config change
    config_manager.config.command_timeout = 600
    print(f"   Updated command_timeout: {config_manager.config.command_timeout}")
    print(f"   Hot-reloadable keys: {', '.join(config.hot_reloadable_keys[:3])}...")


if __name__ == "__main__":
    try:
        demo_server_config()
        demo_agent_config()
        demo_hot_reload()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
