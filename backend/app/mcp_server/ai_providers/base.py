# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Base AI provider interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, AsyncIterator

if TYPE_CHECKING:
    from app.ai_services.usage_recorder import AIUsageContext


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
        tracking: "AIUsageContext | None" = None,
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
            tracking: Optional attribution metadata. When provided, the
                provider writes a row to ``ai_call_audit`` after the
                call (success or failure) so spend can be aggregated
                by user / feature / model. Recorder failures never
                propagate to the caller.

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
        tracking: "AIUsageContext | None" = None,
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
