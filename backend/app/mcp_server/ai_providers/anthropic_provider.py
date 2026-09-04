# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Anthropic Claude AI provider implementation."""

import logging
import time
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic

from app.ai_services.skills import SkillNotFoundError, get_registry
from app.ai_services.usage_recorder import AIUsageContext, record_call
from app.mcp_server.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)

# Models that support extended thinking
THINKING_MODELS = {
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-opus-4-5-20251101",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-5",
}
# Models that support adaptive thinking (preferred over manual budget_tokens).
# Sonnet 5 belongs here (not the budget_tokens branch): manual budget_tokens
# is REMOVED on Sonnet 5 and returns HTTP 400 — it only supports adaptive.
# Opus 5 also belongs here: thinking is on by default and budget_tokens is
# removed (400), same as Opus 4.8/4.7/4.6.
ADAPTIVE_THINKING_MODELS = {
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-5",
}


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-opus-5") -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: Claude Opus 5 — latest,
                most capable for OT scenario generation + deep tool use).
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

        Opus 5 / 4.8 / 4.7 / 4.6: Uses adaptive thinking (model decides when to think deeply).
        Sonnet 4.6 / 4.5: Uses extended thinking with a budget — but only
        when the caller asked for enough ``max_tokens`` to leave room.
        Anthropic requires ``max_tokens > budget_tokens`` and the minimum
        budget is 1024, so any caller passing < ~1536 tokens (e.g. the
        scenario_description path at max_tokens=500) silently 400s
        unless we just skip thinking for that call.
        """
        if self._supports_adaptive_thinking():
            kwargs["thinking"] = {"type": "adaptive"}
        elif self._supports_thinking():
            max_tokens = kwargs.get("max_tokens", 16384)
            min_budget = 1024
            output_headroom = 512
            if max_tokens < min_budget + output_headroom:
                return
            budget = min(5000, max(min_budget, max_tokens - output_headroom))
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

    def _build_system_blocks(
        self,
        system_message: str | None,
        skills: list[str] | None,
    ) -> list[dict[str, Any]] | None:
        """Compose the ``system`` field as a list of cacheable text blocks.

        Skill bodies are stable and reused across requests, so each skill
        gets its own ephemeral-cache marker. The task-specific system
        prompt is appended last (also cached) so it can evolve per call
        without invalidating the skill prefix.

        Args:
            system_message: Task-specific system prompt text (may be None).
            skills: Ordered skill names to load and prepend. Unknown
                names are logged and skipped so a missing skill never
                breaks a live call.

        Returns:
            A list of Anthropic ``system`` blocks, or None if there is
            no content to send.
        """
        blocks: list[dict[str, Any]] = []

        if skills:
            registry = get_registry()
            for skill_name in skills:
                try:
                    skill = registry.get(skill_name)
                except SkillNotFoundError:
                    logger.warning(
                        "Skill '%s' not registered; continuing without it",
                        skill_name,
                    )
                    continue
                blocks.append(
                    {
                        "type": "text",
                        "text": skill.body,
                        "cache_control": {"type": "ephemeral"},
                    }
                )

        if system_message:
            blocks.append(
                {
                    "type": "text",
                    "text": system_message,
                    "cache_control": {"type": "ephemeral"},
                }
            )

        return blocks or None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
        skills: list[str] | None = None,
        tracking: AIUsageContext | None = None,
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
            skills: Ordered list of skill names to prepend to the system
                prompt. Each skill is loaded from
                ``backend/app/ai_services/skills/`` and emitted as its
                own cacheable ``system`` block.
            tracking: Optional attribution metadata for token/cost
                auditing (see :class:`AIUsageContext`).

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

            # Skills (if any) + task system prompt, all cacheable.
            system_blocks = self._build_system_blocks(system_message, skills)
            if system_blocks:
                kwargs["system"] = system_blocks

            if claude_tools:
                kwargs["tools"] = claude_tools

            if temperature is not None:
                kwargs["temperature"] = temperature

            # Structured output config for guaranteed JSON schema compliance
            if output_config:
                kwargs["output_config"] = output_config

            # Enable thinking for supported models
            self._add_thinking_params(kwargs)

            t0 = time.monotonic()
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

            formatted = self._format_response(response)
            await record_call(
                provider="anthropic",
                model=self.model,
                usage=formatted.get("usage"),
                latency_ms=int((time.monotonic() - t0) * 1000),
                tracking=tracking,
            )
            return formatted

        except Exception as e:
            await record_call(
                provider="anthropic",
                model=self.model,
                usage=None,
                latency_ms=None,
                tracking=tracking,
                error=str(e),
            )
            logger.error(f"Error calling Anthropic API: {e}", exc_info=True)
            raise

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
        skills: list[str] | None = None,
        tracking: AIUsageContext | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat request to Claude.

        Args:
            messages: List of message objects
            tools: Optional list of MCP tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = Claude default 1.0)
            output_config: Structured output config for guaranteed JSON schema
            skills: Ordered skill names to prepend (see :meth:`chat`).

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

            system_blocks = self._build_system_blocks(system_message, skills)
            if system_blocks:
                kwargs["system"] = system_blocks

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
        # Strict mode is intentionally OFF — Anthropic caps strict-mode
        # tools at 20 per request and PacketArch registers ~69 MCP tools
        # (every scenario CRUD op + every fingerprint helper). Strict
        # mode would guarantee exact schema compliance but isn't worth
        # the cap; non-strict tools still work and the model rarely
        # produces invalid input. See:
        # https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview
        claude_tools = []
        for tool in mcp_tools:
            claude_tool: dict[str, Any] = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            claude_tools.append(claude_tool)

        # Cache the full set of tool definitions on the last entry so
        # subsequent turns hit the prompt cache.
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

        # Format content blocks.
        #
        # Critical: when extended thinking is enabled, Claude emits
        # ``thinking`` (and occasionally ``redacted_thinking``) blocks
        # whose ``signature`` / ``data`` field is REQUIRED to be echoed
        # back verbatim on any follow-up turn. Stripping the signature
        # produces HTTP 400 ``messages.N.content.0.thinking.signature:
        # Field required`` on the second iteration of the tool-use
        # loop. Round-trip both fields.
        for block in response.content:
            if block.type == "text":
                formatted["content"].append(
                    {"type": "text", "text": block.text}
                )
            elif block.type == "thinking":
                thinking_block: dict[str, Any] = {
                    "type": "thinking",
                    "thinking": block.thinking,
                }
                sig = getattr(block, "signature", None)
                if sig is not None:
                    thinking_block["signature"] = sig
                formatted["content"].append(thinking_block)
            elif block.type == "redacted_thinking":
                # Redacted thinking blocks expose ``data`` (an opaque
                # base64 blob) instead of plaintext; still must be
                # round-tripped to keep the assistant turn valid.
                redacted_block: dict[str, Any] = {"type": "redacted_thinking"}
                data = getattr(block, "data", None)
                if data is not None:
                    redacted_block["data"] = data
                formatted["content"].append(redacted_block)
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
