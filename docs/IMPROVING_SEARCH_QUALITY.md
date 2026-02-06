# Improving Search Quality in Trilium AI

This guide covers various strategies to improve search results quality, from simple configuration tweaks to advanced techniques.

## Current Configuration

Your current setup:
- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Search Mode**: Hybrid (vector + keyword)
- **Top-K**: 7 results
- **Min Score**: 0.4
- **Alpha**: 0.75 (75% semantic, 25% keyword)

## Quick Wins (Configuration Only)

### 1. Adjust Retrieval Parameters

Edit `config/config.yaml` or use environment variables:

```yaml
retrieval:
  # Retrieve more results for better context
  top_k: 10  # Increase from 7

  # More strict filtering (higher quality, fewer results)
  min_score: 0.6  # Increase from 0.4

  # Adjust semantic vs keyword balance
  alpha: 0.85  # More semantic (0.0 = all keyword, 1.0 = all semantic)

  # Try different search modes
  mode: "vector"  # Options: vector, hybrid, keyword
```

**Environment variable overrides:**
```bash
# Add to .env
RETRIEVAL_TOP_K=10
RETRIEVAL_MIN_SCORE=0.6
RETRIEVAL_ALPHA=0.85
```

**Testing different configurations:**

```bash
# More semantic search
uv run trilium-ai query "your question" --top-k 10 --alpha 0.9

# Pure keyword search
uv run trilium-ai query "exact phrase match"  # Will use BM25

# More results, lower threshold
uv run trilium-ai query "broad topic" --top-k 15 --min-score 0.3
```

### 2. Optimize Alpha Parameter

| Alpha | Behavior | Best For |
|-------|----------|----------|
| 0.0 | Pure keyword (BM25) | Exact phrases, technical terms, code |
| 0.3 | Mostly keyword | Names, IDs, specific terminology |
| 0.5 | Balanced | General queries |
| 0.75 | Mostly semantic (current) | Conceptual questions |
| 0.9 | Nearly pure semantic | Vague queries, synonyms |
| 1.0 | Pure vector search | Meaning-based, cross-lingual |

**Recommendation:** Start with `alpha: 0.75`, adjust based on query types.

## Medium Impact (Better Models)

### 3. Upgrade Embedding Model

Better embeddings = better semantic understanding.

#### Option A: Better Sentence Transformer (Free, Local)

**all-mpnet-base-v2** - Significantly better quality, 768 dimensions:

```yaml
# config/config.yaml
embeddings:
  provider: "sentence-transformers"
  model: "all-mpnet-base-v2"
  dimension: 768  # Must match model
```

**Performance comparison:**
- `all-MiniLM-L6-v2`: Fast, 384D, good quality
- `all-mpnet-base-v2`: Slower, 768D, **excellent quality** ⭐

**After changing:**
```bash
# Reset and reindex (required for dimension change)
uv run trilium-ai reset
uv run trilium-ai index --full
```

#### Option B: OpenAI Embeddings (Paid, Best Quality)

**text-embedding-3-small** - State-of-the-art:

```yaml
embeddings:
  provider: "openai"
  model: "text-embedding-3-small"
  dimension: 1536
```

```bash
# Add to .env
OPENAI_API_KEY=sk-...
```

**Costs:** ~$0.02 per 1M tokens (very affordable)

**Performance:**
- Much better semantic understanding
- Better cross-lingual support
- Handles synonyms and paraphrasing better

### 4. Optimize Chunking Strategy

Better chunks = better retrieval.

```yaml
chunking:
  # Larger chunks = more context per chunk
  max_chunk_size: 768  # Increase from 512

  # More overlap = less context loss at boundaries
  chunk_overlap: 100   # Increase from 50

  # Try different strategies
  strategy: "sentence"  # Options: sentence, paragraph, token
```

**Trade-offs:**
- **Larger chunks**: More context, fewer chunks, may be less precise
- **Smaller chunks**: More precise, more chunks, less context per chunk
- **More overlap**: Better context continuity, more storage

## High Impact (Code Changes)

### 5. Add Reranking

Reranking dramatically improves result quality by scoring initial results with a cross-encoder.

**Create `src/trilium_ai/gateway/reranker.py`:**

