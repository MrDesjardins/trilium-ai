"""Retriever for semantic search in Weaviate."""

import logging
from typing import Optional

from trilium_ai.gateway.reranker import Reranker
from trilium_ai.indexer.embedder import Embedder
from trilium_ai.shared.models import Chunk, SearchResult
from trilium_ai.shared.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieves relevant chunks from Weaviate for RAG queries."""

    def __init__(
        self,
        weaviate_client: WeaviateClient,
        embedder: Embedder,
        top_k: int = 5,
        min_score: float = 0.5,
        search_mode: str = "hybrid",
        alpha: float = 0.75,
        use_reranking: bool = False,
        reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        """Initialize the retriever.

        Args:
            weaviate_client: Weaviate client instance
            embedder: Embedder for query embedding
            top_k: Number of results to retrieve
            min_score: Minimum similarity score threshold
            search_mode: Search mode (vector, hybrid, keyword)
            alpha: Hybrid search alpha (0=keyword, 1=vector)
            use_reranking: Enable reranking with cross-encoder
            reranking_model: Cross-encoder model name for reranking
        """
        self.weaviate_client = weaviate_client
        self.embedder = embedder
        self.top_k = top_k
        self.min_score = min_score
        self.search_mode = search_mode
        self.alpha = alpha
        self.use_reranking = use_reranking

        # Initialize reranker if enabled
        self._reranker: Optional[Reranker] = None
        if use_reranking:
            self._reranker = Reranker(model_name=reranking_model)
            logger.info("Reranking enabled with model: %s", reranking_model)

    def search(
        self, query: str, top_k: Optional[int] = None, debug: bool = False
    ) -> SearchResult:
        """Search for relevant chunks.

        Args:
            query: Search query
            top_k: Override default top_k
            debug: Enable debug logging

        Returns:
            SearchResult with chunks and scores
        """
        k = top_k or self.top_k

        if debug:
            logger.info(f"Search mode: {self.search_mode}")
            logger.info(f"Top-K: {k}")
            logger.info(f"Min score threshold: {self.min_score}")
            logger.info(f"Alpha (hybrid): {self.alpha}")
            logger.info(f"Reranking: {'enabled' if self.use_reranking else 'disabled'}")

        # If reranking is enabled, retrieve more initial results
        initial_k = k * 3 if self.use_reranking else k

        # Perform initial search
        if self.search_mode == "vector":
            result = self._vector_search(query, initial_k, debug)
        elif self.search_mode == "hybrid":
            result = self._hybrid_search(query, initial_k, debug)
        elif self.search_mode == "keyword":
            result = self._keyword_search(query, initial_k, debug)
        else:
            raise ValueError(f"Unknown search mode: {self.search_mode}")

        # Apply reranking if enabled
        if self.use_reranking and self._reranker and result.chunks:
            if debug:
                logger.info(f"Reranking {len(result.chunks)} results...")

            ranked = self._reranker.rerank(query, result.chunks, top_k=k, debug=debug)
            chunks = [chunk for chunk, _ in ranked]
            scores = [float(score) for _, score in ranked]

            result = SearchResult(
                chunks=chunks, scores=scores, total_results=len(chunks)
            )

            if debug:
                logger.info(f"After reranking: {len(result.chunks)} results")

        return result

    def _vector_search(self, query: str, top_k: int, debug: bool = False) -> SearchResult:
        """Perform pure vector similarity search.

        Args:
            query: Search query
            top_k: Number of results
            debug: Enable debug logging

        Returns:
            SearchResult
        """
        # Generate query embedding
        query_vector = self.embedder.embed(query)

        if debug:
            logger.info(f"Generated query embedding (dim={len(query_vector)})")

        # Search in Weaviate
        results = self.weaviate_client.search_similar(
            query_vector=query_vector,
            limit=top_k,
            min_score=self.min_score,
        )

        chunks = [chunk for chunk, _ in results]
        scores = [score for _, score in results]

        return SearchResult(
            chunks=chunks,
            scores=scores,
            total_results=len(chunks),
        )

    def _hybrid_search(self, query: str, top_k: int, debug: bool = False) -> SearchResult:
        """Perform hybrid search combining vector and keyword search.

        Args:
            query: Search query
            top_k: Number of results
            debug: Enable debug logging

        Returns:
            SearchResult
        """
        self.weaviate_client.connect()

        # Generate query embedding
        query_vector = self.embedder.embed(query)

        if debug:
            logger.info(f"Generated query embedding (dim={len(query_vector)})")

        # Perform hybrid search
        collection = self.weaviate_client._client.collections.get(
            self.weaviate_client.collection_name
        )

        from weaviate.classes.query import MetadataQuery

        response = collection.query.hybrid(
            query=query,
            vector=query_vector,
            alpha=self.alpha,
            limit=top_k,
            return_metadata=MetadataQuery(score=True),
        )

        if debug:
            logger.info(f"Raw results from Weaviate: {len(response.objects)} objects")

        chunks = []
        scores = []
        filtered_count = 0

        for obj in response.objects:
            score = obj.metadata.score if obj.metadata.score else 0.0
            title = obj.properties.get("title", "Unknown")

            if debug:
                logger.info(f"  - '{title}' (score: {score:.4f})")

            if score >= self.min_score:
                chunk = Chunk(
                    chunk_id=obj.properties["chunk_id"],
                    note_id=obj.properties["note_id"],
                    title=obj.properties["title"],
                    content=obj.properties["content"],
                    chunk_index=obj.properties["chunk_index"],
                    metadata={
                        "note_type": obj.properties.get("note_type", "text"),
                        "date_modified": obj.properties.get("date_modified", ""),
                        "path": obj.properties.get("path", ""),
                        "note_id_path": obj.properties.get("note_id_path", ""),
                    },
                )
                chunks.append(chunk)
                scores.append(score)
            else:
                filtered_count += 1
                if debug:
                    logger.info(f"    ^ FILTERED (below min_score {self.min_score})")

        if debug:
            logger.info(f"Results after filtering: {len(chunks)} (filtered out: {filtered_count})")

        return SearchResult(
            chunks=chunks,
            scores=scores,
            total_results=len(chunks),
        )

    def _keyword_search(self, query: str, top_k: int, debug: bool = False) -> SearchResult:
        """Perform BM25 keyword search.

        Args:
            query: Search query
            top_k: Number of results
            debug: Enable debug logging

        Returns:
            SearchResult
        """
        self.weaviate_client.connect()

        collection = self.weaviate_client._client.collections.get(
            self.weaviate_client.collection_name
        )

        from weaviate.classes.query import MetadataQuery

        response = collection.query.bm25(
            query=query,
            limit=top_k,
            return_metadata=MetadataQuery(score=True),
        )

        if debug:
            logger.info(f"Raw BM25 results: {len(response.objects)} objects")

        chunks = []
        scores = []

        for obj in response.objects:
            score = obj.metadata.score if obj.metadata.score else 0.0
            title = obj.properties.get("title", "Unknown")

            if debug:
                logger.info(f"  - '{title}' (BM25 score: {score:.4f})")

            # BM25 scores are not normalized, so we don't apply min_score filter
            chunk = Chunk(
                chunk_id=obj.properties["chunk_id"],
                note_id=obj.properties["note_id"],
                title=obj.properties["title"],
                content=obj.properties["content"],
                chunk_index=obj.properties["chunk_index"],
                metadata={
                    "note_type": obj.properties.get("note_type", "text"),
                    "date_modified": obj.properties.get("date_modified", ""),
                    "path": obj.properties.get("path", ""),
                    "note_id_path": obj.properties.get("note_id_path", ""),
                },
            )
            chunks.append(chunk)
            scores.append(score)

        return SearchResult(
            chunks=chunks,
            scores=scores,
            total_results=len(chunks),
        )
