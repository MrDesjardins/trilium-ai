# Production Deployment Guide - Ubuntu Server

This guide provides comprehensive instructions for deploying Trilium AI on Ubuntu Server with automated setup scripts and systemd services.

## Prerequisites

- **Ubuntu Server**: 20.04 or later
- **Trilium Notes**: Installed and running on the same server
- **System Requirements**:
  - 2GB+ RAM (for embedding models)
  - 5GB+ disk space (for Weaviate and embeddings)
  - Network access to Trilium database

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                Ubuntu Server                         │
│                                                      │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Trilium    │  │ Weaviate    │  │ Trilium AI │ │
│  │ (SQLite DB)  │  │ (Docker)    │  │ (Service)  │ │
│  │              │  │             │  │            │ │
│  │ document.db  │◄─│ Port 8080   │◄─│ Indexer    │ │
│  └──────────────┘  └─────────────┘  └────────────┘ │
│                                                      │
│  Systemd Services:                                  │
│  • trilium-ai-sync.timer (periodic sync)           │
│  • trilium-ai-sync.service (sync execution)        │
└─────────────────────────────────────────────────────┘
```

## Quick Installation

### 1. Install Prerequisites

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y git curl docker.io docker-compose

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add current user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
exit
```

### 2. Install uv (Python Package Manager)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell or add to PATH
source $HOME/.local/bin/env
```

### 3. Clone Repository

```bash
# Clone to /opt/trilium-ai (recommended for system services)
cd /opt
sudo git clone https://github.com/mrdesjardins/trilium-ai.git
sudo chown -R $USER:$USER trilium-ai
cd trilium-ai
```

### 4. Run Automated Setup

```bash
# Run the interactive setup script
./scripts/setup.sh
```

The setup script will:
- Install Python dependencies
- Start Weaviate Docker container
- Configure Trilium database path
- Configure Trilium server URL
- Set up API keys
- Validate configuration
- Optionally run initial index

### 5. Install Systemd Services

```bash
# Install and enable services
sudo ./scripts/install-service.sh

# Check service status
sudo systemctl status trilium-ai-sync.timer
```

Your Trilium AI is now installed! The system will:
- Automatically sync notes every 30 minutes
- Serve the web interface at http://YOUR_SERVER_IP:3000

---

## Manual Installation (Detailed Steps)

If you prefer manual setup or need to customize the installation:

### Step 1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Enable Docker to start on boot
sudo systemctl enable docker
```

### Step 2: Clone and Install

```bash
cd /opt
sudo git clone https://github.com/mrdesjardins/trilium-ai.git
sudo chown -R $USER:$USER trilium-ai
cd trilium-ai

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Install dependencies
uv sync
```

### Step 3: Start Weaviate

```bash
cd docker
docker compose up -d
cd ..

# Verify Weaviate is running
docker ps | grep weaviate
```

### Step 4: Configure Trilium AI

```bash
# Copy configuration templates
cp config/config.example.yaml config/config.yaml
cp .env.example .env

# Edit configuration
nano config/config.yaml
```

Update `config/config.yaml`:

```yaml
trilium:
  database_path: "/home/YOUR_USER/.local/share/trilium-data/document.db"
  server_url: "http://YOUR_SERVER_IP:8080"  # Your Trilium server URL
  sync_interval: 300

weaviate:
  url: "http://localhost:8080"  # Weaviate running in Docker
  collection_name: "TriliumNotes"
  batch_size: 100

# ... rest of config
```

Edit `.env` file:

```bash
nano .env
```

Add your API keys:

```bash
# Choose ONE provider (OpenAI, Anthropic, or Gemini)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GEMINI_API_KEY=...
```

### Step 5: Initial Index

```bash
# Run full index
uv run trilium-ai index --full

# Verify index status
uv run trilium-ai status
```

### Step 6: Install Systemd Services

Create service files (see "Systemd Services" section below) or use the automated script:

```bash
sudo ./scripts/install-service.sh
```

---

## Systemd Services

The deployment includes three systemd services:

### Service Files

**1. trilium-ai-sync.service** - Performs incremental sync

**2. trilium-ai-sync.timer** - Triggers sync every 30 minutes

**3. trilium-ai-web.service** - Runs the web interface

### Service Management

