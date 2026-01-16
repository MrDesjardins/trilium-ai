#!/bin/bash
# Trilium AI - Interactive Setup Script
# This script automates the initial setup of Trilium AI

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
echo -e "${BLUE}   Trilium AI - Setup Wizard${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running with sudo
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script with sudo${NC}"
    echo -e "${YELLOW}Run as your regular user. You'll be prompted for sudo when needed.${NC}"
    exit 1
fi

# Step 1: Check prerequisites
echo -e "${BLUE}[1/8] Checking prerequisites...${NC}"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed${NC}"
    echo -e "${YELLOW}Install Docker first: curl -fsSL https://get.docker.com | sh${NC}"
    exit 1
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv is not installed. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        echo -e "${RED}Failed to install uv${NC}"
        echo -e "${YELLOW}Please install manually: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Prerequisites installed${NC}"
echo

# Step 2: Install Python dependencies
echo -e "${BLUE}[2/8] Installing Python dependencies...${NC}"
cd "$PROJECT_DIR"

if ! uv sync; then
    echo -e "${RED}Failed to install dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo

# Step 3: Start Weaviate
echo -e "${BLUE}[3/8] Starting Weaviate...${NC}"
cd "$PROJECT_DIR/docker"

# Check if Weaviate is already running
if docker ps | grep -q weaviate; then
    echo -e "${YELLOW}Weaviate is already running${NC}"
else
    if ! docker compose up -d; then
        echo -e "${RED}Failed to start Weaviate${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Weaviate started${NC}"
fi

# Wait for Weaviate to be ready
echo -n "Waiting for Weaviate to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8080/v1/meta > /dev/null 2>&1; then
        echo -e " ${GREEN}Ready!${NC}"
        break
    fi
    sleep 1
    echo -n "."
done
echo

cd "$PROJECT_DIR"

# Step 4: Configure Trilium database path
echo -e "${BLUE}[4/8] Configuring Trilium database...${NC}"

# Copy example files if they don't exist
if [ ! -f "$PROJECT_DIR/config/config.yaml" ]; then
    cp "$PROJECT_DIR/config/config.example.yaml" "$PROJECT_DIR/config/config.yaml"
    echo -e "${GREEN}✓ Created config.yaml${NC}"
fi

if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo -e "${GREEN}✓ Created .env${NC}"
fi

# Find Trilium database
DEFAULT_TRILIUM_PATH="$HOME/.local/share/trilium-data/document.db"
echo
echo -e "${YELLOW}Enter the path to your Trilium database:${NC}"
echo -e "${YELLOW}(Press Enter to use: $DEFAULT_TRILIUM_PATH)${NC}"
read -e -p "Database path: " TRILIUM_DB_PATH
TRILIUM_DB_PATH=${TRILIUM_DB_PATH:-$DEFAULT_TRILIUM_PATH}

# Expand tilde to home directory
TRILIUM_DB_PATH="${TRILIUM_DB_PATH/#\~/$HOME}"

# Verify database exists
if [ ! -f "$TRILIUM_DB_PATH" ]; then
    echo -e "${RED}Warning: Database not found at $TRILIUM_DB_PATH${NC}"
    echo -e "${YELLOW}You can continue, but you'll need to fix the path later${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Database found${NC}"
fi

# Update config.yaml with database path
if command -v sed &> /dev/null; then
    # Escape forward slashes for sed
    ESCAPED_PATH=$(echo "$TRILIUM_DB_PATH" | sed 's/\//\\\//g')
    sed -i "s/database_path: .*/database_path: \"$ESCAPED_PATH\"/" "$PROJECT_DIR/config/config.yaml"
    echo -e "${GREEN}✓ Updated config.yaml with database path${NC}"
fi
echo

