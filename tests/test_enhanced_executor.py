"""
Unit Tests for EnhancedExecutor

Tests command execution, stdout/stderr capture, timeout enforcement,
input sanitization, and error handling.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 22.6
"""

import pytest
import platform
import time
from remote_system.enhanced_agent.enhanced_executor import (
    EnhancedExecutor,
    CommandResult
)


@pytest.fixture
def executor():
    """Create an EnhancedExecutor instance"""
    return EnhancedExecutor()


class TestEnhancedExecutorInitialization:
    """Test executor initialization and platform detection"""
    
    def test_initialization(self, executor):
        """Test successful initialization"""
        assert executor is not None
        assert executor.platform in ["Windows", "Linux", "Darwin"]
        assert executor.shell is not None
    
    def test_platform_shell_detection_windows(self):
        """Test Windows shell detection - Requirement 22.6"""
        executor = EnhancedExecutor()
        if platform.system() == "Windows":
            assert executor.shell == ("cmd.exe", "/c")
    
    def test_platform_shell_detection_unix(self):
        """Test Unix/Linux/macOS shell detection - Requirement 22.6"""
        executor = EnhancedExecutor()
        if platform.system() in ["Linux", "Darwin"]:
            assert executor.shell == ("/bin/bash", "-c")


class TestCommandExecution:
    """Test basic command execution"""
    
    def test_execute_simple_command_windows(self, executor):
        """Test simple command execution on Windows - Requirement 4.1"""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")
        
        result = executor.execute_command("echo Hello World")
        
        assert result.success is True
        assert "Hello World" in result.stdout
        assert result.exit_code == 0
        assert result.error is None
        assert result.execution_time > 0
    
    def test_execute_simple_command_unix(self, executor):
        """Test simple command execution on Unix - Requirement 4.1"""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")
        
        result = executor.execute_command("echo Hello World")
        
        assert result.success is True
        assert "Hello World" in result.stdout
        assert result.exit_code == 0
        assert result.error is None
        assert result.execution_time > 0
    
    def test_execute_command_with_output(self, executor):
        """Test command with output capture - Requirement 4.2"""
        if platform.system() == "Windows":
            result = executor.execute_command("echo Test Output")
        else:
            result = executor.execute_command("echo 'Test Output'")
        
        assert result.success is True
        assert "Test Output" in result.stdout
        assert result.exit_code == 0
    
    def test_execute_directory_listing_windows(self, executor):
        """Test directory listing on Windows - Requirement 4.1"""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")
        
        result = executor.execute_command("dir")
        
        assert result.success is True
        assert len(result.stdout) > 0
        assert result.exit_code == 0
    
    def test_execute_directory_listing_unix(self, executor):
        """Test directory listing on Unix - Requirement 4.1"""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")
        
        result = executor.execute_command("ls -la")
        
        assert result.success is True
        assert len(result.stdout) > 0
        assert result.exit_code == 0


class TestStdoutStderrCapture:
    """Test stdout and stderr capture"""
    
    def test_capture_stdout(self, executor):
        """Test stdout capture - Requirement 4.2"""
        if platform.system() == "Windows":
            result = executor.execute_command("echo stdout test")
        else:
            result = executor.execute_command("echo 'stdout test'")
        
        assert result.success is True
        assert "stdout test" in result.stdout
        assert result.stderr == ""
    
    def test_capture_stderr_windows(self, executor):
        """Test stderr capture on Windows - Requirement 4.2"""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")
        
        # Use a command that generates stderr output
        # 'dir nonexistentfile' will write error to stderr
        result = executor.execute_command("dir nonexistentfile12345.txt")
        
        # Command should fail but execute
        assert result.exit_code != 0
        # Error message should be in stderr
        assert len(result.stderr) > 0 or "cannot find" in result.stdout.lower()
    
    def test_capture_stderr_unix(self, executor):
        """Test stderr capture on Unix - Requirement 4.2"""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")
        
        # Use a command that writes to stderr
        result = executor.execute_command("echo 'error message' >&2")
        
        assert result.success is True
        assert "error message" in result.stderr
        assert result.stdout == ""
    
    def test_capture_both_stdout_and_stderr_unix(self, executor):
        """Test capturing both stdout and stderr - Requirement 4.2"""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")
        
        # Command that writes to both
        result = executor.execute_command("echo 'stdout line' && echo 'stderr line' >&2")
        
        assert result.success is True
        assert "stdout line" in result.stdout
        assert "stderr line" in result.stderr


