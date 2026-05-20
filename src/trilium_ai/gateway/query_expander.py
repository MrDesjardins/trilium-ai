"""Deterministic query expansion for recall improvements."""

import re


class QueryExpander:
    """Expand queries with configured synonyms."""

    def __init__(
        self,
        synonyms: dict[str, list[str]] | None = None,
        max_expanded_queries: int = 5,
    ) -> None:
        self.synonyms = {self._normalize(k): v for k, v in (synonyms or {}).items()}
        self.max_expanded_queries = max_expanded_queries

    def expand(self, query: str) -> list[str]:
        """Return original query plus deterministic synonym variants."""
        normalized_query = self._normalize(query)
        variants = [query.strip()]
        seen = {normalized_query}

        for term, replacements in self.synonyms.items():
            if not self._contains_term(normalized_query, term):
                continue

            for replacement in replacements:
                candidate = self._replace_phrase(query, term, replacement)
                normalized_candidate = self._normalize(candidate)
                if normalized_candidate not in seen:
                    seen.add(normalized_candidate)
                    variants.append(candidate)
                if len(variants) >= self.max_expanded_queries:
                    return variants

        return variants

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    def _contains_term(self, query: str, term: str) -> bool:
        return re.search(self._phrase_pattern(term), query) is not None

    def _replace_phrase(self, query: str, source: str, target: str) -> str:
        pattern = re.compile(self._phrase_pattern(source), re.IGNORECASE)
        return pattern.sub(target, query)

    def _phrase_pattern(self, value: str) -> str:
        escaped = re.escape(value).replace(r"\ ", r"\s+")
        return rf"\b{escaped}\b"
