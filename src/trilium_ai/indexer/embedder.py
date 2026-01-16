"""Embedding generation for text chunks."""

import os
from typing import Any, Literal, Union

from sentence_transformers import SentenceTransformer
import tiktoken
from openai import OpenAI

class Embedder:
    """Generates embeddings for text chunks."""

    def __init__(
        self,
        provider: Literal["sentence-transformers", "openai"] = "sentence-transformers",
        model: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
    ) -> None:
        """Initialize the embedder.

        Args:
            provider: Embedding provider (sentence-transformers, openai)
            model: Model name
            dimension: Expected embedding dimension
        """
        self.provider = provider
        self.model = model
        self.dimension = dimension
        self._model_instance: Union[OpenAI, SentenceTransformer] = None
        self._tokenizer: Any = None

    def _load_model(self) -> None:
        """Lazy load the embedding model."""
        if self._model_instance is not None:
            return

        if self.provider == "sentence-transformers":
            self._model_instance = SentenceTransformer(self.model)
            print(f"Loaded sentence-transformers model: {self.model}")

        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self._model_instance = OpenAI(api_key=api_key)
            print(f"Initialized OpenAI client with model: {self.model}")

        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        self._load_model()

        if self.provider == "sentence-transformers":
            embedding = self._model_instance.encode(text, convert_to_numpy=True)
            return embedding.tolist()

        elif self.provider == "openai":
            response = self._model_instance.embeddings.create(input=text, model=self.model)
            return response.data[0].embedding

        raise ValueError(f"Unsupported provider: {self.provider}")

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        self._load_model()

        if not texts:
            return []

        if self.provider == "sentence-transformers":
            # Process in batches to manage memory
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                embeddings = self._model_instance.encode(batch, convert_to_numpy=True)
                all_embeddings.extend(embeddings.tolist())
            return all_embeddings

        elif self.provider == "openai":
            # OpenAI API handles batching internally
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                response = self._model_instance.embeddings.create(input=batch, model=self.model)
                all_embeddings.extend([item.embedding for item in response.data])
            return all_embeddings

        raise ValueError(f"Unsupported provider: {self.provider}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if self._tokenizer is None:
            try:
                # Use tiktoken for OpenAI-compatible token counting
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Fallback: rough estimate
                return len(text) // 4

        return len(self._tokenizer.encode(text))
