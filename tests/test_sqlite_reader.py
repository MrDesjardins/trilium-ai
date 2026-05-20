import sqlite3
from datetime import datetime
from pathlib import Path

from trilium_ai.indexer.sqlite_reader import TriliumSQLiteReader


def _setup_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE notes (
            noteId TEXT PRIMARY KEY,
            title TEXT,
            type TEXT,
            blobId TEXT,
            isDeleted INTEGER,
            utcDateModified TEXT
        );

        CREATE TABLE blobs (
            blobId TEXT PRIMARY KEY,
            content TEXT
        );

        CREATE TABLE branches (
            branchId TEXT PRIMARY KEY,
            noteId TEXT,
            parentNoteId TEXT,
            isDeleted INTEGER
        );

        CREATE TABLE attributes (
            attributeId TEXT PRIMARY KEY,
            noteId TEXT,
            type TEXT,
            name TEXT,
            value TEXT,
            isDeleted INTEGER
        );
        """
    )

    conn.execute(
        "INSERT INTO blobs (blobId, content) VALUES (?, ?)",
        ("blob-1", "exact phrase from a recent note"),
    )
    conn.execute(
        """
        INSERT INTO notes (noteId, title, type, blobId, isDeleted, utcDateModified)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("note-1", "Recent note", "text", "blob-1", 0, "2026-05-20 04:17:04.614Z"),
    )
    conn.execute(
        """
        INSERT INTO branches (branchId, noteId, parentNoteId, isDeleted)
        VALUES (?, ?, ?, ?)
        """,
        ("branch-1", "note-1", "root", 0),
    )
    conn.commit()
    conn.close()


def test_read_notes_since_handles_iso_last_sync_format(tmp_path: Path) -> None:
    db_path = tmp_path / "document.db"
    _setup_db(db_path)

    reader = TriliumSQLiteReader(db_path)
    notes = list(reader.read_notes_since(datetime.fromisoformat("2026-05-20T04:16:31.993162+00:00")))

    assert len(notes) == 1
    assert notes[0].title == "Recent note"
