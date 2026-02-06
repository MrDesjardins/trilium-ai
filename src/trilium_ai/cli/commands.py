"""CLI commands for Trilium AI."""

import os
import sys
import time
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from trilium_ai.indexer.chunker import TextChunker
from trilium_ai.indexer.embedder import Embedder
from trilium_ai.indexer.sync import TriliumIndexer
from trilium_ai.shared.weaviate_client import WeaviateClient


def load_config() -> dict:
    """Load configuration from YAML file or environment.

    Returns:
        Configuration dictionary
    """
    config_path = os.getenv("TRILIUM_AI_CONFIG", "config/config.yaml")

    if not Path(config_path).exists():
        click.echo(f"Warning: Config file not found at {config_path}", err=True)
        click.echo("Using default configuration", err=True)
        return {
            "trilium": {"database_path": "data/document.db", "sync_interval": 300},
            "weaviate": {
                "url": "http://localhost:8601",
                "api_key": None,
                "collection_name": "TriliumNotes",
                "batch_size": 100,
            },
            "embeddings": {
                "provider": "sentence-transformers",
                "model": "all-MiniLM-L6-v2",
                "dimension": 384,
            },
            "chunking": {"max_chunk_size": 512, "chunk_overlap": 50, "strategy": "sentence"},
        }

    with open(config_path) as f:
        return yaml.safe_load(f)


def create_indexer(config: dict) -> TriliumIndexer:
    """Create indexer from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        TriliumIndexer instance
    """
    # Create Weaviate client
    weaviate_client = WeaviateClient(
        url=config["weaviate"]["url"],
        api_key=config["weaviate"].get("api_key"),
        collection_name=config["weaviate"]["collection_name"],
    )

    # Create embedder
    embedder = Embedder(
        provider=config["embeddings"]["provider"],
        model=config["embeddings"]["model"],
        dimension=config["embeddings"]["dimension"],
    )

    # Create chunker
    chunker = TextChunker(
        max_chunk_size=config["chunking"]["max_chunk_size"],
        chunk_overlap=config["chunking"]["chunk_overlap"],
    )

    # Create indexer
    indexer = TriliumIndexer(
        db_path=config["trilium"]["database_path"],
        weaviate_client=weaviate_client,
        embedder=embedder,
        chunker=chunker,
        batch_size=config["weaviate"]["batch_size"],
    )

    return indexer


@click.group()
@click.version_option()
def cli() -> None:
    """Trilium AI - RAG system for Trilium Notes."""
    pass


