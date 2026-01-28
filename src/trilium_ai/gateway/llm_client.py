"""LLM client for OpenAI, Anthropic, and Google Gemini APIs."""

import os
from typing import Any, Optional

from trilium_ai.shared.models import Chunk


class LLMClient:
    """Client for LLM API calls."""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4-turbo",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> None:
        """Initialize the LLM client.

        Args:
            provider: LLM provider (openai, anthropic, gemini)
            model: Model name
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation
        """
        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client: Any = None

    def _init_client(self) -> None:
        """Initialize the API client."""
        if self._client is not None:
            return

        if self.provider == "openai":
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self._client = OpenAI(api_key=api_key)

        elif self.provider == "anthropic":
            from anthropic import Anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self._client = Anthropic(api_key=api_key)

        elif self.provider == "gemini":
            from google import genai

            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set"
                )
            self._client = genai.Client(api_key=api_key)

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def generate(
        self,
        query: str,
        context_chunks: list[Chunk],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate a response using retrieved context.

        Args:
            query: User query
            context_chunks: Retrieved context chunks
            system_prompt: Optional system prompt override

        Returns:
            Generated response text
        """
        self._init_client()

        # Build context from chunks
        context = self._build_context(context_chunks)

        # Default system prompt
        if system_prompt is None:
            system_prompt = (
                "You are an AI assistant with access to the user's personal notes from Trilium. "
                "Use the provided context from their notes to answer questions accurately. "
                "If the context doesn't contain relevant information, say so. "
                "Always cite which note the information comes from when possible."
            )

        # Build user message with context
        user_message = f"""Context from your notes:
{context}

Question: {query}"""

        if self.provider == "openai":
            return self._generate_openai(system_prompt, user_message)
        elif self.provider == "anthropic":
            return self._generate_anthropic(system_prompt, user_message)
        elif self.provider == "gemini":
            return self._generate_gemini(system_prompt, user_message)

        raise ValueError(f"Unsupported provider: {self.provider}")

    def _generate_openai(self, system_prompt: str, user_message: str) -> str:
        """Generate response using OpenAI API.

        Args:
            system_prompt: System prompt
            user_message: User message with context

        Returns:
            Generated response
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return response.choices[0].message.content or ""

    def _generate_anthropic(self, system_prompt: str, user_message: str) -> str:
        """Generate response using Anthropic API.

        Args:
            system_prompt: System prompt
            user_message: User message with context

        Returns:
            Generated response
        """
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text

    def _generate_gemini(self, system_prompt: str, user_message: str) -> str:
        """Generate response using Google Gemini API.

        Args:
            system_prompt: System prompt
            user_message: User message with context

        Returns:
            Generated response
        """
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            ),
        )

        return response.text

    def _build_context(self, chunks: list[Chunk]) -> str:
        """Build context string from chunks.

        Args:
            chunks: List of context chunks

        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant notes found."

        context_parts = []
        seen_notes = set()

        for chunk in chunks:
            # Group chunks by note for cleaner context
            note_header = f"[Note: {chunk.title}]"

            if chunk.note_id not in seen_notes:
                context_parts.append(f"\n{note_header}")
                seen_notes.add(chunk.note_id)

            context_parts.append(chunk.content)

        return "\n".join(context_parts)
