"""
Unit and Property-Based Tests for PluginManager

Tests plugin loading, execution, argument validation, and isolation.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7
"""

import pytest
import time
import os
import tempfile
import shutil
from typing import Dict, Any, List
from hypothesis import given, strategies as st, settings
from remote_system.enhanced_agent.plugin_manager import (
    PluginManager,
    Plugin,
    PluginResult
)


# Test plugin implementations for testing
class SimpleTestPlugin(Plugin):
    """Simple test plugin that returns a fixed value"""
    
    def execute(self, args: Dict[str, Any]) -> Any:
        return {"status": "success", "message": "Hello from SimpleTestPlugin"}
    
    def get_name(self) -> str:
        return "simple_test"
    
    def get_required_arguments(self) -> List[str]:
        return []


class ArgumentTestPlugin(Plugin):
    """Test plugin that requires specific arguments"""
    
    def execute(self, args: Dict[str, Any]) -> Any:
        return {
            "arg1": args["arg1"],
            "arg2": args["arg2"],
            "result": args["arg1"] + args["arg2"]
        }
    
    def get_name(self) -> str:
        return "argument_test"
    
    def get_required_arguments(self) -> List[str]:
        return ["arg1", "arg2"]


class SlowTestPlugin(Plugin):
    """Test plugin that takes time to execute"""
    
    def execute(self, args: Dict[str, Any]) -> Any:
        sleep_time = args.get("sleep_time", 2)
        time.sleep(sleep_time)
        return {"slept": sleep_time}
    
    def get_name(self) -> str:
        return "slow_test"
    
    def get_required_arguments(self) -> List[str]:
        return []


class ErrorTestPlugin(Plugin):
    """Test plugin that raises an error"""
    
    def execute(self, args: Dict[str, Any]) -> Any:
        raise RuntimeError("Intentional test error")
    
    def get_name(self) -> str:
        return "error_test"
    
    def get_required_arguments(self) -> List[str]:
        return []