```python
"""Reranker for improving search result quality."""

from typing import List, Tuple
from sentence_transformers import CrossEncoder
from trilium_ai.shared.models import Chunk

class Reranker:
    """Reranks search results using a cross-encoder."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize reranker.

        Args:
            model_name: Cross-encoder model name
        """
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """Rerank chunks by relevance to query.

        Args:
            query: Search query
            chunks: Initial retrieved chunks
            top_k: Number of results to return

        Returns:
            List of (chunk, score) tuples, sorted by relevance
        """
        if not chunks:
            return []

        # Create query-chunk pairs
        pairs = [[query, chunk.content] for chunk in chunks]

        # Get cross-encoder scores
        scores = self.model.predict(pairs)

        # Sort by score
        ranked = sorted(
            zip(chunks, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return ranked[:top_k]
```

**Update `retriever.py` to use reranking:**

```python
from trilium_ai.gateway.reranker import Reranker

class Retriever:
    def __init__(self, *args, use_reranking: bool = True, **kwargs):
        # ... existing init ...
        self.use_reranking = use_reranking
        if use_reranking:
            self.reranker = Reranker()

    def search(self, query: str, top_k: Optional[int] = None, debug: bool = False) -> SearchResult:
        k = top_k or self.top_k

        # Retrieve more results if reranking
        initial_k = k * 3 if self.use_reranking else k

        # ... existing search logic ...
        result = self._hybrid_search(query, initial_k, debug)

        # Rerank if enabled
        if self.use_reranking and result.chunks:
            ranked = self.reranker.rerank(query, result.chunks, k)
            chunks = [chunk for chunk, _ in ranked]
            scores = [score for _, score in ranked]
            result = SearchResult(chunks=chunks, scores=scores, total_results=len(chunks))

        return result
```

**Add to config:**
```yaml
retrieval:
  use_reranking: true
  reranking_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
```

**Expected improvement:** 15-30% better relevance

### 6. Query Expansion

Expand queries with synonyms and related terms.

**Create `src/trilium_ai/gateway/query_expander.py`:**

```python
"""Query expansion for improved recall."""

class QueryExpander:
    """Expands queries with related terms."""

    def expand(self, query: str) -> str:
        """Expand query with synonyms and related terms.

        Args:
            query: Original query

        Returns:
            Expanded query
        """
        # Simple keyword expansion
        expansions = {
            "python": "python programming language script",
            "javascript": "javascript js typescript node",
            "react": "react reactjs component jsx",
            # Add more based on your domain
        }

        query_lower = query.lower()
        for term, expanded in expansions.items():
            if term in query_lower:
                query += f" {expanded}"

        return query
```

**Use in retriever:**
```python
def search(self, query: str, ...):
    # Expand query
    if self.use_query_expansion:
        expanded_query = self.query_expander.expand(query)
        if debug:
            logger.info(f"Expanded query: {expanded_query}")
        query = expanded_query

    # Continue with search...
```

### 7. Metadata Filtering

Filter results by note type, date, or path.

**Add to retriever:**
```python
def search(
    self,
    query: str,
    note_type: Optional[str] = None,
    date_after: Optional[str] = None,
    path_contains: Optional[str] = None,
    **kwargs
) -> SearchResult:
    """Search with metadata filters."""

    # Build Weaviate filter
    filters = []
    if note_type:
        filters.append(Filter.by_property("note_type").equal(note_type))
    if date_after:
        filters.append(Filter.by_property("date_modified").greater_than(date_after))
    if path_contains:
        filters.append(Filter.by_property("path").contains_any([path_contains]))

    combined_filter = Filter.all_of(filters) if filters else None

    # Apply filter to search
    response = collection.query.hybrid(
        query=query,
        vector=query_vector,
        alpha=self.alpha,
        limit=top_k,
        filters=combined_filter,  # Add filter
        return_metadata=MetadataQuery(score=True),
    )
```

**Usage:**
```python
# Only search in code notes
results = retriever.search("function definition", note_type="code")

# Only recent notes
results = retriever.search("meeting notes", date_after="2024-01-01")

# Only notes in specific path
results = retriever.search("project", path_contains="Work/Projects")
```

## Advanced Techniques

### 8. Two-Stage Retrieval

Retrieve broadly, then filter precisely.

```python
def two_stage_search(self, query: str, top_k: int = 5) -> SearchResult:
    """Two-stage retrieval: broad recall, then precise reranking."""

    # Stage 1: Broad recall (low min_score, high top_k)
    self.min_score = 0.3
    initial = self.search(query, top_k=top_k * 5)

    # Stage 2: Precise reranking
    if self.use_reranking:
        ranked = self.reranker.rerank(query, initial.chunks, top_k)
        return SearchResult(
            chunks=[c for c, _ in ranked],
            scores=[s for _, s in ranked],
            total_results=len(ranked)
        )

    return initial
```

### 9. Multi-Query Retrieval

Generate multiple query variations for better recall.

