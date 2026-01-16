# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trilium AI is a RAG (Retrieval Augmented Generation) system that enables semantic search and LLM integration with Trilium Notes. It reads from Trilium's SQLite database, indexes notes into Weaviate (vector database), and provides an LLM gateway for natural language queries.

## Development Commands

### Package Management (using uv)

```bash
# Install/sync dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras

# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Run a command in the virtual environment
uv run <command>
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_indexer/test_sqlite_reader.py

# Run with coverage
uv run pytest --cov=src/trilium_ai --cov-report=html

# Run specific test
uv run pytest tests/test_indexer/test_sqlite_reader.py::test_read_notes
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Check formatting
uv run black --check src/ tests/

# Lint
uv run ruff check src/ tests/

# Fix linting issues
uv run ruff check --fix src/ tests/

# Type check
uv run mypy src/
```

### Running the Application

```bash
# Full index
uv run trilium-ai index --full

# Incremental sync
uv run trilium-ai index --incremental

# Watch mode
uv run trilium-ai index --watch

# Query
uv run trilium-ai query "your question here"

# Status check
uv run trilium-ai status
```

### Docker

```bash
# Start Weaviate
cd docker && docker compose up -d

# Stop Weaviate
cd docker && docker compose down

# View logs
cd docker && docker compose logs -f
```

## Architecture

### High-Level Data Flow

1. **Trilium SQLite** → Indexer reads notes, attributes, tags
2. **Indexer** → Chunks text, generates embeddings, syncs to Weaviate
3. **Weaviate** → Stores vectors + metadata for semantic search
4. **Gateway** → Retrieves relevant context, assembles prompt, calls LLM
5. **LLM** → Returns natural language answer based on retrieved notes

### Component Structure

```
src/trilium_ai/
├── indexer/          # Trilium Indexer Service
│   ├── sqlite_reader.py    # Reads from Trilium SQLite database
│   ├── chunker.py          # Splits notes into chunks
│   ├── embedder.py         # Generates vector embeddings
│   └── sync.py             # Manages incremental sync with Weaviate
│
├── gateway/          # LLM Gateway
│   ├── retriever.py        # Retrieves relevant chunks from Weaviate
│   ├── prompt.py           # Assembles prompts with context
│   └── llm_client.py       # Calls OpenAI/Anthropic APIs
│
├── shared/           # Shared utilities
│   ├── weaviate_client.py  # Weaviate connection and operations
│   ├── config.py           # Configuration management
│   └── models.py           # Pydantic models for data validation
│
└── cli/              # CLI interface
    └── commands.py         # Click commands for user interaction
```

## Trilium Database Schema

Trilium uses SQLite with the following key tables:

### `notes` table
- `noteId` (TEXT, PRIMARY KEY): Unique note identifier
- `title` (TEXT): Note title
- `type` (TEXT): Note type (text, code, image, etc.)
- `mime` (TEXT): MIME type
- `blobId` (TEXT): Foreign key to blobs table (content storage)
- `isDeleted` (INTEGER): Soft delete flag
- `dateCreated` (TEXT): Creation timestamp
- `dateModified` (TEXT): Last modification timestamp
- `utcDateModified` (TEXT): UTC modification timestamp (for sync tracking)

### `blobs` table
- `blobId` (TEXT, PRIMARY KEY): Unique blob identifier
- `content` (TEXT): Note content (text or binary)
- `dateModified` (TEXT): Modification timestamp
- `utcDateModified` (TEXT): UTC modification timestamp

### `branches` table
- `branchId` (TEXT, PRIMARY KEY): Unique branch identifier
- `noteId` (TEXT): Foreign key to notes
- `parentNoteId` (TEXT): Parent note ID (tree structure)
- `notePosition` (INTEGER): Position in parent's children
- `isExpanded` (INTEGER): UI expansion state
- `isDeleted` (INTEGER): Soft delete flag

### `attributes` table
- `attributeId` (TEXT, PRIMARY KEY): Unique attribute identifier
- `noteId` (TEXT): Foreign key to notes
- `type` (TEXT): "label" or "relation"
- `name` (TEXT): Attribute name
- `value` (TEXT): Attribute value (for labels)
- `isDeleted` (INTEGER): Soft delete flag

### Important Patterns

1. **Soft Deletes**: Always filter by `isDeleted = 0`
2. **Hierarchy**: Use `branches` table to navigate note tree
3. **Sync Tracking**: Use `utcDateModified` for incremental updates
4. **Content Retrieval**: JOIN `notes` with `blobs` on `blobId`

## Key Implementation Patterns

### Configuration Management

Configuration is loaded from YAML files using Pydantic Settings. Environment variables override config file values:

```python
from trilium_ai.shared.config import get_config

config = get_config()
db_path = config.trilium.database_path
```

### Weaviate Integration

