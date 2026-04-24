# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Anthropic Claude AI provider implementation."""

import logging
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic

from app.mcp_server.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)

# Models that support extended thinking
THINKING_MODELS = {
    "claude-opus-4-6",
    "claude-opus-4-5-20251101",
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-5",
}
# Models that support adaptive thinking (preferred over manual budget_tokens)
ADAPTIVE_THINKING_MODELS = {"claude-opus-4-6"}


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-6") -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: Claude Opus 4.6)
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    def _supports_thinking(self) -> bool:
        """Check if the current model supports extended thinking."""
        return self.model in THINKING_MODELS

    def _supports_adaptive_thinking(self) -> bool:
        """Check if the current model supports adaptive thinking."""
        return self.model in ADAPTIVE_THINKING_MODELS

    def _add_thinking_params(self, kwargs: dict[str, Any]) -> None:
        """Add thinking parameters based on model capabilities.

        Opus 4.6: Uses adaptive thinking (model decides when to think deeply).
        Sonnet 4.5: Uses extended thinking with a budget.
        """
        if self._supports_adaptive_thinking():
            kwargs["thinking"] = {"type": "adaptive"}
        elif self._supports_thinking():
            max_tokens = kwargs.get("max_tokens", 16384)
            budget = min(5000, max(1024, max_tokens - 1024))
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a chat request to Claude.

        Args:
            messages: List of message objects with role and content
            tools: Optional list of MCP tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = Claude default 1.0)
            output_config: Structured output config for guaranteed JSON schema
                compliance. Example: {"format": {"type": "json_schema",
                "schema": {...}}}

        Returns:
            Claude's response
        """
        # Convert MCP tools to Claude format
        claude_tools = None
        if tools:
            claude_tools = self._convert_tools_to_claude_format(tools)

        # Separate system message if present
        system_message = None
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                chat_messages.append(msg)

        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": chat_messages,
            }

            # System message with prompt caching
            if system_message:
                kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_message,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]

            if claude_tools:
                kwargs["tools"] = claude_tools

            if temperature is not None:
                kwargs["temperature"] = temperature

            # Structured output config for guaranteed JSON schema compliance
            if output_config:
                kwargs["output_config"] = output_config

            # Enable thinking for supported models
            self._add_thinking_params(kwargs)

            try:
                response = await self.client.messages.create(**kwargs)
            except ValueError as e:
                if "Streaming is required" in str(e):
                    # SDK requires streaming for high max_tokens requests;
                    # collect the full response via stream
                    logger.info("Falling back to streaming collection for long request")
                    async with self.client.messages.stream(**kwargs) as stream:
                        response = await stream.get_final_message()
                else:
                    raise

            return self._format_response(response)

        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}", exc_info=True)
            raise

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat request to Claude.

        Args:
            messages: List of message objects
            tools: Optional list of MCP tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = Claude default 1.0)
            output_config: Structured output config for guaranteed JSON schema

        Yields:
            Streaming response chunks
        """
        # Convert MCP tools to Claude format
        claude_tools = None
        if tools:
            claude_tools = self._convert_tools_to_claude_format(tools)

        # Separate system message if present
        system_message = None
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                chat_messages.append(msg)

        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": chat_messages,
            }

            # System message with prompt caching
            if system_message:
                kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_message,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]

            if claude_tools:
                kwargs["tools"] = claude_tools

            if temperature is not None:
                kwargs["temperature"] = temperature

            if output_config:
                kwargs["output_config"] = output_config

            # Enable thinking for supported models
            self._add_thinking_params(kwargs)

            async with self.client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    # Yield formatted events
                    yield self._format_stream_event(event)

        except Exception as e:
            logger.error(f"Error streaming from Anthropic API: {e}", exc_info=True)
            raise

    def _convert_tools_to_claude_format(
        self, mcp_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert MCP tool definitions to Claude's format.

        Enables strict mode for guaranteed schema-compliant tool inputs and
        adds cache_control to the last tool definition for prompt caching.

        Args:
            mcp_tools: List of MCP tool definitions

        Returns:
            List of Claude-formatted tool definitions with strict validation
        """
        claude_tools = []
        for tool in mcp_tools:
            input_schema = dict(tool["input_schema"])
            # Ensure additionalProperties is false for strict mode
            if "type" in input_schema and input_schema["type"] == "object":
                input_schema["additionalProperties"] = False

            claude_tool: dict[str, Any] = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": input_schema,
                "strict": True,
            }
            claude_tools.append(claude_tool)

        # Cache the full set of tool definitions
        if claude_tools:
            claude_tools[-1]["cache_control"] = {"type": "ephemeral"}

        return claude_tools

    def _format_response(self, response: Any) -> dict[str, Any]:
        """Format Claude response to standard format.

        Args:
            response: Claude API response

        Returns:
            Formatted response
        """
        usage: dict[str, Any] = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        # Include cache metrics if available
        if hasattr(response.usage, "cache_creation_input_tokens"):
            usage["cache_creation_input_tokens"] = response.usage.cache_creation_input_tokens
        if hasattr(response.usage, "cache_read_input_tokens"):
            usage["cache_read_input_tokens"] = response.usage.cache_read_input_tokens

        formatted = {
            "id": response.id,
            "role": response.role,
            "content": [],
            "model": response.model,
            "stop_reason": response.stop_reason,
            "usage": usage,
        }

        # Format content blocks
        for block in response.content:
            if block.type == "text":
                formatted["content"].append(
                    {"type": "text", "text": block.text}
                )
            elif block.type == "thinking":
                formatted["content"].append(
                    {"type": "thinking", "thinking": block.thinking}
                )
            elif block.type == "tool_use":
                formatted["content"].append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return formatted

    def _format_stream_event(self, event: Any) -> dict[str, Any]:
        """Format streaming event.

        Args:
            event: Stream event

        Returns:
            Formatted event
        """
        event_type = event.type

        formatted = {"type": event_type}

        if event_type == "message_start":
            formatted["message"] = {
                "id": event.message.id,
                "role": event.message.role,
                "model": event.message.model,
            }
        elif event_type == "content_block_start":
            formatted["index"] = event.index
            formatted["content_block"] = {"type": event.content_block.type}
        elif event_type == "content_block_delta":
            formatted["index"] = event.index
            formatted["delta"] = {"type": event.delta.type}
            if hasattr(event.delta, "text"):
                formatted["delta"]["text"] = event.delta.text
            if hasattr(event.delta, "thinking"):
                formatted["delta"]["thinking"] = event.delta.thinking
        elif event_type == "content_block_stop":
            formatted["index"] = event.index
        elif event_type == "message_delta":
            formatted["delta"] = {}
            if hasattr(event.delta, "stop_reason"):
                formatted["delta"]["stop_reason"] = event.delta.stop_reason
            formatted["usage"] = {
                "output_tokens": event.usage.output_tokens,
            }
        elif event_type == "message_stop":
            pass

        return formatted
