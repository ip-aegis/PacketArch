# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Anthropic Claude AI provider implementation."""

import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator

import anthropic
from anthropic import AsyncAnthropic

from app.ai_services.skills import SkillNotFoundError, get_registry
from app.ai_services.usage_recorder import AIUsageContext, record_call
from app.mcp_server.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelCapabilities:
    """What a given Claude model accepts on the Messages API.

    Attributes:
        thinking: ``"adaptive"`` (the model decides how deeply to think),
            ``"budget"`` (pre-4.6 style ``budget_tokens``), or ``"none"``.
        effort: Whether ``output_config.effort`` is accepted. Haiku 4.5
            and Sonnet 4.5 return an error for it.
        sampling: Whether ``temperature`` / ``top_p`` / ``top_k`` are
            accepted. Removed on Opus 4.7+ and Sonnet 5 (HTTP 400).
    """

    thinking: str = "adaptive"
    effort: bool = True
    sampling: bool = False


# The default describes a CURRENT-GENERATION model, and unknown model
# ids resolve to it. That direction is deliberate and is the opposite of
# what this module used to do.
#
# It used to carry two exact-match allowlists (``THINKING_MODELS`` and
# ``ADAPTIVE_THINKING_MODELS``). A model id in neither set got no
# thinking at all, silently — so adding a newly released flagship to the
# Settings dropdown without also editing both sets shipped a
# no-thinking flagship that looked fine and reasoned worse. Adding it to
# the wrong set was worse still: ``budget_tokens`` is rejected outright
# on Opus 5/5.5 and Sonnet 5.
#
# An unrecognised id in practice means "released after this build", and
# every model released since Opus 4.6 takes adaptive thinking, takes
# effort, and rejects sampling parameters. So unknown now means modern,
# and the table below lists only the models that DIFFER from that.
DEFAULT_CAPABILITIES = ModelCapabilities()

MODEL_CAPABILITIES: dict[str, ModelCapabilities] = {
    # Pre-4.6: manual thinking budget, sampling still allowed.
    "claude-haiku-4-5": ModelCapabilities(thinking="budget", effort=False, sampling=True),
    "claude-haiku-4-5-20251001": ModelCapabilities(
        thinking="budget", effort=False, sampling=True
    ),
    "claude-sonnet-4-5": ModelCapabilities(thinking="budget", effort=False, sampling=True),
    "claude-sonnet-4-5-20250929": ModelCapabilities(
        thinking="budget", effort=False, sampling=True
    ),
    # Opus 4.5 takes effort (low/medium/high) but still uses budget_tokens.
    "claude-opus-4-5-20251101": ModelCapabilities(
        thinking="budget", effort=True, sampling=True
    ),
    # The 4.6 line: adaptive thinking arrives, sampling not yet removed.
    "claude-opus-4-6": ModelCapabilities(thinking="adaptive", effort=True, sampling=True),
    "claude-sonnet-4-6": ModelCapabilities(
        thinking="adaptive", effort=True, sampling=True
    ),
    # Opus 5.5 / 5 / 4.8 / 4.7 and Sonnet 5 are DEFAULT_CAPABILITIES —
    # deliberately absent so they need no maintenance.
}

# Above this, ask the SDK to stream. Non-streaming requests with a large
# ``max_tokens`` can exceed the SDK's HTTP timeout, and the SDK refuses
# them rather than hanging.
#
# This used to be discovered by catching ValueError and string-matching
# "Streaming is required" out of the message — i.e. depending on the
# wording of an SDK error. A threshold is deterministic and survives
# SDK upgrades.
NON_STREAMING_MAX_TOKENS = 16_384

# Server-side context management: drops stale tool results from the
# prefix so a long agentic loop stops resending every earlier result.
CONTEXT_MANAGEMENT_BETA = "context-management-2025-06-27"
CLEAR_TOOL_USES_EDIT = {"type": "clear_tool_uses_20250919"}


# Assistant content blocks that are not ours to interpret but ARE ours
# to replay verbatim on the next turn.
_PASSTHROUGH_BLOCK_TYPES = frozenset(
    {"server_tool_use", "tool_search_tool_result"}
)