class TestTimeoutEnforcement:
    """Test command timeout enforcement"""
    
    def test_timeout_enforcement_windows(self, executor):
        """Test timeout on Windows - Requirement 4.3"""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")
        
        # Use ping with long delay to test timeout (ping waits 1 second per attempt)
        # This command will take ~5 seconds but we timeout at 1 second
        result = executor.execute_command("ping -n 6 127.0.0.1", timeout=1)
        
        assert result.success is False
        assert "timed out" in result.error.lower()
        assert result.exit_code == -1
        assert result.execution_time >= 1.0
        assert result.execution_time < 3.0  # Should not wait full duration
    
    def test_timeout_enforcement_unix(self, executor):
        """Test timeout on Unix - Requirement 4.3"""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")
        
        # Command that sleeps for 5 seconds, but timeout is 1 second
        result = executor.execute_command("sleep 5", timeout=1)
        
        assert result.success is False
        assert "timed out" in result.error.lower()
        assert result.exit_code == -1
        assert result.execution_time >= 1.0
        assert result.execution_time < 3.0  # Should not wait full 5 seconds
    
    def test_command_completes_within_timeout(self, executor):
        """Test command that completes within timeout - Requirement 4.3"""
        if platform.system() == "Windows":
            result = executor.execute_command("echo fast", timeout=10)
        else:
            result = executor.execute_command("echo 'fast'", timeout=10)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.execution_time < 10.0
    
    def test_invalid_timeout(self, executor):
        """Test invalid timeout value"""
        result = executor.execute_command("echo test", timeout=0)
        
        assert result.success is False
        assert "Timeout must be positive" in result.error
        assert result.exit_code == -1
    
    def test_negative_timeout(self, executor):
        """Test negative timeout value"""
        result = executor.execute_command("echo test", timeout=-5)
        
        assert result.success is False
        assert "Timeout must be positive" in result.error


class TestInputSanitization:
    """Test input sanitization to prevent command injection"""
    
    def test_sanitize_empty_command(self, executor):
        """Test empty command rejection - Requirement 4.6"""
        result = executor.execute_command("")
        
        assert result.success is False
        assert "Command cannot be empty" in result.error
        assert result.exit_code == -1
    
    def test_sanitize_whitespace_only_command(self, executor):
        """Test whitespace-only command rejection - Requirement 4.6"""
        result = executor.execute_command("   ")
        
        assert result.success is False
        assert "Command cannot be empty" in result.error
    
    def test_sanitize_semicolon_injection(self, executor):
        """Test semicolon command chaining prevention - Requirement 4.6"""
        result = executor.execute_command("echo test; rm -rf /")
        
        assert result.success is False
        assert "dangerous pattern" in result.error.lower()
        assert result.exit_code == -1
    
    def test_sanitize_pipe_injection(self, executor):
        """Test pipe command chaining prevention - Requirement 4.6"""
        result = executor.execute_command("echo test | cat /etc/passwd")
        
        assert result.success is False
        assert "dangerous pattern" in result.error.lower()
    
    def test_sanitize_ampersand_injection(self, executor):
        """Test ampersand command chaining prevention - Requirement 4.6"""
        result = executor.execute_command("echo test & whoami")
        
        assert result.success is False
        assert "dangerous pattern" in result.error.lower()
    
    def test_sanitize_backtick_injection(self, executor):
        """Test backtick command substitution prevention - Requirement 4.6"""
        result = executor.execute_command("echo `whoami`")
        
        assert result.success is False
        assert "dangerous pattern" in result.error.lower()
    
    def test_sanitize_dollar_substitution(self, executor):
        """Test dollar command substitution prevention - Requirement 4.6"""
        result = executor.execute_command("echo $(whoami)")
        
        assert result.success is False
        assert "dangerous pattern" in result.error.lower()
    
    def test_sanitize_null_byte_injection(self, executor):
        """Test null byte injection prevention - Requirement 4.6"""
        result = executor.execute_command("echo test\x00rm -rf /")
        
        assert result.success is False
        assert "null bytes" in result.error.lower()
    
    def test_sanitize_dev_redirection(self, executor):
        """Test device file redirection prevention - Requirement 4.6"""
        result = executor.execute_command("echo test > /dev/null")
        
        assert result.success is False
        assert "dangerous pattern" in result.error.lower()
    
    def test_safe_command_passes_sanitization(self, executor):
        """Test that safe commands pass sanitization - Requirement 4.6"""
        if platform.system() == "Windows":
            result = executor.execute_command("echo Hello World")
        else:
            result = executor.execute_command("echo Hello World")
        
        # Should not fail due to sanitization
        assert result.success is True or "sanitization" not in result.error.lower()


