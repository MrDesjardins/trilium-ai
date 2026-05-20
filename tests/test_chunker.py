from datetime import datetime

from trilium_ai.indexer.chunker import TextChunker
from trilium_ai.shared.models import Note


def test_chunker_adds_enriched_retrieval_text_without_polluting_chunk_content() -> None:
    chunker = TextChunker(max_chunk_size=128, chunk_overlap=16)
    note = Note(
        note_id="note-1",
        title="Search Techniques",
        type="text",
        content="Hybrid retrieval combines semantic and keyword search.",
        utc_date_modified=datetime.fromisoformat("2026-03-19T10:00:00"),
        path="Knowledge > Search",
        id_path="root/search",
    )

    chunks = list(chunker.chunk_note(note))

    assert len(chunks) == 1
    assert chunks[0].content == "Hybrid retrieval combines semantic and keyword search."
    assert (
        chunks[0].metadata["retrieval_text"]
        == "Title: Search Techniques Path: Knowledge > Search Note Type: text Content: Hybrid retrieval combines semantic and keyword search."
    )