@pytest.fixture
def temp_plugin_dir():
    """Create a temporary plugin directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def plugin_manager(temp_plugin_dir):
    """Create a PluginManager instance with temp directory"""
    return PluginManager(temp_plugin_dir)


class TestPluginManagerInitialization:
    """Test plugin manager initialization"""
    
    def test_initialization_with_valid_dir(self, temp_plugin_dir):
        """Test successful initialization with valid directory"""
        manager = PluginManager(temp_plugin_dir)
        assert manager.plugin_dir == temp_plugin_dir
        assert len(manager.plugins) == 0
    
    def test_initialization_with_empty_dir(self):
        """Test that empty directory raises ValueError"""
        with pytest.raises(ValueError, match="Plugin directory cannot be empty"):
            PluginManager("")
    
    def test_initialization_creates_dir_if_not_exists(self, temp_plugin_dir):
        """Test that non-existent directory is created on load_plugins"""
        non_existent = os.path.join(temp_plugin_dir, "non_existent")
        manager = PluginManager(non_existent)
        
        # Directory should not exist yet
        assert not os.path.exists(non_existent)
        
        # load_plugins should create it
        manager.load_plugins()
        assert os.path.exists(non_existent)


class TestPluginRegistration:
    """Test manual plugin registration"""
    
    def test_register_plugin_basic(self, plugin_manager):
        """Test basic plugin registration - Requirement 17.6"""
        plugin = SimpleTestPlugin()
        plugin_manager.register_plugin(plugin)
        
        assert "simple_test" in plugin_manager.plugins
        assert plugin_manager.plugins["simple_test"] == plugin
    
    def test_register_plugin_none(self, plugin_manager):
        """Test that registering None raises ValueError"""
        with pytest.raises(ValueError, match="Plugin cannot be None"):
            plugin_manager.register_plugin(None)
    
    def test_register_plugin_invalid_type(self, plugin_manager):
        """Test that registering non-Plugin raises ValueError"""
        with pytest.raises(ValueError, match="must inherit from Plugin"):
            plugin_manager.register_plugin("not a plugin")
    
    def test_register_plugin_hot_reload(self, plugin_manager):
        """Test hot-reloading by re-registering plugin - Requirement 17.6"""
        plugin1 = SimpleTestPlugin()
        plugin_manager.register_plugin(plugin1)
        
        # Re-register with new instance (simulating hot-reload)
        plugin2 = SimpleTestPlugin()
        plugin_manager.register_plugin(plugin2)
        
        # Should have replaced the old plugin
        assert plugin_manager.plugins["simple_test"] == plugin2
        assert plugin_manager.plugins["simple_test"] is not plugin1


class TestPluginLoading:
    """Test plugin loading from files"""
    
    def test_load_plugins_empty_directory(self, plugin_manager):
        """Test loading from empty directory - Requirement 17.1"""
        plugin_manager.load_plugins()
        assert len(plugin_manager.plugins) == 0
    
    def test_load_plugins_with_plugin_file(self, temp_plugin_dir):
        """Test loading plugin from file - Requirement 17.1"""
        # Create a plugin file
        plugin_code = '''
from remote_system.enhanced_agent.plugin_manager import Plugin
from typing import Dict, Any, List

class TestFilePlugin(Plugin):
    def execute(self, args: Dict[str, Any]) -> Any:
        return "file_plugin_result"
    
    def get_name(self) -> str:
        return "file_plugin"
    
    def get_required_arguments(self) -> List[str]:
        return []
'''
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write(plugin_code)
        
        manager = PluginManager(temp_plugin_dir)
        manager.load_plugins()
        
        assert "file_plugin" in manager.plugins
    
    def test_load_plugins_ignores_invalid_files(self, temp_plugin_dir):
        """Test that invalid plugin files are ignored - Requirement 17.3"""
        # Create an invalid plugin file
        invalid_file = os.path.join(temp_plugin_dir, "invalid.py")
        with open(invalid_file, 'w') as f:
            f.write("this is not valid python code {{{")
        
        manager = PluginManager(temp_plugin_dir)
        # Should not crash, just ignore the invalid file
        manager.load_plugins()
        assert len(manager.plugins) == 0


class TestListPlugins:
    """Test listing available plugins"""
    
    def test_list_plugins_empty(self, plugin_manager):
        """Test listing plugins when none are loaded - Requirement 17.5"""
        plugins = plugin_manager.list_plugins()
        assert plugins == []
    
    def test_list_plugins_with_registered(self, plugin_manager):
        """Test listing plugins after registration - Requirement 17.5"""
        plugin_manager.register_plugin(SimpleTestPlugin())
        plugin_manager.register_plugin(ArgumentTestPlugin())
        
        plugins = plugin_manager.list_plugins()
        assert len(plugins) == 2
        assert "simple_test" in plugins
        assert "argument_test" in plugins


class TestPluginExecution:
    """Test plugin execution"""
    
    def test_execute_simple_plugin(self, plugin_manager):
        """Test executing a simple plugin - Requirement 17.2"""
        plugin_manager.register_plugin(SimpleTestPlugin())
        
        result = plugin_manager.execute_plugin("simple_test", {})
        
        assert result.success is True
        assert result.data == {"status": "success", "message": "Hello from SimpleTestPlugin"}
        assert result.error is None
    
    def test_execute_plugin_not_found(self, plugin_manager):
        """Test executing non-existent plugin - Requirement 17.2"""
        result = plugin_manager.execute_plugin("non_existent", {})
        
        assert result.success is False
        assert result.error == "Plugin not found: non_existent"
        assert result.data is None
    
    def test_execute_plugin_with_arguments(self, plugin_manager):
        """Test executing plugin with arguments - Requirement 17.7"""
        plugin_manager.register_plugin(ArgumentTestPlugin())
        
        result = plugin_manager.execute_plugin("argument_test", {
            "arg1": 10,
            "arg2": 20
        })
        
        assert result.success is True
        assert result.data["result"] == 30
    
    def test_execute_plugin_missing_required_argument(self, plugin_manager):
        """Test executing plugin with missing argument - Requirement 17.7"""
        plugin_manager.register_plugin(ArgumentTestPlugin())
        
        result = plugin_manager.execute_plugin("argument_test", {
            "arg1": 10
            # arg2 is missing
        })
        
        assert result.success is False
        assert "Missing required argument: arg2" in result.error
    
    def test_execute_plugin_with_error(self, plugin_manager):
        """Test plugin execution with error - Requirement 17.3"""
        plugin_manager.register_plugin(ErrorTestPlugin())
        
        result = plugin_manager.execute_plugin("error_test", {})
        
        assert result.success is False
        assert "Plugin execution error" in result.error
        assert "Intentional test error" in result.error
    
    def test_execute_plugin_with_timeout(self, plugin_manager):
        """Test plugin execution timeout - Requirement 17.4"""
        plugin_manager.register_plugin(SlowTestPlugin())
        
        # Execute with 1 second timeout, but plugin sleeps for 3 seconds
        result = plugin_manager.execute_plugin("slow_test", {
            "sleep_time": 3,
            "timeout": 1
        })
        
        assert result.success is False
        assert "timeout" in result.error.lower()
    
    def test_execute_plugin_completes_within_timeout(self, plugin_manager):
        """Test plugin completes within timeout - Requirement 17.4"""
        plugin_manager.register_plugin(SlowTestPlugin())
        
        # Execute with 5 second timeout, plugin sleeps for 1 second
        result = plugin_manager.execute_plugin("slow_test", {
            "sleep_time": 1,
            "timeout": 5
        })
        
        assert result.success is True
        assert result.data == {"slept": 1}


class TestPluginIsolation:
    """Test plugin isolation"""
    
    def test_plugin_error_does_not_crash_manager(self, plugin_manager):
        """Test that plugin errors don't crash manager - Requirement 17.3"""
        plugin_manager.register_plugin(ErrorTestPlugin())
        plugin_manager.register_plugin(SimpleTestPlugin())
        
        # Execute error plugin
        result1 = plugin_manager.execute_plugin("error_test", {})
        assert result1.success is False
        
        # Manager should still work for other plugins
        result2 = plugin_manager.execute_plugin("simple_test", {})
        assert result2.success is True
    
    def test_multiple_plugins_independent(self, plugin_manager):
        """Test that plugins operate independently - Requirement 17.3"""
        plugin_manager.register_plugin(SimpleTestPlugin())
        plugin_manager.register_plugin(ArgumentTestPlugin())
        plugin_manager.register_plugin(ErrorTestPlugin())
        
        # All plugins should be available
        plugins = plugin_manager.list_plugins()
        assert len(plugins) == 3
        
        # Error in one plugin doesn't affect others
        plugin_manager.execute_plugin("error_test", {})
        
        result = plugin_manager.execute_plugin("simple_test", {})
        assert result.success is True


