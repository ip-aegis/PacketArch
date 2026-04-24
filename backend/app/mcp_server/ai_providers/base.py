# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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
        skills: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send a chat request to the AI.

        Args:
            messages: List of message objects
            tools: Optional list of tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = provider default)
            output_config: Structured output config (e.g. JSON schema enforcement)
            skills: Ordered skill names to prepend to the system prompt.
                Providers that support Agent Skills load each skill's
                body and emit it as cacheable context. Providers without
                skill support may ignore this parameter.

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
        skills: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat request to the AI.

        Args:
            messages: List of message objects
            tools: Optional list of tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = provider default)
            output_config: Structured output config (e.g. JSON schema enforcement)
            skills: Ordered skill names to prepend (see :meth:`chat`).

        Yields:
            Streaming response chunks
        """
        pass