def _block_to_dict(block: Any) -> dict[str, Any]:
    """Convert an SDK content block to a plain replayable dict.

    Uses the model's own serialiser where available so a block we do not
    model explicitly still round-trips field-for-field.
    """
    for attr in ("model_dump", "to_dict", "dict"):
        dumper = getattr(block, attr, None)
        if callable(dumper):
            try:
                return dumper()
            except TypeError:
                continue
    return {"type": getattr(block, "type", None)}


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-5-5",
        effort: str | None = None,
    ) -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key.
            model: Model to use (default: Claude Opus 5.5 — current
                flagship, and cheaper than Opus 5 at $4/$20 per MTok).
            effort: ``output_config.effort`` level for every call on this
                provider instance (``low`` … ``max``). ``None`` omits the
                key and lets the model default apply. The factory sets
                this from :func:`model_router.select_effort`.
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.effort = effort

    @property
    def caps(self) -> ModelCapabilities:
        """Capabilities of the configured model.

        Unknown ids resolve to :data:`DEFAULT_CAPABILITIES` (current
        generation) — see the comment on that constant for why the
        default is the permissive one.
        """
        return MODEL_CAPABILITIES.get(self.model, DEFAULT_CAPABILITIES)

    def _add_thinking_params(self, kwargs: dict[str, Any]) -> None:
        """Add thinking parameters based on model capabilities.

        Adaptive models (Opus 4.6 and later, Sonnet 4.6 and later) let
        the model decide how deeply to think; ``display: "summarized"``
        asks for a readable summary, which is what the streaming chat
        route surfaces as real reasoning. Thinking is billed identically
        whatever the display setting, so this costs nothing.

        Budget models (Sonnet 4.5, Haiku 4.5, Opus 4.5) take an explicit
        ``budget_tokens`` — but only when the caller asked for enough
        ``max_tokens`` to leave room. Anthropic requires
        ``max_tokens > budget_tokens`` and the minimum budget is 1024, so
        any caller passing < ~1536 tokens (e.g. the scenario_description
        path at max_tokens=500) silently 400s unless we skip thinking
        for that call.
        """
        thinking = self.caps.thinking
        if thinking == "adaptive":
            kwargs["thinking"] = {"type": "adaptive", "display": "summarized"}
        elif thinking == "budget":
            max_tokens = kwargs.get("max_tokens", 16384)
            min_budget = 1024
            output_headroom = 512
            if max_tokens < min_budget + output_headroom:
                return
            budget = min(5000, max(min_budget, max_tokens - output_headroom))
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

    def _build_output_config(
        self, output_config: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Merge this provider's effort level into the caller's config.

        ``output_config`` carries both the structured-output ``format``
        and the ``effort`` level, and callers own the former — the
        scenario designer and the scenario reviewer both pass a
        ``json_schema`` format. So merge rather than assign: clobbering
        the caller's dict would silently disable structured outputs and
        turn a schema-guaranteed response back into free text.
        """
        if not self.effort or not self.caps.effort:
            return output_config
        merged = dict(output_config or {})
        merged.setdefault("effort", self.effort)
        return merged

    def _apply_sampling(self, kwargs: dict[str, Any], temperature: float | None) -> None:
        """Forward ``temperature`` only to models that still accept it.

        Sampling parameters are removed from the 1.x SDK signatures
        (passing ``temperature=`` is a ``TypeError``) and rejected by
        Opus 4.7+ / Sonnet 5 with a 400. Models that still honour it get
        it through ``extra_body``, which is merged into the request JSON
        verbatim; everything else drops it with a log rather than
        failing the call.
        """
        if temperature is None:
            return
        if not self.caps.sampling:
            logger.debug(
                "Dropping temperature=%s: %s does not accept sampling parameters",
                temperature,
                self.model,
            )
            return
        extra_body = dict(kwargs.get("extra_body") or {})
        extra_body["temperature"] = temperature
        kwargs["extra_body"] = extra_body

    def _request_target(self, manage_context: bool) -> tuple[Any, dict[str, Any]]:
        """Pick the messages namespace and any beta-only request kwargs.

        Server-side context management is a beta, so a request that wants
        it has to go through ``client.beta.messages`` with the beta flag.
        Everything else uses the stable namespace — betas are opt-in per
        call rather than switched on globally.
        """
        if not manage_context:
            return self.client.messages, {}
        return self.client.beta.messages, {
            "betas": [CONTEXT_MANAGEMENT_BETA],
            "context_management": {"edits": [CLEAR_TOOL_USES_EDIT]},
        }

    def _build_system_blocks(
        self,
        system_message: str | None,
        skills: list[str] | None,
    ) -> list[dict[str, Any]] | None:
        """Compose the ``system`` field as a list of cacheable text blocks.

        Two ``cache_control`` breakpoints, no more: one after the LAST
        skill block and one on the task system prompt.

        Caching is a prefix match, so a single breakpoint after the last
        skill already covers every skill before it — marking each one
        individually bought nothing and spent from a hard budget of four
        breakpoints per request. With three skills plus the system prompt
        that was exactly four, leaving no room for the tool-definition
        breakpoint; a fourth skill, or skills on a tool-bearing call,
        would have been a 400.

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
                blocks.append({"type": "text", "text": skill.body})

        # One breakpoint covering the whole skill prefix.
        if blocks:
            blocks[-1]["cache_control"] = {"type": "ephemeral"}

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
        manage_context: bool = False,
    ) -> dict[str, Any]:
        """Send a chat request to Claude.

        Args:
            messages: List of message objects with role and content
            tools: Optional list of MCP tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature. Only forwarded to models
                that still accept sampling parameters (see
                :meth:`_apply_sampling`).
            output_config: Structured output config for guaranteed JSON schema
                compliance. Example: {"format": {"type": "json_schema",
                "schema": {...}}}. This provider's effort level is merged
                in alongside, never over, what the caller passes.
            skills: Ordered list of skill names to prepend to the system
                prompt. Each skill is loaded from
                ``backend/app/ai_services/skills/`` and emitted as part
                of a single cacheable ``system`` prefix.
            tracking: Optional attribution metadata for token/cost
                auditing (see :class:`AIUsageContext`).
            manage_context: Enable server-side context management, which
                clears stale tool results out of the prefix. For long
                agentic loops only; a one-shot call has nothing to clear.

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

        t0 = time.monotonic()
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

            self._apply_sampling(kwargs, temperature)

            # Structured output config + per-task effort.
            resolved_output_config = self._build_output_config(output_config)
            if resolved_output_config:
                kwargs["output_config"] = resolved_output_config

            # Enable thinking for supported models
            self._add_thinking_params(kwargs)

            messages_api, beta_kwargs = self._request_target(manage_context)
            kwargs.update(beta_kwargs)

            if max_tokens > NON_STREAMING_MAX_TOKENS:
                # Large responses must stream or the request can outlive
                # the SDK's HTTP timeout; collect the final message.
                async with messages_api.stream(**kwargs) as stream:
                    response = await stream.get_final_message()
            else:
                response = await messages_api.create(**kwargs)

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
                latency_ms=int((time.monotonic() - t0) * 1000),
                tracking=tracking,
                error=str(e),
            )
            self._log_api_error("calling", e)
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
        manage_context: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat request to Claude.

        Yields the SDK's events as they arrive and then one terminal
        ``{"type": "final", "message": ...}`` event carrying the fully
        assembled response in the same shape :meth:`chat` returns.

        That terminal event is what makes streaming usable inside an
        agentic loop: the caller needs the assembled ``tool_use`` blocks
        to execute tools and the assistant content to replay on the next
        turn, and neither can be reconstructed reliably from deltas.
        Usage is recorded here too, so a streamed call lands in
        ``ai_call_audit`` exactly like a non-streamed one.

        Args:
            messages: List of message objects
            tools: Optional list of tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (see :meth:`_apply_sampling`)
            output_config: Structured output config for guaranteed JSON schema
            skills: Ordered skill names to prepend (see :meth:`chat`).
            tracking: Optional attribution metadata for token/cost auditing.
            manage_context: Enable server-side context management.

        Yields:
            Streaming response chunks, then the terminal ``final`` event.
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

        t0 = time.monotonic()
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

            self._apply_sampling(kwargs, temperature)

            resolved_output_config = self._build_output_config(output_config)
            if resolved_output_config:
                kwargs["output_config"] = resolved_output_config

            # Enable thinking for supported models
            self._add_thinking_params(kwargs)

            messages_api, beta_kwargs = self._request_target(manage_context)
            kwargs.update(beta_kwargs)

            async with messages_api.stream(**kwargs) as stream:
                async for event in stream:
                    # Yield formatted events
                    yield self._format_stream_event(event)

                final = self._format_response(await stream.get_final_message())

            await record_call(
                provider="anthropic",
                model=self.model,
                usage=final.get("usage"),
                latency_ms=int((time.monotonic() - t0) * 1000),
                tracking=tracking,
            )
            yield {"type": "final", "message": final}

        except Exception as e:
            await record_call(
                provider="anthropic",
                model=self.model,
                usage=None,
                latency_ms=int((time.monotonic() - t0) * 1000),
                tracking=tracking,
                error=str(e),
            )
            self._log_api_error("streaming from", e)
            raise

    def _log_api_error(self, verb: str, exc: Exception) -> None:
        """Log an SDK failure, classified by the SDK's own exception types.

        Most specific first. The point of the chain is that a 404 (bad
        model id — the usual outcome of a stale entry in the Settings
        dropdown) reads differently in the log from a 429 or a dropped
        connection, which are retryable and not anyone's bug.
        """
        if isinstance(exc, anthropic.NotFoundError):
            logger.error(
                "Anthropic %s the API failed: model '%s' not found (404). "
                "The configured model may have been retired or misspelled.",
                verb,
                self.model,
            )
        elif isinstance(exc, anthropic.RateLimitError):
            logger.warning("Anthropic %s the API was rate limited (429)", verb)
        elif isinstance(exc, anthropic.APIStatusError):
            logger.error(
                "Anthropic %s the API returned HTTP %s: %s",
                verb,
                exc.status_code,
                exc.message,
            )
        elif isinstance(exc, anthropic.APIConnectionError):
            logger.error("Anthropic %s the API failed to connect: %s", verb, exc)
        else:
            logger.error("Error %s Anthropic API: %s", verb, exc, exc_info=True)

    def _convert_tools_to_claude_format(
        self, mcp_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert MCP tool definitions to Claude's format.

        Passes Anthropic server-tool entries (anything carrying a
        ``type``, e.g. the tool search tool) through verbatim, preserves
        ``defer_loading`` on client tools, and places one prompt-cache
        breakpoint on the last NON-DEFERRED tool.

        The breakpoint placement is not cosmetic: a tool marked
        ``defer_loading: true`` cannot also carry ``cache_control`` — the
        API rejects the request with a 400. Marking "the last tool"
        unconditionally, as this used to, breaks the moment deferred
        loading is switched on.

        Args:
            mcp_tools: List of MCP tool definitions

        Returns:
            List of Claude-formatted tool definitions
        """
        # Strict mode is intentionally OFF — Anthropic caps strict-mode
        # tools at 20 per request and PacketArch registers ~69 MCP tools
        # (every scenario CRUD op + every fingerprint helper). Deferred
        # loading does NOT relax this: the strict grammar is built from
        # the full toolset, not the loaded subset, so the cap still
        # applies. Non-strict tools work fine and the model rarely
        # produces invalid input. See:
        # https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
        claude_tools: list[dict[str, Any]] = []
        for tool in mcp_tools:
            if "type" in tool:
                # Anthropic-defined server tool (tool search, etc.) —
                # schema-less by design, forward as given.
                claude_tools.append(dict(tool))
                continue
            claude_tool: dict[str, Any] = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            if tool.get("defer_loading"):
                claude_tool["defer_loading"] = True
            claude_tools.append(claude_tool)

        # Cache the tool prefix on the last entry that is allowed to
        # carry a breakpoint.
        for claude_tool in reversed(claude_tools):
            if not claude_tool.get("defer_loading"):
                claude_tool["cache_control"] = {"type": "ephemeral"}
                break

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

        # ``stop_details`` is populated only for stop_reason="refusal",
        # and it carries the classifier category (e.g. "cyber") plus an
        # explanation. Worth surfacing: PacketArch generates ICS attack
        # playbooks, so a cyber-category decline is a plausible and
        # actionable outcome, and "AI declined" on its own tells the
        # operator nothing about whether to rephrase or to stop.
        stop_details = getattr(response, "stop_details", None)
        if stop_details is not None:
            formatted["stop_details"] = {
                "type": getattr(stop_details, "type", None),
                "category": getattr(stop_details, "category", None),
                "explanation": getattr(stop_details, "explanation", None),
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
            elif block.type in _PASSTHROUGH_BLOCK_TYPES:
                # Server-side tool blocks (tool search). These MUST be
                # replayed unchanged on the next turn — the API expands
                # the tool_reference blocks inside them so Claude can
                # reuse a discovered tool without searching again, and
                # a history missing them makes the loop re-search or
                # fail outright. They must never receive a tool_result:
                # the srvtoolu_... id is not ours to answer.
                formatted["content"].append(_block_to_dict(block))

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
