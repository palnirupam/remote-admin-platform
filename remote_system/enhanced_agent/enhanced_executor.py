"""
Enhanced Command Executor Module

Provides secure command execution with timeout enforcement, input sanitization,
and platform-specific shell support.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 22.6
"""

import subprocess
import platform
import time
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    error: Optional[str]
    execution_time: float


class EnhancedExecutor:
    """
    Enhanced command executor with security and reliability features
    
    Features:
    - Platform-specific shell selection (cmd.exe on Windows, /bin/bash on Unix)
    - Input sanitization to prevent command injection
    - Timeout enforcement with configurable duration
    - Comprehensive stdout/stderr capture
    - Exit code and error message handling
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 22.6
    """
    
    # Dangerous characters that could be used for command injection
    DANGEROUS_PATTERNS = [
        r'[;&|`$]',  # Command chaining and substitution
        r'\$\(',     # Command substitution
        r'>\s*/dev/', # Device file redirection
    ]
    
    def __init__(self):
        """Initialize the enhanced executor with platform detection"""
        self.platform = platform.system()
        self.shell = self._get_platform_shell()
    
    def _get_platform_shell(self) -> tuple:
        """
        Get the appropriate shell for the current platform
        
        Returns:
            tuple: (shell_executable, shell_flag) for subprocess
        
        Requirement: 22.6 - Cross-Platform Compatibility
        """
        if self.platform == "Windows":
            return ("cmd.exe", "/c")
        else:  # Linux, macOS, and other Unix-like systems
            return ("/bin/bash", "-c")
    
    def _sanitize_input(self, command: str) -> tuple[bool, Optional[str]]:
        """
        Sanitize command input to prevent injection attacks
        
        Args:
            command: The command string to sanitize
        
        Returns:
            tuple: (is_safe, error_message)
                - is_safe: True if command is safe, False otherwise
                - error_message: Description of the issue if unsafe, None if safe
        
        Requirement: 4.6 - Input sanitization to prevent injection attacks
        """
        if not command or not command.strip():
            return False, "Command cannot be empty"
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return False, f"Command contains potentially dangerous pattern: {pattern}"
        
        # Check for null bytes (can be used to bypass filters)
        if '\x00' in command:
            return False, "Command contains null bytes"
        
        return True, None
    
    def execute_command(self, command: str, timeout: int = 300) -> CommandResult:
        """
        Execute a command with timeout and security controls
        
        Args:
            command: The command to execute
            timeout: Maximum execution time in seconds (default: 300)
        
        Returns:
            CommandResult: Object containing execution results
        
        Requirements:
            - 4.1: Execute command using system shell
            - 4.2: Return both stdout and stderr output
            - 4.3: Terminate process and return timeout error on timeout
            - 4.4: Return exit code and error message on failure
            - 4.5: Log commands with timestamps (handled by caller)
            - 4.6: Sanitize input to prevent injection attacks
        """
        start_time = time.time()
        
        # Validate timeout
        if timeout <= 0:
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error="Timeout must be positive",
                execution_time=0.0
            )
        
        # Sanitize input (Requirement 4.6)
        is_safe, error_msg = self._sanitize_input(command)
        if not is_safe:
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error=f"Input sanitization failed: {error_msg}",
                execution_time=time.time() - start_time
            )
        
        try:
            # Execute command with platform-specific shell (Requirements 4.1, 22.6)
            shell_exec, shell_flag = self.shell
            process = subprocess.Popen(
                [shell_exec, shell_flag, command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False  # We're explicitly using shell executable
            )
            
            # Wait for completion with timeout (Requirement 4.3)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
                execution_time = time.time() - start_time
                
                # Requirement 4.2: Return both stdout and stderr
                # Requirement 4.4: Return exit code and error message
                success = exit_code == 0
                error = None if success else f"Command failed with exit code {exit_code}"
                
                return CommandResult(
                    success=success,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    error=error,
                    execution_time=execution_time
                )
            
            except subprocess.TimeoutExpired:
                # Requirement 4.3: Terminate process and return timeout error
                process.kill()
                # Wait for process to actually terminate
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    process.terminate()
                
                execution_time = time.time() - start_time
                
                return CommandResult(
                    success=False,
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    error=f"Command execution timed out after {timeout} seconds",
                    execution_time=execution_time
                )
        
        except FileNotFoundError as e:
            # Shell executable not found
            execution_time = time.time() - start_time
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error=f"Shell not found: {str(e)}",
                execution_time=execution_time
            )
        
        except PermissionError as e:
            # Permission denied to execute command
            execution_time = time.time() - start_time
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error=f"Permission denied: {str(e)}",
                execution_time=execution_time
            )
        
        except Exception as e:
            # Catch-all for unexpected errors
            execution_time = time.time() - start_time
            return CommandResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error=f"Unexpected error: {str(e)}",
                execution_time=execution_time
            )
