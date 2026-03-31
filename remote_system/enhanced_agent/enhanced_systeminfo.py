"""
Enhanced System Information Collector

Collects comprehensive system information including hostname, username, OS details,
network information, hardware specifications, and optional software inventory.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

import platform
import socket
import psutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class SystemInfo:
    """System information data structure"""
    hostname: str
    username: str
    os_type: str
    os_version: str
    error: Optional[str] = None


@dataclass
class NetworkInfo:
    """Network information data structure"""
    ip_address: str
    mac_address: str
    interfaces: List[Dict[str, Any]]
    error: Optional[str] = None


@dataclass
class HardwareInfo:
    """Hardware information data structure"""
    cpu_architecture: str
    cpu_count: int
    memory_total: int
    memory_available: int
    error: Optional[str] = None


class EnhancedSystemInfo:
    """
    Enhanced system information collector
    
    Collects comprehensive system information with graceful error handling.
    If collection of specific data fails, returns partial data with error indicators.
    
    Requirements:
    - 5.1: Collect hostname, username, OS type, and OS version
    - 5.2: Include IP address and MAC address
    - 5.3: Include CPU architecture and memory information
    - 5.4: Return partial data with error indicators on failure
    - 5.5: Include installed software list if requested
    - 5.6: Include all active network interfaces
    """
    
    def __init__(self):
        """Initialize the enhanced system info collector"""
        pass
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Collect basic system information
        
        Collects hostname, username, OS type, and OS version.
        Returns partial data with error indicator if collection fails.
        
        Returns:
            Dictionary with system information and optional error field
        
        Requirement 5.1: Collect hostname, username, OS type, and OS version
        Requirement 5.4: Return partial data with error indicators on failure
        """
        hostname = "unknown"
        username = "unknown"
        os_type = "unknown"
        os_version = "unknown"
        errors = []
        
        # Collect hostname
        try:
            hostname = socket.gethostname()
        except Exception as e:
            errors.append(f"hostname: {str(e)}")
        
        # Collect username
        try:
            import getpass
            username = getpass.getuser()
        except Exception as e:
            errors.append(f"username: {str(e)}")
        
        # Collect OS type
        try:
            os_type = platform.system()
        except Exception as e:
            errors.append(f"os_type: {str(e)}")
        
        # Collect OS version
        try:
            os_version = platform.release()
        except Exception as e:
            errors.append(f"os_version: {str(e)}")
        
        result = {
            "hostname": hostname,
            "username": username,
            "os_type": os_type,
            "os_version": os_version
        }
        
        if errors:
            result["error"] = "; ".join(errors)
        
        return result
    
    def get_network_info(self) -> Dict[str, Any]:
        """
        Collect network information
        
        Collects IP address, MAC address, and all active network interfaces.
        Returns partial data with error indicator if collection fails.
        
        Returns:
            Dictionary with network information and optional error field
        
        Requirement 5.2: Include IP address and MAC address
        Requirement 5.6: Include all active network interfaces
        Requirement 5.4: Return partial data with error indicators on failure
        """
        ip_address = "unknown"
        mac_address = "unknown"
        interfaces = []
        errors = []
        
        # Collect IP address (primary)
        try:
            # Get primary IP by connecting to external address (doesn't actually send data)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
            finally:
                s.close()
        except Exception as e:
            errors.append(f"ip_address: {str(e)}")
        
        # Collect MAC address (primary interface)
        try:
            import uuid
            mac = uuid.getnode()
            mac_address = ':'.join(['{:02x}'.format((mac >> elements) & 0xff)
                                   for elements in range(0, 8*6, 8)][::-1])
        except Exception as e:
            errors.append(f"mac_address: {str(e)}")
        
        # Collect all network interfaces
        try:
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            for interface_name, addresses in net_if_addrs.items():
                # Check if interface is up
                is_up = False
                if interface_name in net_if_stats:
                    is_up = net_if_stats[interface_name].isup
                
                interface_info = {
                    "name": interface_name,
                    "is_up": is_up,
                    "addresses": []
                }
                
                for addr in addresses:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address
                    }
                    
                    if addr.netmask:
                        addr_info["netmask"] = addr.netmask
                    if addr.broadcast:
                        addr_info["broadcast"] = addr.broadcast
                    
                    interface_info["addresses"].append(addr_info)
                
                interfaces.append(interface_info)
        
        except Exception as e:
            errors.append(f"interfaces: {str(e)}")
        
        result = {
            "ip_address": ip_address,
            "mac_address": mac_address,
            "interfaces": interfaces
        }
        
        if errors:
            result["error"] = "; ".join(errors)
        
        return result
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Collect hardware information
        
        Collects CPU architecture, CPU count, and memory information.
        Returns partial data with error indicator if collection fails.
        
        Returns:
            Dictionary with hardware information and optional error field
        
        Requirement 5.3: Include CPU architecture and memory information
        Requirement 5.4: Return partial data with error indicators on failure
        """
        cpu_architecture = "unknown"
        cpu_count = 0
        memory_total = 0
        memory_available = 0
        errors = []
        
        # Collect CPU architecture
        try:
            cpu_architecture = platform.machine()
        except Exception as e:
            errors.append(f"cpu_architecture: {str(e)}")
        
        # Collect CPU count
        try:
            cpu_count = psutil.cpu_count(logical=True)
            if cpu_count is None:
                cpu_count = 0
        except Exception as e:
            errors.append(f"cpu_count: {str(e)}")
        
        # Collect memory information
        try:
            mem = psutil.virtual_memory()
            memory_total = mem.total
            memory_available = mem.available
        except Exception as e:
            errors.append(f"memory: {str(e)}")
        
        result = {
            "cpu_architecture": cpu_architecture,
            "cpu_count": cpu_count,
            "memory_total": memory_total,
            "memory_available": memory_available
        }
        
        if errors:
            result["error"] = "; ".join(errors)
        
        return result
    
    def get_installed_software(self) -> Dict[str, Any]:
        """
        Collect installed software inventory (optional)
        
        Attempts to collect a list of installed software packages.
        Implementation varies by platform and may not be available on all systems.
        
        Returns:
            Dictionary with software list and optional error field
        
        Requirement 5.5: Include installed software list if requested
        Requirement 5.4: Return partial data with error indicators on failure
        """
        software_list = []
        errors = []
        
        try:
            os_type = platform.system()
            
            if os_type == "Windows":
                # Windows: Query registry for installed programs
                try:
                    import winreg
                    
                    registry_paths = [
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
                    ]
                    
                    for reg_path in registry_paths:
                        try:
                            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                            for i in range(winreg.QueryInfoKey(key)[0]):
                                try:
                                    subkey_name = winreg.EnumKey(key, i)
                                    subkey = winreg.OpenKey(key, subkey_name)
                                    
                                    try:
                                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        version = ""
                                        try:
                                            version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                        except:
                                            pass
                                        
                                        software_list.append({
                                            "name": name,
                                            "version": version
                                        })
                                    except:
                                        pass
                                    finally:
                                        winreg.CloseKey(subkey)
                                except:
                                    pass
                            winreg.CloseKey(key)
                        except:
                            pass
                
                except ImportError:
                    errors.append("winreg module not available")
                except Exception as e:
                    errors.append(f"Windows registry query failed: {str(e)}")
            
            elif os_type == "Linux":
                # Linux: Try common package managers
                import subprocess
                
                # Try dpkg (Debian/Ubuntu)
                try:
                    result = subprocess.run(
                        ["dpkg", "-l"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if line.startswith('ii'):
                                parts = line.split()
                                if len(parts) >= 3:
                                    software_list.append({
                                        "name": parts[1],
                                        "version": parts[2]
                                    })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
                
                # Try rpm (RedHat/CentOS/Fedora) if dpkg didn't work
                if not software_list:
                    try:
                        result = subprocess.run(
                            ["rpm", "-qa", "--queryformat", "%{NAME} %{VERSION}\n"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if result.returncode == 0:
                            for line in result.stdout.split('\n'):
                                parts = line.split()
                                if len(parts) >= 2:
                                    software_list.append({
                                        "name": parts[0],
                                        "version": parts[1]
                                    })
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        pass
                
                if not software_list:
                    errors.append("No supported package manager found (dpkg, rpm)")
            
            elif os_type == "Darwin":
                # macOS: Use system_profiler
                import subprocess
                
                try:
                    result = subprocess.run(
                        ["system_profiler", "SPApplicationsDataType", "-json"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        import json
                        data = json.loads(result.stdout)
                        
                        apps = data.get("SPApplicationsDataType", [])
                        for app in apps:
                            software_list.append({
                                "name": app.get("_name", "unknown"),
                                "version": app.get("version", "unknown")
                            })
                except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
                    errors.append(f"macOS system_profiler failed: {str(e)}")
            
            else:
                errors.append(f"Unsupported OS for software inventory: {os_type}")
        
        except Exception as e:
            errors.append(f"Software inventory failed: {str(e)}")
        
        result = {
            "software_count": len(software_list),
            "software_list": software_list
        }
        
        if errors:
            result["error"] = "; ".join(errors)
        
        return result
    
    def get_all_info(self, include_software: bool = False) -> Dict[str, Any]:
        """
        Collect all system information
        
        Convenience method to collect all available system information.
        
        Args:
            include_software: Whether to include software inventory (optional, may be slow)
        
        Returns:
            Dictionary with all system information
        
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
        """
        result = {
            "system": self.get_system_info(),
            "network": self.get_network_info(),
            "hardware": self.get_hardware_info()
        }
        
        if include_software:
            result["software"] = self.get_installed_software()
        
        return result