The system uses a shared Weaviate client for all operations:

```python
from trilium_ai.shared.weaviate_client import get_weaviate_client

client = get_weaviate_client()
collection = client.collections.get(config.weaviate.collection_name)
```

### Incremental Sync Strategy

1. Track last sync timestamp in Weaviate metadata
2. Query Trilium for notes where `utcDateModified > last_sync_time`
3. Update/delete changed notes in Weaviate
4. Update last sync timestamp

### Chunking Strategy

Notes are chunked to fit within embedding model token limits:

1. Split by sentence boundaries (using sentence-transformers)
2. Combine sentences up to `max_chunk_size` tokens
3. Overlap chunks by `chunk_overlap` tokens for context continuity
4. Each chunk maintains metadata (noteId, title, chunk_index)

### Embedding Generation

Embeddings are generated per chunk:

1. **Sentence Transformers** (default): Local model, fast, no API costs
2. **OpenAI**: `text-embedding-3-small` or `text-embedding-3-large`
3. All chunks from same note share metadata but have unique vectors

### Retrieval Strategy

Hybrid search combines vector and keyword search:

1. Vector search finds semantically similar chunks
2. Keyword search (BM25) finds exact matches
3. `alpha` parameter controls vector vs keyword weight (0-1)
4. Results filtered by `min_score` threshold
5. Top-K chunks returned with metadata

### Prompt Assembly

Context is assembled from retrieved chunks:

```
System: You are an AI assistant with access to the user's Trilium notes.

Context from notes:
[Note: {title}]
{chunk_content}

[Note: {title}]
{chunk_content}

User: {query}
```

Response includes source citations (noteId, title) for transparency.

## Data Models

### Note Model
```python
class Note:
    note_id: str
    title: str
    type: str
    content: str
    attributes: List[Attribute]
    utc_date_modified: datetime
```

### Chunk Model
```python
class Chunk:
    chunk_id: str  # {noteId}_{chunk_index}
    note_id: str
    title: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any]  # tags, labels, path
```

### SearchResult Model
```python
class SearchResult:
    chunks: List[Chunk]
    scores: List[float]
    total_results: int
```

## Error Handling

### Database Connection Errors
- Check database file exists and is readable
- Verify SQLite version compatibility
- Handle locked database (Trilium running)

### Weaviate Connection Errors
- Verify Weaviate is running (`docker compose ps`)
- Check network connectivity
- Validate collection schema matches configuration

### Embedding Errors
- Monitor API rate limits (OpenAI)
- Handle timeout errors with retry logic
- Fall back to local models if API fails

### LLM API Errors
- Implement exponential backoff for rate limits
- Validate API keys in environment
- Handle context length exceeded errors

## Performance Considerations

### Indexing
- Batch inserts to Weaviate (default 100 chunks)
- Use multiprocessing for embedding generation
- Incremental sync minimizes database reads

### Retrieval
- Hybrid search is slower than pure vector search
- Adjust `top_k` based on query complexity
- Cache frequently accessed notes

### Memory
- Sentence Transformers models load into RAM (~500MB)
- Stream large note contents during chunking
- Clear embedding batches after Weaviate insert

## Testing Strategy

### Unit Tests
- Mock SQLite database with test data
- Mock Weaviate client with in-memory store
- Mock LLM APIs with fixed responses

### Integration Tests
- Use test Trilium database
- Use test Weaviate collection
- Test full indexing and retrieval pipeline

### Test Fixtures
```python
# tests/fixtures/trilium_db.py
@pytest.fixture
def test_trilium_db():
    # Create temporary SQLite with sample notes
    pass

# tests/fixtures/weaviate.py
@pytest.fixture
def test_weaviate():
    # Create test collection
    pass
```

## Security Notes

### API Keys
- Never commit `.env` or `config.yaml` with real keys
- Use environment variables in production
- Rotate keys regularly

### Database Access
- Trilium database should be read-only for this service
- Use SQLite file locks to prevent corruption
- Back up before initial full index

### LLM Privacy
- Note contents are sent to OpenAI/Anthropic
- Use local embeddings if privacy is critical
- Consider self-hosted LLMs (Ollama, vLLM)

## Common Issues

### "Database is locked"
Trilium is running and has the database locked. Either:
1. Close Trilium temporarily during indexing
2. Use a copy of the database
3. Configure Trilium for WAL mode

### Weaviate schema mismatch
Collection schema doesn't match configuration. Reset:
```bash
uv run trilium-ai reset
```

### Out of memory during indexing
Reduce batch size in config:
```yaml
weaviate:
  batch_size: 50  # reduce from 100
```

### Poor search results
1. Try hybrid search instead of pure vector
2. Increase `top_k` for more context
3. Adjust `alpha` (0.5 = balanced, 0.75 = more semantic)
4. Use better embedding model (mpnet vs minilm)