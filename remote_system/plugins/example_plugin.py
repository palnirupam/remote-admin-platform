"""
Example Plugin for demonstration purposes

This is a simple example plugin that demonstrates how to create
a plugin for the enhanced agent.
"""

from typing import Dict, Any, List
from remote_system.enhanced_agent.plugin_manager import Plugin


class ExamplePlugin(Plugin):
    """
    Example plugin that echoes back the input message
    """
    
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Execute the plugin with the given arguments
        
        Args:
            args: Dictionary containing 'message' key
            
        Returns:
            Dictionary with the echoed message
        """
        message = args.get('message', 'No message provided')
        return {
            'status': 'success',
            'echo': message,
            'length': len(message)
        }
    
    def get_name(self) -> str:
        """
        Get the name of the plugin
        
        Returns:
            The plugin name
        """
        return "example"
    
    def get_required_arguments(self) -> List[str]:
        """
        Get the list of required argument names
        
        Returns:
            List of required argument names
        """
        return ['message']
