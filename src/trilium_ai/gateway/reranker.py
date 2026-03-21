"""Reranker for improving search result quality using cross-encoder models."""

import logging
import os
from typing import List, Tuple

from sentence_transformers import CrossEncoder

from trilium_ai.shared.config import get_runtime_cache_dir
from trilium_ai.shared.models import Chunk

logger = logging.getLogger(__name__)


class Reranker:
    """Reranks search results using a cross-encoder model.

    Cross-encoders process query-document pairs together, providing more
    accurate relevance scores than bi-encoders (which embed separately).
    This significantly improves result quality but is slower, so it's used
    as a second stage after initial retrieval.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        """Initialize reranker with a cross-encoder model.

        Args:
            model_name: HuggingFace cross-encoder model name.
                Default: ms-marco-MiniLM-L-6-v2 (fast, good quality)
                Other options:
                - cross-encoder/ms-marco-MiniLM-L-12-v2 (slower, better)
                - cross-encoder/ms-marco-electra-base (even better quality)
        """
        self.model_name = model_name
        self._model: CrossEncoder | None = None
        logger.info(f"Reranker initialized with model: {model_name}")

    @property
    def model(self) -> CrossEncoder:
        """Lazy load the cross-encoder model."""
        if self._model is None:
            cache_dir = get_runtime_cache_dir() / "huggingface"
            cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("HF_HOME", str(cache_dir))
            os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_dir / "hub"))
            os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_dir / "transformers"))
            os.environ.setdefault(
                "SENTENCE_TRANSFORMERS_HOME", str(cache_dir / "sentence-transformers")
            )
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self._model = CrossEncoder(self.model_name, cache_folder=str(cache_dir))
            logger.info("Cross-encoder model loaded successfully")
        return self._model

    def rerank(
        self, query: str, chunks: List[Chunk], top_k: int = 5, debug: bool = False
    ) -> List[Tuple[Chunk, float]]:
        """Rerank chunks by relevance to query using cross-encoder.

        Args:
            query: Search query
            chunks: Initial retrieved chunks to rerank
            top_k: Number of top results to return
            debug: Enable debug logging

        Returns:
            List of (chunk, score) tuples, sorted by relevance (best first)
        """
        if not chunks:
            return []

        if debug:
            logger.info(f"Reranking {len(chunks)} chunks for query: '{query[:50]}...'")

        # Create query-document pairs for cross-encoder
        pairs = [[query, chunk.content] for chunk in chunks]

        # Get cross-encoder scores
        # Higher scores = more relevant
        scores = self.model.predict(pairs)

        if debug:
            logger.info(f"Reranking scores: min={min(scores):.4f}, max={max(scores):.4f}")

        # Sort by score (descending)
        ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)

        if debug:
            logger.info(f"Top {min(top_k, len(ranked))} results after reranking:")
            for i, (chunk, score) in enumerate(ranked[:top_k]):
                logger.info(f"  {i+1}. '{chunk.title}' (score: {score:.4f})")

        return ranked[:top_k]

    def rerank_with_threshold(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = 5,
        min_score: float = 0.0,
        debug: bool = False,
    ) -> List[Tuple[Chunk, float]]:
        """Rerank chunks and filter by minimum score threshold.

        Args:
            query: Search query
            chunks: Initial retrieved chunks
            top_k: Maximum number of results
            min_score: Minimum reranking score threshold
            debug: Enable debug logging

        Returns:
            List of (chunk, score) tuples above threshold
        """
        ranked = self.rerank(query, chunks, top_k=len(chunks), debug=debug)

        # Filter by minimum score
        filtered = [(chunk, score) for chunk, score in ranked if score >= min_score]

        if debug:
            logger.info(
                f"Filtered {len(ranked) - len(filtered)} results below threshold {min_score}"
            )

        return filtered[:top_k]
