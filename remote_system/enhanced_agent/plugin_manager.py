"""
Plugin Manager for Enhanced Agent

Manages plugin loading, execution, and isolation for the enhanced agent.
Provides a plugin architecture that allows modular capabilities.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7
"""

import os
import importlib.util
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PluginResult:
    """
    Result of plugin execution
    
    Attributes:
        success: Whether the plugin executed successfully
        data: The result data from the plugin
        error: Error message if execution failed
        metadata: Additional metadata about the execution
    """
    success: bool
    data: Any
    error: Optional[str]
    metadata: Dict[str, Any]


class Plugin(ABC):
    """
    Base class for all plugins
    
    All plugins must inherit from this class and implement the required methods.
    """
    
    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Execute the plugin with the given arguments
        
        Args:
            args: Dictionary of arguments for the plugin
            
        Returns:
            The result of the plugin execution
            
        Raises:
            Exception: If execution fails
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the plugin
        
        Returns:
            The plugin name as a string
        """
        pass
    
    @abstractmethod
    def get_required_arguments(self) -> List[str]:
        """
        Get the list of required argument names
        
        Returns:
            List of required argument names
        """
        pass


class PluginManager:
    """
    Manages plugin loading and execution for the enhanced agent
    
    Responsibilities:
    - Discover and load plugins from plugin directory (Requirement 17.1)
    - Route commands to appropriate plugins (Requirement 17.2)
    - Isolate plugin failures (Requirement 17.3)
    - Enforce plugin execution timeouts (Requirement 17.4)
    - Support hot-reloading (Requirement 17.6)
    - Validate required arguments (Requirement 17.7)
    """
    
    def __init__(self, plugin_dir: str):
        """
        Initialize the plugin manager
        
        Args:
            plugin_dir: Directory path containing plugin modules
            
        Raises:
            ValueError: If plugin_dir is empty or invalid
        """
        if not plugin_dir:
            raise ValueError("Plugin directory cannot be empty")
        
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Plugin] = {}
    
    def load_plugins(self) -> None:
        """
        Discover and load all plugins from the plugin directory
        
        Scans the plugin directory for Python modules and attempts to load
        any classes that inherit from the Plugin base class.
        
        Requirement 17.1: Plugin_Manager SHALL discover and load all plugins
        from plugin directory
        """
        if not os.path.exists(self.plugin_dir):
            # Create directory if it doesn't exist
            os.makedirs(self.plugin_dir, exist_ok=True)
            return
        
        if not os.path.isdir(self.plugin_dir):
            raise ValueError(f"Plugin directory is not a directory: {self.plugin_dir}")
        
        # Scan for Python files in plugin directory
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                plugin_path = os.path.join(self.plugin_dir, filename)
                self._load_plugin_from_file(plugin_path)
    
    def _load_plugin_from_file(self, plugin_path: str) -> None:
        """
        Load a plugin from a specific file
        
        Args:
            plugin_path: Path to the plugin file
        """
        try:
            # Load the module
            module_name = os.path.splitext(os.path.basename(plugin_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            
            if spec is None or spec.loader is None:
                return
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find Plugin subclasses in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it's a class that inherits from Plugin (but not Plugin itself)
                if (isinstance(attr, type) and 
                    issubclass(attr, Plugin) and 
                    attr is not Plugin):
                    
                    # Instantiate the plugin
                    plugin_instance = attr()
                    plugin_name = plugin_instance.get_name()
                    
                    # Register the plugin
                    self.plugins[plugin_name] = plugin_instance
                    
        except Exception as e:
            # Isolate plugin loading failures - don't crash the manager
            # Requirement 17.3: Isolate failures
            pass
    
    def execute_plugin(self, plugin_name: str, args: Dict[str, Any]) -> PluginResult:
        """
        Execute a plugin with the given arguments
        
        Follows the design algorithm:
        1. Validate plugin exists
        2. Validate required arguments
        3. Execute with timeout and error handling in separate thread
        4. Return PluginResult with success status, data, error, and metadata
        
        Args:
            plugin_name: Name of the plugin to execute
            args: Dictionary of arguments for the plugin
            
        Returns:
            PluginResult containing execution status and data
            
        Requirements:
        - 17.2: Route commands to appropriate plugin
        - 17.3: Isolate failures
        - 17.4: Terminate on timeout
        - 17.7: Validate required arguments
        """
        # Step 1: Validate plugin exists
        if plugin_name not in self.plugins:
            return PluginResult(
                success=False,
                data=None,
                error=f"Plugin not found: {plugin_name}",
                metadata={}
            )
        
        plugin = self.plugins[plugin_name]
        
        # Step 2: Validate required arguments (Requirement 17.7)
        required_args = plugin.get_required_arguments()
        
        for arg in required_args:
            if arg not in args:
                return PluginResult(
                    success=False,
                    data=None,
                    error=f"Missing required argument: {arg}",
                    metadata={'plugin_name': plugin_name}
                )
        
        # Step 3: Execute with timeout and error handling
        timeout = args.get('timeout', 300)  # Default 5 minutes
        
        # Validate timeout is a positive number
        try:
            timeout = float(timeout)
            if timeout <= 0:
                timeout = 300  # Use default if invalid
        except (TypeError, ValueError):
            timeout = 300  # Use default if not a number
        
        # Container for result from thread
        result_container = {'result': None, 'error': None, 'completed': False}
        
        def execute_in_thread():
            """Execute plugin in separate thread"""
            try:
                result = plugin.execute(args)
                result_container['result'] = result
                result_container['completed'] = True
            except Exception as e:
                result_container['error'] = str(e)
                result_container['completed'] = True
        
        # Create and start execution thread
        execution_thread = threading.Thread(target=execute_in_thread, daemon=True)
        execution_thread.start()
        
        # Wait for completion with timeout (Requirement 17.4)
        execution_thread.join(timeout=timeout)
        
        # Check if thread is still alive (timeout occurred)
        if execution_thread.is_alive():
            return PluginResult(
                success=False,
                data=None,
                error="Plugin execution timeout",
                metadata={'plugin_name': plugin_name, 'timeout': timeout}
            )
        
        # Check if execution completed with error
        if result_container['error'] is not None:
            return PluginResult(
                success=False,
                data=None,
                error=f"Plugin execution error: {result_container['error']}",
                metadata={'plugin_name': plugin_name}
            )
        
        # Step 4: Return successful result
        return PluginResult(
            success=True,
            data=result_container['result'],
            error=None,
            metadata={'plugin_name': plugin_name}
        )
    
    def list_plugins(self) -> List[str]:
        """
        Get list of available plugin names
        
        Returns:
            List of plugin names
            
        Requirement 17.5: Agent SHALL report all loaded plugins to server
        """
        return list(self.plugins.keys())
    
    def register_plugin(self, plugin: Plugin) -> None:
        """
        Manually register a plugin instance
        
        Allows plugins to be registered programmatically without file loading.
        Supports hot-reloading by allowing plugins to be re-registered.
        
        Args:
            plugin: Plugin instance to register
            
        Raises:
            ValueError: If plugin is None or invalid
            
        Requirement 17.6: Support hot-reloading without restarting agent
        """
        if plugin is None:
            raise ValueError("Plugin cannot be None")
        
        if not isinstance(plugin, Plugin):
            raise ValueError("Plugin must inherit from Plugin base class")
        
        plugin_name = plugin.get_name()
        
        if not plugin_name:
            raise ValueError("Plugin name cannot be empty")
        
        # Register or re-register the plugin (hot-reload support)
        self.plugins[plugin_name] = plugin
