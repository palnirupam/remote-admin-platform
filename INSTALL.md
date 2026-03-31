# Installation Guide

This guide provides detailed instructions for installing and configuring the Remote System Enhancement platform.

## System Requirements

### Server Requirements

- **Operating System**: Linux (Ubuntu 20.04+, CentOS 8+), Windows Server 2016+, or macOS 10.15+
- **Python**: 3.8 or higher
- **RAM**: Minimum 2GB, recommended 4GB+ for large deployments
- **Storage**: 10GB+ for database and logs
- **Network**: Static IP address or dynamic DNS for internet deployment

### Agent Requirements

- **Operating System**: Windows 7+, Linux (any modern distribution), macOS 10.12+
- **Python**: 3.8+ (if running from source)
- **RAM**: 256MB minimum
- **Storage**: 50MB for agent executable and logs

## Installation Methods

### Method 1: Standard Installation (Recommended)

#### Step 1: Install Python

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.8 python3.8-venv python3-pip
```

**Linux (CentOS/RHEL):**
```bash
sudo yum install python38 python38-pip
```

**Windows:**
Download and install Python from [python.org](https://www.python.org/downloads/)
- Check "Add Python to PATH" during installation

**macOS:**
```bash
brew install python@3.8
```

#### Step 2: Clone Repository

```bash
git clone <repository-url>
cd remote-system-enhancement
```

#### Step 3: Create Virtual Environment

```bash
python3 -m venv venv
```

Activate the virtual environment:
- **Linux/macOS**: `source venv/bin/activate`
- **Windows**: `venv\Scripts\activate`

#### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 5: Generate TLS Certificates

For development (self-signed):
```bash
python -m remote_system.enhanced_server.tls_wrapper --generate-cert
```

For production, use certificates from a trusted CA.

#### Step 6: Configure Server

Create configuration file at `remote_system/enhanced_server/config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 9999,
    "use_tls": true,
    "cert_file": "server.crt",
    "key_file": "server.key"
  },
  "database": {
    "type": "sqlite",
    "path": "./data/remote_system.db"
  },
  "authentication": {
    "secret_key": "CHANGE_THIS_TO_RANDOM_STRING",
    "token_expiry": 86400
  },
  "web_ui": {
    "enabled": true,
    "port": 8080,
    "username": "admin",
    "password": "CHANGE_THIS_PASSWORD"
  }
}
```

**Important**: Change default passwords and secret keys!

#### Step 7: Initialize Database

```bash
python -m remote_system.enhanced_server.database_manager --init
```

#### Step 8: Start Server

```bash
python -m remote_system.enhanced_server.enhanced_server
```

Verify server is running:
- Agent port: `netstat -an | grep 9999`
- Web UI: Open browser to `http://localhost:8080`

### Method 2: Docker Installation

#### Step 1: Install Docker

