# Model Setup Guide

This guide explains how to configure LLM models for Trilium AI using environment variables.

## Quick Setup

The easiest way to configure your LLM model is using environment variables in your `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and set your provider and model
```

## Environment Variables

### LLM Configuration

You can override any LLM setting from `config.yaml` using environment variables with the `LLM_` prefix:

```bash
# Required: Set the LLM provider
LLM_PROVIDER=gemini

# Required: Set the model name
LLM_MODEL=gemini-2.5-flash

# Optional: Adjust temperature (0.0 = deterministic, 1.0 = creative)
LLM_TEMPERATURE=0.7

# Optional: Set max output tokens
LLM_MAX_TOKENS=2000
```

### API Keys

Depending on your chosen provider, you'll need the corresponding API key:

```bash
# For OpenAI models
OPENAI_API_KEY=sk-...

# For Anthropic/Claude models
ANTHROPIC_API_KEY=sk-ant-...

# For Google Gemini models (either variable works)
GEMINI_API_KEY=...
# or
GOOGLE_API_KEY=...
```

## Supported Models

### OpenAI
- `gpt-4o` - Latest GPT-4 Omni (recommended)
- `gpt-4-turbo` - Fast GPT-4
- `gpt-3.5-turbo` - Faster, cheaper option
- `gpt-5-mini` - Latest small model

**Example:**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key-here
```

### Anthropic Claude
- `claude-3-5-sonnet-20241022` - Best balance (recommended)
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Fast and capable
- `claude-3-haiku-20240307` - Fastest, cheapest

**Example:**
```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Google Gemini
- `gemini-2.5-flash` - **Latest and recommended** - Fast, high quality, cost-effective
- `gemini-1.5-pro` - Most capable for complex tasks
- `gemini-1.5-flash` - Fast and efficient
- `gemini-2.0-flash-exp` - Experimental v2.0 (may change)

**Example:**
```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your-key-here
```

## Getting API Keys

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add credits to your account at https://platform.openai.com/settings/organization/billing/overview

### Anthropic
1. Go to https://console.anthropic.com/settings/keys
2. Create a new API key
3. Add credits if needed

### Google Gemini
1. Go to https://aistudio.google.com/app/apikey
2. Create a new API key
3. Gemini offers a generous free tier

## Example .env File

Here's a complete example for using Gemini 2.5 Flash:

```bash
# LLM Configuration
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# API Key
GEMINI_API_KEY=your-gemini-api-key-here

# Optional: Other API keys if you switch providers
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

## Testing Your Setup

After configuring your `.env` file, test it with:

```bash
# Run a simple query
uv run trilium-ai query "What notes do I have about Python?"

# Check the logs to verify which model is being used
tail -f logs/trilium-ai.log
```

## Troubleshooting

### "API key not set" error
- Make sure your `.env` file exists in the project root
- Verify the API key variable name matches your provider
- Check for extra spaces or quotes around the key

### "Model not found" error
- Verify the model name is spelled correctly
- Check that your API key has access to that model
- Some models require special access (like GPT-5 or experimental models)

### Rate limit errors
- Consider using a slower, cheaper model
- Add delays between requests
- Upgrade your API plan if needed

## Advanced: Using config.yaml

You can also configure models in `config/config.yaml`:

```yaml
llm:
  provider: "gemini"
  model: "gemini-2.5-flash"
  max_tokens: 2000
  temperature: 0.7
```

**Note:** Environment variables in `.env` will override `config.yaml` settings, so you can set defaults in the YAML and override them per-environment.