class TestPropertyBasedPluginArgumentValidation:
    """
    Property-Based Tests for Plugin Argument Validation
    
    Property 4: Plugin Isolation - Invalid arguments must always be rejected
    Validates: Requirements 17.7
    """
    
    @given(
        missing_args=st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=50, deadline=1000)
    def test_property_missing_required_arguments_rejected(self, missing_args):
        """
        Property 4: Plugin Isolation - Missing required arguments must be rejected
        
        For all sets of required arguments:
        - If any required argument is missing, execution MUST fail
        - Error message MUST indicate which argument is missing
        - Plugin MUST NOT execute with incomplete arguments
        
        Requirement: 17.7
        """
        # Create a custom plugin with the specified required arguments
        class CustomArgPlugin(Plugin):
            def execute(self, args: Dict[str, Any]) -> Any:
                # This should never be called if validation works
                return {"executed": True}
            
            def get_name(self) -> str:
                return "custom_arg_test"
            
            def get_required_arguments(self) -> List[str]:
                return missing_args
        
        # Create manager and register plugin
        temp_dir = tempfile.mkdtemp()
        try:
            manager = PluginManager(temp_dir)
            manager.register_plugin(CustomArgPlugin())
            
            # Try to execute with empty arguments (all required args missing)
            result = manager.execute_plugin("custom_arg_test", {})
            
            # Property: Execution MUST fail
            assert result.success is False, \
                "Plugin execution must fail when required arguments are missing"
            
            # Property: Error must be present
            assert result.error is not None, \
                "Error message must be present for missing arguments"
            
            # Property: Error must mention missing argument
            assert "Missing required argument" in result.error, \
                f"Error must indicate missing argument. Got: {result.error}"
            
            # Property: One of the required args must be mentioned in error
            error_mentions_arg = any(arg in result.error for arg in missing_args)
            assert error_mentions_arg, \
                f"Error must mention one of the required arguments {missing_args}. Got: {result.error}"
            
            # Property: Plugin must not have executed (data should be None)
            assert result.data is None, \
                "Plugin must not return data when arguments are invalid"
        
        finally:
            shutil.rmtree(temp_dir)
    
    @given(
        required_args=st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),
            min_size=1,
            max_size=5,
            unique=True
        ).filter(lambda args: 'timeout' not in args),  # Avoid 'timeout' as it's a reserved argument
        arg_values=st.lists(
            st.one_of(
                st.integers(),
                st.text(max_size=20),
                st.booleans(),
                st.floats(allow_nan=False, allow_infinity=False)
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=1000)
    def test_property_valid_arguments_accepted(self, required_args, arg_values):
        """
        Property: Valid arguments must be accepted
        
        For all sets of required arguments:
        - If all required arguments are provided, validation MUST pass
        - Plugin MUST execute successfully
        - Result MUST contain data from plugin
        
        Requirement: 17.7
        """
        # Ensure we have enough values for all required args
        arg_values = arg_values[:len(required_args)]
        if len(arg_values) < len(required_args):
            arg_values.extend([0] * (len(required_args) - len(arg_values)))
        
        # Create argument dictionary
        args_dict = dict(zip(required_args, arg_values))
        
        # Create a custom plugin
        class ValidArgPlugin(Plugin):
            def execute(self, args: Dict[str, Any]) -> Any:
                return {"executed": True, "args_received": args}
            
            def get_name(self) -> str:
                return "valid_arg_test"
            
            def get_required_arguments(self) -> List[str]:
                return required_args
        
        # Create manager and register plugin
        temp_dir = tempfile.mkdtemp()
        try:
            manager = PluginManager(temp_dir)
            manager.register_plugin(ValidArgPlugin())
            
            # Execute with all required arguments provided
            result = manager.execute_plugin("valid_arg_test", args_dict)
            
            # Property: Execution MUST succeed
            assert result.success is True, \
                f"Plugin execution must succeed when all required arguments are provided. Error: {result.error}"
            
            # Property: No error should be present
            assert result.error is None, \
                f"No error should be present for valid arguments. Got: {result.error}"
            
            # Property: Data must be present
            assert result.data is not None, \
                "Plugin must return data when execution succeeds"
            
            # Property: Data should indicate execution occurred
            assert result.data.get("executed") is True, \
                "Plugin must have executed successfully"
        
        finally:
            shutil.rmtree(temp_dir)
    
    @given(
        required_args=st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),
            min_size=2,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=30, deadline=1000)
    def test_property_partial_arguments_rejected(self, required_args):
        """
        Property: Partial arguments must be rejected
        
        For all sets of required arguments with 2+ elements:
        - If only some required arguments are provided, execution MUST fail
        - Error MUST indicate which argument is missing
        
        Requirement: 17.7
        """
        # Provide only the first argument, omit the rest
        partial_args = {required_args[0]: "value"}
        
        # Create a custom plugin
        class PartialArgPlugin(Plugin):
            def execute(self, args: Dict[str, Any]) -> Any:
                return {"executed": True}
            
            def get_name(self) -> str:
                return "partial_arg_test"
            
            def get_required_arguments(self) -> List[str]:
                return required_args
        
        # Create manager and register plugin
        temp_dir = tempfile.mkdtemp()
        try:
            manager = PluginManager(temp_dir)
            manager.register_plugin(PartialArgPlugin())
            
            # Execute with partial arguments
            result = manager.execute_plugin("partial_arg_test", partial_args)
            
            # Property: Execution MUST fail
            assert result.success is False, \
                "Plugin execution must fail when only partial arguments are provided"
            
            # Property: Error must indicate missing argument
            assert "Missing required argument" in result.error, \
                f"Error must indicate missing argument. Got: {result.error}"
            
            # Property: One of the missing args must be mentioned
            missing_args = required_args[1:]  # All except the first
            error_mentions_missing = any(arg in result.error for arg in missing_args)
            assert error_mentions_missing, \
                f"Error must mention one of the missing arguments {missing_args}. Got: {result.error}"
        
        finally:
            shutil.rmtree(temp_dir)


class TestPluginResult:
    """Test PluginResult dataclass"""
    
    def test_plugin_result_success(self):
        """Test PluginResult for successful execution"""
        result = PluginResult(
            success=True,
            data={"key": "value"},
            error=None,
            metadata={"plugin_name": "test"}
        )
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata == {"plugin_name": "test"}
    
    def test_plugin_result_failure(self):
        """Test PluginResult for failed execution"""
        result = PluginResult(
            success=False,
            data=None,
            error="Test error",
            metadata={}
        )
        
        assert result.success is False
        assert result.data is None
        assert result.error == "Test error"
