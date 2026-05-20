"""SQLite reader for Trilium database."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator

from trilium_ai.shared.models import Note


class TriliumSQLiteReader:
    """Reads notes from Trilium SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the SQLite reader.

        Args:
            db_path: Path to Trilium SQLite database
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

    def _get_note_paths(self, conn: sqlite3.Connection) -> tuple[dict[str, str], dict[str, str]]:
        """Build mappings of note IDs to their title paths and ID paths.

        Args:
            conn: SQLite connection

        Returns:
            Tuple of (title_paths, id_paths) dictionaries
            - title_paths: noteId -> "Parent Title > Child Title"
            - id_paths: noteId -> "parentId/childId" (for URL building)
        """
        # Get all branches for path building
        cursor = conn.cursor()

        # Get parent relationships
        branches = cursor.execute("""
            SELECT noteId, parentNoteId
            FROM branches
            WHERE isDeleted = 0
        """).fetchall()

        # Get note titles
        titles = dict(cursor.execute("""
            SELECT noteId, title
            FROM notes
            WHERE isDeleted = 0
        """).fetchall())

        # Build parent map
        parent_map = {}
        for note_id, parent_id in branches:
            if note_id not in parent_map:  # Take first parent if multiple
                parent_map[note_id] = parent_id

        # Build title paths recursively
        def get_title_path(note_id: str, seen: set) -> str:
            if note_id in seen or note_id == 'root' or note_id not in parent_map:
                return ""

            seen.add(note_id)
            parent_id = parent_map[note_id]
            parent_path = get_title_path(parent_id, seen)
            parent_title = str(titles.get(parent_id, ""))

            if parent_path and parent_title:
                return f"{parent_path} > {parent_title}"
            elif parent_title:
                return parent_title
            return ""

        # Build ID paths recursively (for URLs)
        def get_id_path(note_id: str, seen: set) -> str:
            if note_id in seen or note_id not in parent_map:
                return ""

            seen.add(note_id)
            parent_id = str(parent_map[note_id])

            if parent_id == 'root':
                return "root"

            parent_path = get_id_path(parent_id, seen)

            if parent_path:
                return f"{parent_path}/{parent_id}"
            return parent_id

        title_paths = {}
        id_paths = {}
        for note_id in titles:
            title_paths[note_id] = get_title_path(note_id, set())
            id_paths[note_id] = get_id_path(note_id, set())

        return title_paths, id_paths

    def read_all_notes(self) -> Iterator[Note]:
        """Read all non-deleted, non-private text notes with their paths.

        Yields:
            Note objects with content, metadata, and path
        """
        query = """
            SELECT
                n.noteId,
                n.title,
                n.type,
                b.content,
                n.utcDateModified
            FROM notes n
            LEFT JOIN blobs b ON n.blobId = b.blobId
            WHERE n.isDeleted = 0
                AND n.type IN ('text', 'code')
                AND NOT EXISTS (
                    SELECT 1 FROM attributes a
                    WHERE a.noteId = n.noteId
                        AND a.isDeleted = 0
                        AND a.type = 'label'
                        AND a.name = 'private'
                        AND a.value = 'true'
                )
            ORDER BY n.utcDateModified DESC
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Build note paths (both title paths and ID paths)
            title_paths, id_paths = self._get_note_paths(conn)

            cursor = conn.cursor()
            for row in cursor.execute(query):
                content = row["content"] or ""
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="ignore")

                # Skip notes with no content
                if not content.strip():
                    continue

                note_id = row["noteId"]
                path = title_paths.get(note_id, "")
                id_path = id_paths.get(note_id, "")

                yield Note(
                    note_id=note_id,
                    title=row["title"] or "Untitled",
                    type=row["type"],
                    content=content,
                    utc_date_modified=datetime.fromisoformat(row["utcDateModified"]),
                    path=path,
                    id_path=id_path,
                )

    def read_notes_since(self, last_sync: datetime) -> Iterator[Note]:
        """Read non-private notes modified since last sync.

        Args:
            last_sync: Timestamp of last sync

        Yields:
            Note objects modified after last_sync
        """
        query = """
            SELECT
                n.noteId,
                n.title,
                n.type,
                b.content,
                n.utcDateModified
            FROM notes n
            LEFT JOIN blobs b ON n.blobId = b.blobId
            WHERE n.isDeleted = 0
                AND n.type IN ('text', 'code')
                AND julianday(n.utcDateModified) > julianday(?)
                AND NOT EXISTS (
                    SELECT 1 FROM attributes a
                    WHERE a.noteId = n.noteId
                        AND a.isDeleted = 0
                        AND a.type = 'label'
                        AND a.name = 'private'
                        AND a.value = 'true'
                )
            ORDER BY n.utcDateModified DESC
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Build note paths (both title paths and ID paths)
            title_paths, id_paths = self._get_note_paths(conn)

            cursor = conn.cursor()
            for row in cursor.execute(query, (last_sync.isoformat(),)):
                content = row["content"] or ""
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="ignore")

                note_id = row["noteId"]
                path = title_paths.get(note_id, "")
                id_path = id_paths.get(note_id, "")

                yield Note(
                    note_id=note_id,
                    title=row["title"] or "Untitled",
                    type=row["type"],
                    content=content,
                    utc_date_modified=datetime.fromisoformat(row["utcDateModified"]),
                    path=path,
                    id_path=id_path,
                )

    def get_note_count(self) -> int:
        """Get total count of indexable notes (excluding private).

        Returns:
            Number of non-deleted, non-private text/code notes
        """
        query = """
            SELECT COUNT(*) as count
            FROM notes n
            LEFT JOIN blobs b ON n.blobId = b.blobId
            WHERE n.isDeleted = 0
                AND n.type IN ('text', 'code')
                AND b.content IS NOT NULL
                AND b.content != ''
                AND NOT EXISTS (
                    SELECT 1 FROM attributes a
                    WHERE a.noteId = n.noteId
                        AND a.isDeleted = 0
                        AND a.type = 'label'
                        AND a.name = 'private'
                        AND a.value = 'true'
                )
        """

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            result = cursor.execute(query).fetchone()
            return result[0] if result else 0
