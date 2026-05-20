from trilium_ai.gateway.query_expander import QueryExpander


def test_query_expander_returns_original_query_when_no_match() -> None:
    expander = QueryExpander(synonyms={"rag": ["retrieval augmented generation"]})

    assert expander.expand("python notes") == ["python notes"]


def test_query_expander_adds_synonym_variants() -> None:
    expander = QueryExpander(
        synonyms={"rag": ["retrieval augmented generation", "retrieval-augmented generation"]},
        max_expanded_queries=3,
    )

    variants = expander.expand("improve rag search")

    assert variants == [
        "improve rag search",
        "improve retrieval augmented generation search",
        "improve retrieval-augmented generation search",
    ]


def test_query_expander_does_not_replace_inside_other_words() -> None:
    expander = QueryExpander(synonyms={"ai": ["artificial intelligence"]})

    assert expander.expand("paid search systems") == ["paid search systems"]