```bash
# Enable services (start on boot)
sudo systemctl enable trilium-ai-sync.timer

# Start timer
sudo systemctl start trilium-ai-sync.timer

# Check status
sudo systemctl status trilium-ai-sync.timer
sudo systemctl status trilium-ai-sync.service

# View logs
sudo journalctl -u trilium-ai-sync.service -f

# Manually trigger sync
sudo systemctl start trilium-ai-sync.service
```

### Service Configuration

Services are located in:
- `/etc/systemd/system/trilium-ai-sync.service`
- `/etc/systemd/system/trilium-ai-sync.timer`

To modify sync interval:

```bash
sudo systemctl edit trilium-ai-sync.timer
```

Add:

```ini
[Timer]
OnBootSec=5min
OnUnitActiveSec=15min  # Change from 30min to 15min
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart trilium-ai-sync.timer
```

---

## Web Interface

The deployment includes a web interface accessible via browser.

### Accessing the Web Interface

Default URL: `http://YOUR_SERVER_IP:3000`

### Configuration

The web interface port can be configured in `config/config.yaml`:

```yaml
web:
  enabled: true
  host: "0.0.0.0"  # All interfaces
  port: 3000       # Change if needed
```

### Changing the Port

If port 3000 is already in use:

1. Edit config:
```bash
nano /opt/trilium-ai/config/config.yaml
```

2. Change the port:
```yaml
web:
  port: 8080  # or any available port
```

3. Restart service:
```bash
sudo systemctl restart trilium-ai-web.service
```

### Web Service Management

```bash
# Status
sudo systemctl status trilium-ai-web.service

# Logs
sudo journalctl -u trilium-ai-web.service -f

# Restart
sudo systemctl restart trilium-ai-web.service

# Stop
sudo systemctl stop trilium-ai-web.service

# Start
sudo systemctl start trilium-ai-web.service
```

### Development Mode

For development with auto-reload:

```bash
cd /opt/trilium-ai
uv run trilium-ai web --reload
```

### API Access

The web interface exposes REST API endpoints:

```bash
# Query notes
curl -X POST http://localhost:3000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are my notes about Python?"}'

# Check status
curl http://localhost:3000/api/status

# Health check
curl http://localhost:3000/health
```

See [WEB.md](WEB.md) for complete web interface documentation.

---

## Maintenance

### Updating Trilium AI

```bash
cd /opt/trilium-ai
./scripts/update.sh
```

The update script will:
1. Stop services
2. Pull latest changes from git
3. Update dependencies
4. Restart services
5. Verify everything is working

### Manual Update

```bash
cd /opt/trilium-ai

# Stop services
sudo systemctl stop trilium-ai-sync.timer
sudo systemctl stop trilium-ai-sync.service

# Pull updates
git pull

# Update dependencies
uv sync

# Restart services
sudo systemctl start trilium-ai-sync.timer

# Verify
sudo systemctl status trilium-ai-sync.timer
```

### Backing Up

```bash
# Backup Weaviate data
cd /opt/trilium-ai/docker
docker compose exec -T weaviate /bin/weaviate-backup backup

# Backup configuration
cp config/config.yaml config/config.yaml.backup
cp .env .env.backup

# Backup sync state
cp .trilium-ai-sync-state.json .trilium-ai-sync-state.json.backup
```

### Resetting Index

```bash
# Stop sync service
sudo systemctl stop trilium-ai-sync.timer
sudo systemctl stop trilium-ai-sync.service

# Reset index
cd /opt/trilium-ai
uv run trilium-ai reset

# Full reindex
uv run trilium-ai index --full

# Restart services
sudo systemctl start trilium-ai-sync.timer
```

---

## Monitoring

### View Service Logs

```bash
# Follow sync service logs in real-time
sudo journalctl -u trilium-ai-sync.service -f

# View last 100 lines
sudo journalctl -u trilium-ai-sync.service -n 100

# View logs since yesterday
sudo journalctl -u trilium-ai-sync.service --since yesterday
```

### Check Service Status

```bash
# Check if services are running
systemctl list-timers | grep trilium
sudo systemctl status trilium-ai-sync.service
sudo systemctl status trilium-ai-sync.timer

# Check Weaviate
docker ps | grep weaviate
curl http://localhost:8080/v1/meta
```

### Check Index Status

```bash
cd /opt/trilium-ai
uv run trilium-ai status
```

---

## Troubleshooting

### Service Not Starting

```bash
# Check service logs
sudo journalctl -u trilium-ai-sync.service -n 50

# Check service file syntax
sudo systemctl daemon-reload
sudo systemctl status trilium-ai-sync.service

# Verify permissions
ls -la /opt/trilium-ai
ls -la /opt/trilium-ai/.env
```