class TestErrorHandling:
    """Test error handling for invalid commands"""
    
    def test_invalid_command(self, executor):
        """Test handling of invalid command - Requirement 4.4"""
        result = executor.execute_command("nonexistentcommand12345")
        
        assert result.success is False
        assert result.exit_code != 0
        assert result.error is not None
    
    def test_command_with_error_exit_code(self, executor):
        """Test command that fails with non-zero exit code - Requirement 4.4"""
        if platform.system() == "Windows":
            # Use 'exit 1' to return error code
            result = executor.execute_command("exit 1")
        else:
            # Use 'false' command which returns exit code 1
            result = executor.execute_command("false")
        
        assert result.success is False
        assert result.exit_code != 0
        assert "exit code" in result.error.lower()
    
    def test_exit_code_capture(self, executor):
        """Test exit code capture - Requirement 4.4"""
        if platform.system() == "Windows":
            result = executor.execute_command("exit 42")
        else:
            result = executor.execute_command("exit 42")
        
        assert result.success is False
        assert result.exit_code == 42
        assert "42" in result.error


class TestCommandResult:
    """Test CommandResult dataclass"""
    
    def test_command_result_success(self):
        """Test CommandResult for successful execution"""
        result = CommandResult(
            success=True,
            stdout="output",
            stderr="",
            exit_code=0,
            error=None,
            execution_time=0.5
        )
        
        assert result.success is True
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.error is None
        assert result.execution_time == 0.5
    
    def test_command_result_failure(self):
        """Test CommandResult for failed execution"""
        result = CommandResult(
            success=False,
            stdout="",
            stderr="error output",
            exit_code=1,
            error="Command failed",
            execution_time=0.3
        )
        
        assert result.success is False
        assert result.stdout == ""
        assert result.stderr == "error output"
        assert result.exit_code == 1
        assert result.error == "Command failed"
        assert result.execution_time == 0.3


class TestExecutionTime:
    """Test execution time tracking"""
    
    def test_execution_time_recorded(self, executor):
        """Test that execution time is recorded"""
        if platform.system() == "Windows":
            result = executor.execute_command("echo test")
        else:
            result = executor.execute_command("echo test")
        
        assert result.execution_time > 0
        assert result.execution_time < 5.0  # Should be very fast
    
    def test_execution_time_for_timeout(self, executor):
        """Test execution time for timed out command"""
        if platform.system() == "Windows":
            # Use ping with long delay
            result = executor.execute_command("ping -n 11 127.0.0.1", timeout=1)
        else:
            result = executor.execute_command("sleep 10", timeout=1)
        
        assert result.execution_time >= 1.0
        assert result.execution_time < 3.0


class TestPlatformSpecificShells:
    """Test platform-specific shell usage"""
    
    def test_windows_cmd_shell(self, executor):
        """Test Windows cmd.exe shell - Requirement 22.6"""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")
        
        # Use Windows-specific command
        result = executor.execute_command("ver")
        
        assert result.success is True
        assert len(result.stdout) > 0
    
    def test_unix_bash_shell(self, executor):
        """Test Unix /bin/bash shell - Requirement 22.6"""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")
        
        # Use bash-specific command
        result = executor.execute_command("echo $SHELL")
        
        assert result.success is True
        # Should contain shell path
        assert len(result.stdout) > 0
    
    def test_platform_detection(self, executor):
        """Test that platform is correctly detected - Requirement 22.6"""
        assert executor.platform == platform.system()
        
        if executor.platform == "Windows":
            assert executor.shell[0] == "cmd.exe"
            assert executor.shell[1] == "/c"
        else:
            assert executor.shell[0] == "/bin/bash"
            assert executor.shell[1] == "-c"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_output(self, executor):
        """Test handling of commands with very long output"""
        if platform.system() == "Windows":
            # Generate long output on Windows
            result = executor.execute_command("for /L %i in (1,1,100) do @echo Line %i")
        else:
            # Generate long output on Unix
            result = executor.execute_command("for i in {1..100}; do echo Line $i; done")
        
        assert result.success is True
        assert len(result.stdout) > 100
    
    def test_command_with_special_characters(self, executor):
        """Test command with special characters in output"""
        if platform.system() == "Windows":
            result = executor.execute_command("echo Special: @#%^*")
        else:
            result = executor.execute_command("echo 'Special: @#%^*'")
        
        assert result.success is True
        assert "Special" in result.stdout
    
    def test_multiple_executions(self, executor):
        """Test multiple command executions in sequence"""
        for i in range(5):
            if platform.system() == "Windows":
                result = executor.execute_command(f"echo Test {i}")
            else:
                result = executor.execute_command(f"echo 'Test {i}'")
            
            assert result.success is True
            assert f"Test {i}" in result.stdout
