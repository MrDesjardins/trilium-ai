#!/bin/bash
# Trilium AI - Install Systemd Services Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}This script must be run with sudo${NC}"
    echo -e "${YELLOW}Usage: sudo ./scripts/install-service.sh${NC}"
    exit 1
fi

# Get the actual user (not root when using sudo)
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Installing Trilium AI Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Find uv binary
UV_PATH=$(su - $ACTUAL_USER -c "command -v uv" 2>/dev/null || echo "$ACTUAL_HOME/.local/bin/uv")

if [ ! -x "$UV_PATH" ]; then
    echo -e "${RED}Error: uv not found${NC}"
    echo -e "${YELLOW}Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi

echo -e "${BLUE}Installation settings:${NC}"
echo -e "  User: ${GREEN}$ACTUAL_USER${NC}"
echo -e "  Install path: ${GREEN}$PROJECT_DIR${NC}"
echo -e "  uv path: ${GREEN}$UV_PATH${NC}"
echo

# Create temporary service files with substituted values
echo -e "${BLUE}Creating service files...${NC}"

# Process service file
sed -e "s|%INSTALL_USER%|$ACTUAL_USER|g" \
    -e "s|%INSTALL_PATH%|$PROJECT_DIR|g" \
    -e "s|%UV_PATH%|$UV_PATH|g" \
    "$SCRIPT_DIR/trilium-ai-sync.service" > /tmp/trilium-ai-sync.service

# Copy service files to systemd
cp /tmp/trilium-ai-sync.service /etc/systemd/system/
cp "$SCRIPT_DIR/trilium-ai-sync.timer" /etc/systemd/system/

# Clean up temp files
rm /tmp/trilium-ai-sync.service

echo -e "${GREEN}✓ Service files installed${NC}"

# Reload systemd
echo -e "${BLUE}Reloading systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

# Enable and start timer
echo -e "${BLUE}Enabling services...${NC}"
systemctl enable trilium-ai-sync.timer
systemctl start trilium-ai-sync.timer

echo -e "${GREEN}✓ Services enabled and started${NC}"
echo

# Show status
echo -e "${BLUE}Service status:${NC}"
systemctl status trilium-ai-sync.timer --no-pager || true
echo

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "${BLUE}Service management commands:${NC}"
echo -e "  Status: ${YELLOW}sudo systemctl status trilium-ai-sync.timer${NC}"
echo -e "  Logs: ${YELLOW}sudo journalctl -u trilium-ai-sync.service -f${NC}"
echo -e "  Manual sync: ${YELLOW}sudo systemctl start trilium-ai-sync.service${NC}"
echo -e "  Stop: ${YELLOW}sudo systemctl stop trilium-ai-sync.timer${NC}"
echo -e "  Restart: ${YELLOW}sudo systemctl restart trilium-ai-sync.timer${NC}"
echo
echo -e "${BLUE}The service will:${NC}"
echo -e "  - Run ${GREEN}5 minutes after system boot${NC}"
echo -e "  - Run ${GREEN}every 30 minutes${NC} after that"
echo -e "  - Auto-start on system reboot"
echo
