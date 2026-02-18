"""OpenAI GPT AI provider implementation."""

import json
import logging
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from app.mcp_server.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str, model: str = "gpt-4.1") -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: GPT-4.1)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a chat request to OpenAI.

        Args:
            messages: List of message objects with role and content
            tools: Optional list of MCP tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = OpenAI default)
            output_config: Structured output config (mapped to response_format)

        Returns:
            OpenAI's response in standard format
        """
        # Convert MCP tools to OpenAI function calling format
        openai_tools = None
        if tools:
            openai_tools = self._convert_tools_to_openai_format(tools)

        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages)

        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": openai_messages,
            }

            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"

            if temperature is not None:
                kwargs["temperature"] = temperature

            # Map output_config to OpenAI's response_format
            if output_config and output_config.get("format", {}).get("type") == "json_schema":
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "scenario_design",
                        "schema": output_config["format"]["schema"],
                        "strict": True,
                    },
                }

            response = await self.client.chat.completions.create(**kwargs)

            return self._format_response(response)

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            raise

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat request to OpenAI.

        Args:
            messages: List of message objects
            tools: Optional list of MCP tool definitions
            max_tokens: Maximum tokens to generate

        Yields:
            Streaming response chunks
        """
        # Convert MCP tools to OpenAI format
        openai_tools = None
        if tools:
            openai_tools = self._convert_tools_to_openai_format(tools)

        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages)

        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": openai_messages,
                "stream": True,
            }

            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**kwargs)

            async for chunk in response:
                yield self._format_stream_event(chunk)

        except Exception as e:
            logger.error(f"Error streaming from OpenAI API: {e}", exc_info=True)
            raise

    def _convert_tools_to_openai_format(
        self, mcp_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert MCP tool definitions to OpenAI's function calling format.

        Args:
            mcp_tools: List of MCP tool definitions

        Returns:
            List of OpenAI-formatted tool definitions
        """
        openai_tools = []
        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            openai_tools.append(openai_tool)

        return openai_tools

    def _convert_messages_to_openai_format(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert standard messages to OpenAI format.

        Args:
            messages: Standard message format

        Returns:
            OpenAI-formatted messages
        """
        openai_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                openai_messages.append({"role": "system", "content": content})
            elif role == "user":
                # Handle tool results (content is a list)
                if isinstance(content, list):
                    # Convert tool results to OpenAI format
                    for item in content:
                        if item.get("type") == "tool_result":
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": item.get("tool_use_id"),
                                "content": item.get("content", ""),
                            })
                else:
                    openai_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                # Handle assistant messages with tool calls
                if isinstance(content, list):
                    # Extract text and tool uses
                    text_content = ""
                    tool_calls = []

                    for item in content:
                        if item.get("type") == "text":
                            text_content += item.get("text", "")
                        elif item.get("type") == "tool_use":
                            tool_calls.append({
                                "id": item.get("id"),
                                "type": "function",
                                "function": {
                                    "name": item.get("name"),
                                    "arguments": json.dumps(item.get("input", {})),
                                },
                            })

                    openai_msg: dict[str, Any] = {"role": "assistant"}
                    if text_content:
                        openai_msg["content"] = text_content
                    if tool_calls:
                        openai_msg["tool_calls"] = tool_calls

                    openai_messages.append(openai_msg)
                else:
                    openai_messages.append({"role": "assistant", "content": content})

        return openai_messages

    def _format_response(self, response: Any) -> dict[str, Any]:
        """Format OpenAI response to standard format.

        Args:
            response: OpenAI API response

        Returns:
            Formatted response matching Anthropic format
        """
        choice = response.choices[0]
        message = choice.message

        formatted = {
            "id": response.id,
            "role": "assistant",
            "content": [],
            "model": response.model,
            "stop_reason": choice.finish_reason,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
        }

        # Add text content if present
        if message.content:
            formatted["content"].append({"type": "text", "text": message.content})

        # Add tool calls if present
        if message.tool_calls:
            for tool_call in message.tool_calls:
                formatted["content"].append({
                    "type": "tool_use",
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "input": json.loads(tool_call.function.arguments),
                })

        return formatted

    def _format_stream_event(self, chunk: Any) -> dict[str, Any]:
        """Format streaming chunk.

        Args:
            chunk: Stream chunk

        Returns:
            Formatted event
        """
        formatted: dict[str, Any] = {"type": "stream_delta"}

        if chunk.choices:
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                formatted["content"] = delta.content
            if delta.tool_calls:
                formatted["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name if tc.function else None,
                        "arguments": tc.function.arguments if tc.function else None,
                    }
                    for tc in delta.tool_calls
                ]

            formatted["finish_reason"] = choice.finish_reason

        return formatted
