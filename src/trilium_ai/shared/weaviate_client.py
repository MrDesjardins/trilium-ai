"""Weaviate client for managing collections and data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter, MetadataQuery

from trilium_ai.shared.models import Chunk


class WeaviateClient:
    """Manages Weaviate connection and operations."""

    def __init__(
        self,
        url: str = "http://localhost:8601",
        api_key: Optional[str] = None,
        collection_name: str = "TriliumNotes",
        sync_state_file: str = ".trilium-ai-sync-state.json",
    ) -> None:
        """Initialize Weaviate client.

        Args:
            url: Weaviate URL
            api_key: Optional API key for authentication
            collection_name: Name of the collection to use
            sync_state_file: Path to file storing sync state
        """
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.sync_state_file = Path(sync_state_file)
        self._client: Optional[weaviate.WeaviateClient] = None

    def _read_sync_state(self) -> dict[str, Any]:
        """Read sync state from disk."""
        if not self.sync_state_file.exists():
            return {}

        try:
            with open(self.sync_state_file, "r") as f:
                state = json.load(f)
                return state if isinstance(state, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_sync_state(self, state: dict[str, Any]) -> None:
        """Persist sync state to disk."""
        self.sync_state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.sync_state_file, "w") as f:
            json.dump(state, f, indent=2)

    def connect(self) -> None:
        """Connect to Weaviate."""
        if self._client is not None:
            return

        # Parse URL to extract host and port
        url_without_scheme = self.url.replace("http://", "").replace("https://", "")
        host_port = url_without_scheme.split(":")
        http_host = host_port[0]
        http_port = int(host_port[1]) if len(host_port) > 1 else 8080
        http_secure = self.url.startswith("https://")

        if self.api_key:
            self._client = weaviate.connect_to_custom(
                http_host=http_host,
                http_port=http_port,
                http_secure=http_secure,
                grpc_host=http_host,
                grpc_port=50051,
                grpc_secure=http_secure,
                auth_credentials=Auth.api_key(self.api_key),
            )
        else:
            self._client = weaviate.connect_to_custom(
                http_host=http_host,
                http_port=http_port,
                http_secure=http_secure,
                grpc_host=http_host,
                grpc_port=50051,
                grpc_secure=http_secure,
            )

        print(f"Connected to Weaviate at {self.url}")

    def disconnect(self) -> None:
        """Disconnect from Weaviate."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def create_collection(self, embedding_dimension: int = 384) -> None:
        """Create the Trilium notes collection if it doesn't exist.

        Args:
            embedding_dimension: Dimension of embedding vectors
        """
        if self._client is None:
            self.connect()

        # Check if collection exists
        if self._client.collections.exists(self.collection_name):
            print(f"Collection '{self.collection_name}' already exists")
            return

        # Create collection with schema
        self._client.collections.create(
            name=self.collection_name,
            description="Trilium notes chunks with embeddings",
            properties=[
                Property(
                    name="chunk_id",
                    data_type=DataType.TEXT,
                    description="Unique chunk identifier",
                ),
                Property(
                    name="note_id",
                    data_type=DataType.TEXT,
                    description="Parent note ID",
                    skip_vectorization=True,
                ),
                Property(
                    name="title",
                    data_type=DataType.TEXT,
                    description="Note title",
                ),
                Property(
                    name="content",
                    data_type=DataType.TEXT,
                    description="Chunk content",
                ),
                Property(
                    name="retrieval_text",
                    data_type=DataType.TEXT,
                    description="Normalized text used for embeddings and retrieval",
                ),
                Property(
                    name="chunk_index",
                    data_type=DataType.INT,
                    description="Chunk index in note",
                    skip_vectorization=True,
                ),
                Property(
                    name="note_type",
                    data_type=DataType.TEXT,
                    description="Note type (text, code)",
                    skip_vectorization=True,
                ),
                Property(
                    name="date_modified",
                    data_type=DataType.TEXT,
                    description="Last modification date",
                    skip_vectorization=True,
                ),
                Property(
                    name="path",
                    data_type=DataType.TEXT,
                    description="Note path (title hierarchy)",
                    skip_vectorization=True,
                ),
                Property(
                    name="note_id_path",
                    data_type=DataType.TEXT,
                    description="Note ID path for URL building",
                    skip_vectorization=True,
                ),
            ],
        )

        print(f"Created collection '{self.collection_name}' with {embedding_dimension}D vectors")

    def delete_collection(self) -> None:
        """Delete the collection."""
        if self._client is None:
            self.connect()

        if self._client.collections.exists(self.collection_name):
            self._client.collections.delete(self.collection_name)
            print(f"Deleted collection '{self.collection_name}'")
        else:
            print(f"Collection '{self.collection_name}' does not exist")

    def insert_chunks(
        self, chunks: list[Chunk], embeddings: list[list[float]], batch_size: int = 100
    ) -> int:
        """Insert chunks with embeddings into Weaviate.

        Args:
            chunks: List of chunks to insert
            embeddings: List of embedding vectors (same order as chunks)
            batch_size: Batch size for insertion

        Returns:
            Number of chunks inserted
        """
        if self._client is None:
            self.connect()

        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        collection = self._client.collections.get(self.collection_name)

        inserted_count = 0
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            with collection.batch.dynamic() as batch:
                for chunk, embedding in zip(batch_chunks, batch_embeddings):
                    properties = {
                        "chunk_id": chunk.chunk_id,
                        "note_id": chunk.note_id,
                        "title": chunk.title,
                        "content": chunk.content,
                        "retrieval_text": chunk.metadata.get("retrieval_text", chunk.content),
                        "chunk_index": chunk.chunk_index,
                        "note_type": chunk.metadata.get("note_type", "text"),
                        "date_modified": chunk.metadata.get("date_modified", ""),
                        "path": chunk.metadata.get("path", ""),
                        "note_id_path": chunk.metadata.get("id_path", ""),
                    }

                    batch.add_object(properties=properties, vector=embedding)
                    inserted_count += 1

            print(f"Inserted batch {i // batch_size + 1}: {len(batch_chunks)} chunks")

        return inserted_count

    def delete_by_note_id(self, note_id: str) -> int:
        """Delete all chunks for a specific note.

        Args:
            note_id: Note ID to delete chunks for

        Returns:
            Number of chunks deleted
        """
        if self._client is None:
            self.connect()

        collection = self._client.collections.get(self.collection_name)

        # Delete all objects with matching note_id
        result = collection.data.delete_many(where=Filter.by_property("note_id").equal(note_id))

        deleted_count = result.successful if hasattr(result, "successful") else 0
        print(f"Deleted {deleted_count} chunks for note {note_id}")
        return deleted_count

    def get_total_chunks(self) -> int:
        """Get total number of chunks in collection.

        Returns:
            Total chunk count
        """
        if self._client is None:
            self.connect()

        collection = self._client.collections.get(self.collection_name)
        result = collection.aggregate.over_all(total_count=True)

        return result.total_count

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last sync timestamp from local state file.

        Returns:
            Last sync time or None if never synced
        """
        try:
            state = self._read_sync_state()
            last_sync_str = state.get("last_sync_time")
            if last_sync_str:
                return datetime.fromisoformat(last_sync_str)
        except ValueError:
            return None

        return None

    def set_last_sync_time(self, sync_time: datetime) -> None:
        """Set the last sync timestamp in local state file.

        Args:
            sync_time: Timestamp to store
        """
        state = self._read_sync_state()
        state["last_sync_time"] = sync_time.isoformat()
        self._write_sync_state(state)

    def record_sync_result(
        self,
        *,
        sync_time: datetime,
        notes_synced: int,
        chunks_created: int,
        chunks_indexed: int,
        last_note_updated_at: Optional[datetime],
    ) -> None:
        """Persist summary data for a sync run."""
        state = self._read_sync_state()

        history = state.get("sync_history", [])
        if not isinstance(history, list):
            history = []

        history.append(
            {
                "sync_time": sync_time.isoformat(),
                "notes_synced": notes_synced,
                "chunks_created": chunks_created,
                "chunks_indexed": chunks_indexed,
                "last_note_updated_at": (
                    last_note_updated_at.isoformat() if last_note_updated_at else None
                ),
            }
        )

        state["last_sync_time"] = sync_time.isoformat()
        state["last_sync_notes_synced"] = notes_synced
        state["last_sync_chunks_created"] = chunks_created
        state["last_sync_chunks_indexed"] = chunks_indexed
        state["last_note_updated_at"] = (
            last_note_updated_at.isoformat() if last_note_updated_at else state.get("last_note_updated_at")
        )
        state["sync_history"] = history[-100:]

        self._write_sync_state(state)

    def get_sync_state(self) -> dict[str, Any]:
        """Return the raw sync state data."""
        return self._read_sync_state()

    def search_similar(
        self, query_vector: list[float], limit: int = 5, min_score: float = 0.7
    ) -> list[tuple[Chunk, float]]:
        """Search for similar chunks using vector similarity.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score

        Returns:
            List of (chunk, score) tuples
        """
        if self._client is None:
            self.connect()

        collection = self._client.collections.get(self.collection_name)

        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=limit,
            return_metadata=MetadataQuery(distance=True),
        )

        results = []
        for obj in response.objects:
            # Convert distance to similarity score (closer to 1 is more similar)
            score = 1.0 - obj.metadata.distance

            if score >= min_score:
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
                        "retrieval_text": obj.properties.get(
                            "retrieval_text", obj.properties.get("content", "")
                        ),
                    },
                )
                results.append((chunk, score))

        return results


_client: Optional[WeaviateClient] = None


def get_weaviate_client(
    url: str = "http://localhost:8601",
    api_key: Optional[str] = None,
    collection_name: str = "TriliumNotes",
) -> WeaviateClient:
    """Get or create the singleton Weaviate client.

    Args:
        url: Weaviate URL
        api_key: Optional API key
        collection_name: Collection name

    Returns:
        WeaviateClient instance
    """
    global _client
    if _client is None:
        _client = WeaviateClient(url=url, api_key=api_key, collection_name=collection_name)
    return _client