### Weaviate Connection Issues

```bash
# Check if Weaviate is running
docker ps | grep weaviate

# Check Weaviate logs
cd /opt/trilium-ai/docker
docker compose logs weaviate

# Restart Weaviate
docker compose restart weaviate
```

### Database Access Issues

```bash
# Verify database path
ls -la /home/YOUR_USER/.local/share/trilium-data/document.db

# Check permissions
stat /home/YOUR_USER/.local/share/trilium-data/document.db

# Test database access
cd /opt/trilium-ai
uv run python -c "import sqlite3; conn = sqlite3.connect('PATH_TO_DB'); print('OK')"
```

### API Key Issues

```bash
# Verify .env file exists and is readable
cat /opt/trilium-ai/.env

# Test API key
cd /opt/trilium-ai
uv run python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

### Memory Issues

If you experience memory issues during indexing:

```bash
# Edit config to reduce batch size
nano /opt/trilium-ai/config/config.yaml

# Change:
weaviate:
  batch_size: 50  # Reduce from 100 to 50

# Restart service
sudo systemctl restart trilium-ai-sync.timer
```

---

## Security Best Practices

### File Permissions

```bash
# Secure configuration files
chmod 600 /opt/trilium-ai/.env
chmod 600 /opt/trilium-ai/config/config.yaml

# Ensure proper ownership
sudo chown -R $USER:$USER /opt/trilium-ai
```

### API Keys

- Never commit `.env` or `config/config.yaml` to git
- Use environment variables for production secrets
- Rotate API keys regularly
- Use separate API keys for different environments

### Network Security

```bash
# Weaviate should only be accessible locally
# Ensure Weaviate is not exposed externally
sudo ufw status
sudo ufw allow 8080/tcp  # Only if you need external access to Trilium
```

### Database Security

- Keep Trilium database in secure location
- Use read-only access if possible (currently reads only)
- Back up Trilium database regularly

---

## Performance Optimization

### Adjust Sync Frequency

For large note collections, reduce sync frequency:

```bash
sudo systemctl edit trilium-ai-sync.timer
```

Change to hourly:

```ini
[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
```

### Optimize Embeddings

Use faster embedding model:

```yaml
# config/config.yaml
embeddings:
  provider: "sentence-transformers"
  model: "all-MiniLM-L6-v2"  # Fastest, 384 dimensions
  # model: "all-mpnet-base-v2"  # Slower but better quality, 768 dimensions
```

### Batch Size Tuning

```yaml
weaviate:
  batch_size: 100  # Increase to 200 for faster indexing if you have RAM
```

---

## Uninstalling

To completely remove Trilium AI:

```bash
# Stop and disable services
sudo systemctl stop trilium-ai-sync.timer
sudo systemctl stop trilium-ai-sync.service
sudo systemctl disable trilium-ai-sync.timer
sudo systemctl disable trilium-ai-sync.service

# Remove service files
sudo rm /etc/systemd/system/trilium-ai-sync.service
sudo rm /etc/systemd/system/trilium-ai-sync.timer
sudo systemctl daemon-reload

# Stop and remove Weaviate
cd /opt/trilium-ai/docker
docker compose down -v

# Remove installation
sudo rm -rf /opt/trilium-ai

# Remove uv (optional)
rm -rf ~/.local/share/uv
```

---

## FAQ

### How do I change the Trilium database path?

Edit `config/config.yaml` and update the `database_path`, then restart services:

```bash
sudo systemctl restart trilium-ai-sync.timer
```

### How do I switch LLM providers?

Update `.env` with the new API key and edit `config/config.yaml`:

```yaml
llm:
  provider: "anthropic"  # Change from "openai"
  model: "claude-3-5-sonnet-20241022"
```

### Can I run this on a different server than Trilium?

Yes! Just update the `database_path` to point to a network mount or copy of the Trilium database. Also update `server_url` to point to your Trilium server.

### How much disk space does it use?

- Weaviate: ~500MB-2GB (depends on note count)
- Embeddings model: ~80MB-500MB
- Python environment: ~500MB

### How do I query my notes?

```bash
cd /opt/trilium-ai
uv run trilium-ai query "your question here"
```

Or access programmatically through the Python API.

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/mrdesjardins/trilium-ai/issues
- Documentation: See README.md and CLAUDE.md
