"""
Integration tests for REST API Server with EnhancedServer

Tests the REST API with a real (but test-configured) EnhancedServer instance
to verify end-to-end functionality.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
"""

import pytest
import json
import base64
import tempfile
import os
from remote_system.enhanced_server.enhanced_server import EnhancedServer
from remote_system.web_ui.rest_api import RESTAPIServer


@pytest.fixture
def temp_db():
    """Create a temporary database file"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def enhanced_server(temp_db):
    """Create an EnhancedServer instance for testing"""
    server = EnhancedServer(
        host="127.0.0.1",
        port=19999,  # Use different port to avoid conflicts
        db_path=temp_db,
        use_tls=False,  # Disable TLS for testing
        secret_key="test_secret_key_for_integration"
    )
    yield server
    # Cleanup
    try:
        server.stop()
    except Exception:
        pass


@pytest.fixture
def api_server(enhanced_server):
    """Create REST API server with real EnhancedServer"""
    api = RESTAPIServer(
        core_server=enhanced_server,
        port=18080,
        web_username="testuser",
        web_password="testpass"
    )
    return api


@pytest.fixture
def client(api_server):
    """Create Flask test client"""
    api_server.app.config['TESTING'] = True
    return api_server.app.test_client()


@pytest.fixture
def auth_headers():
    """Create HTTP Basic Auth headers"""
    credentials = base64.b64encode(b"testuser:testpass").decode('utf-8')
    return {'Authorization': f'Basic {credentials}'}


class TestRESTAPIIntegration:
    """Integration tests with real EnhancedServer"""
    
    def test_get_agents_with_empty_database(self, client, auth_headers):
        """Test getting agents when database is empty"""
        response = client.get('/api/agents', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['agents'] == []
        assert data['count'] == 0
    
    def test_health_check_integration(self, client):
        """Test health check endpoint in integration"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['status'] == 'healthy'
    
    def test_send_command_to_nonexistent_agent(self, client, auth_headers):
        """Test sending command to agent that doesn't exist in database"""
        command = {'action': 'test'}
        response = client.post(
            '/api/agents/nonexistent-agent/command',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error']
    
    def test_get_history_for_nonexistent_agent(self, client, auth_headers):
        """Test getting history for agent that doesn't exist"""
        response = client.get(
            '/api/agents/nonexistent-agent/history',
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error']
    
    def test_broadcast_command_with_empty_agents(self, client, auth_headers):
        """Test broadcasting when no agents are connected"""
        command = {'action': 'test'}
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['queued_count'] == 0
    
    def test_authentication_required_for_all_endpoints(self, client):
        """Test that all protected endpoints require authentication"""
        endpoints = [
            ('GET', '/api/agents'),
            ('POST', '/api/agents/test/command'),
            ('GET', '/api/agents/test/history'),
            ('GET', '/api/agents/test/screenshot'),
            ('POST', '/api/agents/broadcast')
        ]
        
        for method, endpoint in endpoints:
            if method == 'GET':
                response = client.get(endpoint)
            else:
                response = client.post(
                    endpoint,
                    data=json.dumps({'command': {'action': 'test'}}),
                    content_type='application/json'
                )
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require auth"
            data = json.loads(response.data)
            assert data['success'] is False


class TestRESTAPIWithMockAgent:
    """Integration tests simulating agent registration"""
    
    def test_get_agents_after_manual_registration(self, client, auth_headers, enhanced_server):
        """Test getting agents after manually adding to database"""
        # Manually add an agent to the database
        agent_info = {
            'hostname': 'test-host',
            'username': 'testuser',
            'os_type': 'Windows',
            'os_version': '10',
            'ip_address': '127.0.0.1',
            'mac_address': '00:11:22:33:44:55',
            'capabilities': ['screenshot', 'file_transfer']
        }
        
        enhanced_server.db_manager.log_connection('test-agent-001', agent_info)
        
        # Get agents through API
        response = client.get('/api/agents', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 1
        assert data['agents'][0]['agent_id'] == 'test-agent-001'
        assert data['agents'][0]['hostname'] == 'test-host'
    
    def test_get_history_after_logging_commands(self, client, auth_headers, enhanced_server):
        """Test getting history after logging commands"""
        agent_id = 'test-agent-002'
        
        # Add agent
        agent_info = {
            'hostname': 'test-host-2',
            'username': 'testuser',
            'os_type': 'Linux',
            'os_version': 'Ubuntu 20.04',
            'ip_address': '127.0.0.1',
            'mac_address': '00:11:22:33:44:66',
            'capabilities': []
        }
        enhanced_server.db_manager.log_connection(agent_id, agent_info)
        
        # Log some commands
        log_id1 = enhanced_server.db_manager.log_command(
            agent_id=agent_id,
            command='whoami',
            result='testuser',
            status='success',
            execution_time=0.1
        )
        
        log_id2 = enhanced_server.db_manager.log_command(
            agent_id=agent_id,
            command='hostname',
            result='test-host-2',
            status='success',
            execution_time=0.05
        )
        
        # Get history through API
        response = client.get(f'/api/agents/{agent_id}/history', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 2
        assert len(data['history']) == 2
        
        # Verify commands are in reverse chronological order (newest first)
        assert data['history'][0]['log_id'] == log_id2
        assert data['history'][1]['log_id'] == log_id1
