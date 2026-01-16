"""Configuration management using Pydantic Settings."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        env_file=".env",
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

        # Create config from YAML (environment variables will override via SettingsConfigDict)
        _config = Config(**yaml_config)
    return _config
