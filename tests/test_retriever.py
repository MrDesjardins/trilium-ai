from trilium_ai.gateway.retriever import Retriever
from trilium_ai.shared.models import Chunk, SearchResult


class DummyEmbedder:
    def embed(self, query: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class StubRetriever(Retriever):
    def __init__(self) -> None:
        super().__init__(
            weaviate_client=None,  # type: ignore[arg-type]
            embedder=DummyEmbedder(),  # type: ignore[arg-type]
            use_query_expansion=True,
            synonyms={"rag": ["retrieval augmented generation"]},
            group_by_note=True,
            use_reranking=False,
        )

    def _search_single_query(self, query: str, top_k: int, debug: bool) -> SearchResult:
        if query == "rag notes":
            chunk = Chunk(
                chunk_id="c1",
                note_id="n1",
                title="RAG Basics",
                content="raw body",
                chunk_index=0,
                metadata={"retrieval_text": "Title: RAG Basics Content: raw body"},
            )
            duplicate_note = Chunk(
                chunk_id="c2",
                note_id="n1",
                title="RAG Basics",
                content="another body",
                chunk_index=1,
                metadata={"retrieval_text": "Title: RAG Basics Content: another body"},
            )
            return SearchResult(chunks=[chunk, duplicate_note], scores=[0.7, 0.6], total_results=2)

        expanded = Chunk(
            chunk_id="c3",
            note_id="n2",
            title="Retrieval Augmented Generation",
            content="expanded body",
            chunk_index=0,
            metadata={"retrieval_text": "Title: Retrieval Augmented Generation Content: expanded body"},
        )
        return SearchResult(chunks=[expanded], scores=[0.9], total_results=1)


def test_retriever_merges_expanded_queries_and_groups_by_note() -> None:
    retriever = StubRetriever()

    result = retriever.search("rag notes", top_k=5)

    assert [chunk.chunk_id for chunk in result.chunks] == ["c3", "c1"]
    assert result.scores == [0.9, 0.7]
