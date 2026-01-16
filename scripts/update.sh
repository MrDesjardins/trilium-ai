#!/bin/bash
# Trilium AI - Update Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Updating Trilium AI${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if we're in a git repository
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo -e "${RED}Error: Not a git repository${NC}"
    echo -e "${YELLOW}This script should be run from a git clone of Trilium AI${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# Step 1: Check for local changes
echo -e "${BLUE}[1/7] Checking for local changes...${NC}"

if git diff-index --quiet HEAD --; then
    echo -e "${GREEN}✓ No local changes${NC}"
else
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    echo -e "${YELLOW}The following files have been modified:${NC}"
    git status --short
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Update cancelled${NC}"
        exit 1
    fi
fi
echo

# Step 2: Stop services if running
echo -e "${BLUE}[2/7] Stopping services...${NC}"

# Check if services exist and are active
if systemctl is-active --quiet trilium-ai-sync.timer 2>/dev/null; then
    echo -e "${YELLOW}Stopping trilium-ai-sync.timer...${NC}"
    sudo systemctl stop trilium-ai-sync.timer
    TIMER_WAS_RUNNING=true
else
    echo -e "${YELLOW}Service not running or not installed${NC}"
    TIMER_WAS_RUNNING=false
fi

if systemctl is-active --quiet trilium-ai-sync.service 2>/dev/null; then
    echo -e "${YELLOW}Stopping trilium-ai-sync.service...${NC}"
    sudo systemctl stop trilium-ai-sync.service
fi

echo -e "${GREEN}✓ Services stopped${NC}"
echo

# Step 3: Backup configuration
echo -e "${BLUE}[3/7] Backing up configuration...${NC}"

BACKUP_DIR="$PROJECT_DIR/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "$PROJECT_DIR/config/config.yaml" ]; then
    cp "$PROJECT_DIR/config/config.yaml" "$BACKUP_DIR/"
fi

if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$BACKUP_DIR/"
fi

if [ -f "$PROJECT_DIR/.trilium-ai-sync-state.json" ]; then
    cp "$PROJECT_DIR/.trilium-ai-sync-state.json" "$BACKUP_DIR/"
fi

echo -e "${GREEN}✓ Configuration backed up to: $BACKUP_DIR${NC}"
echo

# Step 4: Pull latest changes
echo -e "${BLUE}[4/7] Pulling latest changes from git...${NC}"

CURRENT_COMMIT=$(git rev-parse HEAD)
echo -e "${YELLOW}Current commit: ${CURRENT_COMMIT:0:8}${NC}"

if ! git pull; then
    echo -e "${RED}Failed to pull changes${NC}"
    echo -e "${YELLOW}You may need to resolve conflicts manually${NC}"
    exit 1
fi

NEW_COMMIT=$(git rev-parse HEAD)
echo -e "${YELLOW}New commit: ${NEW_COMMIT:0:8}${NC}"

if [ "$CURRENT_COMMIT" = "$NEW_COMMIT" ]; then
    echo -e "${GREEN}Already up to date${NC}"
else
    echo -e "${GREEN}✓ Updated successfully${NC}"
    echo -e "${BLUE}Changes:${NC}"
    git log --oneline --no-merges "$CURRENT_COMMIT..$NEW_COMMIT" | head -10
fi
echo

# Step 5: Update dependencies
echo -e "${BLUE}[5/7] Updating dependencies...${NC}"

if ! uv sync; then
    echo -e "${RED}Failed to update dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies updated${NC}"
echo

# Step 6: Update Docker containers
echo -e "${BLUE}[6/7] Updating Docker containers...${NC}"

cd "$PROJECT_DIR/docker"

# Pull latest images
if ! docker compose pull; then
    echo -e "${YELLOW}Warning: Failed to pull Docker images${NC}"
fi

# Restart containers
if ! docker compose up -d; then
    echo -e "${RED}Failed to restart Docker containers${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker containers updated${NC}"
echo

cd "$PROJECT_DIR"

# Step 7: Reinstall services if they were installed
echo -e "${BLUE}[7/7] Updating services...${NC}"

if [ -f "/etc/systemd/system/trilium-ai-sync.service" ]; then
    echo -e "${YELLOW}Reinstalling systemd services...${NC}"
    if [ -x "$SCRIPT_DIR/install-service.sh" ]; then
        sudo "$SCRIPT_DIR/install-service.sh"
    else
        echo -e "${YELLOW}Service installer not found or not executable${NC}"
        echo -e "${YELLOW}Services were not updated${NC}"
    fi
elif [ "$TIMER_WAS_RUNNING" = true ]; then
    # Restart the timer if it was running before
    sudo systemctl start trilium-ai-sync.timer
    echo -e "${GREEN}✓ Services restarted${NC}"
else
    echo -e "${YELLOW}Services not installed${NC}"
fi
echo

# Final status
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Update Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "${BLUE}Summary:${NC}"
echo -e "  Backup location: ${GREEN}$BACKUP_DIR${NC}"
echo -e "  Git commit: ${GREEN}${NEW_COMMIT:0:8}${NC}"
echo

if [ "$TIMER_WAS_RUNNING" = true ]; then
    echo -e "${BLUE}Service status:${NC}"
    sudo systemctl status trilium-ai-sync.timer --no-pager || true
    echo
fi

echo -e "${BLUE}Next steps:${NC}"
echo -e "  - Check logs: ${YELLOW}sudo journalctl -u trilium-ai-sync.service -n 50${NC}"
echo -e "  - Run sync manually: ${YELLOW}uv run trilium-ai index --incremental${NC}"
echo -e "  - Query notes: ${YELLOW}uv run trilium-ai query \"your question\"${NC}"
echo
