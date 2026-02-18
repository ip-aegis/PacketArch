"""Base AI provider interface."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a chat request to the AI.

        Args:
            messages: List of message objects
            tools: Optional list of tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = provider default)
            output_config: Structured output config (e.g. JSON schema enforcement)

        Returns:
            AI response
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat request to the AI.

        Args:
            messages: List of message objects
            tools: Optional list of tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = provider default)
            output_config: Structured output config (e.g. JSON schema enforcement)

        Yields:
            Streaming response chunks
        """
        pass
