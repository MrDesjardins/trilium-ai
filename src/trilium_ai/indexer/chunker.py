"""Text chunker for splitting notes into manageable chunks."""

import re
from typing import Iterator

from trilium_ai.shared.models import Chunk, Note


def _normalize_search_text(text: str) -> str:
    """Normalize text for retrieval-friendly indexing."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_retrieval_text(
    title: str,
    path: str,
    note_type: str,
    body: str,
) -> str:
    """Build enriched retrieval text for embedding and keyword search."""
    sections = [f"Title: {title}"]
    if path:
        sections.append(f"Path: {path}")
    if note_type:
        sections.append(f"Note Type: {note_type}")
    sections.append(f"Content: {body}")
    return _normalize_search_text("\n".join(sections))


class TextChunker:
    """Chunks text into smaller pieces for embedding."""

    def __init__(self, max_chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        """Initialize the chunker.

        Args:
            max_chunk_size: Maximum chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences using simple regex.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Remove HTML tags for better sentence splitting
        text = re.sub(r'<[^>]+>', ' ', text)

        # Split on sentence boundaries (., !, ?, followed by space and capital letter or end)
        # This is a simple implementation - could be improved with NLTK if needed
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$'
        sentences = re.split(sentence_pattern, text)

        # Filter out empty sentences and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses a simple heuristic: ~4 characters per token on average.
        This is close enough for chunking purposes.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def chunk_note(self, note: Note) -> Iterator[Chunk]:
        """Chunk a note into smaller pieces using sentence-based chunking.

        Args:
            note: Note to chunk

        Yields:
            Chunk objects
        """
        content = note.content
        if not content or not content.strip():
            return

        # Reserve space for enriched retrieval text that includes note metadata.
        metadata_prefix = build_retrieval_text(note.title, note.path, note.type, "")
        available_tokens = self.max_chunk_size - self._estimate_tokens(metadata_prefix)
        available_tokens = max(available_tokens, 1)

        # Split content into sentences
        sentences = self._split_into_sentences(content)

        # If content is very short or no sentences detected, use as single chunk
        if not sentences or self._estimate_tokens(content) <= available_tokens:
            chunk_content = content.strip()
            yield Chunk(
                chunk_id=f"{note.note_id}_0",
                note_id=note.note_id,
                title=note.title,
                content=chunk_content,
                chunk_index=0,
                metadata={
                    "note_type": note.type,
                    "date_modified": note.utc_date_modified.isoformat(),
                    "path": note.path,
                    "id_path": note.id_path,
                    "retrieval_text": build_retrieval_text(
                        note.title, note.path, note.type, chunk_content
                    ),
                },
            )
            return

        # Chunk by combining sentences up to max_chunk_size
        chunks: list[tuple[int, str]] = []
        chunk_index = 0
        current_chunk: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)

            # If single sentence exceeds max size, split it by characters
            if sentence_tokens > available_tokens:
                # First, yield current chunk if not empty
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunk_content = chunk_text.strip()
                    chunks.append((chunk_index, chunk_content))
                    chunk_index += 1
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence into character chunks
                max_chars = available_tokens * 4
                for j in range(0, len(sentence), max_chars):
                    sub_chunk = sentence[j:j + max_chars].strip()
                    chunks.append((chunk_index, sub_chunk))
                    chunk_index += 1
                continue

            # Check if adding this sentence would exceed limit
            if current_tokens + sentence_tokens > available_tokens and current_chunk:
                # Yield current chunk
                chunk_text = " ".join(current_chunk)
                chunk_content = chunk_text.strip()
                chunks.append((chunk_index, chunk_content))
                chunk_index += 1

                # Start new chunk with overlap
                # Include last few sentences for context continuity
                overlap_sentences: list[str] = []
                overlap_tokens = 0
                for prev_sentence in reversed(current_chunk):
                    sent_tokens = self._estimate_tokens(prev_sentence)
                    if overlap_tokens + sent_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, prev_sentence)
                        overlap_tokens += sent_tokens
                    else:
                        break

                current_chunk = overlap_sentences
                current_tokens = overlap_tokens

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_content = chunk_text.strip()
            chunks.append((chunk_index, chunk_content))

        # Yield all chunks
        for idx, content in chunks:
            yield Chunk(
                chunk_id=f"{note.note_id}_{idx}",
                note_id=note.note_id,
                title=note.title,
                content=content,
                chunk_index=idx,
                metadata={
                    "note_type": note.type,
                    "date_modified": note.utc_date_modified.isoformat(),
                    "path": note.path,
                    "id_path": note.id_path,
                    "retrieval_text": build_retrieval_text(
                        note.title, note.path, note.type, content
                    ),
                },
            )
