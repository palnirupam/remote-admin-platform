"""
Unit tests for REST API Server

Tests all endpoints with mock server and database, authentication,
command routing, history retrieval, and error handling.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
"""

import pytest
import json
import base64
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from remote_system.web_ui.rest_api import RESTAPIServer


@pytest.fixture
def mock_core_server():
    """Create a mock EnhancedServer instance"""
    server = Mock()
    server.db_manager = Mock()
    server.get_active_agents = Mock()
    server.broadcast_command = Mock()
    return server


@pytest.fixture
def api_server(mock_core_server):
    """Create REST API server instance with mock core server"""
    return RESTAPIServer(
        core_server=mock_core_server,
        port=8080,
        web_username="testuser",
        web_password="testpass"
    )


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


@pytest.fixture
def invalid_auth_headers():
    """Create invalid HTTP Basic Auth headers"""
    credentials = base64.b64encode(b"wrong:wrong").decode('utf-8')
    return {'Authorization': f'Basic {credentials}'}



class TestRESTAPIServerInitialization:
    """Test REST API server initialization"""
    
    def test_initialization_with_defaults(self, mock_core_server):
        """Test initialization with default parameters"""
        api = RESTAPIServer(core_server=mock_core_server)
        
        assert api.core_server == mock_core_server
        assert api.port == 8080
        assert api.web_username == "admin"
        assert api.web_password == "admin"
        assert api.running is False
    
    def test_initialization_with_custom_params(self, mock_core_server):
        """Test initialization with custom parameters"""
        api = RESTAPIServer(
            core_server=mock_core_server,
            port=9090,
            web_username="custom_user",
            web_password="custom_pass"
        )
        
        assert api.port == 9090
        assert api.web_username == "custom_user"
        assert api.web_password == "custom_pass"


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_no_auth_required(self, client):
        """Test health endpoint doesn't require authentication"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_health_check_returns_timestamp(self, client):
        """Test health endpoint returns valid timestamp"""
        response = client.get('/api/health')
        data = json.loads(response.data)
        
        # Verify timestamp is valid ISO format
        timestamp = datetime.fromisoformat(data['timestamp'])
        assert isinstance(timestamp, datetime)


class TestAuthentication:
    """Test authentication middleware - Requirement 11.8"""
    
    def test_get_agents_without_auth(self, client):
        """Test that endpoints require authentication"""
        response = client.get('/api/agents')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Authentication required' in data['error']
    
    def test_get_agents_with_invalid_auth(self, client, invalid_auth_headers):
        """Test authentication failure with wrong credentials"""
        response = client.get('/api/agents', headers=invalid_auth_headers)
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid credentials' in data['error']
    
    def test_get_agents_with_valid_auth(self, client, auth_headers, mock_core_server):
        """Test authentication success with correct credentials"""
        mock_core_server.get_active_agents.return_value = []
        
        response = client.get('/api/agents', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True



class TestGetAgentsEndpoint:
    """Test GET /api/agents endpoint - Requirements 11.1, 11.2"""
    
    def test_get_agents_empty_list(self, client, auth_headers, mock_core_server):
        """Test getting agents when no agents are active"""
        mock_core_server.get_active_agents.return_value = []
        
        response = client.get('/api/agents', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['agents'] == []
        assert data['count'] == 0
    
    def test_get_agents_with_active_agents(self, client, auth_headers, mock_core_server):
        """Test getting list of active agents"""
        mock_agents = [
            {
                'agent_id': 'agent-001',
                'hostname': 'test-host-1',
                'username': 'user1',
                'os_type': 'Windows',
                'status': 'online'
            },
            {
                'agent_id': 'agent-002',
                'hostname': 'test-host-2',
                'username': 'user2',
                'os_type': 'Linux',
                'status': 'online'
            }
        ]
        mock_core_server.get_active_agents.return_value = mock_agents
        
        response = client.get('/api/agents', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['agents']) == 2
        assert data['count'] == 2
        assert data['agents'][0]['agent_id'] == 'agent-001'
        assert data['agents'][1]['agent_id'] == 'agent-002'
    
    def test_get_agents_server_error(self, client, auth_headers, mock_core_server):
        """Test error handling when server fails"""
        mock_core_server.get_active_agents.side_effect = Exception("Database error")
        
        response = client.get('/api/agents', headers=auth_headers)
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Database error' in data['error']


class TestSendCommandEndpoint:
    """Test POST /api/agents/<agent_id>/command endpoint - Requirements 11.3, 11.4"""
    
    def test_send_command_success(self, client, auth_headers, mock_core_server):
        """Test sending command to online agent"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'online'
        }
        mock_core_server.broadcast_command.return_value = {agent_id: 'queued'}
        
        command = {'action': 'execute', 'cmd': 'whoami'}
        response = client.post(
            f'/api/agents/{agent_id}/command',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['agent_id'] == agent_id
        assert 'queued successfully' in data['message']
        
        # Verify broadcast_command was called correctly
        mock_core_server.broadcast_command.assert_called_once_with(command, [agent_id])
    
    def test_send_command_missing_json(self, client, auth_headers, mock_core_server):
        """Test sending command without JSON content type"""
        response = client.post(
            '/api/agents/agent-001/command',
            headers=auth_headers,
            data='not json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'must be JSON' in data['error']
    
    def test_send_command_missing_command_field(self, client, auth_headers, mock_core_server):
        """Test sending request without command field"""
        response = client.post(
            '/api/agents/agent-001/command',
            headers=auth_headers,
            data=json.dumps({'other': 'data'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Missing command field' in data['error']
    
    def test_send_command_agent_not_found(self, client, auth_headers, mock_core_server):
        """Test sending command to non-existent agent"""
        mock_core_server.db_manager.get_agent_by_id.return_value = None
        
        command = {'action': 'test'}
        response = client.post(
            '/api/agents/nonexistent/command',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error']
    
    def test_send_command_agent_offline(self, client, auth_headers, mock_core_server):
        """Test sending command to offline agent"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'offline'
        }
        
        command = {'action': 'test'}
        response = client.post(
            f'/api/agents/{agent_id}/command',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'offline' in data['error']



class TestGetHistoryEndpoint:
    """Test GET /api/agents/<agent_id>/history endpoint - Requirements 11.4, 11.6"""
    
    def test_get_history_success(self, client, auth_headers, mock_core_server):
        """Test retrieving command history for agent"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'online'
        }
        mock_history = [
            {
                'log_id': 1,
                'command': 'whoami',
                'result': 'user',
                'status': 'success',
                'executed_at': '2024-01-01T12:00:00'
            },
            {
                'log_id': 2,
                'command': 'hostname',
                'result': 'test-host',
                'status': 'success',
                'executed_at': '2024-01-01T12:01:00'
            }
        ]
        mock_core_server.db_manager.get_agent_history.return_value = mock_history
        
        response = client.get(
            f'/api/agents/{agent_id}/history',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['agent_id'] == agent_id
        assert len(data['history']) == 2
        assert data['count'] == 2
        
        # Verify get_agent_history was called with default limit
        mock_core_server.db_manager.get_agent_history.assert_called_once_with(agent_id, 100)
    
    def test_get_history_with_custom_limit(self, client, auth_headers, mock_core_server):
        """Test retrieving history with custom limit"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'online'
        }
        mock_core_server.db_manager.get_agent_history.return_value = []
        
        response = client.get(
            f'/api/agents/{agent_id}/history?limit=50',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        mock_core_server.db_manager.get_agent_history.assert_called_once_with(agent_id, 50)
    
    def test_get_history_limit_too_low(self, client, auth_headers, mock_core_server):
        """Test history with limit below minimum"""
        response = client.get(
            '/api/agents/agent-001/history?limit=0',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'between 1 and 1000' in data['error']
    
    def test_get_history_limit_too_high(self, client, auth_headers, mock_core_server):
        """Test history with limit above maximum"""
        response = client.get(
            '/api/agents/agent-001/history?limit=2000',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'between 1 and 1000' in data['error']
    
    def test_get_history_agent_not_found(self, client, auth_headers, mock_core_server):
        """Test getting history for non-existent agent"""
        mock_core_server.db_manager.get_agent_by_id.return_value = None
        
        response = client.get(
            '/api/agents/nonexistent/history',
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error']
    
    def test_get_history_empty(self, client, auth_headers, mock_core_server):
        """Test getting history when no commands executed"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'online'
        }
        mock_core_server.db_manager.get_agent_history.return_value = []
        
        response = client.get(
            f'/api/agents/{agent_id}/history',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['history'] == []
        assert data['count'] == 0


class TestGetScreenshotEndpoint:
    """Test GET /api/agents/<agent_id>/screenshot endpoint - Requirement 11.5"""
    
    def test_get_screenshot_success(self, client, auth_headers, mock_core_server):
        """Test capturing screenshot from agent"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'online'
        }
        mock_core_server.broadcast_command.return_value = {agent_id: 'queued'}
        
        response = client.get(
            f'/api/agents/{agent_id}/screenshot',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'queued' in data['message']
        
        # Verify screenshot command was queued
        call_args = mock_core_server.broadcast_command.call_args
        command = call_args[0][0]
        assert command['plugin'] == 'screenshot'
        assert command['action'] == 'capture'
        assert command['args']['quality'] == 85
        assert command['args']['format'] == 'PNG'
    
    def test_get_screenshot_with_custom_quality(self, client, auth_headers, mock_core_server):
        """Test screenshot with custom quality parameter"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'online'
        }
        mock_core_server.broadcast_command.return_value = {agent_id: 'queued'}
        
        response = client.get(
            f'/api/agents/{agent_id}/screenshot?quality=50',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        call_args = mock_core_server.broadcast_command.call_args
        command = call_args[0][0]
        assert command['args']['quality'] == 50
    
    def test_get_screenshot_with_custom_format(self, client, auth_headers, mock_core_server):
        """Test screenshot with custom format parameter"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'online'
        }
        mock_core_server.broadcast_command.return_value = {agent_id: 'queued'}
        
        response = client.get(
            f'/api/agents/{agent_id}/screenshot?format=JPEG',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        call_args = mock_core_server.broadcast_command.call_args
        command = call_args[0][0]
        assert command['args']['format'] == 'JPEG'
    
    def test_get_screenshot_invalid_quality(self, client, auth_headers, mock_core_server):
        """Test screenshot with invalid quality parameter"""
        response = client.get(
            '/api/agents/agent-001/screenshot?quality=150',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'between 1 and 100' in data['error']
    
    def test_get_screenshot_invalid_format(self, client, auth_headers, mock_core_server):
        """Test screenshot with invalid format parameter"""
        response = client.get(
            '/api/agents/agent-001/screenshot?format=GIF',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'PNG, JPEG, or BMP' in data['error']
    
    def test_get_screenshot_agent_offline(self, client, auth_headers, mock_core_server):
        """Test screenshot from offline agent"""
        agent_id = 'agent-001'
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'offline'
        }
        
        response = client.get(
            f'/api/agents/{agent_id}/screenshot',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'offline' in data['error']



class TestBroadcastCommandEndpoint:
    """Test POST /api/agents/broadcast endpoint - Requirement 11.7"""
    
    def test_broadcast_to_all_agents(self, client, auth_headers, mock_core_server):
        """Test broadcasting command to all agents"""
        mock_core_server.broadcast_command.return_value = {
            'agent-001': 'queued',
            'agent-002': 'queued',
            'agent-003': 'queued'
        }
        
        command = {'action': 'update', 'version': '2.0'}
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['queued_count'] == 3
        assert data['total_count'] == 3
        
        # Verify broadcast_command was called with None for agent_ids (all agents)
        mock_core_server.broadcast_command.assert_called_once_with(command, None)
    
    def test_broadcast_to_specific_agents(self, client, auth_headers, mock_core_server):
        """Test broadcasting command to specific agents"""
        agent_ids = ['agent-001', 'agent-002']
        mock_core_server.broadcast_command.return_value = {
            'agent-001': 'queued',
            'agent-002': 'queued'
        }
        
        command = {'action': 'restart'}
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data=json.dumps({'command': command, 'agent_ids': agent_ids}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['queued_count'] == 2
        
        # Verify broadcast_command was called with specific agent_ids
        mock_core_server.broadcast_command.assert_called_once_with(command, agent_ids)
    
    def test_broadcast_missing_command(self, client, auth_headers, mock_core_server):
        """Test broadcast without command field"""
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data=json.dumps({'agent_ids': ['agent-001']}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Missing command field' in data['error']
    
    def test_broadcast_invalid_agent_ids_type(self, client, auth_headers, mock_core_server):
        """Test broadcast with invalid agent_ids type"""
        command = {'action': 'test'}
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data=json.dumps({'command': command, 'agent_ids': 'not-a-list'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'must be a list' in data['error']
    
    def test_broadcast_empty_agent_ids(self, client, auth_headers, mock_core_server):
        """Test broadcast with empty agent_ids list"""
        command = {'action': 'test'}
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data=json.dumps({'command': command, 'agent_ids': []}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'cannot be empty' in data['error']
    
    def test_broadcast_partial_success(self, client, auth_headers, mock_core_server):
        """Test broadcast with some agents not found"""
        mock_core_server.broadcast_command.return_value = {
            'agent-001': 'queued',
            'agent-002': 'not_found',
            'agent-003': 'queued'
        }
        
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
        assert data['queued_count'] == 2
        assert data['total_count'] == 3
        assert data['results']['agent-002'] == 'not_found'
    
    def test_broadcast_not_json(self, client, auth_headers, mock_core_server):
        """Test broadcast without JSON content type"""
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data='not json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'must be JSON' in data['error']


class TestErrorHandling:
    """Test error handling across all endpoints"""
    
    def test_send_command_exception(self, client, auth_headers, mock_core_server):
        """Test exception handling in send_command endpoint"""
        mock_core_server.db_manager.get_agent_by_id.side_effect = Exception("Database connection failed")
        
        command = {'action': 'test'}
        response = client.post(
            '/api/agents/agent-001/command',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Database connection failed' in data['error']
    
    def test_get_history_exception(self, client, auth_headers, mock_core_server):
        """Test exception handling in get_history endpoint"""
        mock_core_server.db_manager.get_agent_by_id.side_effect = Exception("Query failed")
        
        response = client.get(
            '/api/agents/agent-001/history',
            headers=auth_headers
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Query failed' in data['error']
    
    def test_broadcast_exception(self, client, auth_headers, mock_core_server):
        """Test exception handling in broadcast endpoint"""
        mock_core_server.broadcast_command.side_effect = Exception("Broadcast failed")
        
        command = {'action': 'test'}
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Broadcast failed' in data['error']


class TestIntegrationScenarios:
    """Test integration scenarios across multiple endpoints"""
    
    def test_full_workflow_get_agents_send_command_check_history(
        self, client, auth_headers, mock_core_server
    ):
        """Test complete workflow: get agents, send command, check history"""
        agent_id = 'agent-001'
        
        # Step 1: Get agents
        mock_core_server.get_active_agents.return_value = [
            {'agent_id': agent_id, 'hostname': 'test-host', 'status': 'online'}
        ]
        response = client.get('/api/agents', headers=auth_headers)
        assert response.status_code == 200
        
        # Step 2: Send command
        mock_core_server.db_manager.get_agent_by_id.return_value = {
            'agent_id': agent_id,
            'status': 'online'
        }
        mock_core_server.broadcast_command.return_value = {agent_id: 'queued'}
        
        command = {'action': 'whoami'}
        response = client.post(
            f'/api/agents/{agent_id}/command',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # Step 3: Check history
        mock_core_server.db_manager.get_agent_history.return_value = [
            {
                'log_id': 1,
                'command': json.dumps(command),
                'result': 'testuser',
                'status': 'success'
            }
        ]
        response = client.get(f'/api/agents/{agent_id}/history', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['history']) == 1
    
    def test_multiple_agents_broadcast_workflow(
        self, client, auth_headers, mock_core_server
    ):
        """Test broadcasting to multiple agents and checking results"""
        # Get multiple agents
        mock_agents = [
            {'agent_id': f'agent-{i:03d}', 'status': 'online'}
            for i in range(5)
        ]
        mock_core_server.get_active_agents.return_value = mock_agents
        
        response = client.get('/api/agents', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 5
        
        # Broadcast command to all
        mock_core_server.broadcast_command.return_value = {
            agent['agent_id']: 'queued' for agent in mock_agents
        }
        
        command = {'action': 'update'}
        response = client.post(
            '/api/agents/broadcast',
            headers=auth_headers,
            data=json.dumps({'command': command}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['queued_count'] == 5
