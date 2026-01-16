"""Prompt templates and assembly for RAG queries."""

from dataclasses import dataclass
from typing import Optional

from trilium_ai.shared.models import Chunk


@dataclass
class PromptTemplate:
    """Template for RAG prompts."""

    system: str
    context_prefix: str
    question_prefix: str


# Default RAG prompt template
DEFAULT_TEMPLATE = PromptTemplate(
    system=(
        "You are an AI assistant with access to the user's personal notes from Trilium Notes. "
        "Use the provided context from their notes to answer questions accurately and helpfully. "
        "If the context doesn't contain relevant information to answer the question, acknowledge this. "
        "When citing information, mention which note it comes from."
    ),
    context_prefix="Context from your notes:",
    question_prefix="Question:",
)

# Summarization template
SUMMARIZE_TEMPLATE = PromptTemplate(
    system=(
        "You are an AI assistant helping to summarize notes from Trilium Notes. "
        "Provide clear, concise summaries that capture the key points."
    ),
    context_prefix="Notes to summarize:",
    question_prefix="Please summarize the above notes, focusing on:",
)

# Search template (for when user wants to find specific info)
SEARCH_TEMPLATE = PromptTemplate(
    system=(
        "You are an AI assistant helping to find information in the user's Trilium notes. "
        "Focus on extracting and presenting the most relevant information to the query. "
        "Be specific about which notes contain the information."
    ),
    context_prefix="Relevant notes found:",
    question_prefix="What I'm looking for:",
)


class PromptBuilder:
    """Builds prompts for RAG queries."""

    def __init__(self, template: Optional[PromptTemplate] = None) -> None:
        """Initialize the prompt builder.

        Args:
            template: Prompt template to use (defaults to DEFAULT_TEMPLATE)
        """
        self.template = template or DEFAULT_TEMPLATE

    def build_prompt(
        self,
        query: str,
        chunks: list[Chunk],
        include_metadata: bool = True,
    ) -> tuple[str, str]:
        """Build system and user prompts from query and chunks.

        Args:
            query: User's question
            chunks: Retrieved context chunks
            include_metadata: Whether to include chunk metadata

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Build context section
        context = self._format_context(chunks, include_metadata)

        # Build user prompt
        user_prompt = f"""{self.template.context_prefix}

{context}

{self.template.question_prefix} {query}"""

        return self.template.system, user_prompt

    def _format_context(self, chunks: list[Chunk], include_metadata: bool) -> str:
        """Format chunks into context string.

        Args:
            chunks: List of chunks
            include_metadata: Whether to include metadata

        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant notes found in your knowledge base."

        formatted_parts = []
        current_note_id = None

        for i, chunk in enumerate(chunks, 1):
            # Add note header when switching to a new note
            if chunk.note_id != current_note_id:
                current_note_id = chunk.note_id
                header = f"\n--- Note: {chunk.title} ---"
                if include_metadata and chunk.metadata.get("note_type"):
                    header += f" (type: {chunk.metadata['note_type']})"
                formatted_parts.append(header)

            # Add chunk content
            formatted_parts.append(chunk.content.strip())

        return "\n".join(formatted_parts)

    def build_sources_citation(self, chunks: list[Chunk]) -> str:
        """Build a sources citation section.

        Args:
            chunks: Chunks used as context

        Returns:
            Formatted sources citation
        """
        if not chunks:
            return ""

        # Deduplicate notes
        seen = set()
        sources = []

        for chunk in chunks:
            if chunk.note_id not in seen:
                seen.add(chunk.note_id)
                sources.append(f"- {chunk.title} (ID: {chunk.note_id})")

        return "\n\nSources:\n" + "\n".join(sources)
