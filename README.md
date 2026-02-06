# Trilium AI

RAG (Retrieval Augmented Generation) system for Trilium Notes that enables semantic search and LLM integration with your personal knowledge base.

## Architecture

```
                  ┌────────────────────────────┐
                  │        Trilium             │
                  │     SQLite Database        │
                  │ (notes, tree, tags, attrs) │
                  └────────────┬───────────────┘
                               │
                    Full/Incremental Extract
                               │
                               ▼
                  ┌────────────────────────────┐
                  │  Trilium Indexer Service   │
                  │                            │
                  │ - Reads SQLite             │
                  │ - Chunks notes             │
                  │ - Generates embeddings     │
                  │ - Syncs Weaviate           │
                  └────────────┬───────────────┘
                               │
                        Vector + Metadata
                               │
                               ▼
                  ┌────────────────────────────┐
                  │          Weaviate          │
                  │                            │
                  │  - Vector index            │
                  │  - Metadata filtering      │
                  │  - Hybrid search           │
                  └────────────┬───────────────┘
                               │
                    Semantic retrieval (Top-K)
                               │
                               ▼
                  ┌────────────────────────────┐
                  │        LLM Gateway         │
                  │                            │
                  │ - Prompt assembly          │
                  │ - Context injection        │
                  │ - Model calls (GPT/Claude) │
                  └────────────┬───────────────┘
                               │
                               ▼
                    Natural-language answer
```

## Features

- **Web Interface**: Modern, responsive web UI for easy querying
- **REST API**: Programmatic access via FastAPI endpoints
- **Semantic Search**: Vector-based search across all your Trilium notes
- **Incremental Indexing**: Efficiently sync only changed notes
- **Hybrid Search**: Combine keyword and semantic search for better results
- **Multi-LLM Support**: Works with OpenAI GPT, Anthropic Claude, and Google Gemini
- **Note Links**: Direct links to notes in your Trilium instance
- **Hierarchical Context**: Includes note paths for better semantic search
- **Sentence-Based Chunking**: Intelligent text splitting at sentence boundaries
- **Metadata Filtering**: Search by tags, attributes, and note hierarchy
- **Flexible Embeddings**: Support for multiple embedding providers

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- Docker (for running Weaviate locally)
- Trilium Notes with access to its SQLite database

## Quick Start

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Setup

```bash
git clone git@github.com:MrDesjardins/trilium-ai.git
cd trilium-ai
uv sync
```

### 3. Start Weaviate

```bash
cd docker
docker compose up -d
```

### 4. Configure

```bash
cp .env.example .env
```

**Quick Setup with Environment Variables:**

Edit `.env` and set your LLM provider, model, and API key:

```bash
# Example: Using Gemini 2.5 Flash (fast and cost-effective)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your-api-key-here
```

**Supported Providers:**
- **OpenAI**: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`, `gpt-5-mini`
- **Anthropic**: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
- **Gemini**: `gemini-2.5-flash` (recommended), `gemini-1.5-pro`, `gemini-1.5-flash`

See **[docs/MODEL_SETUP.md](docs/MODEL_SETUP.md)** for detailed model configuration guide.

You'll also need to configure your Trilium database path in `config/config.yaml`.

### 5. Initial Index

```bash
uv run trilium-ai index --full
```

### 6. Query Your Notes

**Command Line:**
```bash
uv run trilium-ai query "What are my notes about Python?"
```

**Web Interface:**
```bash
# Start the web server
uv run trilium-ai web

# Or with auto-reload for development
uv run trilium-ai web --reload
```

Then open http://localhost:3000 in your browser.

## Development

### Install Dev Dependencies

```bash
uv sync --all-extras
```

### Run Tests

```bash
uv run pytest
```

### Linting and Formatting

```bash
# Format code
uv run black src/ tests/

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

### Project Structure

```
trilium-ai/
├── src/trilium_ai/
│   ├── indexer/          # SQLite reader, chunker, embedder
│   ├── gateway/          # LLM integration and retrieval
│   ├── web/              # FastAPI web interface
│   │   ├── static/       # CSS, JavaScript
│   │   └── templates/    # HTML templates
│   ├── shared/           # Shared utilities (Weaviate client, config)
│   └── cli/              # CLI commands
├── tests/                # Test suite
├── config/               # Configuration files
├── docker/               # Docker Compose for Weaviate
└── scripts/              # Deployment scripts
```

## CLI Commands

### Indexing

```bash
# Full reindex
uv run trilium-ai index --full

# Incremental sync
uv run trilium-ai index --incremental

# Watch mode (continuous sync)
uv run trilium-ai index --watch
```

### Querying

```bash
# Query with default settings
uv run trilium-ai query "your question"

# Query with custom top-k
uv run trilium-ai query "your question" --top-k 10

# Query specific model
uv run trilium-ai query "your question" --model gpt-4-turbo
```

### Web Interface

```bash
# Start web server
uv run trilium-ai web

# Custom port
uv run trilium-ai web --port 8080

# Development mode with auto-reload
uv run trilium-ai web --reload
```

### Management

```bash
# Check index status
uv run trilium-ai status

# Reset index
uv run trilium-ai reset
```

## Configuration

### Environment Variables (Recommended)

The easiest way to configure Trilium AI is using environment variables in `.env`:

```bash
# LLM Configuration (override config.yaml)
LLM_PROVIDER=gemini              # openai, anthropic, or gemini
LLM_MODEL=gemini-2.5-flash       # See MODEL_SETUP.md for all options
LLM_TEMPERATURE=0.7              # 0.0-1.0 (optional)
LLM_MAX_TOKENS=2000             # Max response tokens (optional)

# API Keys
GEMINI_API_KEY=your-key-here    # For Gemini models
OPENAI_API_KEY=sk-...           # For OpenAI models
ANTHROPIC_API_KEY=sk-ant-...    # For Claude models
```

**See [docs/MODEL_SETUP.md](docs/MODEL_SETUP.md) for the complete model configuration guide.**

### config.yaml

See `config/config.yaml` for all available configuration options.

Key configuration sections:
- **trilium**: Database path and sync settings
- **weaviate**: Vector database connection
- **embeddings**: Embedding model and parameters
- **chunking**: Text chunking strategy
- **llm**: LLM provider and model settings (can be overridden by env vars)
- **retrieval**: Search parameters

## Production Deployment

For production deployment on Ubuntu Server with automated setup and systemd services:

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/mrdesjardins/trilium-ai.git
sudo chown -R $USER:$USER trilium-ai
cd trilium-ai

# Run automated setup
./scripts/setup.sh

# Install systemd services
sudo ./scripts/install-service.sh
```

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for comprehensive production deployment guide including:
- Automated setup scripts
- Systemd service installation (sync + web)
- Auto-start on boot
- Update procedures
- Monitoring and troubleshooting
- Security best practices

See **[WEB.md](WEB.md)** for web interface documentation including:
- Development and production setup
- API endpoints and examples
- Security considerations
- Customization guide

## License

MIT
