#!/bin/bash
# Trilium AI - Update Script (runs on the server)

set -e

# Ensure uv is in PATH (SSH non-interactive sessions don't source ~/.bashrc)
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "========================================="
echo "Trilium AI - Update"
echo "========================================="
echo

# Check service states before updating
WEB_RUNNING=false
SYNC_RUNNING=false
if systemctl is-active --quiet trilium-ai-web.service 2>/dev/null; then
    WEB_RUNNING=true
    echo "✓ Web service is running"
fi
if systemctl is-active --quiet trilium-ai-sync.timer 2>/dev/null; then
    SYNC_RUNNING=true
    echo "✓ Sync timer is running"
fi
echo

echo "Step 1: Pulling latest changes from git..."
echo "----------------------------------------"
CURRENT_COMMIT=$(git rev-parse HEAD)
git pull origin main
NEW_COMMIT=$(git rev-parse HEAD)

if [ "$CURRENT_COMMIT" = "$NEW_COMMIT" ]; then
    echo "Already up to date"
else
    echo "Updated: ${CURRENT_COMMIT:0:8} → ${NEW_COMMIT:0:8}"
    git log --oneline --no-merges "$CURRENT_COMMIT..$NEW_COMMIT" | head -10
fi
echo

echo "Step 2: Installing/updating dependencies..."
echo "----------------------------------------"
uv sync
echo "✓ Dependencies updated"
echo

echo "Step 3: Restarting services..."
echo "----------------------------------------"
if [ "$WEB_RUNNING" = true ]; then
    sudo systemctl restart trilium-ai-web.service
    sleep 2
    if systemctl is-active --quiet trilium-ai-web.service; then
        echo "✓ Web service restarted"
    else
        echo "✗ Web service failed to start. Check logs with:"
        echo "  sudo journalctl -u trilium-ai-web.service -n 50"
        exit 1
    fi
else
    echo "ℹ Web service was not running, skipping"
fi

if [ "$SYNC_RUNNING" = true ]; then
    sudo systemctl restart trilium-ai-sync.timer
    echo "✓ Sync timer restarted"
else
    echo "ℹ Sync timer was not running, skipping"
fi
echo

echo "========================================="
echo "Update Complete!"
echo "========================================="
echo

echo "Service status:"
systemctl status trilium-ai-web.service --no-pager || true
echo
