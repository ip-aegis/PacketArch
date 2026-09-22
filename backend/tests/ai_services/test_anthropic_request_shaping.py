# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""How the Anthropic provider shapes a request.

Every assertion here is about a kwarg that reaches (or is deliberately
kept out of) ``messages.create`` — thinking mode, effort, sampling,
cache breakpoints, deferred tools — plus the response blocks we have to
hand back unchanged. These are the details that 400 at runtime when a
new model lands, so they are pinned rather than left to a live call.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.mcp_server.ai_providers.anthropic_provider import (
    DEFAULT_CAPABILITIES,
    AnthropicProvider,
)
from app.mcp_server.ai_providers.model_router import (
    AITask,
    FALLBACK_MODEL,
    TASK_MODEL_MAP,
    select_effort,
)


def _provider(model: str, effort: str | None = "high") -> AnthropicProvider:
    return AnthropicProvider(api_key="not-used", model=model, effort=effort)


# --------------------------------------------------------------------
# Capability resolution
# --------------------------------------------------------------------


def test_unknown_model_is_assumed_current_generation() -> None:
    """A model id we've never heard of must not lose thinking.

    This is the regression the capability table exists for: the old
    allowlists gave an unlisted id no thinking at all, silently.
    """
    provider = _provider("claude-opus-9-9")

    assert provider.caps == DEFAULT_CAPABILITIES
    assert provider.caps.thinking == "adaptive"
    assert provider.caps.effort is True
    assert provider.caps.sampling is False

    kwargs: dict[str, Any] = {"max_tokens": 16384}
    provider._add_thinking_params(kwargs)
    assert kwargs["thinking"]["type"] == "adaptive"
    assert "budget_tokens" not in kwargs["thinking"]


def test_current_flagship_uses_adaptive_thinking_with_summary() -> None:
    kwargs: dict[str, Any] = {"max_tokens": 16384}
    _provider("claude-opus-5-5")._add_thinking_params(kwargs)

    assert kwargs["thinking"] == {"type": "adaptive", "display": "summarized"}


def test_legacy_model_uses_budget_thinking() -> None:
    kwargs: dict[str, Any] = {"max_tokens": 16384}
    _provider("claude-haiku-4-5")._add_thinking_params(kwargs)

    assert kwargs["thinking"]["type"] == "enabled"
    assert kwargs["thinking"]["budget_tokens"] >= 1024


def test_budget_thinking_skipped_when_max_tokens_too_small() -> None:
    """max_tokens must exceed budget_tokens, and the minimum budget is
    1024 — the 500-token description path would otherwise 400."""
    kwargs: dict[str, Any] = {"max_tokens": 500}
    _provider("claude-haiku-4-5")._add_thinking_params(kwargs)

    assert "thinking" not in kwargs


# --------------------------------------------------------------------
# Effort
# --------------------------------------------------------------------


def test_effort_merges_without_clobbering_caller_format() -> None:
    """The scenario designer's json_schema must survive the merge."""
    caller = {"format": {"type": "json_schema", "schema": {"type": "object"}}}

    merged = _provider("claude-opus-5-5", effort="high")._build_output_config(caller)

    assert merged["effort"] == "high"
    assert merged["format"] == caller["format"]
    # The caller's dict is not mutated in place.
    assert "effort" not in caller


def test_effort_omitted_for_models_that_reject_it() -> None:
    assert _provider("claude-haiku-4-5", effort="low")._build_output_config(None) is None


def test_effort_omitted_when_caller_declared_no_task() -> None:
    assert _provider("claude-opus-5-5", effort=None)._build_output_config(None) is None


# --------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------


def test_temperature_dropped_for_current_generation() -> None:
    """Sampling params are a TypeError on the 1.x SDK and a 400 on the
    API for Opus 4.7+ / Sonnet 5."""
    kwargs: dict[str, Any] = {}
    _provider("claude-opus-5-5")._apply_sampling(kwargs, 0.2)

    assert kwargs == {}


def test_temperature_forwarded_via_extra_body_for_legacy_models() -> None:
    kwargs: dict[str, Any] = {}
    _provider("claude-haiku-4-5")._apply_sampling(kwargs, 0.2)

    assert kwargs["extra_body"] == {"temperature": 0.2}
    assert "temperature" not in kwargs


# --------------------------------------------------------------------
# Tool definitions
# --------------------------------------------------------------------


def _mcp_tool(name: str, defer: bool = False) -> dict[str, Any]:
    tool = {
        "name": name,
        "description": f"{name} description",
        "input_schema": {"type": "object", "properties": {}},
    }
    if defer:
        tool["defer_loading"] = True
    return tool


