# Systemd Service Environment Configuration

## Overview

The Trilium AI application automatically loads environment variables from your `.env` file using Python's `python-dotenv` library, making it easy to configure LLM providers, models, and API keys without modifying service files.

## How It Works

**In `src/trilium_ai/shared/config.py`:**

```python
# Load .env file early
_project_root = Path(__file__).parent.parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
```

This means:
1. The application automatically loads `.env` when the config module is imported
2. It finds the `.env` file relative to the source code location
3. All environment variables become available to the application
4. **No systemd configuration needed** - the app handles it itself

The systemd service files only need to set the `WorkingDirectory`:
```ini
WorkingDirectory=%INSTALL_PATH%
```

This ensures the application can find its `.env` file.

## Configuration

### 1. Edit Your .env File

```bash
cd /opt/trilium-ai  # or your installation path
nano .env
```

### 2. Set LLM Configuration

```bash
# LLM Configuration
LLM_PROVIDER=gemini            # openai, anthropic, or gemini
LLM_MODEL=gemini-2.5-flash     # Model name
LLM_TEMPERATURE=0.7            # Optional
LLM_MAX_TOKENS=2000            # Optional

# API Key (matching your provider)
GEMINI_API_KEY=your-key-here
```

### 3. Restart Services

After editing `.env`, restart the services to pick up changes:

```bash
# Restart web service
sudo systemctl restart trilium-ai-web.service

# Sync service will pick up changes on next run
# Or manually trigger:
sudo systemctl start trilium-ai-sync.service
```

## Verification

### Check Application Loads .env

The application loads `.env` automatically via `python-dotenv`. Verify it's working:

```bash
cd /opt/trilium-ai

# Test that config loads environment variables
uv run python -c "
from trilium_ai.shared.config import get_config
cfg = get_config()
print(f'Provider: {cfg.llm.provider}')
print(f'Model: {cfg.llm.model}')
"
```

### Check Service Working Directory

Verify the service has the correct working directory:

```bash
# Check working directory is set
sudo systemctl cat trilium-ai-web.service | grep WorkingDirectory

# Should show:
# WorkingDirectory=/opt/trilium-ai
```

### Check Service Logs

After starting a service, check that the application loaded correctly:

```bash
# Check logs for any configuration errors
sudo journalctl -u trilium-ai-web.service -n 50

# Look for successful startup messages
sudo journalctl -u trilium-ai-web.service | grep -i "provider\|model"
```

## Switching Providers

### Switch to OpenAI

```bash
# Edit .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Restart
sudo systemctl restart trilium-ai-web.service
```

### Switch to Anthropic

```bash
# Edit .env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Restart
sudo systemctl restart trilium-ai-web.service
```

### Switch to Gemini

```bash
# Edit .env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=...

# Restart
sudo systemctl restart trilium-ai-web.service
```

## Troubleshooting

### Environment Variables Not Loading

**Check .env file exists and is readable:**

```bash
ls -la /opt/trilium-ai/.env
cat /opt/trilium-ai/.env
```

**Check file permissions:**

```bash
# Ensure the service user can read the file
sudo chmod 644 /opt/trilium-ai/.env
```

**Check for syntax errors:**

```bash
# .env should have no spaces around =
# Correct:
LLM_PROVIDER=gemini

# Incorrect:
LLM_PROVIDER = gemini
```

### Service Not Picking Up Changes

**Verify systemd saw the change:**

```bash
# Check when service was last started
sudo systemctl status trilium-ai-web.service

# Check journalctl for errors
sudo journalctl -u trilium-ai-web.service -n 100
```

**Force reload systemd and restart:**

```bash
sudo systemctl daemon-reload
sudo systemctl restart trilium-ai-web.service
```

### API Key Not Working

**Verify API key is loaded:**

```bash
# Check environment (be careful - this shows your API key!)
sudo systemctl show trilium-ai-web.service --property=Environment | grep API_KEY
```

**Test API key manually:**

```bash
cd /opt/trilium-ai
source .env
uv run python -c "import os; print(f'Key loaded: {bool(os.getenv(\"GEMINI_API_KEY\"))}')"
```

### Wrong Model Being Used

**Check configuration priority:**

1. Environment variables (`.env`) override `config.yaml`
2. If a value is set in both, `.env` wins
3. Check both files:

```bash
# Check .env
cat .env | grep LLM_

# Check config.yaml
cat config/config.yaml | grep -A 5 "llm:"
```

## Security Notes

### File Permissions

Your `.env` file contains sensitive API keys. Ensure proper permissions:

```bash
# Make file readable only by owner
chmod 600 /opt/trilium-ai/.env

# Verify permissions
ls -la /opt/trilium-ai/.env
```

Should show:
```
-rw------- 1 user user ... .env
```

### Systemd Security

The service files include security hardening:

```ini
# From service files
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/trilium-ai
```

These ensure:
- Services run with minimal privileges
- Can only write to their installation directory
- Have isolated temporary directories
- Cannot escalate privileges

### API Key Rotation

When rotating API keys:

1. Update `.env` with new key
2. Restart services
3. Test that it works
4. Revoke old key at provider

```bash
# Update .env
nano /opt/trilium-ai/.env

# Restart services
sudo systemctl restart trilium-ai-web.service

# Test
curl http://localhost:3000/api/health

# If working, revoke old key at provider
```

## Advanced: Multiple Environments

If you need different configurations for different services, you can:

### Option 1: Multiple .env Files

```bash
# Create environment-specific files
cp .env .env.production
cp .env .env.testing

# Edit service files to use specific env file
sudo systemctl edit trilium-ai-web.service

# Add:
[Service]
EnvironmentFile=-/opt/trilium-ai/.env.production
```

### Option 2: Service Overrides

```bash
# Override specific variables per service
sudo systemctl edit trilium-ai-web.service

# Add:
[Service]
Environment="LLM_MODEL=gpt-4o"
Environment="LLM_TEMPERATURE=0.5"
```

### Option 3: Separate Installations

```bash
# Install to different directories
/opt/trilium-ai-prod/
/opt/trilium-ai-dev/

# Each with its own .env and services
```

## Summary

✅ **Services automatically load `.env`** - No manual configuration needed

✅ **Easy provider switching** - Edit `.env` and restart

✅ **Secure by default** - Proper file permissions and service hardening

✅ **Changes persist** - Configuration survives service restarts and system reboots

For more information, see:
- [MODEL_SETUP.md](MODEL_SETUP.md) - LLM model configuration
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Full deployment guide
- [README.md](../README.md) - Quick start guide
