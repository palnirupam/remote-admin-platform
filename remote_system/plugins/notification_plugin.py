"""
Notification Plugin - Display popup messages on client screen
Sends notifications from server to client that appear as Windows toast notifications
"""
import platform
import subprocess
import json
from typing import Dict, Any


class NotificationPlugin:
    """Plugin to display popup notifications on client machine"""
    
    def __init__(self):
        self.name = "notification"
        self.os_type = platform.system()
    
    def get_name(self) -> str:
        return self.name
    
    def get_required_arguments(self) -> list:
        return ["message"]
    
    def execute(self, action: str = "show", **kwargs) -> Dict[str, Any]:
        """
        Execute notification action
        
        Args:
            action: Action to perform (show, show_with_title)
            message: Message text to display
            title: Optional title for notification
            duration: Optional duration in seconds (default: 10)
            icon: Optional icon type (info, warning, error)
        
        Returns:
            Dict with success status and result
        """
        try:
            if action == "show" or action == "show_with_title":
                return self._show_notification(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _show_notification(self, message: str, title: str = "Server Message", 
                          duration: int = 10, icon: str = "info") -> Dict[str, Any]:
        """Show notification on client screen"""
        
        if self.os_type == "Windows":
            return self._show_windows_notification(message, title, duration, icon)
        elif self.os_type == "Linux":
            return self._show_linux_notification(message, title, duration, icon)
        elif self.os_type == "Darwin":  # macOS
            return self._show_macos_notification(message, title, duration)
        else:
            return {
                "success": False,
                "error": f"Unsupported OS: {self.os_type}"
            }
    
    def _show_windows_notification(self, message: str, title: str, 
                                   duration: int, icon: str) -> Dict[str, Any]:
        """Show Windows toast notification using PowerShell"""
        try:
            # Map icon types to Windows notification icons
            icon_map = {
                "info": "None",
                "warning": "Warning",
                "error": "Error"
            }
            icon_type = icon_map.get(icon, "None")
            
            # PowerShell script to show notification
            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$notification = New-Object System.Windows.Forms.NotifyIcon
$notification.Icon = [System.Drawing.SystemIcons]::Information
$notification.BalloonTipIcon = '{icon_type}'
$notification.BalloonTipTitle = '{title}'
$notification.BalloonTipText = '{message}'
$notification.Visible = $true
$notification.ShowBalloonTip({duration * 1000})
Start-Sleep -Seconds {duration}
$notification.Dispose()
"""
            
            # Execute PowerShell script
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=duration + 5
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Notification displayed successfully",
                    "title": title,
                    "text": message,
                    "duration": duration,
                    "os": "Windows"
                }
            else:
                return {
                    "success": False,
                    "error": f"PowerShell error: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": True,
                "message": "Notification displayed (timeout reached)",
                "title": title,
                "text": message
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Windows notification error: {str(e)}"
            }
    
    def _show_linux_notification(self, message: str, title: str, 
                                 duration: int, icon: str) -> Dict[str, Any]:
        """Show Linux notification using notify-send"""
        try:
            # Map icon types
            icon_map = {
                "info": "dialog-information",
                "warning": "dialog-warning",
                "error": "dialog-error"
            }
            icon_name = icon_map.get(icon, "dialog-information")
            
            # Use notify-send command
            cmd = [
                "notify-send",
                "-t", str(duration * 1000),
                "-i", icon_name,
                title,
                message
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Notification displayed successfully",
                    "title": title,
                    "text": message,
                    "duration": duration,
                    "os": "Linux"
                }
            else:
                return {
                    "success": False,
                    "error": f"notify-send error: {result.stderr}"
                }
                
        except FileNotFoundError:
            return {
                "success": False,
                "error": "notify-send not found. Install libnotify-bin package."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Linux notification error: {str(e)}"
            }
    
    def _show_macos_notification(self, message: str, title: str, 
                                 duration: int) -> Dict[str, Any]:
        """Show macOS notification using osascript"""
        try:
            # AppleScript to show notification
            script = f'display notification "{message}" with title "{title}"'
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Notification displayed successfully",
                    "title": title,
                    "text": message,
                    "os": "macOS"
                }
            else:
                return {
                    "success": False,
                    "error": f"osascript error: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"macOS notification error: {str(e)}"
            }


# Plugin instance
plugin = NotificationPlugin()
