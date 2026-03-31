"""
Integration tests for Web UI Frontend

Tests the web UI functionality including agent list display, command execution,
real-time updates, and authentication flow.

Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
"""

import pytest
import threading
import time
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch
from remote_system.web_ui.rest_api import RESTAPIServer
from remote_system.enhanced_server.enhanced_server import EnhancedServer
from remote_system.enhanced_server.database_manager import DatabaseManager


class TestWebUIIntegration:
    """Integration tests for web UI functionality"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)
    
    @pytest.fixture
    def mock_server(self, temp_db):
        """Create mock enhanced server"""
        server = Mock(spec=EnhancedServer)
        server.db_manager = Mock(spec=DatabaseManager)
        
        # Mock agent data
        server.get_active_agents = Mock(return_value=[
            {
                'agent_id': 'test-agent-1',
                'hostname': 'test-host-1',
                'username': 'testuser',
                'os_type': 'Windows',
                'os_version': '10',
                'ip_address': '192.168.1.100',
                'mac_address': '00:11:22:33:44:55',
                'status': 'online',
                'connected_at': '2024-01-01T00:00:00',
                'last_seen': '2024-01-01T00:05:00'
            },
            {
                'agent_id': 'test-agent-2',
                'hostname': 'test-host-2',
                'username': 'testuser2',
                'os_type': 'Linux',
                'os_version': 'Ubuntu 20.04',
                'ip_address': '192.168.1.101',
                'mac_address': '00:11:22:33:44:56',
                'status': 'offline',
                'connected_at': '2024-01-01T00:00:00',
                'last_seen': '2024-01-01T00:03:00'
            }
        ])
        
        # Mock command broadcasting
        server.broadcast_command = Mock(return_value={'test-agent-1': 'queued'})
        
        # Mock database methods
        server.db_manager.get_agent_by_id = Mock(return_value={
            'agent_id': 'test-agent-1',
            'hostname': 'test-host-1',
            'status': 'online'
        })
        
        server.db_manager.get_agent_history = Mock(return_value=[
            {
                'log_id': 'log-1',
                'agent_id': 'test-agent-1',
                'command': {'plugin': 'executor', 'args': {'command': 'dir'}},
                'result': 'Directory listing...',
                'status': 'success',
                'executed_at': '2024-01-01T00:01:00',
                'execution_time': 0.5
            },
            {
                'log_id': 'log-2',
                'agent_id': 'test-agent-1',
                'command': {'plugin': 'screenshot', 'action': 'capture'},
                'result': 'Screenshot captured',
                'status': 'success',
                'executed_at': '2024-01-01T00:02:00',
                'execution_time': 1.2
            }
        ])
        
        return server
    
    @pytest.fixture
    def api_server(self, mock_server):
        """Create REST API server for testing"""
        server = RESTAPIServer(
            core_server=mock_server,
            port=8081,  # Use different port for testing
            web_username='admin',
            web_password='admin'
        )
        return server
    
    @pytest.fixture
    def client(self, api_server):
        """Create Flask test client"""
        api_server.app.config['TESTING'] = True
        return api_server.app.test_client()
    
    def test_static_files_served(self, client):
        """
        Test that static files are served correctly
        
        Requirements: 11.1
        """
        # Test index.html
        response = client.get('/')
        assert response.status_code == 200
        assert b'Remote System Control' in response.data
        
        # Test CSS file
        response = client.get('/styles.css')
        assert response.status_code == 200
        assert b'body' in response.data
        
        # Test JS file
        response = client.get('/app.js')
        assert response.status_code == 200
        assert b'RemoteSystemApp' in response.data
    
    def test_agent_list_display(self, client, mock_server):
        """
        Test agent list display and updates
        
        Requirements: 11.2
        """
        # Test without authentication
        response = client.get('/api/agents')
        assert response.status_code == 401
        
        # Test with authentication
        auth_header = self._get_auth_header('admin', 'admin')
        response = client.get('/api/agents', headers=auth_header)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'agents' in data
        assert len(data['agents']) == 2
        
        # Verify agent data
        agent1 = data['agents'][0]
        assert agent1['agent_id'] == 'test-agent-1'
        assert agent1['hostname'] == 'test-host-1'
        assert agent1['status'] == 'online'
        
        agent2 = data['agents'][1]
        assert agent2['agent_id'] == 'test-agent-2'
        assert agent2['status'] == 'offline'
    
    def test_command_execution_flow(self, client, mock_server):
        """
        Test command execution flow through web UI
        
        Requirements: 11.3, 11.4
        """
        auth_header = self._get_auth_header('admin', 'admin')
        
        # Test command execution
        command = {
            'command': {
                'plugin': 'executor',
                'action': 'execute',
                'args': {'command': 'dir'}
            }
        }
        
        response = client.post(
            '/api/agents/test-agent-1/command',
            json=command,
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Command queued successfully'
        assert data['agent_id'] == 'test-agent-1'
        
        # Verify broadcast_command was called
        mock_server.broadcast_command.assert_called_once()
    
    def test_command_execution_invalid_agent(self, client, mock_server):
        """
        Test command execution with invalid agent
        
        Requirements: 11.3
        """
        auth_header = self._get_auth_header('admin', 'admin')
        
        # Mock agent not found
        mock_server.db_manager.get_agent_by_id.return_value = None
        
        command = {
            'command': {
                'plugin': 'executor',
                'args': {'command': 'dir'}
            }
        }
        
        response = client.post(
            '/api/agents/invalid-agent/command',
            json=command,
            headers=auth_header
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error']
    
    def test_command_history_retrieval(self, client, mock_server):
        """
        Test command history view with filtering
        
        Requirements: 11.4, 11.6
        """
        auth_header = self._get_auth_header('admin', 'admin')
        
        # Test history retrieval
        response = client.get(
            '/api/agents/test-agent-1/history',
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'history' in data
        assert len(data['history']) == 2
        
        # Verify history data
        history1 = data['history'][0]
        assert history1['log_id'] == 'log-1'
        assert history1['status'] == 'success'
        assert 'command' in history1
        
        # Test with limit parameter
        response = client.get(
            '/api/agents/test-agent-1/history?limit=1',
            headers=auth_header
        )
        
        assert response.status_code == 200
        mock_server.db_manager.get_agent_history.assert_called_with('test-agent-1', 1)
    
    def test_screenshot_command(self, client, mock_server):
        """
        Test screenshot viewer component
        
        Requirements: 11.5
        """
        auth_header = self._get_auth_header('admin', 'admin')
        
        # Test screenshot request
        response = client.get(
            '/api/agents/test-agent-1/screenshot?quality=85&format=PNG',
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'Screenshot command queued' in data['message']
        
        # Verify command was queued with correct parameters
        mock_server.broadcast_command.assert_called()
        call_args = mock_server.broadcast_command.call_args
        command = call_args[0][0]
        assert command['plugin'] == 'screenshot'
        assert command['args']['quality'] == 85
        assert command['args']['format'] == 'PNG'
    
    def test_broadcast_command(self, client, mock_server):
        """
        Test broadcast command to multiple agents
        
        Requirements: 11.7
        """
        auth_header = self._get_auth_header('admin', 'admin')
        
        # Mock broadcast result
        mock_server.broadcast_command.return_value = {
            'test-agent-1': 'queued',
            'test-agent-2': 'queued'
        }
        
        # Test broadcast to all agents
        command = {
            'command': {
                'plugin': 'executor',
                'args': {'command': 'whoami'}
            }
        }
        
        response = client.post(
            '/api/agents/broadcast',
            json=command,
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['queued_count'] == 2
        assert data['total_count'] == 2
        
        # Test broadcast to specific agents
        command['agent_ids'] = ['test-agent-1']
        mock_server.broadcast_command.return_value = {'test-agent-1': 'queued'}
        
        response = client.post(
            '/api/agents/broadcast',
            json=command,
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['queued_count'] == 1
    
    def test_authentication_flow(self, client):
        """
        Test authentication login page and flow
        
        Requirements: 11.8
        """
        # Test without authentication
        response = client.get('/api/agents')
        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False
        assert 'Authentication required' in data['error']
        
        # Test with invalid credentials
        auth_header = self._get_auth_header('wrong', 'credentials')
        response = client.get('/api/agents', headers=auth_header)
        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False
        assert 'Invalid credentials' in data['error']
        
        # Test with valid credentials
        auth_header = self._get_auth_header('admin', 'admin')
        response = client.get('/api/agents', headers=auth_header)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_health_check_endpoint(self, client):
        """
        Test health check endpoint (no auth required)
        
        Requirements: 11.1
        """
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_invalid_request_handling(self, client, mock_server):
        """
        Test error handling for invalid requests
        
        Requirements: 11.3, 11.4
        """
        auth_header = self._get_auth_header('admin', 'admin')
        
        # Test missing command field
        response = client.post(
            '/api/agents/test-agent-1/command',
            json={},
            headers=auth_header
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Missing command field' in data['error']
        
        # Test non-JSON request
        response = client.post(
            '/api/agents/test-agent-1/command',
            data='not json',
            headers=auth_header
        )
        assert response.status_code == 400
        
        # Test invalid limit parameter
        response = client.get(
            '/api/agents/test-agent-1/history?limit=9999',
            headers=auth_header
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'Limit must be between' in data['error']
    
    def test_offline_agent_command(self, client, mock_server):
        """
        Test command execution on offline agent
        
        Requirements: 11.3
        """
        auth_header = self._get_auth_header('admin', 'admin')
        
        # Mock offline agent
        mock_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': 'test-agent-2',
            'status': 'offline'
        }
        
        command = {
            'command': {
                'plugin': 'executor',
                'args': {'command': 'dir'}
            }
        }
        
        response = client.post(
            '/api/agents/test-agent-2/command',
            json=command,
            headers=auth_header
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'offline' in data['error']
    
    def _get_auth_header(self, username, password):
        """Helper to create Basic Auth header"""
        import base64
        credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
        return {'Authorization': f'Basic {credentials}'}


class TestWebUIComponents:
    """Test individual web UI components"""
    
    def test_html_structure(self):
        """
        Test HTML structure contains required elements
        
        Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
        """
        html_path = os.path.join(
            os.path.dirname(__file__),
            '../remote_system/web_ui/static/index.html'
        )
        
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Check for login page
        assert 'id="login-page"' in html_content
        assert 'id="login-form"' in html_content
        
        # Check for dashboard
        assert 'id="dashboard-page"' in html_content
        assert 'id="agent-list"' in html_content
        
        # Check for agent detail
        assert 'id="agent-detail-section"' in html_content
        assert 'id="command-form"' in html_content
        assert 'id="command-history"' in html_content
        
        # Check for screenshot modal
        assert 'id="screenshot-modal"' in html_content
    
    def test_css_file_exists(self):
        """
        Test CSS file exists and contains styles
        
        Requirements: 11.1
        """
        css_path = os.path.join(
            os.path.dirname(__file__),
            '../remote_system/web_ui/static/styles.css'
        )
        
        assert os.path.exists(css_path)
        
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Check for key styles
        assert '.agent-card' in css_content
        assert '.login-container' in css_content
        assert '.command-section' in css_content
    
    def test_javascript_file_exists(self):
        """
        Test JavaScript file exists and contains app logic
        
        Requirements: 11.1
        """
        js_path = os.path.join(
            os.path.dirname(__file__),
            '../remote_system/web_ui/static/app.js'
        )
        
        assert os.path.exists(js_path)
        
        with open(js_path, 'r') as f:
            js_content = f.read()
        
        # Check for key classes and methods
        assert 'class RemoteSystemApp' in js_content
        assert 'handleLogin' in js_content
        assert 'loadAgents' in js_content
        assert 'executeCommand' in js_content
        assert 'loadHistory' in js_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
