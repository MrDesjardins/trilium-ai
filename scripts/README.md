# Deployment Scripts

This directory contains automated scripts for deploying and managing Trilium AI on Ubuntu Server.

## Scripts

### setup.sh
**Purpose**: Interactive setup wizard for initial installation

**Usage**:
```bash
./scripts/setup.sh
```

**What it does**:
- Checks and installs prerequisites (Docker, uv)
- Installs Python dependencies
- Starts Weaviate Docker container
- Configures Trilium database path
- Configures Trilium server URL
- Sets up API keys for LLM providers
- Validates configuration
- Optionally runs initial full index

**When to use**: First-time setup on a new server

---

### install-service.sh
**Purpose**: Installs and enables systemd services for automatic syncing

**Usage**:
```bash
sudo ./scripts/install-service.sh
```

**What it does**:
- Installs systemd service files to `/etc/systemd/system/`
- Configures service with correct paths and user
- Enables services to start on boot
- Starts the timer for automatic syncing

**When to use**: After running setup.sh, or when reinstalling services

---

### update.sh
**Purpose**: Updates Trilium AI to the latest version

**Usage**:
```bash
./scripts/update.sh
```

**What it does**:
1. Checks for local changes
2. Stops running services
3. Backs up configuration files
4. Pulls latest changes from git
5. Updates dependencies with uv
6. Updates Docker containers
7. Reinstalls/restarts services

**When to use**: To upgrade to a newer version of Trilium AI

---

## Systemd Service Files

### trilium-ai-sync.service
Systemd service that runs incremental sync of Trilium notes to Weaviate.

**Features**:
- Runs as oneshot service (completes and stops)
- Auto-restarts on failure
- Logs to systemd journal
- Security hardening (PrivateTmp, NoNewPrivileges, ProtectSystem)

### trilium-ai-sync.timer
Systemd timer that triggers the sync service periodically.

**Schedule**:
- Runs 5 minutes after system boot
- Runs every 30 minutes thereafter
- Persistent (catches up if system was off)

---

## Service Management

### Check Status
```bash
sudo systemctl status trilium-ai-sync.timer
sudo systemctl status trilium-ai-sync.service
```

### View Logs
```bash
# Follow logs in real-time
sudo journalctl -u trilium-ai-sync.service -f

# View last 50 lines
sudo journalctl -u trilium-ai-sync.service -n 50
```

### Manual Trigger
```bash
sudo systemctl start trilium-ai-sync.service
```

### Stop/Start Timer
```bash
sudo systemctl stop trilium-ai-sync.timer
sudo systemctl start trilium-ai-sync.timer
```

### Change Sync Interval
```bash
# Edit timer configuration
sudo systemctl edit trilium-ai-sync.timer

# Add this to change to 15 minutes:
[Timer]
OnBootSec=5min
OnUnitActiveSec=15min

# Save and reload
sudo systemctl daemon-reload
sudo systemctl restart trilium-ai-sync.timer
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check service logs
sudo journalctl -u trilium-ai-sync.service -n 50

# Verify service file syntax
sudo systemctl daemon-reload
sudo systemctl status trilium-ai-sync.service

# Check permissions
ls -la /opt/trilium-ai
ls -la /opt/trilium-ai/.env
```

### Reinstall Services
```bash
# Remove old services
sudo systemctl stop trilium-ai-sync.timer
sudo systemctl disable trilium-ai-sync.timer
sudo rm /etc/systemd/system/trilium-ai-sync.*

# Reinstall
sudo ./scripts/install-service.sh
```

---

## File Structure

```
scripts/
├── README.md                    # This file
├── setup.sh                     # Interactive setup wizard
├── install-service.sh           # Service installer
├── update.sh                    # Update script
├── trilium-ai-sync.service     # Systemd service template
└── trilium-ai-sync.timer       # Systemd timer configuration
```

---

## Notes

- All scripts are designed to be idempotent (safe to run multiple times)
- Scripts use color-coded output for better readability
- Configuration files (.env, config.yaml) are never overwritten during updates
- Backups are created automatically during updates
- Services survive system reboots and automatically resume

For more detailed documentation, see [DEPLOYMENT.md](../DEPLOYMENT.md) in the root directory.
