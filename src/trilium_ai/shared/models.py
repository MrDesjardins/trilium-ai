"""Pydantic models for data validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Note(BaseModel):
    """Trilium note model."""

    note_id: str = Field(..., description="Unique note identifier")
    title: str = Field(..., description="Note title")
    type: str = Field(..., description="Note type (text, code, etc.)")
    content: str = Field(..., description="Note content")
    utc_date_modified: datetime = Field(..., description="Last modification timestamp")
    path: str = Field(default="", description="Note path/breadcrumb (e.g., 'Parent > Child')")
    id_path: str = Field(default="", description="Note ID path for URL building (e.g., 'root/parentId/noteId')")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Chunk(BaseModel):
    """Text chunk model."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    note_id: str = Field(..., description="Parent note ID")
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="Chunk index in note")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class SearchResult(BaseModel):
    """Search result model."""

    chunks: list[Chunk] = Field(..., description="Retrieved chunks")
    scores: list[float] = Field(..., description="Similarity scores")
    total_results: int = Field(..., description="Total number of results")


class QueryResponse(BaseModel):
    """LLM query response model."""

    answer: str = Field(..., description="Generated answer")
    sources: list[dict[str, str]] = Field(..., description="Source citations")
    chunks_used: int = Field(..., description="Number of chunks used")
