"""Anthropic Claude AI provider implementation."""

import json
import logging
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic

from app.mcp_server.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-5-20251101") -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: Claude Opus 4.5)
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a chat request to Claude.

        Args:
            messages: List of message objects with role and content
            tools: Optional list of MCP tool definitions
            max_tokens: Maximum tokens to generate

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

            if system_message:
                kwargs["system"] = system_message

            if claude_tools:
                kwargs["tools"] = claude_tools

            response = await self.client.messages.create(**kwargs)

            return self._format_response(response)

        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}", exc_info=True)
            raise

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat request to Claude.

        Args:
            messages: List of message objects
            tools: Optional list of MCP tool definitions
            max_tokens: Maximum tokens to generate

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

            if system_message:
                kwargs["system"] = system_message

            if claude_tools:
                kwargs["tools"] = claude_tools

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

        Args:
            mcp_tools: List of MCP tool definitions

        Returns:
            List of Claude-formatted tool definitions
        """
        claude_tools = []
        for tool in mcp_tools:
            claude_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            claude_tools.append(claude_tool)

        return claude_tools

    def _format_response(self, response: Any) -> dict[str, Any]:
        """Format Claude response to standard format.

        Args:
            response: Claude API response

        Returns:
            Formatted response
        """
        formatted = {
            "id": response.id,
            "role": response.role,
            "content": [],
            "model": response.model,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

        # Format content blocks
        for block in response.content:
            if block.type == "text":
                formatted["content"].append(
                    {"type": "text", "text": block.text}
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
