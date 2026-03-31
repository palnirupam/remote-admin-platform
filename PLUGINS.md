# Plugin Development Guide

This guide explains how to create custom plugins for the Remote System Enhancement platform.

## Table of Contents

- [Plugin Architecture](#plugin-architecture)
- [Creating a Plugin](#creating-a-plugin)
- [Plugin Interface](#plugin-interface)
- [Example Plugins](#example-plugins)
- [Testing Plugins](#testing-plugins)
- [Best Practices](#best-practices)
- [Deployment](#deployment)

## Plugin Architecture

Plugins extend agent capabilities by implementing specific functionality as modular components. The Plugin Manager loads plugins dynamically and routes commands to the appropriate plugin based on the plugin name.

### Plugin Lifecycle

1. **Discovery**: Plugin Manager scans plugin directory
2. **Loading**: Plugin class is imported and instantiated
3. **Registration**: Plugin registers with Plugin Manager
4. **Execution**: Commands are routed to plugin's execute() method
5. **Cleanup**: Plugin resources are released on agent shutdown

### Plugin Directory Structure

```
remote_system/plugins/
├── __init__.py
├── file_transfer_plugin.py
├── screenshot_plugin.py
├── keylogger_plugin.py
├── custom_plugin.py
└── my_plugin/
    ├── __init__.py
    ├── plugin.py
    └── helpers.py
```

## Creating a Plugin

### Step 1: Create Plugin File

Create a new Python file in `remote_system/plugins/`:

```python
# remote_system/plugins/my_plugin.py

from remote_system.enhanced_agent.plugin_manager import Plugin, PluginResult

class MyPlugin(Plugin):
    """
    Description of what your plugin does.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "my_plugin"
        # Initialize plugin state
    
    def get_name(self) -> str:
        """Return the plugin name."""
        return self.name
    
    def get_required_arguments(self) -> list:
        """Return list of required argument names."""
        return []
    
    def execute(self, action: str, args: dict) -> PluginResult:
        """
        Execute plugin action with given arguments.
        
        Args:
            action: Action to perform
            args: Dictionary of arguments
            
        Returns:
            PluginResult with success status and data
        """
        try:
            if action == "my_action":
                return self._my_action(args)
            else:
                return PluginResult(
                    success=False,
                    data=None,
                    error=f"Unknown action: {action}"
                )
        except Exception as e:
            return PluginResult(
                success=False,
                data=None,
                error=str(e)
            )
    
    def _my_action(self, args: dict) -> PluginResult:
        """Implement your action logic here."""
        # Your implementation
        result_data = {"message": "Action completed"}
        
        return PluginResult(
            success=True,
            data=result_data,
            error=None,
            metadata={"execution_time": 0.5}
        )
```

### Step 2: Register Plugin

Plugins are automatically discovered if placed in the plugins directory. For manual registration:

```python
from remote_system.enhanced_agent.plugin_manager import PluginManager
from my_plugin import MyPlugin

plugin_manager = PluginManager(plugin_dir="./plugins")
plugin_manager.register_plugin(MyPlugin())
```

## Plugin Interface

### Base Plugin Class

```python
class Plugin:
    """Base class for all plugins."""
    
    def get_name(self) -> str:
        """
        Return the unique plugin name.
        Used for command routing.
        """
        raise NotImplementedError
    
    def get_required_arguments(self) -> list:
        """
        Return list of required argument names.
        Plugin Manager validates these before execution.
        """
        return []
    
    def execute(self, action: str, args: dict) -> PluginResult:
        """
        Execute plugin action.
        
        Args:
            action: Action name to perform
            args: Dictionary of arguments
            
        Returns:
            PluginResult object
        """
        raise NotImplementedError
```

### PluginResult Class

```python
class PluginResult:
    """Result of plugin execution."""
    
    def __init__(self, success: bool, data: any, error: str = None, metadata: dict = None):
        self.success = success  # True if execution succeeded
        self.data = data        # Result data (any type)
        self.error = error      # Error message if failed
        self.metadata = metadata or {}  # Additional metadata
```

## Example Plugins

### Example 1: System Information Plugin

```python
import platform
import psutil
from remote_system.enhanced_agent.plugin_manager import Plugin, PluginResult

class SystemInfoPlugin(Plugin):
    """Collect detailed system information."""
    
    def get_name(self) -> str:
        return "systeminfo"
    
    def get_required_arguments(self) -> list:
        return []
    
    def execute(self, action: str, args: dict) -> PluginResult:
        try:
            if action == "get_info":
                return self._get_system_info()
            elif action == "get_processes":
                return self._get_processes()
            else:
                return PluginResult(False, None, f"Unknown action: {action}")
        except Exception as e:
            return PluginResult(False, None, str(e))
    
    def _get_system_info(self) -> PluginResult:
        """Collect comprehensive system information."""
        info = {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": {
                partition.mountpoint: {
                    "total": psutil.disk_usage(partition.mountpoint).total,
                    "used": psutil.disk_usage(partition.mountpoint).used,
                    "free": psutil.disk_usage(partition.mountpoint).free
                }
                for partition in psutil.disk_partitions()
            }
        }
        
        return PluginResult(True, info)
    
    def _get_processes(self) -> PluginResult:
        """Get list of running processes."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return PluginResult(True, processes)
```

### Example 2: Network Scanner Plugin

```python
import socket
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from remote_system.enhanced_agent.plugin_manager import Plugin, PluginResult

class NetworkScannerPlugin(Plugin):
    """Scan network for active hosts."""
    
    def get_name(self) -> str:
        return "network_scanner"
    
    def get_required_arguments(self) -> list:
        return ["network"]  # e.g., "192.168.1.0/24"
    
    def execute(self, action: str, args: dict) -> PluginResult:
        try:
            if action == "scan":
                return self._scan_network(args)
            elif action == "port_scan":
                return self._port_scan(args)
            else:
                return PluginResult(False, None, f"Unknown action: {action}")
        except Exception as e:
            return PluginResult(False, None, str(e))
    
    def _scan_network(self, args: dict) -> PluginResult:
        """Scan network for active hosts."""
        network = args.get("network")
        timeout = args.get("timeout", 1)
        
        active_hosts = []
        network_obj = ipaddress.ip_network(network, strict=False)
        
        def check_host(ip):
            try:
                socket.setdefaulttimeout(timeout)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((str(ip), 80))
                return str(ip)
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            results = executor.map(check_host, network_obj.hosts())
            active_hosts = [ip for ip in results if ip]
        
        return PluginResult(True, {"active_hosts": active_hosts, "count": len(active_hosts)})
    
    def _port_scan(self, args: dict) -> PluginResult:
        """Scan ports on a specific host."""
        host = args.get("host")
        ports = args.get("ports", range(1, 1024))
        timeout = args.get("timeout", 1)
        
        open_ports = []
        
        def check_port(port):
            try:
                socket.setdefaulttimeout(timeout)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((host, port))
                sock.close()
                return port if result == 0 else None
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=100) as executor:
            results = executor.map(check_port, ports)
            open_ports = [port for port in results if port]
        
        return PluginResult(True, {"host": host, "open_ports": open_ports})
```

### Example 3: Registry Editor Plugin (Windows)

```python
import winreg
from remote_system.enhanced_agent.plugin_manager import Plugin, PluginResult

class RegistryPlugin(Plugin):
    """Windows Registry operations."""
    
    def get_name(self) -> str:
        return "registry"
    
    def get_required_arguments(self) -> list:
        return ["key"]
    
    def execute(self, action: str, args: dict) -> PluginResult:
        try:
            if action == "read":
                return self._read_key(args)
            elif action == "write":
                return self._write_key(args)
            elif action == "delete":
                return self._delete_key(args)
            else:
                return PluginResult(False, None, f"Unknown action: {action}")
        except Exception as e:
            return PluginResult(False, None, str(e))
    
    def _read_key(self, args: dict) -> PluginResult:
        """Read registry key value."""
        key_path = args.get("key")
        value_name = args.get("value")
        
        # Parse key path (e.g., "HKEY_CURRENT_USER\\Software\\MyApp")
        root, subkey = self._parse_key_path(key_path)
        
        try:
            key = winreg.OpenKey(root, subkey, 0, winreg.KEY_READ)
            value, value_type = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            
            return PluginResult(True, {"value": value, "type": value_type})
        except FileNotFoundError:
            return PluginResult(False, None, "Key or value not found")
    
    def _write_key(self, args: dict) -> PluginResult:
        """Write registry key value."""
        key_path = args.get("key")
        value_name = args.get("value")
        value_data = args.get("data")
        value_type = args.get("type", winreg.REG_SZ)
        
        root, subkey = self._parse_key_path(key_path)
        
        try:
            key = winreg.CreateKey(root, subkey)
            winreg.SetValueEx(key, value_name, 0, value_type, value_data)
            winreg.CloseKey(key)
            
            return PluginResult(True, {"message": "Value written successfully"})
        except Exception as e:
            return PluginResult(False, None, str(e))
    
    def _delete_key(self, args: dict) -> PluginResult:
        """Delete registry key."""
        key_path = args.get("key")
        value_name = args.get("value", None)
        
        root, subkey = self._parse_key_path(key_path)
        
        try:
            if value_name:
                # Delete value
                key = winreg.OpenKey(root, subkey, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, value_name)
                winreg.CloseKey(key)
            else:
                # Delete key
                winreg.DeleteKey(root, subkey)
            
            return PluginResult(True, {"message": "Deleted successfully"})
        except Exception as e:
            return PluginResult(False, None, str(e))
    
    def _parse_key_path(self, key_path: str):
        """Parse registry key path into root and subkey."""
        parts = key_path.split("\\", 1)
        root_name = parts[0]
        subkey = parts[1] if len(parts) > 1 else ""
        
        root_map = {
            "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_USERS": winreg.HKEY_USERS,
            "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
        }
        
        return root_map.get(root_name, winreg.HKEY_CURRENT_USER), subkey
```

## Testing Plugins

### Unit Testing

Create test file `tests/test_my_plugin.py`:

```python
import unittest
from remote_system.plugins.my_plugin import MyPlugin

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = MyPlugin()
    
    def test_plugin_name(self):
        self.assertEqual(self.plugin.get_name(), "my_plugin")
    
    def test_my_action_success(self):
        result = self.plugin.execute("my_action", {})
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
    
    def test_unknown_action(self):
        result = self.plugin.execute("unknown", {})
        self.assertFalse(result.success)
        self.assertIn("Unknown action", result.error)
    
    def test_required_arguments(self):
        # Test with missing required arguments
        required_args = self.plugin.get_required_arguments()
        if required_args:
            result = self.plugin.execute("my_action", {})
            # Plugin Manager would reject this before execution

if __name__ == "__main__":
    unittest.main()
```

### Integration Testing

Test plugin with Plugin Manager:

```python
from remote_system.enhanced_agent.plugin_manager import PluginManager
from remote_system.plugins.my_plugin import MyPlugin

# Initialize plugin manager
plugin_manager = PluginManager(plugin_dir="./plugins")

# Register plugin
plugin_manager.register_plugin(MyPlugin())

# Execute plugin
result = plugin_manager.execute_plugin("my_plugin", {
    "action": "my_action",
    "args": {}
})

print(f"Success: {result.success}")
print(f"Data: {result.data}")
```

## Best Practices

### 1. Error Handling

Always wrap plugin logic in try-except blocks:

```python
def execute(self, action: str, args: dict) -> PluginResult:
    try:
        # Plugin logic
        return PluginResult(True, data)
    except ValueError as e:
        return PluginResult(False, None, f"Invalid argument: {e}")
    except Exception as e:
        return PluginResult(False, None, f"Unexpected error: {e}")
```

### 2. Argument Validation

Validate arguments before processing:

```python
def _my_action(self, args: dict) -> PluginResult:
    # Validate required arguments
    if "required_param" not in args:
        return PluginResult(False, None, "Missing required_param")
    
    # Validate argument types
    if not isinstance(args["required_param"], str):
        return PluginResult(False, None, "required_param must be string")
    
    # Validate argument values
    if args["required_param"] not in ["option1", "option2"]:
        return PluginResult(False, None, "Invalid required_param value")
    
    # Process...
```

### 3. Timeout Handling

For long-running operations, respect timeouts:

```python
import signal

def _long_operation(self, args: dict) -> PluginResult:
    timeout = args.get("timeout", 300)
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Operation timeout")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        # Long operation
        result = perform_operation()
        signal.alarm(0)  # Cancel alarm
        return PluginResult(True, result)
    except TimeoutError:
        return PluginResult(False, None, "Operation timeout")
```

### 4. Resource Cleanup

Ensure resources are properly released:

```python
def _file_operation(self, args: dict) -> PluginResult:
    file_handle = None
    try:
        file_handle = open(args["path"], "r")
        data = file_handle.read()
        return PluginResult(True, data)
    except Exception as e:
        return PluginResult(False, None, str(e))
    finally:
        if file_handle:
            file_handle.close()
```

### 5. Platform Compatibility

Check platform before executing platform-specific code:

```python
import platform

def execute(self, action: str, args: dict) -> PluginResult:
    if platform.system() != "Windows":
        return PluginResult(False, None, "This plugin requires Windows")
    
    # Windows-specific code
```

### 6. Logging

Use logging for debugging:

```python
import logging

logger = logging.getLogger(__name__)

def execute(self, action: str, args: dict) -> PluginResult:
    logger.info(f"Executing action: {action}")
    logger.debug(f"Arguments: {args}")
    
    try:
        result = self._perform_action(action, args)
        logger.info(f"Action completed successfully")
        return result
    except Exception as e:
        logger.error(f"Action failed: {e}", exc_info=True)
        return PluginResult(False, None, str(e))
```

### 7. Documentation

Document your plugin thoroughly:

```python
class MyPlugin(Plugin):
    """
    Brief description of plugin functionality.
    
    Actions:
        action1: Description of action1
            Required args: arg1 (type), arg2 (type)
            Optional args: arg3 (type, default: value)
            Returns: Description of return data
        
        action2: Description of action2
            ...
    
    Example:
        >>> plugin = MyPlugin()
        >>> result = plugin.execute("action1", {"arg1": "value"})
        >>> print(result.data)
    """
```

## Deployment

### Installing Plugin on Agent

1. Copy plugin file to agent's plugin directory
2. Restart agent or use hot-reload if supported
3. Verify plugin is loaded:

```python
# Check available plugins
result = plugin_manager.list_plugins()
print(result)  # Should include your plugin name
```

### Distributing Plugins

For distribution with agents:

1. Add plugin to `remote_system/plugins/` directory
2. Rebuild agent executable with builder
3. Plugin will be included in the agent package

For runtime distribution:

1. Package plugin as Python module
2. Transfer to agent machine
3. Place in agent's plugin directory
4. Agent will discover on next restart

## Advanced Topics

### Plugin Dependencies

If your plugin requires external libraries:

```python
class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        try:
            import required_library
            self.library = required_library
        except ImportError:
            raise ImportError("This plugin requires 'required_library'. Install with: pip install required_library")
```

### Plugin Configuration

Support plugin-specific configuration:

```python
class MyPlugin(Plugin):
    def __init__(self, config_path=None):
        super().__init__()
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path):
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self):
        return {
            "option1": "default_value",
            "option2": 100
        }
```

### Async Operations

For async operations (requires async support in Plugin Manager):

```python
import asyncio

class MyAsyncPlugin(Plugin):
    async def execute_async(self, action: str, args: dict) -> PluginResult:
        try:
            if action == "async_action":
                result = await self._async_operation(args)
                return PluginResult(True, result)
        except Exception as e:
            return PluginResult(False, None, str(e))
    
    async def _async_operation(self, args: dict):
        await asyncio.sleep(1)
        return {"status": "completed"}
```

## Troubleshooting

### Plugin Not Loading

- Check plugin file is in correct directory
- Verify plugin class inherits from Plugin base class
- Check for syntax errors in plugin code
- Review agent logs for import errors

### Plugin Execution Fails

- Verify required arguments are provided
- Check argument types and values
- Review error messages in PluginResult
- Add logging to plugin for debugging

### Performance Issues

- Profile plugin execution time
- Optimize database queries
- Use caching for repeated operations
- Consider async operations for I/O-bound tasks

## Support

For plugin development questions:
- Review existing plugins in `remote_system/plugins/`
- Check agent logs for detailed error messages
- Consult ARCHITECTURE.md for system design
- Open an issue on the project repository
