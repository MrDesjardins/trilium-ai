#!/bin/bash
# Deploy script - push to GitHub and update the remote server
# Usage: ./scripts/deploy.sh

set -e

REMOTE_HOST="10.0.0.181"
REMOTE_USER="pdesjardins"
REMOTE_DIR="/home/pdesjardins/code/trilium-ai"

echo "Pushing to GitHub..."
git push origin main

echo "Deploying to $REMOTE_HOST..."
ssh "$REMOTE_USER@$REMOTE_HOST" "bash -l $REMOTE_DIR/scripts/update.sh"

echo ""
echo "Deploy complete!"
