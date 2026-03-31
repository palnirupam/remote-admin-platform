# 📖 Step-by-Step Guide - Remote Admin Platform

Complete guide to setup and use the Remote Admin Platform easily.

---

## 📋 Table of Contents

1. [Initial Setup](#1-initial-setup)
2. [Starting the Server](#2-starting-the-server)
3. [Connecting an Agent](#3-connecting-an-agent)
4. [Using the Web UI](#4-using-the-web-ui)
5. [Sending Notifications](#5-sending-notifications)
6. [Other Features](#6-other-features)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Initial Setup

### Step 1.1: Install Python

Make sure Python 3.7+ is installed:

```bash
# Check Python version
python --version

# Should show: Python 3.7.x or higher
```

### Step 1.2: Clone the Repository

```bash
# Clone from GitHub
git clone https://github.com/palnirupam/remote-admin-platform.git

# Go to project folder
cd remote-admin-platform
```

### Step 1.3: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate
```

### Step 1.4: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Wait for installation to complete
```

✅ **Setup Complete!** Now you're ready to run the system.

---

## 2. Starting the Server

### Step 2.1: Start the Server with Web UI

```bash
# Run the server
python run_web_ui.py
```

**You should see:**
```
🚀 Starting Remote Admin Platform Web UI...
============================================================
📡 Initializing Enhanced Server...
🌐 Initializing REST API Server...

✅ Starting servers...
[STARTED] Enhanced Server listening on 0.0.0.0:9999 with TLS

============================================================
✅ Web UI is now running!
============================================================

📊 Access the Web UI:
   URL: http://localhost:8080
   Username: admin
   Password: admin

📡 Server listening on:
   Host: 0.0.0.0
   Port: 9999

⚠️  Press Ctrl+C to stop the servers
============================================================
```

✅ **Server is running!** Keep this terminal open.

---

## 3. Connecting an Agent

### Step 3.1: Open a New Terminal

Open a **second terminal window** (keep the server running in the first one).

### Step 3.2: Activate Virtual Environment (in new terminal)

```bash
# Go to project folder
cd remote-admin-platform

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate
```

### Step 3.3: Start the Agent

```bash
# Run the agent (connects to localhost server)
python -m remote_system.enhanced_agent.enhanced_agent
```

**You should see:**
```
🤖 Enhanced Agent Starting...
   Connecting to: 127.0.0.1:9999
   TLS: Enabled
   Plugins: 7 loaded
✅ Connected to server!
⏳ Waiting for commands...
```

✅ **Agent connected!** Now you can control it from the Web UI.

---

## 4. Using the Web UI

### Step 4.1: Open Browser

Open your web browser and go to:
```
http://localhost:8080
```

### Step 4.2: Login

Enter credentials:
- **Username:** `admin`
- **Password:** `admin`

Click **Login**

### Step 4.3: View Connected Agents

You should see your connected agent in the dashboard:
- Hostname
- IP Address
- Operating System
- Status: **Online** (green)

### Step 4.4: Select an Agent

Click on the agent card to view details and send commands.

✅ **Web UI is ready!** You can now control the agent.

---

## 5. Sending Notifications

### Method 1: Using Web UI (Coming Soon)

The Web UI notification feature will be added in the next update.

### Method 2: Using REST API (Current Method)

#### Step 5.1: Get Agent ID

First, get the list of agents:

```bash
curl -u admin:admin http://localhost:8080/api/agents
```

**Response:**
```json
{
  "success": true,
  "agents": [
    {
      "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "hostname": "DESKTOP-ABC123",
      "status": "online"
    }
  ]
}
```

Copy the `agent_id` value.

#### Step 5.2: Send Notification

Replace `AGENT_ID` with your actual agent ID:

```bash
# Send info notification
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/notify \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello from server!\", \"title\": \"Test Message\", \"icon\": \"info\"}"
```

**The client PC will show a popup notification!** 🔔

#### Step 5.3: Send Different Types of Notifications

**Info Notification (Blue icon):**
```bash
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/notify \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"This is an information message\", \"title\": \"Info\", \"icon\": \"info\", \"duration\": 10}"
```

**Warning Notification (Yellow icon):**
```bash
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/notify \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Please check your system\", \"title\": \"Warning\", \"icon\": \"warning\", \"duration\": 15}"
```

**Error Notification (Red icon):**
```bash
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/notify \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Critical error detected!\", \"title\": \"Error\", \"icon\": \"error\", \"duration\": 20}"
```

**Custom Message (Your own text):**
```bash
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/notify \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello! How are you?\", \"title\": \"Server Message\"}"
```

✅ **Notifications working!** Client will see popup on screen.

---

## 6. Other Features

### 6.1: Execute Shell Commands

```bash
# Execute a command on client PC
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/command \
  -H "Content-Type: application/json" \
  -d "{\"command\": {\"plugin\": \"executor\", \"action\": \"execute\", \"args\": {\"command\": \"whoami\"}}}"
```

### 6.2: Capture Screenshot

```bash
# Take screenshot of client PC
curl -u admin:admin http://localhost:8080/api/agents/AGENT_ID/screenshot?quality=85&format=PNG
```

### 6.3: Get System Information

```bash
# Get client PC system info
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/command \
  -H "Content-Type: application/json" \
  -d "{\"command\": {\"plugin\": \"systeminfo\", \"action\": \"get_all\"}}"
```

### 6.4: View Command History

```bash
# Get last 50 commands
curl -u admin:admin http://localhost:8080/api/agents/AGENT_ID/history?limit=50
```

### 6.5: Broadcast to All Agents

```bash
# Send notification to ALL connected agents
curl -u admin:admin -X POST http://localhost:8080/api/agents/broadcast \
  -H "Content-Type: application/json" \
  -d "{\"command\": {\"plugin\": \"notification\", \"action\": \"show\", \"args\": {\"message\": \"Server announcement!\", \"title\": \"Broadcast\"}}}"
```

---

## 7. Troubleshooting

### Problem 1: Server won't start

**Error:** `Port 9999 already in use`

**Solution:**
```bash
# Check what's using the port
netstat -ano | findstr 9999

# Kill the process or use a different port
python run_web_ui.py --port 9998
```

### Problem 2: Agent can't connect

**Error:** `Connection refused`

**Solution:**
1. Make sure server is running first
2. Check firewall settings
3. Verify server IP and port

```bash
# Test server connection
curl http://localhost:8080/api/health
```

### Problem 3: Web UI not loading

**Error:** `Cannot connect to localhost:8080`

**Solution:**
1. Check if server is running
2. Try different browser
3. Clear browser cache

```bash
# Check if REST API is responding
curl http://localhost:8080/api/health
```

### Problem 4: Notification not showing on client

**Possible causes:**
1. Agent not connected (check status)
2. Wrong agent ID
3. Client PC notification settings disabled

**Solution:**
```bash
# Verify agent is online
curl -u admin:admin http://localhost:8080/api/agents

# Check agent status should be "online"
```

### Problem 5: Authentication failed

**Error:** `401 Unauthorized`

**Solution:**
- Make sure you're using correct credentials: `admin` / `admin`
- Include `-u admin:admin` in curl commands

---

## 🎯 Quick Reference Commands

### Start Server
```bash
python run_web_ui.py
```

### Start Agent
```bash
python -m remote_system.enhanced_agent.enhanced_agent
```

### Get Agents List
```bash
curl -u admin:admin http://localhost:8080/api/agents
```

### Send Notification
```bash
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/notify \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Your message here\", \"title\": \"Title\"}"
```

### Execute Command
```bash
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/command \
  -H "Content-Type: application/json" \
  -d "{\"command\": {\"plugin\": \"executor\", \"action\": \"execute\", \"args\": {\"command\": \"dir\"}}}"
```

### Stop Server
```
Press Ctrl+C in the server terminal
```

---

## 📚 Additional Resources

- **Full Documentation:** [README.md](README.md)
- **Usage Examples:** [USAGE.md](USAGE.md)
- **API Reference:** [API.md](API.md)
- **Security Guide:** [SECURITY.md](SECURITY.md)
- **Installation Guide:** [INSTALL.md](INSTALL.md)

---

## 🆘 Need Help?

- **GitHub Issues:** https://github.com/palnirupam/remote-admin-platform/issues
- **Documentation:** Check the docs folder
- **Email Support:** Contact repository owner

---

**🎉 Congratulations!** You now know how to use the Remote Admin Platform!

For advanced features and configurations, check the full documentation.
