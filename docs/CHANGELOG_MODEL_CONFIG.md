# Model Configuration Improvements

## Summary

Made it much easier to configure LLM models using environment variables in `.env` file, and added full support for Google Gemini 2.5 Flash.

## Changes Made

### 1. Environment Variable Configuration (NEW ✨)

You can now easily override LLM settings using simple environment variables:

```bash
# In your .env file:
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

**Previous way (still works):**
```bash
LLM__PROVIDER=gemini  # Double underscore
LLM__MODEL=gemini-2.5-flash
```

**New way (easier):**
```bash
LLM_PROVIDER=gemini   # Single underscore
LLM_MODEL=gemini-2.5-flash
```

### 2. Gemini 2.5 Flash Support

Added full support for Google's latest Gemini 2.5 Flash model:
- Fast and cost-effective
- High-quality responses
- Proper model name handling (`models/` prefix added automatically)

### 3. Updated Documentation

- **docs/MODEL_SETUP.md**: Comprehensive guide for setting up any LLM model
- **README.md**: Updated with quick setup instructions
- **.env.example**: Clear examples with all supported models
- **config.yaml**: Added Gemini 2.5 Flash to model list

### 4. Code Changes

**src/trilium_ai/shared/config.py:**
- Added automatic `.env` file loading using `python-dotenv`
- Added `LLM_*` environment variable overrides (simpler than `LLM__*`)
- Proper handling of nested configuration

**src/trilium_ai/gateway/llm_client.py:**
- Improved Gemini model name handling
- Automatically adds `models/` prefix if not present

## How to Use

### Quick Start with Gemini 2.5 Flash

1. Edit your `.env` file:
```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your-api-key-here
```

2. Test it:
```bash
uv run trilium-ai query "What notes do I have about Python?"
```

### Switching Between Providers

Just change the environment variables - no need to edit config files:

```bash
# Use OpenAI GPT-4
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Use Anthropic Claude
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Use Google Gemini
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=...
```

## Supported Models

### OpenAI
- gpt-4o (latest, recommended)
- gpt-4-turbo
- gpt-3.5-turbo
- gpt-5-mini

### Anthropic Claude
- claude-3-5-sonnet-20241022 (recommended)
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307

### Google Gemini
- **gemini-2.5-flash** ⭐ (NEW - recommended for cost/performance)
- gemini-1.5-pro
- gemini-1.5-flash
- gemini-2.0-flash-exp

## Migration Guide

If you were using `config.yaml` to configure your LLM:

**Before:**
```yaml
# config/config.yaml
llm:
  provider: "openai"
  model: "gpt-4-turbo"
```

**After (recommended):**
```bash
# .env (easier to change, no git commits needed)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
```

Your `config.yaml` settings still work as defaults - environment variables just override them.

## Benefits

1. **Easier Configuration**: No need to edit YAML files
2. **Per-Environment Settings**: Different models for dev/prod
3. **No Git Commits**: Keep your `.env` local
4. **Quick Switching**: Try different models without editing config files
5. **Cost Optimization**: Easily switch to cheaper models (e.g., Gemini 2.5 Flash)

## Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **Google Gemini**: https://aistudio.google.com/app/apikey (generous free tier!)

## Documentation

For more details, see:
- [MODEL_SETUP.md](MODEL_SETUP.md) - Complete model configuration guide
- [README.md](../README.md) - Quick start guide
- [.env.example](../.env.example) - Example environment file
