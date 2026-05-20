"""Retriever for semantic search in Weaviate."""

import logging
from typing import Optional

from trilium_ai.gateway.query_expander import QueryExpander
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
        use_query_expansion: bool = True,
        synonyms: Optional[dict[str, list[str]]] = None,
        max_expanded_queries: int = 5,
        group_by_note: bool = True,
        use_reranking: bool = False,
        reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        """Initialize the retriever."""
        self.weaviate_client = weaviate_client
        self.embedder = embedder
        self.top_k = top_k
        self.min_score = min_score
        self.search_mode = search_mode
        self.alpha = alpha
        self.use_query_expansion = use_query_expansion
        self.group_by_note = group_by_note
        self.query_expander = QueryExpander(
            synonyms=synonyms,
            max_expanded_queries=max_expanded_queries,
        )
        self.use_reranking = use_reranking

        self._reranker: Optional[Reranker] = None
        if use_reranking:
            self._reranker = Reranker(model_name=reranking_model)
            logger.info("Reranking enabled with model: %s", reranking_model)

    def search(
        self, query: str, top_k: Optional[int] = None, debug: bool = False
    ) -> SearchResult:
        """Search for relevant chunks."""
        k = top_k or self.top_k

        if debug:
            logger.info("Search mode: %s", self.search_mode)
            logger.info("Top-K: %s", k)
            logger.info("Min score threshold: %s", self.min_score)
            logger.info("Alpha (hybrid): %s", self.alpha)
            logger.info("Query expansion: %s", "enabled" if self.use_query_expansion else "disabled")
            logger.info("Group by note: %s", "enabled" if self.group_by_note else "disabled")
            logger.info("Reranking: %s", "enabled" if self.use_reranking else "disabled")

        initial_k = k * 5 if self.use_reranking or self.group_by_note else k
        queries = self.query_expander.expand(query) if self.use_query_expansion else [query]

        if debug and len(queries) > 1:
            logger.info("Expanded queries: %s", queries)

        merged_scores: dict[str, tuple[Chunk, float]] = {}
        for candidate_query in queries:
            result = self._search_single_query(candidate_query, initial_k, debug)
            for chunk, score in zip(result.chunks, result.scores):
                existing = merged_scores.get(chunk.chunk_id)
                if existing is None or score > existing[1]:
                    merged_scores[chunk.chunk_id] = (chunk, score)

        sorted_results = sorted(merged_scores.values(), key=lambda item: item[1], reverse=True)
        chunks = [chunk for chunk, _ in sorted_results]
        scores = [score for _, score in sorted_results]

        if self.use_reranking and self._reranker and chunks:
            if debug:
                logger.info("Reranking %s merged results...", len(chunks))

            rerankable_chunks = self._chunks_for_reranking(chunks)
            ranked = self._reranker.rerank(query, rerankable_chunks, top_k=len(rerankable_chunks), debug=debug)
            score_by_chunk_id = {chunk.chunk_id: float(score) for chunk, score in ranked}
            chunks = sorted(chunks, key=lambda item: score_by_chunk_id.get(item.chunk_id, 0.0), reverse=True)
            scores = [score_by_chunk_id.get(chunk.chunk_id, 0.0) for chunk in chunks]

        if self.group_by_note:
            chunks, scores = self._group_top_chunk_per_note(chunks, scores)

        chunks = chunks[:k]
        scores = scores[:k]
        return SearchResult(chunks=chunks, scores=scores, total_results=len(chunks))

    def _search_single_query(self, query: str, top_k: int, debug: bool) -> SearchResult:
        if self.search_mode == "vector":
            return self._vector_search(query, top_k, debug)
        if self.search_mode == "hybrid":
            return self._hybrid_search(query, top_k, debug)
        if self.search_mode == "keyword":
            return self._keyword_search(query, top_k, debug)
        raise ValueError(f"Unknown search mode: {self.search_mode}")

    def _vector_search(self, query: str, top_k: int, debug: bool = False) -> SearchResult:
        query_vector = self.embedder.embed(query)
        if debug:
            logger.info("Generated query embedding (dim=%s)", len(query_vector))

        results = self.weaviate_client.search_similar(
            query_vector=query_vector,
            limit=top_k,
            min_score=self.min_score,
        )

        chunks = [chunk for chunk, _ in results]
        scores = [score for _, score in results]
        return SearchResult(chunks=chunks, scores=scores, total_results=len(chunks))

    def _hybrid_search(self, query: str, top_k: int, debug: bool = False) -> SearchResult:
        self.weaviate_client.connect()
        query_vector = self.embedder.embed(query)

        if debug:
            logger.info("Generated query embedding (dim=%s)", len(query_vector))

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
            logger.info("Raw results from Weaviate: %s objects", len(response.objects))

        chunks: list[Chunk] = []
        scores: list[float] = []
        filtered_count = 0

        for obj in response.objects:
            score = obj.metadata.score if obj.metadata.score else 0.0
            title = obj.properties.get("title", "Unknown")

            if debug:
                logger.info("  - '%s' (score: %.4f)", title, score)

            if score >= self.min_score:
                chunks.append(self._chunk_from_object(obj.properties))
                scores.append(score)
            else:
                filtered_count += 1
                if debug:
                    logger.info("    ^ FILTERED (below min_score %s)", self.min_score)

        if debug:
            logger.info("Results after filtering: %s (filtered out: %s)", len(chunks), filtered_count)

        return SearchResult(chunks=chunks, scores=scores, total_results=len(chunks))

    def _keyword_search(self, query: str, top_k: int, debug: bool = False) -> SearchResult:
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
            logger.info("Raw BM25 results: %s objects", len(response.objects))

        chunks: list[Chunk] = []
        scores: list[float] = []

        for obj in response.objects:
            score = obj.metadata.score if obj.metadata.score else 0.0
            title = obj.properties.get("title", "Unknown")

            if debug:
                logger.info("  - '%s' (BM25 score: %.4f)", title, score)

            chunks.append(self._chunk_from_object(obj.properties))
            scores.append(score)

        return SearchResult(chunks=chunks, scores=scores, total_results=len(chunks))

    def _chunk_from_object(self, properties: dict) -> Chunk:
        return Chunk(
            chunk_id=properties["chunk_id"],
            note_id=properties["note_id"],
            title=properties["title"],
            content=properties["content"],
            chunk_index=properties["chunk_index"],
            metadata={
                "note_type": properties.get("note_type", "text"),
                "date_modified": properties.get("date_modified", ""),
                "path": properties.get("path", ""),
                "note_id_path": properties.get("note_id_path", ""),
                "retrieval_text": properties.get("retrieval_text", properties.get("content", "")),
            },
        )

    def _chunks_for_reranking(self, chunks: list[Chunk]) -> list[Chunk]:
        rerank_chunks: list[Chunk] = []
        for chunk in chunks:
            rerank_chunks.append(
                Chunk(
                    chunk_id=chunk.chunk_id,
                    note_id=chunk.note_id,
                    title=chunk.title,
                    content=chunk.metadata.get("retrieval_text", chunk.content),
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.metadata,
                )
            )
        return rerank_chunks

    def _group_top_chunk_per_note(
        self, chunks: list[Chunk], scores: list[float]
    ) -> tuple[list[Chunk], list[float]]:
        grouped_chunks: list[Chunk] = []
        grouped_scores: list[float] = []
        seen_notes: set[str] = set()

        for chunk, score in zip(chunks, scores):
            if chunk.note_id in seen_notes:
                continue
            seen_notes.add(chunk.note_id)
            grouped_chunks.append(chunk)
            grouped_scores.append(score)

        return grouped_chunks, grouped_scores