@cli.command()
@click.option("--full", is_flag=True, help="Perform full reindex")
@click.option("--incremental", is_flag=True, help="Perform incremental sync")
@click.option("--watch", is_flag=True, help="Watch mode for continuous sync")
def index(full: bool, incremental: bool, watch: bool) -> None:
    """Index Trilium notes into Weaviate."""
    indexer = None
    try:
        config = load_config()
        indexer = create_indexer(config)

        if full:
            click.echo("Starting full index...")
            stats = indexer.index_full()
            click.echo("\nIndexing complete!")
            click.echo(f"Notes processed: {stats['notes_read']}")
            click.echo(f"Chunks created: {stats['chunks_created']}")
            click.echo(f"Chunks indexed: {stats['chunks_indexed']}")

        elif incremental:
            click.echo("Starting incremental sync...")
            stats = indexer.index_incremental()
            click.echo("\nSync complete!")
            click.echo(f"Notes synced: {stats['notes_read']}")
            click.echo(f"Chunks created: {stats['chunks_created']}")
            click.echo(f"Chunks indexed: {stats['chunks_indexed']}")

        elif watch:
            click.echo("Starting watch mode...")
            click.echo(f"Sync interval: {config['trilium']['sync_interval']} seconds")
            click.echo("Press Ctrl+C to stop\n")

            try:
                while True:
                    click.echo(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running incremental sync...")
                    stats = indexer.index_incremental()
                    if stats["notes_read"] > 0:
                        click.echo(f"Synced {stats['notes_read']} notes, {stats['chunks_indexed']} chunks")
                    else:
                        click.echo("No changes detected")

                    time.sleep(config["trilium"]["sync_interval"])

            except KeyboardInterrupt:
                click.echo("\nStopping watch mode...")

        else:
            click.echo("Please specify --full, --incremental, or --watch")
            click.echo("Run 'trilium-ai index --help' for more information")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        if indexer:
            indexer.weaviate_client.disconnect()


@cli.command()
@click.argument("query_text")
@click.option("--top-k", default=5, help="Number of results to retrieve")
@click.option("--model", help="LLM model to use (overrides config)")
@click.option("--provider", help="LLM provider (openai, anthropic, gemini)")
@click.option("--search-only", is_flag=True, help="Only show search results, no LLM")
@click.option("--verbose", "-v", is_flag=True, help="Show retrieved context")
@click.option("--debug", is_flag=True, help="Enable debug logging for diagnostics")
@click.option("--min-score", type=float, help="Override minimum score threshold")
def query(
    query_text: str,
    top_k: int,
    model: str | None,
    provider: str | None,
    search_only: bool,
    verbose: bool,
    debug: bool,
    min_score: float | None,
) -> None:
    """Query your Trilium notes using natural language."""
    import logging

    from trilium_ai.gateway.llm_client import LLMClient
    from trilium_ai.gateway.retriever import Retriever

    # Set up logging for debug mode
    if debug:
        logging.basicConfig(
            level=logging.INFO,
            format="[DEBUG] %(message)s",
        )

    weaviate_client = None
    try:
        config = load_config()

        # Create Weaviate client
        weaviate_client = WeaviateClient(
            url=config["weaviate"]["url"],
            api_key=config["weaviate"].get("api_key"),
            collection_name=config["weaviate"]["collection_name"],
        )

        # Create embedder
        embedder = Embedder(
            provider=config["embeddings"]["provider"],
            model=config["embeddings"]["model"],
            dimension=config["embeddings"]["dimension"],
        )

        # Get retrieval config with defaults
        retrieval_config = config.get("retrieval", {})

        # Allow min_score override from CLI
        effective_min_score = min_score if min_score is not None else retrieval_config.get("min_score", 0.5)

        if debug:
            click.echo(f"[DEBUG] Config retrieval settings:")
            click.echo(f"[DEBUG]   mode: {retrieval_config.get('mode', 'hybrid')}")
            click.echo(f"[DEBUG]   min_score: {effective_min_score}")
            click.echo(f"[DEBUG]   alpha: {retrieval_config.get('alpha', 0.75)}")
            click.echo(f"[DEBUG]   top_k: {top_k}")
            click.echo("")

        # Create retriever
        retriever = Retriever(
            weaviate_client=weaviate_client,
            embedder=embedder,
            top_k=top_k,
            min_score=effective_min_score,
            search_mode=retrieval_config.get("mode", "hybrid"),
            alpha=retrieval_config.get("alpha", 0.75),
            use_reranking=retrieval_config.get("use_reranking", False),
            reranking_model=retrieval_config.get(
                "reranking_model", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            ),
        )

        click.echo(f"Searching for: {query_text}\n")

        # Retrieve relevant chunks
        results = retriever.search(query_text, top_k=top_k, debug=debug)

        if results.total_results == 0:
            click.echo("No relevant notes found for your query.")
            return

        click.echo(f"Found {results.total_results} relevant chunks from your notes.\n")

        # Show retrieved context if verbose or search-only mode
        if verbose or search_only:
            click.echo("=" * 60)
            click.echo("Retrieved Context:")
            click.echo("=" * 60)
            for i, (chunk, score) in enumerate(zip(results.chunks, results.scores), 1):
                # Build note URL if we have the id_path
                note_url = ""
                id_path = chunk.metadata.get("note_id_path", "")
                if id_path:
                    server_url = config["trilium"].get("server_url", "http://localhost:8080")
                    note_url = f"{server_url}#{id_path}/{chunk.note_id}"

                # Show location path
                location = chunk.metadata.get("path", "")
                if location:
                    click.echo(f"\n[{i}] {chunk.title} (score: {score:.3f})")
                    click.echo(f"Location: {location}")
                else:
                    click.echo(f"\n[{i}] {chunk.title} (score: {score:.3f})")

                if note_url:
                    click.echo(f"Link: {note_url}")

                click.echo("-" * 40)
                # Truncate long content for display
                content = chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content
                click.echo(content)
            click.echo("\n" + "=" * 60)

        if search_only:
            return

        # Get LLM config
        llm_config = config.get("llm", {})
        llm_provider = provider or llm_config.get("provider", "openai")
        llm_model = model or llm_config.get("model", "gpt-4-turbo")

        click.echo(f"\nGenerating response using {llm_provider}/{llm_model}...\n")

        # Create LLM client
        llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            max_tokens=llm_config.get("max_tokens", 2000),
            temperature=llm_config.get("temperature", 0.7),
        )

        # Generate response
        response = llm_client.generate(
            query=query_text,
            context_chunks=results.chunks,
        )

        click.echo("=" * 60)
        click.echo("Answer:")
        click.echo("=" * 60)
        click.echo(response)
        click.echo("=" * 60)

        # Show sources with links
        seen_notes = set()
        sources = []
        for chunk in results.chunks:
            if chunk.note_id not in seen_notes:
                seen_notes.add(chunk.note_id)
                # Build note URL
                note_url = ""
                id_path = chunk.metadata.get("note_id_path", "")
                if id_path:
                    server_url = config["trilium"].get("server_url", "http://localhost:8080")
                    note_url = f"{server_url}#{id_path}/{chunk.note_id}"

                sources.append((chunk.title, note_url))

        click.echo("\nSources:")
        for title, url in sources:
            if url:
                click.echo(f"  - {title}")
                click.echo(f"    {url}")
            else:
                click.echo(f"  - {title}")

    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        click.echo("Make sure your API keys are set in .env or environment variables", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        if weaviate_client:
            weaviate_client.disconnect()


@cli.command()
def status() -> None:
    """Check the status of the index."""
    indexer = None
    try:
        config = load_config()
        indexer = create_indexer(config)

        click.echo("Checking index status...\n")

        # Check Weaviate connection
        try:
            indexer.weaviate_client.connect()
            click.echo("✓ Weaviate connection: OK")
        except Exception as e:
            click.echo(f"✗ Weaviate connection: FAILED ({e})", err=True)
            sys.exit(1)

        # Get stats
        stats = indexer.get_stats()
        click.echo(f"✓ Total chunks indexed: {stats['total_chunks']}")

        # Check database
        db_path = Path(config["trilium"]["database_path"])
        if db_path.exists():
            click.echo(f"✓ Trilium database: {db_path}")
        else:
            click.echo(f"✗ Trilium database not found: {db_path}", err=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        if indexer:
            indexer.weaviate_client.disconnect()


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to reset the index?")
def reset() -> None:
    """Reset the Weaviate index."""
    weaviate_client = None
    try:
        config = load_config()
        weaviate_client = WeaviateClient(
            url=config["weaviate"]["url"],
            api_key=config["weaviate"].get("api_key"),
            collection_name=config["weaviate"]["collection_name"],
        )

        click.echo("Resetting index...")
        weaviate_client.connect()
        weaviate_client.delete_collection()
        click.echo("Index reset complete!")
        click.echo("Run 'trilium-ai index --full' to reindex")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        if weaviate_client:
            weaviate_client.disconnect()


@cli.command()
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload (development only)")
def web(host: str | None, port: int | None, reload: bool) -> None:
    """Start the web interface."""
    try:
        config = load_config()

        # Get web config with overrides
        web_config = config.get("web", {})
        final_host = host or web_config.get("host", "0.0.0.0")
        final_port = port or web_config.get("port", 3000)

        click.echo(f"Starting Trilium AI web server...")
        click.echo(f"Host: {final_host}")
        click.echo(f"Port: {final_port}")
        click.echo(f"URL: http://{final_host if final_host != '0.0.0.0' else 'localhost'}:{final_port}")
        click.echo()

        if reload:
            click.echo("⚠️  Auto-reload enabled (development mode)")
            click.echo()

        import uvicorn

        uvicorn.run(
            "trilium_ai.web.app:app",
            host=final_host,
            port=final_port,
            reload=reload,
        )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
