"""API routes for Trilium AI web interface."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from trilium_ai.gateway.llm_client import LLMClient
from trilium_ai.gateway.retriever import Retriever
from trilium_ai.indexer.embedder import Embedder
from trilium_ai.shared.config import get_config
from trilium_ai.shared.weaviate_client import get_weaviate_client

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Query request model."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of results to retrieve")
    provider: Optional[str] = Field(None, description="LLM provider (openai, anthropic, gemini)")
    model: Optional[str] = Field(None, description="LLM model name")


class QueryResponse(BaseModel):
    """Query response model."""

    answer: str = Field(..., description="Generated answer")
    sources: list[dict[str, str]] = Field(..., description="Source notes")
    chunks_found: int = Field(..., description="Number of relevant chunks found")


class StatusResponse(BaseModel):
    """Status response model."""

    weaviate_connected: bool
    total_chunks: int
    config_valid: bool


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Query Trilium notes using natural language.

    Args:
        request: Query request with search parameters

    Returns:
        Query response with answer and sources
    """
    try:
        # Load configuration
        config = get_config()

        # Create Weaviate client
        weaviate_client = get_weaviate_client(
            url=config.weaviate.url,
            api_key=config.weaviate.api_key,
            collection_name=config.weaviate.collection_name,
        )
        weaviate_client.connect()

        # Create embedder
        embedder = Embedder(
            provider=config.embeddings.provider,
            model=config.embeddings.model,
            dimension=config.embeddings.dimension,
        )

        # Create retriever
        retriever = Retriever(
            weaviate_client=weaviate_client,
            embedder=embedder,
            top_k=request.top_k or config.retrieval.top_k,
            min_score=config.retrieval.min_score,
            search_mode=config.retrieval.mode,
            alpha=config.retrieval.alpha,
            use_reranking=config.retrieval.use_reranking,
            reranking_model=config.retrieval.reranking_model,
        )

        # Retrieve relevant chunks
        results = retriever.search(request.query, top_k=request.top_k)

        if results.total_results == 0:
            return QueryResponse(
                answer="No relevant notes found for your query.",
                sources=[],
                chunks_found=0,
            )

        # Create LLM client
        llm_provider = request.provider or config.llm.provider
        llm_model = request.model or config.llm.model

        llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
        )

        # Generate response
        answer = llm_client.generate(
            query=request.query,
            context_chunks=results.chunks,
        )

        # Build sources list with note links
        seen_notes = set()
        sources = []
        server_url = config.trilium.server_url if hasattr(config.trilium, "server_url") else ""

        for chunk in results.chunks:
            if chunk.note_id not in seen_notes:
                seen_notes.add(chunk.note_id)

                # Build note URL
                note_url = ""
                id_path = chunk.metadata.get("note_id_path", "")
                if id_path and server_url:
                    note_url = f"{server_url}#{id_path}/{chunk.note_id}"

                source = {
                    "title": chunk.title,
                    "note_id": chunk.note_id,
                }

                if note_url:
                    source["url"] = note_url

                location = chunk.metadata.get("path", "")
                if location:
                    source["path"] = location

                sources.append(source)

        return QueryResponse(
            answer=answer,
            sources=sources,
            chunks_found=results.total_results,
        )

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if weaviate_client:
            weaviate_client.disconnect()


@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """
    Check the status of Trilium AI.

    Returns:
        Status information
    """
    try:
        config = get_config()

        # Check Weaviate connection
        weaviate_connected = False
        total_chunks = 0

        try:
            weaviate_client = get_weaviate_client(
                url=config.weaviate.url,
                api_key=config.weaviate.api_key,
                collection_name=config.weaviate.collection_name,
            )
            weaviate_client.connect()
            total_chunks = weaviate_client.get_total_chunks()
            weaviate_connected = True
            weaviate_client.disconnect()
        except Exception as e:
            logger.warning(f"Weaviate connection failed: {e}")

        return StatusResponse(
            weaviate_connected=weaviate_connected,
            total_chunks=total_chunks,
            config_valid=True,
        )

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return StatusResponse(
            weaviate_connected=False,
            total_chunks=0,
            config_valid=False,
        )
