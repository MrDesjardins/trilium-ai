"""Configuration management using Pydantic Settings."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file from current working directory (set by systemd WorkingDirectory)
load_dotenv()


class TriliumConfig(BaseSettings):
    """Trilium database configuration."""

    database_path: str = Field(..., description="Path to Trilium SQLite database")
    server_url: str = Field("http://localhost:8080", description="Trilium server URL for note links")
    sync_interval: int = Field(300, description="Sync interval in seconds")


class WeaviateConfig(BaseSettings):
    """Weaviate configuration."""

    url: str = Field("http://localhost:8601", description="Weaviate URL")
    api_key: Optional[str] = Field(None, description="Weaviate API key")
    collection_name: str = Field("TriliumNotes", description="Collection name")
    batch_size: int = Field(100, description="Batch size for indexing")


class EmbeddingsConfig(BaseSettings):
    """Embeddings configuration."""

    provider: str = Field("sentence-transformers", description="Embedding provider")
    model: str = Field("all-MiniLM-L6-v2", description="Embedding model")
    dimension: int = Field(384, description="Embedding dimension")


class ChunkingConfig(BaseSettings):
    """Chunking configuration."""

    max_chunk_size: int = Field(512, description="Maximum chunk size in tokens")
    chunk_overlap: int = Field(50, description="Overlap between chunks in tokens")
    strategy: str = Field("sentence", description="Chunking strategy")


class LLMConfig(BaseSettings):
    """LLM configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        extra="ignore",
    )

    provider: str = Field("openai", description="LLM provider")
    model: str = Field("gpt-4-turbo", description="LLM model")
    max_tokens: int = Field(2000, description="Maximum tokens in response")
    temperature: float = Field(0.7, description="Temperature for generation")


class RetrievalConfig(BaseSettings):
    """Retrieval configuration."""

    top_k: int = Field(5, description="Number of top results to retrieve")
    min_score: float = Field(0.7, description="Minimum similarity score")
    mode: str = Field("hybrid", description="Search mode")
    alpha: float = Field(0.75, description="Alpha for hybrid search")
    use_query_expansion: bool = Field(True, description="Enable deterministic synonym expansion")
    synonyms: Dict[str, list[str]] = Field(
        default_factory=dict, description="Synonym map used for query expansion"
    )
    max_expanded_queries: int = Field(5, description="Maximum number of expanded query variants")
    group_by_note: bool = Field(True, description="Limit final results to one chunk per note")
    use_reranking: bool = Field(False, description="Enable reranking with cross-encoder")
    reranking_model: str = Field(
        "cross-encoder/ms-marco-MiniLM-L-6-v2", description="Cross-encoder model for reranking"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field("INFO", description="Logging level")
    file: Optional[str] = Field("logs/trilium-ai.log", description="Log file path")


class WebConfig(BaseSettings):
    """Web interface configuration."""

    enabled: bool = Field(True, description="Enable web interface")
    host: str = Field("0.0.0.0", description="Host to bind to")
    port: int = Field(3000, description="Port to bind to")


class Config(BaseSettings):
    """Main configuration."""

    model_config = SettingsConfigDict(
        env_file=str(Path.cwd() / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    trilium: TriliumConfig
    weaviate: WeaviateConfig
    embeddings: EmbeddingsConfig
    chunking: ChunkingConfig
    llm: LLMConfig
    retrieval: RetrievalConfig
    logging: LoggingConfig
    web: WebConfig


_config: Optional[Config] = None


def get_runtime_cache_dir(app_name: str = "trilium-ai") -> Path:
    """Return a writable runtime cache directory.

    Preference order:
    1. `TRILIUM_AI_CACHE_DIR`
    2. `XDG_CACHE_HOME/<app_name>`
    3. `~/.cache/<app_name>`
    4. `/tmp/<app_name>`
    """
    configured_cache_dir = os.getenv("TRILIUM_AI_CACHE_DIR")
    candidates: list[Path] = []

    if configured_cache_dir:
        candidates.append(Path(configured_cache_dir).expanduser())

    xdg_cache_home = os.getenv("XDG_CACHE_HOME")
    if xdg_cache_home:
        candidates.append(Path(xdg_cache_home).expanduser() / app_name)

    candidates.append(Path.home() / ".cache" / app_name)
    candidates.append(Path("/tmp") / app_name)

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write-test"
            test_file.write_text("ok")
            test_file.unlink()
            return candidate
        except OSError:
            continue

    raise OSError("Unable to determine a writable runtime cache directory")


def load_yaml_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    yaml_path = Path(config_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


def get_config() -> Config:
    """Get or create the singleton configuration."""
    global _config
    if _config is None:
        # Load YAML configuration
        config_path = os.getenv("TRILIUM_AI_CONFIG", "config/config.yaml")
        yaml_config = load_yaml_config(config_path)

        # Manually override with environment variables if present
        # This ensures LLM_* env vars take precedence over YAML
        if "llm" in yaml_config:
            if os.getenv("LLM_PROVIDER"):
                yaml_config["llm"]["provider"] = os.getenv("LLM_PROVIDER")
            if os.getenv("LLM_MODEL"):
                yaml_config["llm"]["model"] = os.getenv("LLM_MODEL")
            if os.getenv("LLM_TEMPERATURE"):
                yaml_config["llm"]["temperature"] = float(os.getenv("LLM_TEMPERATURE"))
            if os.getenv("LLM_MAX_TOKENS"):
                yaml_config["llm"]["max_tokens"] = int(os.getenv("LLM_MAX_TOKENS"))

        # Create config from YAML (environment variables will override via SettingsConfigDict)
        _config = Config(**yaml_config)
    return _config
