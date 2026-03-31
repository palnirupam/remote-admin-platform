"""
Unit Tests for Enhanced System Information Collector

Tests system info, network info, hardware info collection, and error handling.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

import pytest
from unittest.mock import patch, MagicMock
from remote_system.enhanced_agent.enhanced_systeminfo import EnhancedSystemInfo


class TestSystemInfoCollection:
    """Test basic system information collection"""
    
    def test_get_system_info_success(self):
        """Test successful system info collection - Requirement 5.1"""
        collector = EnhancedSystemInfo()
        
        with patch('socket.gethostname', return_value='test-host'), \
             patch('getpass.getuser', return_value='test-user'), \
             patch('platform.system', return_value='Linux'), \
             patch('platform.release', return_value='5.10.0'):
            
            result = collector.get_system_info()
            
            assert result['hostname'] == 'test-host'
            assert result['username'] == 'test-user'
            assert result['os_type'] == 'Linux'
            assert result['os_version'] == '5.10.0'
            assert 'error' not in result
    
    def test_get_system_info_partial_failure(self):
        """Test system info with partial failure - Requirement 5.4"""
        collector = EnhancedSystemInfo()
        
        with patch('socket.gethostname', return_value='test-host'), \
             patch('getpass.getuser', side_effect=Exception('User lookup failed')), \
             patch('platform.system', return_value='Linux'), \
             patch('platform.release', return_value='5.10.0'):
            
            result = collector.get_system_info()
            
            # Should still return partial data
            assert result['hostname'] == 'test-host'
            assert result['username'] == 'unknown'
            assert result['os_type'] == 'Linux'
            assert result['os_version'] == '5.10.0'
            
            # Should have error indicator
            assert 'error' in result
            assert 'username' in result['error']
    
    def test_get_system_info_all_failures(self):
        """Test system info with all failures - Requirement 5.4"""
        collector = EnhancedSystemInfo()
        
        with patch('socket.gethostname', side_effect=Exception('Hostname failed')), \
             patch('getpass.getuser', side_effect=Exception('User failed')), \
             patch('platform.system', side_effect=Exception('OS failed')), \
             patch('platform.release', side_effect=Exception('Version failed')):
            
            result = collector.get_system_info()
            
            # Should return unknown values
            assert result['hostname'] == 'unknown'
            assert result['username'] == 'unknown'
            assert result['os_type'] == 'unknown'
            assert result['os_version'] == 'unknown'
            
            # Should have error indicator with all failures
            assert 'error' in result
            assert 'hostname' in result['error']
            assert 'username' in result['error']
            assert 'os_type' in result['error']
            assert 'os_version' in result['error']


class TestNetworkInfoCollection:
    """Test network information collection"""
    
    def test_get_network_info_success(self):
        """Test successful network info collection - Requirements 5.2, 5.6"""
        collector = EnhancedSystemInfo()
        
        # Mock socket for IP address
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ('192.168.1.100', 0)
        
        # Mock psutil for network interfaces
        mock_addr = MagicMock()
        mock_addr.family = 2  # AF_INET
        mock_addr.address = '192.168.1.100'
        mock_addr.netmask = '255.255.255.0'
        mock_addr.broadcast = '192.168.1.255'
        
        mock_stat = MagicMock()
        mock_stat.isup = True
        
        with patch('socket.socket', return_value=mock_socket), \
             patch('uuid.getnode', return_value=0x112233445566), \
             patch('psutil.net_if_addrs', return_value={'eth0': [mock_addr]}), \
             patch('psutil.net_if_stats', return_value={'eth0': mock_stat}):
            
            result = collector.get_network_info()
            
            assert result['ip_address'] == '192.168.1.100'
            assert result['mac_address'] == '11:22:33:44:55:66'
            assert len(result['interfaces']) == 1
            assert result['interfaces'][0]['name'] == 'eth0'
            assert result['interfaces'][0]['is_up'] is True
            assert 'error' not in result
    
    def test_get_network_info_partial_failure(self):
        """Test network info with partial failure - Requirement 5.4"""
        collector = EnhancedSystemInfo()
        
        # Mock socket to fail
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = Exception('Network unreachable')
        
        with patch('socket.socket', return_value=mock_socket), \
             patch('uuid.getnode', return_value=0x112233445566), \
             patch('psutil.net_if_addrs', return_value={}), \
             patch('psutil.net_if_stats', return_value={}):
            
            result = collector.get_network_info()
            
            # Should still return partial data
            assert result['ip_address'] == 'unknown'
            assert result['mac_address'] == '11:22:33:44:55:66'
            assert result['interfaces'] == []
            
            # Should have error indicator
            assert 'error' in result
            assert 'ip_address' in result['error']
    
    def test_get_network_info_multiple_interfaces(self):
        """Test network info with multiple interfaces - Requirement 5.6"""
        collector = EnhancedSystemInfo()
        
        # Mock socket for IP address
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ('192.168.1.100', 0)
        
        # Mock multiple network interfaces
        mock_addr1 = MagicMock()
        mock_addr1.family = 2
        mock_addr1.address = '192.168.1.100'
        mock_addr1.netmask = '255.255.255.0'
        mock_addr1.broadcast = '192.168.1.255'
        
        mock_addr2 = MagicMock()
        mock_addr2.family = 2
        mock_addr2.address = '10.0.0.5'
        mock_addr2.netmask = '255.255.255.0'
        mock_addr2.broadcast = None
        
        mock_stat1 = MagicMock()
        mock_stat1.isup = True
        
        mock_stat2 = MagicMock()
        mock_stat2.isup = False
        
        with patch('socket.socket', return_value=mock_socket), \
             patch('uuid.getnode', return_value=0x112233445566), \
             patch('psutil.net_if_addrs', return_value={
                 'eth0': [mock_addr1],
                 'eth1': [mock_addr2]
             }), \
             patch('psutil.net_if_stats', return_value={
                 'eth0': mock_stat1,
                 'eth1': mock_stat2
             }):
            
            result = collector.get_network_info()
            
            assert len(result['interfaces']) == 2
            
            # Check first interface
            eth0 = next(i for i in result['interfaces'] if i['name'] == 'eth0')
            assert eth0['is_up'] is True
            assert len(eth0['addresses']) == 1
            
            # Check second interface
            eth1 = next(i for i in result['interfaces'] if i['name'] == 'eth1')
            assert eth1['is_up'] is False
            assert len(eth1['addresses']) == 1


class TestHardwareInfoCollection:
    """Test hardware information collection"""
    
    def test_get_hardware_info_success(self):
        """Test successful hardware info collection - Requirement 5.3"""
        collector = EnhancedSystemInfo()
        
        # Mock memory info
        mock_mem = MagicMock()
        mock_mem.total = 16000000000  # 16 GB
        mock_mem.available = 8000000000  # 8 GB
        
        with patch('platform.machine', return_value='x86_64'), \
             patch('psutil.cpu_count', return_value=8), \
             patch('psutil.virtual_memory', return_value=mock_mem):
            
            result = collector.get_hardware_info()
            
            assert result['cpu_architecture'] == 'x86_64'
            assert result['cpu_count'] == 8
            assert result['memory_total'] == 16000000000
            assert result['memory_available'] == 8000000000
            assert 'error' not in result
    
    def test_get_hardware_info_partial_failure(self):
        """Test hardware info with partial failure - Requirement 5.4"""
        collector = EnhancedSystemInfo()
        
        # Mock memory to fail
        with patch('platform.machine', return_value='x86_64'), \
             patch('psutil.cpu_count', return_value=4), \
             patch('psutil.virtual_memory', side_effect=Exception('Memory query failed')):
            
            result = collector.get_hardware_info()
            
            # Should still return partial data
            assert result['cpu_architecture'] == 'x86_64'
            assert result['cpu_count'] == 4
            assert result['memory_total'] == 0
            assert result['memory_available'] == 0
            
            # Should have error indicator
            assert 'error' in result
            assert 'memory' in result['error']
    
    def test_get_hardware_info_cpu_count_none(self):
        """Test hardware info when cpu_count returns None"""
        collector = EnhancedSystemInfo()
        
        mock_mem = MagicMock()
        mock_mem.total = 8000000000
        mock_mem.available = 4000000000
        
        with patch('platform.machine', return_value='arm64'), \
             patch('psutil.cpu_count', return_value=None), \
             patch('psutil.virtual_memory', return_value=mock_mem):
            
            result = collector.get_hardware_info()
            
            # Should handle None gracefully
            assert result['cpu_count'] == 0
            assert 'error' not in result


class TestSoftwareInventory:
    """Test software inventory collection"""
    
    def test_get_installed_software_windows(self):
        """Test software inventory on Windows - Requirement 5.5"""
        collector = EnhancedSystemInfo()
        
        # Mock Windows registry
        mock_key = MagicMock()
        mock_subkey = MagicMock()
        
        with patch('platform.system', return_value='Windows'), \
             patch('winreg.OpenKey', side_effect=[mock_key, mock_subkey]), \
             patch('winreg.QueryInfoKey', return_value=(1, 0, 0)), \
             patch('winreg.EnumKey', return_value='TestApp'), \
             patch('winreg.QueryValueEx', side_effect=[
                 ('Test Application', 1),
                 ('1.0.0', 1)
             ]), \
             patch('winreg.CloseKey'):
            
            result = collector.get_installed_software()
            
            assert 'software_list' in result
            assert 'software_count' in result
    
    def test_get_installed_software_linux_dpkg(self):
        """Test software inventory on Linux with dpkg - Requirement 5.5"""
        collector = EnhancedSystemInfo()
        
        # Mock subprocess for dpkg
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ii  test-package  1.0.0  Test package\n"
        
        with patch('platform.system', return_value='Linux'), \
             patch('subprocess.run', return_value=mock_result):
            
            result = collector.get_installed_software()
            
            assert 'software_list' in result
            assert result['software_count'] >= 0
    
    def test_get_installed_software_unsupported_os(self):
        """Test software inventory on unsupported OS - Requirement 5.4"""
        collector = EnhancedSystemInfo()
        
        with patch('platform.system', return_value='UnknownOS'):
            result = collector.get_installed_software()
            
            # Should return empty list with error
            assert result['software_count'] == 0
            assert result['software_list'] == []
            assert 'error' in result
            assert 'Unsupported OS' in result['error']
    
    def test_get_installed_software_error_handling(self):
        """Test software inventory error handling - Requirement 5.4"""
        collector = EnhancedSystemInfo()
        
        with patch('platform.system', side_effect=Exception('Platform error')):
            result = collector.get_installed_software()
            
            # Should return empty list with error
            assert result['software_count'] == 0
            assert result['software_list'] == []
            assert 'error' in result


class TestGetAllInfo:
    """Test comprehensive info collection"""
    
    def test_get_all_info_without_software(self):
        """Test getting all info without software inventory"""
        collector = EnhancedSystemInfo()
        
        # Mock all components
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ('192.168.1.100', 0)
        
        mock_mem = MagicMock()
        mock_mem.total = 8000000000
        mock_mem.available = 4000000000
        
        with patch('socket.gethostname', return_value='test-host'), \
             patch('getpass.getuser', return_value='test-user'), \
             patch('platform.system', return_value='Linux'), \
             patch('platform.release', return_value='5.10.0'), \
             patch('platform.machine', return_value='x86_64'), \
             patch('socket.socket', return_value=mock_socket), \
             patch('uuid.getnode', return_value=0x112233445566), \
             patch('psutil.net_if_addrs', return_value={}), \
             patch('psutil.net_if_stats', return_value={}), \
             patch('psutil.cpu_count', return_value=4), \
             patch('psutil.virtual_memory', return_value=mock_mem):
            
            result = collector.get_all_info(include_software=False)
            
            assert 'system' in result
            assert 'network' in result
            assert 'hardware' in result
            assert 'software' not in result
            
            # Verify system info
            assert result['system']['hostname'] == 'test-host'
            assert result['system']['username'] == 'test-user'
            
            # Verify network info
            assert result['network']['ip_address'] == '192.168.1.100'
            
            # Verify hardware info
            assert result['hardware']['cpu_count'] == 4
    
    def test_get_all_info_with_software(self):
        """Test getting all info with software inventory - Requirement 5.5"""
        collector = EnhancedSystemInfo()
        
        # Mock all components
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ('192.168.1.100', 0)
        
        mock_mem = MagicMock()
        mock_mem.total = 8000000000
        mock_mem.available = 4000000000
        
        with patch('socket.gethostname', return_value='test-host'), \
             patch('getpass.getuser', return_value='test-user'), \
             patch('platform.system', return_value='Linux'), \
             patch('platform.release', return_value='5.10.0'), \
             patch('platform.machine', return_value='x86_64'), \
             patch('socket.socket', return_value=mock_socket), \
             patch('uuid.getnode', return_value=0x112233445566), \
             patch('psutil.net_if_addrs', return_value={}), \
             patch('psutil.net_if_stats', return_value={}), \
             patch('psutil.cpu_count', return_value=4), \
             patch('psutil.virtual_memory', return_value=mock_mem), \
             patch('subprocess.run') as mock_run:
            
            # Mock dpkg output
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "ii  test-pkg  1.0  Test\n"
            mock_run.return_value = mock_result
            
            result = collector.get_all_info(include_software=True)
            
            assert 'system' in result
            assert 'network' in result
            assert 'hardware' in result
            assert 'software' in result
            
            # Verify software info is included
            assert 'software_list' in result['software']
            assert 'software_count' in result['software']


class TestErrorHandling:
    """Test comprehensive error handling"""
    
    def test_multiple_partial_failures(self):
        """Test handling multiple partial failures across components - Requirement 5.4"""
        collector = EnhancedSystemInfo()
        
        # Mock failures in different components
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = Exception('Network error')
        
        with patch('socket.gethostname', side_effect=Exception('Hostname error')), \
             patch('getpass.getuser', return_value='test-user'), \
             patch('platform.system', return_value='Linux'), \
             patch('platform.release', side_effect=Exception('Version error')), \
             patch('platform.machine', return_value='x86_64'), \
             patch('socket.socket', return_value=mock_socket), \
             patch('uuid.getnode', return_value=0x112233445566), \
             patch('psutil.net_if_addrs', return_value={}), \
             patch('psutil.net_if_stats', return_value={}), \
             patch('psutil.cpu_count', side_effect=Exception('CPU error')), \
             patch('psutil.virtual_memory', side_effect=Exception('Memory error')):
            
            result = collector.get_all_info()
            
            # All components should return partial data
            assert 'system' in result
            assert 'network' in result
            assert 'hardware' in result
            
            # Each should have error indicators
            assert 'error' in result['system']
            assert 'error' in result['network']
            assert 'error' in result['hardware']
            
            # But should still have some data
            assert result['system']['username'] == 'test-user'
            assert result['system']['os_type'] == 'Linux'
            assert result['network']['mac_address'] == '11:22:33:44:55:66'
            assert result['hardware']['cpu_architecture'] == 'x86_64'