# Step 5: Configure Trilium server URL
echo -e "${BLUE}[5/8] Configuring Trilium server URL...${NC}"
echo -e "${YELLOW}Enter your Trilium server URL (e.g., http://10.0.0.181:8080):${NC}"
echo -e "${YELLOW}(Press Enter to use: http://localhost:8080)${NC}"
read -p "Server URL: " TRILIUM_URL
TRILIUM_URL=${TRILIUM_URL:-http://localhost:8080}

if command -v sed &> /dev/null; then
    # Escape forward slashes and special chars for sed
    ESCAPED_URL=$(echo "$TRILIUM_URL" | sed 's/[\/&]/\\&/g')
    sed -i "s|server_url: .*|server_url: \"$ESCAPED_URL\"|" "$PROJECT_DIR/config/config.yaml"
    echo -e "${GREEN}✓ Updated config.yaml with server URL${NC}"
fi
echo

# Step 6: Configure API keys
echo -e "${BLUE}[6/8] Configuring LLM API keys...${NC}"
echo -e "${YELLOW}Which LLM provider would you like to use?${NC}"
echo "  1) OpenAI (GPT-4, GPT-3.5)"
echo "  2) Anthropic (Claude)"
echo "  3) Google (Gemini)"
echo "  4) Skip (configure later)"
read -p "Enter choice (1-4): " LLM_CHOICE

case $LLM_CHOICE in
    1)
        echo -e "${YELLOW}Enter your OpenAI API key:${NC}"
        read -s OPENAI_KEY
        if [ -n "$OPENAI_KEY" ]; then
            sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_KEY/" "$PROJECT_DIR/.env"
            echo -e "${GREEN}✓ OpenAI API key configured${NC}"
        fi
        ;;
    2)
        echo -e "${YELLOW}Enter your Anthropic API key:${NC}"
        read -s ANTHROPIC_KEY
        if [ -n "$ANTHROPIC_KEY" ]; then
            sed -i "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$ANTHROPIC_KEY/" "$PROJECT_DIR/.env"
            sed -i 's/provider: "openai"/provider: "anthropic"/' "$PROJECT_DIR/config/config.yaml"
            sed -i 's/model: "gpt-4-turbo"/model: "claude-3-5-sonnet-20241022"/' "$PROJECT_DIR/config/config.yaml"
            echo -e "${GREEN}✓ Anthropic API key configured${NC}"
        fi
        ;;
    3)
        echo -e "${YELLOW}Enter your Google Gemini API key:${NC}"
        read -s GEMINI_KEY
        if [ -n "$GEMINI_KEY" ]; then
            sed -i "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=$GEMINI_KEY/" "$PROJECT_DIR/.env"
            sed -i 's/provider: "openai"/provider: "gemini"/' "$PROJECT_DIR/config/config.yaml"
            sed -i 's/model: "gpt-4-turbo"/model: "gemini-2.0-flash-exp"/' "$PROJECT_DIR/config/config.yaml"
            echo -e "${GREEN}✓ Gemini API key configured${NC}"
        fi
        ;;
    4)
        echo -e "${YELLOW}Skipping API key configuration${NC}"
        echo -e "${YELLOW}Edit .env file later to add your API key${NC}"
        ;;
esac
echo

# Step 7: Validate configuration
echo -e "${BLUE}[7/8] Validating configuration...${NC}"

# Test Weaviate connection
if curl -s http://localhost:8080/v1/meta > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Weaviate connection successful${NC}"
else
    echo -e "${RED}✗ Cannot connect to Weaviate${NC}"
fi

# Test database access
if [ -f "$TRILIUM_DB_PATH" ]; then
    if uv run python -c "import sqlite3; conn = sqlite3.connect('$TRILIUM_DB_PATH'); conn.close()" 2>/dev/null; then
        echo -e "${GREEN}✓ Database access successful${NC}"
    else
        echo -e "${RED}✗ Cannot access database${NC}"
    fi
fi

# Secure sensitive files
chmod 600 "$PROJECT_DIR/.env"
chmod 600 "$PROJECT_DIR/config/config.yaml"
echo -e "${GREEN}✓ Secured configuration files${NC}"
echo

# Step 8: Initial indexing
echo -e "${BLUE}[8/8] Initial indexing...${NC}"
echo -e "${YELLOW}Would you like to run the initial full index now?${NC}"
echo -e "${YELLOW}(This may take several minutes depending on your note count)${NC}"
read -p "Run initial index? (Y/n): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${BLUE}Starting full index...${NC}"
    if uv run trilium-ai index --full; then
        echo -e "${GREEN}✓ Initial index complete${NC}"
    else
        echo -e "${RED}✗ Index failed${NC}"
        echo -e "${YELLOW}You can run 'uv run trilium-ai index --full' later${NC}"
    fi
else
    echo -e "${YELLOW}Skipping initial index${NC}"
    echo -e "${YELLOW}Run 'uv run trilium-ai index --full' when ready${NC}"
fi
echo

# Final instructions
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Install systemd services: ${YELLOW}sudo ./scripts/install-service.sh${NC}"
echo -e "  2. Check status: ${YELLOW}uv run trilium-ai status${NC}"
echo -e "  3. Query notes: ${YELLOW}uv run trilium-ai query \"your question\"${NC}"
echo
echo -e "${BLUE}Configuration files:${NC}"
echo -e "  - Config: ${YELLOW}$PROJECT_DIR/config/config.yaml${NC}"
echo -e "  - API Keys: ${YELLOW}$PROJECT_DIR/.env${NC}"
echo
echo -e "${BLUE}Documentation:${NC}"
echo -e "  - See ${YELLOW}DEPLOYMENT.md${NC} for more details"
echo
