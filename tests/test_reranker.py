import os
from pathlib import Path

from trilium_ai.gateway.reranker import Reranker


class DummyCrossEncoder:
    def __init__(self, model_name: str, cache_folder: str) -> None:
        self.model_name = model_name
        self.cache_folder = cache_folder


def test_reranker_uses_writable_cache_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TRILIUM_AI_CACHE_DIR", str(tmp_path / "cache-root"))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_CACHE", raising=False)
    monkeypatch.delenv("SENTENCE_TRANSFORMERS_HOME", raising=False)
    monkeypatch.setattr("trilium_ai.gateway.reranker.CrossEncoder", DummyCrossEncoder)

    reranker = Reranker()
    model = reranker.model

    expected_cache_dir = tmp_path / "cache-root" / "huggingface"
    assert isinstance(model, DummyCrossEncoder)
    assert model.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert model.cache_folder == str(expected_cache_dir)
    assert os.environ["HF_HOME"] == str(expected_cache_dir)
    assert os.environ["HUGGINGFACE_HUB_CACHE"] == str(expected_cache_dir / "hub")
    assert os.environ["TRANSFORMERS_CACHE"] == str(expected_cache_dir / "transformers")
    assert os.environ["SENTENCE_TRANSFORMERS_HOME"] == str(
        expected_cache_dir / "sentence-transformers"
    )