```python
def multi_query_search(self, query: str, top_k: int = 5) -> SearchResult:
    """Generate multiple query variations and merge results."""

    # Generate query variations using LLM
    variations = self.generate_query_variations(query)  # e.g., 3 variations

    # Search with each variation
    all_chunks = {}
    for variation in variations:
        result = self.search(variation, top_k=top_k * 2)
        for chunk, score in zip(result.chunks, result.scores):
            # Merge by taking max score
            if chunk.chunk_id in all_chunks:
                all_chunks[chunk.chunk_id] = max(all_chunks[chunk.chunk_id], score)
            else:
                all_chunks[chunk.chunk_id] = score

    # Sort and return top k
    sorted_chunks = sorted(all_chunks.items(), key=lambda x: x[1], reverse=True)[:top_k]
    # ... convert back to SearchResult ...
```

### 10. Weaviate Configuration Tuning

Edit Weaviate Docker configuration for better performance.

**In `docker/docker-compose.yml`:**

```yaml
services:
  weaviate:
    environment:
      # Increase query limits
      QUERY_MAXIMUM_RESULTS: 10000

      # Better vector index (HNSW parameters)
      HNSW_MAX_CONNECTIONS: 64  # Default: 32, higher = more memory, better quality
      HNSW_EF_CONSTRUCTION: 256  # Default: 128, higher = slower indexing, better quality

      # Distance metric (cosine is usually best)
      DISTANCE_METRIC: cosine  # Options: cosine, dot, l2-squared, hamming, manhattan
```

**Restart Weaviate:**
```bash
cd docker
docker compose down
docker compose up -d
```

## Recommended Improvement Path

### Phase 1: Quick Wins (1 hour)
1. ✅ Adjust `alpha` to 0.85 for more semantic search
2. ✅ Increase `top_k` to 10
3. ✅ Increase `min_score` to 0.6
4. ✅ Test with various queries

### Phase 2: Better Model (2 hours)
1. ✅ Upgrade to `all-mpnet-base-v2` embeddings
2. ✅ Reindex with `--full`
3. ✅ Compare results quality

### Phase 3: Reranking (4 hours)
1. ✅ Implement reranker class
2. ✅ Integrate with retriever
3. ✅ Add configuration options
4. ✅ Measure improvement

### Phase 4: Advanced (1-2 days)
1. ✅ Add query expansion
2. ✅ Implement metadata filtering
3. ✅ Try two-stage retrieval
4. ✅ Tune Weaviate parameters

## Measuring Improvements

### Manual Testing

```bash
# Create a test query set
cat > test_queries.txt << EOF
What are my notes about machine learning?
Show me all Python code examples
Recent meeting notes about the project
How do I configure authentication?
EOF

# Test each query
while read query; do
  echo "Query: $query"
  uv run trilium-ai query "$query" --debug
  echo "---"
done < test_queries.txt
```

### Relevance Scoring

Rate results 1-5 for relevance:
- 5: Perfect match
- 4: Highly relevant
- 3: Somewhat relevant
- 2: Tangentially related
- 1: Not relevant

Track average relevance score before/after changes.

## Common Issues

### Issue: Too many irrelevant results

**Solutions:**
- Increase `min_score` (0.6 → 0.7)
- Increase `alpha` (more semantic)
- Add reranking
- Use better embedding model

### Issue: Missing relevant results

**Solutions:**
- Decrease `min_score` (0.6 → 0.4)
- Increase `top_k` (10 → 20)
- Try `alpha: 0.5` (more balanced)
- Add query expansion

### Issue: Keyword searches not working

**Solutions:**
- Decrease `alpha` (0.75 → 0.3)
- Use `mode: keyword` for specific queries
- Ensure BM25 is enabled in Weaviate

### Issue: Slow searches

**Solutions:**
- Reduce `top_k`
- Use smaller embedding model
- Disable reranking for fast queries
- Tune HNSW parameters

## Summary

**Quick improvements (no code):**
1. Adjust `alpha`, `top_k`, `min_score` in config
2. Test different search modes

**Medium improvements (model upgrade):**
3. Upgrade to `all-mpnet-base-v2` or OpenAI embeddings
4. Optimize chunking parameters

**Advanced improvements (code changes):**
5. Add reranking with cross-encoder
6. Implement query expansion
7. Add metadata filtering
8. Try two-stage or multi-query retrieval

**Expected gains:**
- Config tweaks: 5-15% improvement
- Better model: 20-40% improvement
- Reranking: 15-30% improvement
- Combined: 50-70% improvement

Start with Phase 1 (config), measure results, then proceed to Phase 2 (better model) if needed.
