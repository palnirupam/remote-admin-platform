# Production Deployment Guide

This guide provides instructions for deploying the Remote System Enhancement platform in production environments.

## Table of Contents

- [Deployment Architecture](#deployment-architecture)
- [Infrastructure Requirements](#infrastructure-requirements)
- [Server Deployment](#server-deployment)
- [Database Setup](#database-setup)
- [Web Interface Deployment](#web-interface-deployment)
- [Agent Deployment](#agent-deployment)
- [High Availability](#high-availability)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Backup and Recovery](#backup-and-recovery)
- [Scaling](#scaling)

## Deployment Architecture

### Single Server Deployment

```
┌─────────────────────────────────────┐
│         Production Server           │
│  ┌──────────────────────────────┐  │
│  │   Enhanced Server (Port 9999) │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │   REST API (Port 8080)       │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │   PostgreSQL Database        │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### High Availability Deployment

```
┌─────────────┐     ┌─────────────┐
│  Server 1   │     │  Server 2   │
│  (Active)   │────▶│  (Standby)  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └───────┬───────────┘
               │
        ┌──────▼──────┐
        │  PostgreSQL │
        │   Cluster   │
        └─────────────┘
```

### Cloud Deployment

```
┌─────────────────────────────────────┐
│         Cloud Provider (AWS/Azure)  │
│  ┌──────────────────────────────┐  │
│  │   Load Balancer              │  │
│  └────────┬─────────────────────┘  │
│           │                         │
│  ┌────────▼────────┐  ┌──────────┐ │
│  │  Server Instance│  │  Server  │ │
│  │  (Auto-scaling) │  │ Instance │ │
│  └────────┬────────┘  └────┬─────┘ │
│           │                │        │
│  ┌────────▼────────────────▼─────┐ │
│  │   Managed Database (RDS)     │ │
│  └──────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Infrastructure Requirements

### Server Specifications

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 50GB SSD
- Network: 100 Mbps
- OS: Ubuntu 20.04 LTS, CentOS 8, or Windows Server 2016+

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 100GB+ SSD
- Network: 1 Gbps
- OS: Ubuntu 22.04 LTS or CentOS Stream 9

**Large Scale (1000+ agents):**
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 500GB+ SSD
- Network: 10 Gbps
- OS: Ubuntu 22.04 LTS

### Network Requirements

**Ports:**
- 9999: Agent connections (TCP)
- 8080: Web interface (TCP)
- 5432: PostgreSQL (TCP, internal only)

**Bandwidth:**
- Minimum: 10 Mbps per 100 agents
- Recommended: 100 Mbps per 1000 agents
- Consider file transfer and screenshot traffic

**Firewall Rules:**
```bash
# Allow agent connections from specific networks
sudo ufw allow from 10.0.0.0/8 to any port 9999

# Allow web interface from admin networks
sudo ufw allow from 192.168.1.0/24 to any port 8080

# Deny all other traffic
sudo ufw default deny incoming
sudo ufw enable
```

## Server Deployment

### Step 1: Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3-pip python3-venv \
    postgresql postgresql-contrib nginx supervisor

# Create dedicated user
sudo useradd -r -m -s /bin/bash remote_system
sudo mkdir -p /opt/remote_system
sudo chown remote_system:remote_system /opt/remote_system
```

### Step 2: Install Application

```bash
# Switch to application user
sudo su - remote_system

# Clone repository
cd /opt/remote_system
git clone <repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### Step 3: Configure Application

Create production configuration at `/opt/remote_system/config/production.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 9999,
    "use_tls": true,
    "cert_file": "/opt/remote_system/certs/server.crt",
    "key_file": "/opt/remote_system/certs/server.key"
  },
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "remote_system",
    "username": "remote_admin",
    "password": "SECURE_PASSWORD_HERE"
  },
  "authentication": {
    "secret_key": "GENERATE_RANDOM_KEY_HERE",
    "token_expiry": 3600
  },
  "web_ui": {
    "enabled": true,
    "port": 8080,
    "username": "admin",
    "password": "SECURE_PASSWORD_HERE"
  },
  "logging": {
    "level": "INFO",
    "file": "/var/log/remote_system/server.log",
    "max_size": 104857600,
    "backup_count": 10
  },
  "performance": {
    "max_agents": 10000,
    "connection_pool_size": 50,
    "command_queue_size": 100
  }
}
```

### Step 4: Generate TLS Certificates

**Option 1: Let's Encrypt (Recommended for Internet-facing)**

```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d remote.example.com

# Copy certificates
sudo cp /etc/letsencrypt/live/remote.example.com/fullchain.pem \
    /opt/remote_system/certs/server.crt
sudo cp /etc/letsencrypt/live/remote.example.com/privkey.pem \
    /opt/remote_system/certs/server.key
sudo chown remote_system:remote_system /opt/remote_system/certs/*
```

**Option 2: Self-Signed (Internal Use)**

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /opt/remote_system/certs/server.key \
    -out /opt/remote_system/certs/server.crt \
    -days 365 \
    -subj "/CN=remote.internal.example.com"

sudo chown remote_system:remote_system /opt/remote_system/certs/*
```

### Step 5: Set Up Systemd Service

Create `/etc/systemd/system/remote-system-server.service`:

```ini
[Unit]
Description=Remote System Enhancement Server
After=network.target postgresql.service

[Service]
Type=simple
User=remote_system
Group=remote_system
WorkingDirectory=/opt/remote_system
Environment="PATH=/opt/remote_system/venv/bin"
ExecStart=/opt/remote_system/venv/bin/python -m remote_system.enhanced_server.enhanced_server --config /opt/remote_system/config/production.json
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/remote_system /opt/remote_system/data

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/remote-system-api.service`:

```ini
[Unit]
Description=Remote System Enhancement REST API
After=network.target remote-system-server.service

[Service]
Type=simple
User=remote_system
Group=remote_system
WorkingDirectory=/opt/remote_system
Environment="PATH=/opt/remote_system/venv/bin"
ExecStart=/opt/remote_system/venv/bin/gunicorn -w 4 -b 127.0.0.1:8080 remote_system.web_ui.rest_api:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable remote-system-server remote-system-api
sudo systemctl start remote-system-server remote-system-api
```

### Step 6: Verify Deployment

```bash
# Check service status
sudo systemctl status remote-system-server
sudo systemctl status remote-system-api

# Check logs
sudo journalctl -u remote-system-server -f
sudo journalctl -u remote-system-api -f

# Test connectivity
netstat -tulpn | grep -E '9999|8080'
```

## Database Setup

### PostgreSQL Configuration

```bash
# Switch to postgres user
sudo su - postgres

# Create database and user
psql << EOF
CREATE DATABASE remote_system;
CREATE USER remote_admin WITH PASSWORD 'SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE remote_system TO remote_admin;
\c remote_system
GRANT ALL ON SCHEMA public TO remote_admin;
EOF

# Exit postgres user
exit
```

### Database Tuning

Edit `/etc/postgresql/14/main/postgresql.conf`:

```ini
# Memory settings
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
work_mem = 16MB

# Connection settings
max_connections = 200

# Performance settings
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200

# Logging
log_min_duration_statement = 1000  # Log slow queries
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### Initialize Database Schema

```bash
sudo su - remote_system
cd /opt/remote_system
source venv/bin/activate
python -m remote_system.enhanced_server.database_manager --init --config config/production.json
```

## Web Interface Deployment

### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/remote-system`:

```nginx
upstream api_backend {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name remote.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name remote.example.com;

    ssl_certificate /opt/remote_system/certs/server.crt;
    ssl_certificate_key /opt/remote_system/certs/server.key;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API proxy
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files
    location / {
        root /opt/remote_system/remote_system/web_ui/static;
        try_files $uri $uri/ /index.html;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    location /api/auth/login {
        limit_req zone=api_limit burst=5;
        proxy_pass http://api_backend;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/remote-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Agent Deployment

### Building Production Agents

```bash
# Build agent with production configuration
python -m remote_system.builder.enhanced_builder \
  --server-ip remote.example.com \
  --server-port 9999 \
  --icon ./resources/icon.ico \
  --company "Your Company" \
  --version "1.0.0" \
  --copyright "Copyright 2026 Your Company" \
  --silent \
  --obfuscate \
  --output ./output/agent_prod.exe

# Generate checksum
sha256sum ./output/agent_prod.exe > ./output/agent_prod.exe.sha256
```

### Agent Distribution

**Option 1: HTTPS Download**

```bash
# Host on web server
sudo cp ./output/agent_prod.exe /var/www/html/downloads/
sudo cp ./output/agent_prod.exe.sha256 /var/www/html/downloads/

# Download on target
wget https://remote.example.com/downloads/agent_prod.exe
sha256sum -c agent_prod.exe.sha256
```

**Option 2: Configuration Management**

```yaml
# Ansible playbook
- name: Deploy remote system agent
  hosts: managed_hosts
  tasks:
    - name: Copy agent executable
      copy:
        src: ./output/agent_prod.exe
        dest: C:\Program Files\RemoteSystem\agent.exe
        
    - name: Install as service
      win_service:
        name: RemoteSystemAgent
        path: C:\Program Files\RemoteSystem\agent.exe
        start_mode: auto
        state: started
```

### Agent Deployment Checklist

- [ ] Obtain deployment authorization
- [ ] Verify agent checksum
- [ ] Test agent on staging system
- [ ] Document deployment details
- [ ] Deploy to production systems
- [ ] Verify agent connections
- [ ] Update inventory

## High Availability

### Active-Passive Setup

**Server 1 (Active):**

```bash
# Install and configure as primary
# Enable heartbeat monitoring
```

**Server 2 (Standby):**

```bash
# Install and configure as standby
# Set up replication from primary
# Configure automatic failover
```

**Keepalived Configuration:**

```bash
# Install keepalived
sudo apt install keepalived

# Configure virtual IP
# /etc/keepalived/keepalived.conf
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass SECRET
    }
    virtual_ipaddress {
        10.0.0.100
    }
}
```

### Database Replication

**Primary Server:**

```sql
-- Configure replication
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET wal_keep_size = 1024;

-- Create replication user
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'password';
```

**Standby Server:**

```bash
# Set up streaming replication
pg_basebackup -h primary_server -D /var/lib/postgresql/14/main -U replicator -P -v -R
```

## Monitoring and Maintenance

### Monitoring Setup

**Prometheus Configuration:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'remote_system'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/api/metrics/prometheus'
```

**Grafana Dashboard:**

```json
{
  "dashboard": {
    "title": "Remote System Monitoring",
    "panels": [
      {
        "title": "Active Agents",
        "targets": [{"expr": "active_agents"}]
      },
      {
        "title": "Commands Per Second",
        "targets": [{"expr": "rate(commands_total[1m])"}]
      }
    ]
  }
}
```

### Log Management

**Centralized Logging with ELK:**

```bash
# Install Filebeat
sudo apt install filebeat

# Configure Filebeat
# /etc/filebeat/filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/remote_system/*.log
    
output.elasticsearch:
  hosts: ["localhost:9200"]
```

### Maintenance Tasks

**Daily:**
- Monitor system health
- Review security logs
- Check disk space

**Weekly:**
- Review command history
- Analyze performance metrics
- Update agent inventory

**Monthly:**
- Rotate credentials
- Update certificates
- Review access controls
- Database maintenance

**Quarterly:**
- Security audit
- Performance review
- Capacity planning

## Backup and Recovery

### Backup Strategy

**Database Backup:**

```bash
#!/bin/bash
# /opt/remote_system/scripts/backup_database.sh

BACKUP_DIR="/backup/remote_system"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
pg_dump -U remote_admin remote_system | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Encrypt backup
gpg --encrypt --recipient admin@example.com "$BACKUP_DIR/db_$DATE.sql.gz"

# Remove old backups (keep 30 days)
find "$BACKUP_DIR" -name "db_*.sql.gz.gpg" -mtime +30 -delete

# Upload to S3
aws s3 cp "$BACKUP_DIR/db_$DATE.sql.gz.gpg" s3://backups/remote_system/
```

**Configuration Backup:**

```bash
#!/bin/bash
# Backup configuration files
tar -czf /backup/config_$(date +%Y%m%d).tar.gz \
    /opt/remote_system/config/ \
    /opt/remote_system/certs/ \
    /etc/systemd/system/remote-system-*
```

**Automated Backup:**

```bash
# Add to crontab
0 2 * * * /opt/remote_system/scripts/backup_database.sh
0 3 * * 0 /opt/remote_system/scripts/backup_config.sh
```

### Recovery Procedures

**Database Recovery:**

```bash
# Stop services
sudo systemctl stop remote-system-server remote-system-api

# Restore database
gunzip < backup.sql.gz | psql -U remote_admin remote_system

# Start services
sudo systemctl start remote-system-server remote-system-api
```

**Disaster Recovery:**

1. Provision new server
2. Install application
3. Restore database from backup
4. Restore configuration files
5. Update DNS/IP addresses
6. Verify functionality
7. Reconnect agents

## Scaling

### Vertical Scaling

**Increase Resources:**
- Add CPU cores
- Increase RAM
- Upgrade to faster storage
- Increase network bandwidth

**Optimize Configuration:**

```json
{
  "performance": {
    "max_agents": 20000,
    "connection_pool_size": 100,
    "worker_threads": 16
  }
}
```

### Horizontal Scaling

**Load Balancer Configuration:**

```nginx
upstream remote_system_servers {
    least_conn;
    server 10.0.0.10:9999 max_fails=3 fail_timeout=30s;
    server 10.0.0.11:9999 max_fails=3 fail_timeout=30s;
    server 10.0.0.12:9999 max_fails=3 fail_timeout=30s;
}

server {
    listen 9999;
    proxy_pass remote_system_servers;
}
```

**Session Persistence:**

```python
# Use Redis for session storage
REDIS_CONFIG = {
    "host": "redis.example.com",
    "port": 6379,
    "db": 0
}
```

### Performance Optimization

**Database Optimization:**

```sql
-- Create indexes
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_command_logs_agent_id ON command_logs(agent_id);
CREATE INDEX idx_command_logs_executed_at ON command_logs(executed_at);

-- Analyze tables
ANALYZE agents;
ANALYZE command_logs;
```

**Caching:**

```python
# Implement Redis caching
from redis import Redis

cache = Redis(host='localhost', port=6379)

def get_active_agents():
    cached = cache.get('active_agents')
    if cached:
        return json.loads(cached)
    
    agents = db.get_active_agents()
    cache.setex('active_agents', 5, json.dumps(agents))
    return agents
```

## Troubleshooting

### Common Issues

**High CPU Usage:**
- Check for inefficient queries
- Review command execution patterns
- Consider scaling

**High Memory Usage:**
- Check for memory leaks
- Review connection pool size
- Implement memory limits

**Slow Performance:**
- Analyze database queries
- Check network latency
- Review system resources

### Support

For deployment assistance:
- Review logs: `/var/log/remote_system/`
- Check system status: `systemctl status remote-system-*`
- Monitor resources: `htop`, `iotop`, `nethogs`
- Consult documentation
- Open support ticket

## Deployment Checklist

### Pre-Deployment

- [ ] Infrastructure provisioned
- [ ] Security review completed
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] Documentation updated
- [ ] Deployment authorization obtained

### Deployment

- [ ] Server installed and configured
- [ ] Database initialized
- [ ] TLS certificates installed
- [ ] Services started and verified
- [ ] Web interface accessible
- [ ] Agents built and tested

### Post-Deployment

- [ ] Verify all services running
- [ ] Test agent connections
- [ ] Review logs for errors
- [ ] Configure monitoring alerts
- [ ] Document deployment details
- [ ] Train operators
- [ ] Schedule maintenance tasks

## Conclusion

This deployment guide provides a foundation for production deployment. Adjust configurations based on your specific requirements, scale, and environment. Always follow security best practices and maintain comprehensive documentation.