Follow instructions at [docker.com](https://docs.docker.com/get-docker/)

#### Step 2: Build Docker Image

```bash
docker build -t remote-system-server .
```

#### Step 3: Run Container

```bash
docker run -d \
  --name remote-system-server \
  -p 9999:9999 \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  remote-system-server
```

#### Step 4: Verify Container

```bash
docker logs remote-system-server
docker ps | grep remote-system-server
```

### Method 3: Production Installation with PostgreSQL

#### Step 1: Install PostgreSQL

**Linux:**
```bash
sudo apt install postgresql postgresql-contrib
```

#### Step 2: Create Database

```bash
sudo -u postgres psql
CREATE DATABASE remote_system;
CREATE USER remote_admin WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE remote_system TO remote_admin;
\q
```

#### Step 3: Update Configuration

Modify `config.json`:
```json
{
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "remote_system",
    "username": "remote_admin",
    "password": "secure_password"
  }
}
```

#### Step 4: Install PostgreSQL Python Driver

```bash
pip install psycopg2-binary
```

## Building Agents

### Basic Agent Build

```bash
python -m remote_system.builder.enhanced_builder \
  --server-ip 192.168.1.100 \
  --server-port 9999 \
  --output ./output/agent.exe
```

### Advanced Agent Build with Options

```bash
python -m remote_system.builder.enhanced_builder \
  --server-ip 192.168.1.100 \
  --server-port 9999 \
  --output ./output/agent.exe \
  --icon ./resources/icon.ico \
  --company "Your Company" \
  --version "1.0.0" \
  --copyright "Copyright 2026" \
  --silent \
  --obfuscate
```

### Build Options

- `--server-ip`: Server IP address or domain name (required)
- `--server-port`: Server port (default: 9999)
- `--output`: Output file path (required)
- `--icon`: Custom icon file (.ico for Windows)
- `--company`: Company name for executable metadata
- `--version`: Version string
- `--copyright`: Copyright notice
- `--silent`: Run without console window
- `--obfuscate`: Enable code obfuscation with PyArmor

## Internet Deployment

### Option 1: Port Forwarding

1. Configure router to forward port 9999 to server
2. Find public IP: `curl ifconfig.me`
3. Build agent with public IP:
```bash
python -m remote_system.builder.enhanced_builder \
  --server-ip YOUR_PUBLIC_IP \
  --server-port 9999 \
  --output ./output/agent.exe
```

### Option 2: Ngrok Tunnel

1. Install Ngrok: [ngrok.com](https://ngrok.com/)
2. Start tunnel:
```bash
ngrok tcp 9999
```
3. Use Ngrok URL in agent build:
```bash
python -m remote_system.builder.enhanced_builder \
  --server-ip 0.tcp.ngrok.io \
  --server-port 12345 \
  --output ./output/agent.exe
```

### Option 3: Cloud VPS

1. Deploy server on cloud provider (AWS, DigitalOcean, etc.)
2. Configure firewall to allow port 9999
3. Build agent with VPS public IP

## Verification

### Verify Server Installation

```bash
# Check server process
ps aux | grep enhanced_server

# Check listening ports
netstat -tulpn | grep -E '9999|8080'

# Check database
python -m remote_system.enhanced_server.database_manager --check

# Check logs
tail -f logs/server.log
```

### Verify Agent Installation

```bash
# Test agent connection
python -m remote_system.enhanced_agent.enhanced_agent \
  --server-ip localhost \
  --server-port 9999 \
  --test-connection
```

## Troubleshooting

### Server Won't Start

**Issue**: Port already in use
```bash
# Find process using port
lsof -i :9999  # Linux/macOS
netstat -ano | findstr :9999  # Windows

# Kill process or change port in config
```

**Issue**: Permission denied
```bash
# Run with sudo (Linux) or Administrator (Windows)
sudo python -m remote_system.enhanced_server.enhanced_server
```

### Agent Won't Connect

**Issue**: Connection refused
- Verify server is running
- Check firewall rules
- Verify IP address and port

**Issue**: TLS certificate error
- Ensure certificates are properly generated
- Verify certificate pinning configuration

### Database Errors

**Issue**: Database locked (SQLite)
- Close other connections to database
- Consider switching to PostgreSQL for production

**Issue**: Connection pool exhausted
- Increase pool size in configuration
- Check for connection leaks

## Uninstallation

### Server Uninstallation

```bash
# Stop server
pkill -f enhanced_server

# Remove virtual environment
rm -rf venv

# Remove data (optional)
rm -rf data/

# Remove installation directory
cd ..
rm -rf remote-system-enhancement
```

### Agent Uninstallation

Agents can be removed using the remote uninstall command with password authentication. See USAGE.md for details.

## Next Steps

- Review [USAGE.md](USAGE.md) for common operations
- Configure security settings in [SECURITY.md](SECURITY.md)
- Set up production deployment using [DEPLOYMENT.md](DEPLOYMENT.md)