def test_cache_breakpoint_lands_on_last_non_deferred_tool() -> None:
    """A deferred tool carrying cache_control is a 400."""
    provider = _provider("claude-opus-5-5")

    converted = provider._convert_tools_to_claude_format(
        [
            {"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"},
            _mcp_tool("add_device"),
            _mcp_tool("get_scenario_summary"),
            _mcp_tool("score_realism", defer=True),
            _mcp_tool("validate_topology", defer=True),
        ]
    )

    assert converted[0] == {
        "type": "tool_search_tool_bm25_20251119",
        "name": "tool_search_tool_bm25",
    }
    assert converted[2]["name"] == "get_scenario_summary"
    assert converted[2]["cache_control"] == {"type": "ephemeral"}
    for tool in converted:
        if tool.get("defer_loading"):
            assert "cache_control" not in tool
    assert sum("cache_control" in t for t in converted) == 1


def test_all_tools_cached_on_last_entry_when_nothing_deferred() -> None:
    converted = _provider("claude-opus-5-5")._convert_tools_to_claude_format(
        [_mcp_tool("add_device"), _mcp_tool("add_flow")]
    )

    assert converted[-1]["cache_control"] == {"type": "ephemeral"}
    assert "defer_loading" not in converted[0]


# --------------------------------------------------------------------
# Response formatting
# --------------------------------------------------------------------


class _Block(SimpleNamespace):
    def model_dump(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


def _response(content: list[Any], stop_reason: str = "tool_use", **extra: Any) -> Any:
    return SimpleNamespace(
        id="msg_1",
        role="assistant",
        model="claude-opus-5-5",
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        content=content,
        **extra,
    )


def test_server_tool_blocks_round_trip_verbatim() -> None:
    """Tool-search blocks must survive into the replayed history.

    The chat loop appends whatever ``_format_response`` returns as the
    assistant turn. Drop these and the API either re-searches or rejects
    the next request.
    """
    search_use = _Block(type="server_tool_use", id="srvtoolu_1", name="tool_search_tool_bm25")
    search_result = _Block(type="tool_search_tool_result", tool_use_id="srvtoolu_1")
    tool_use = _Block(type="tool_use", id="toolu_1", name="add_device", input={"a": 1})

    formatted = _provider("claude-opus-5-5")._format_response(
        _response([search_use, search_result, tool_use])
    )

    types = [block["type"] for block in formatted["content"]]
    assert types == ["server_tool_use", "tool_search_tool_result", "tool_use"]
    assert formatted["content"][0]["id"] == "srvtoolu_1"
    assert formatted["content"][1]["tool_use_id"] == "srvtoolu_1"


def test_refusal_carries_its_category() -> None:
    """PacketArch generates ICS attack playbooks, so a cyber-category
    decline is plausible; the operator needs to know which it was."""
    formatted = _provider("claude-opus-5-5")._format_response(
        _response(
            [],
            stop_reason="refusal",
            stop_details=SimpleNamespace(
                type="refusal", category="cyber", explanation="nope"
            ),
        )
    )

    assert formatted["stop_reason"] == "refusal"
    assert formatted["stop_details"]["category"] == "cyber"


def test_thinking_signature_is_preserved() -> None:
    """Signatures must be echoed back or the next turn 400s."""
    thinking = _Block(type="thinking", thinking="reasoning", signature="sig-abc")

    formatted = _provider("claude-opus-5-5")._format_response(_response([thinking]))

    assert formatted["content"][0]["signature"] == "sig-abc"


# --------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------


def test_heavy_tasks_route_to_the_current_flagship() -> None:
    anthropic_map = TASK_MODEL_MAP["anthropic"]

    assert anthropic_map[AITask.CHAT] == "claude-opus-5-5"
    assert anthropic_map[AITask.SCENARIO_GENERATION] == "claude-opus-5-5"
    assert anthropic_map[AITask.SCENARIO_REVIEW] == "claude-opus-5-5"
    assert FALLBACK_MODEL["anthropic"] == "claude-opus-5-5"


def test_every_task_declares_an_effort_level() -> None:
    """Opus 5.5 defaults to medium where Opus 5 defaulted to high, so a
    task with no declared effort would silently change behaviour on the
    next model swap."""
    for task in AITask:
        assert select_effort(task) in {"low", "medium", "high", "xhigh", "max"}

    assert select_effort(None) is None
    assert select_effort(AITask.SCENARIO_GENERATION) == "high"
    assert select_effort(AITask.SITE_IDENTITY) == "low"


def test_every_routed_anthropic_model_is_priced() -> None:
    """An unpriced model shows as NULL cost in the admin dashboard."""
    from app.ai_services.pricing import PRICE_TABLE

    for model in set(TASK_MODEL_MAP["anthropic"].values()) | {FALLBACK_MODEL["anthropic"]}:
        assert ("anthropic", model) in PRICE_TABLE, model
