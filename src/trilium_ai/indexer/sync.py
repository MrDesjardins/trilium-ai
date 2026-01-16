"""Sync orchestrator for indexing Trilium notes into Weaviate."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from trilium_ai.indexer.chunker import TextChunker
from trilium_ai.indexer.embedder import Embedder
from trilium_ai.indexer.sqlite_reader import TriliumSQLiteReader
from trilium_ai.shared.models import Chunk
from trilium_ai.shared.weaviate_client import WeaviateClient


class TriliumIndexer:
    """Orchestrates the indexing pipeline from Trilium to Weaviate."""

    def __init__(
        self,
        db_path: str | Path,
        weaviate_client: WeaviateClient,
        embedder: Embedder,
        chunker: TextChunker,
        batch_size: int = 100,
    ) -> None:
        """Initialize the indexer.

        Args:
            db_path: Path to Trilium SQLite database
            weaviate_client: Weaviate client instance
            embedder: Embedder instance
            chunker: Text chunker instance
            batch_size: Batch size for processing
        """
        self.db_path = db_path
        self.weaviate_client = weaviate_client
        self.embedder = embedder
        self.chunker = chunker
        self.batch_size = batch_size
        self.reader = TriliumSQLiteReader(db_path)

    def index_full(self) -> dict[str, int]:
        """Perform full indexing of all notes.

        Returns:
            Statistics dictionary with counts
        """
        print("Starting full index...")
        print(f"Database: {self.db_path}")

        # Connect to Weaviate and ensure collection exists
        self.weaviate_client.connect()
        self.weaviate_client.create_collection(embedding_dimension=self.embedder.dimension)

        # Read all notes
        print("\nReading notes from Trilium database...")
        notes = list(self.reader.read_all_notes())
        print(f"Found {len(notes)} notes to index")

        if not notes:
            print("No notes to index")
            return {"notes_read": 0, "chunks_created": 0, "chunks_indexed": 0}

        # Process in batches
        total_chunks_created = 0
        total_chunks_indexed = 0
        all_chunks: list[Chunk] = []
        all_texts: list[str] = []

        for i, note in enumerate(notes, 1):
            if i % 100 == 0:
                print(f"Processing note {i}/{len(notes)}...")

            # Chunk the note
            chunks = list(self.chunker.chunk_note(note))
            total_chunks_created += len(chunks)

            # Collect chunks and texts for batch embedding
            for chunk in chunks:
                all_chunks.append(chunk)
                all_texts.append(chunk.content)

            # Process batch when we reach batch size
            if len(all_chunks) >= self.batch_size:
                indexed = self._index_batch(all_chunks, all_texts)
                total_chunks_indexed += indexed
                all_chunks = []
                all_texts = []

        # Process remaining chunks
        if all_chunks:
            indexed = self._index_batch(all_chunks, all_texts)
            total_chunks_indexed += indexed

        print(f"\nIndexing complete!")
        print(f"Notes processed: {len(notes)}")
        print(f"Chunks created: {total_chunks_created}")
        print(f"Chunks indexed: {total_chunks_indexed}")

        # Update last sync time
        self.weaviate_client.set_last_sync_time(datetime.now(timezone.utc))

        return {
            "notes_read": len(notes),
            "chunks_created": total_chunks_created,
            "chunks_indexed": total_chunks_indexed,
        }

    def index_incremental(self, last_sync: Optional[datetime] = None) -> dict[str, int]:
        """Perform incremental indexing of changed notes.

        Args:
            last_sync: Timestamp of last sync (if None, uses stored value)

        Returns:
            Statistics dictionary with counts
        """
        print("Starting incremental sync...")

        # Connect to Weaviate
        self.weaviate_client.connect()

        # Get last sync time
        if last_sync is None:
            last_sync = self.weaviate_client.get_last_sync_time()

        if last_sync is None:
            print("No previous sync found, performing full index instead")
            return self.index_full()

        print(f"Syncing notes modified since {last_sync}")

        # Read modified notes
        notes = list(self.reader.read_notes_since(last_sync))
        print(f"Found {len(notes)} modified notes")

        if not notes:
            print("No notes to sync")
            # Update sync time even if no changes, so next sync doesn't re-check same window
            self.weaviate_client.set_last_sync_time(datetime.now(timezone.utc))
            return {"notes_read": 0, "chunks_created": 0, "chunks_indexed": 0}

        total_chunks_created = 0
        total_chunks_indexed = 0

        for note in notes:
            # Delete existing chunks for this note
            self.weaviate_client.delete_by_note_id(note.note_id)

            # Chunk the note
            chunks = list(self.chunker.chunk_note(note))
            total_chunks_created += len(chunks)

            if chunks:
                # Generate embeddings
                texts = [chunk.content for chunk in chunks]
                embeddings = self.embedder.embed_batch(texts, batch_size=self.batch_size)

                # Insert into Weaviate
                inserted = self.weaviate_client.insert_chunks(
                    chunks, embeddings, batch_size=self.batch_size
                )
                total_chunks_indexed += inserted

        print(f"\nIncremental sync complete!")
        print(f"Notes synced: {len(notes)}")
        print(f"Chunks created: {total_chunks_created}")
        print(f"Chunks indexed: {total_chunks_indexed}")

        # Update last sync time
        self.weaviate_client.set_last_sync_time(datetime.now(timezone.utc))

        return {
            "notes_read": len(notes),
            "chunks_created": total_chunks_created,
            "chunks_indexed": total_chunks_indexed,
        }

    def _index_batch(self, chunks: list[Chunk], texts: list[str]) -> int:
        """Index a batch of chunks.

        Args:
            chunks: List of chunks to index
            texts: List of text contents (same order as chunks)

        Returns:
            Number of chunks indexed
        """
        if not chunks:
            return 0

        # Generate embeddings
        print(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = self.embedder.embed_batch(texts, batch_size=self.batch_size)

        # Insert into Weaviate
        inserted = self.weaviate_client.insert_chunks(chunks, embeddings, batch_size=self.batch_size)

        return inserted

    def get_stats(self) -> dict[str, int]:
        """Get indexing statistics.

        Returns:
            Statistics dictionary
        """
        self.weaviate_client.connect()
        total_chunks = self.weaviate_client.get_total_chunks()

        return {
            "total_chunks": total_chunks,
        }
