# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Task-aware model routing for AI providers.

The user picks a single provider (Anthropic | OpenAI | CIRCUIT) in the
Settings UI. PacketArch then picks the best model from that provider
for each AI task automatically:

* Complex multi-step / multi-turn work (interactive chat, scenario
  generation, scenario review) → the provider's flagship model.
* Short structured generation (device naming, site identity,
  description generation, inline help) → the provider's small/fast
  tier so we don't burn flagship tokens on a 5-word output.

Centralising the table here means every call site that needs an AI
model passes an :class:`AITask` instead of hardcoding a model string —
swap models in one place and every feature picks it up.

CIRCUIT's appkey entitlement varies; today Rocky's dev appkey allows
only ``gpt-5-nano`` and ``gemini-3.1-flash-lite``. We default to
``gpt-5-nano`` for every task because Gemini-via-CIRCUIT requires a
``thought_signature`` round-trip that the gateway enforces strictly
(see ``circuit_provider._convert_messages``); until that path is
verified end-to-end, prefer the GPT model.
"""

from __future__ import annotations

from enum import Enum


class AITask(str, Enum):
    """Enumeration of distinct AI workloads inside PacketArch.

    The string value doubles as a usage-recorder ``feature`` tag so the
    AI cost dashboard groups calls by task.
    """

    CHAT = "chat"
    """Interactive AI assistant in the Studio right panel."""

    SCENARIO_GENERATION = "scenario_generation"
    """Generate a full scenario from a natural-language description."""

    SCENARIO_REVIEW = "scenario_review"
    """Score realism / find issues in an existing scenario."""

    DEVICE_NAMING = "device_naming"
    """Generate human-readable, role-aware device names."""

    SITE_IDENTITY = "site_identity"
    """Generate a SiteIdentity (org name, region, tagline) for naming context."""

    DESCRIPTION_GENERATION = "description_generation"
    """Generate a scenario description from its structure."""

    AI_HELP = "ai_help"
    """Answer inline help / 'explain this' questions."""


# Provider → Task → model deployment name.
#
# Models named here MUST be ones the provider exposes today; the
# AnthropicProvider / OpenAIProvider / CircuitProvider will forward
# the string verbatim, so a typo here surfaces as a 404 from the
# upstream gateway.
TASK_MODEL_MAP: dict[str, dict[AITask, str]] = {
    "anthropic": {
        # Flagship Opus 4.8 for the heavy lifters — tool use,
        # multi-turn reasoning, design review.
        AITask.CHAT: "claude-opus-4-8",
        AITask.SCENARIO_GENERATION: "claude-opus-4-8",
        AITask.SCENARIO_REVIEW: "claude-opus-4-8",
        # Sonnet 4.6 for medium-complexity prose generation.
        AITask.DESCRIPTION_GENERATION: "claude-sonnet-4-6",
        AITask.AI_HELP: "claude-sonnet-4-6",
        # Haiku 4.5 for short structured output where Opus would be
        # massive overkill.
        AITask.DEVICE_NAMING: "claude-haiku-4-5",
        AITask.SITE_IDENTITY: "claude-haiku-4-5",
    },
    "openai": {
        # Flagship GPT-5.5 for the heavy lifters (mirrors the Opus tier).
        AITask.CHAT: "gpt-5.5",
        AITask.SCENARIO_GENERATION: "gpt-5.5",
        AITask.SCENARIO_REVIEW: "gpt-5.5",
        # GPT-5.4 Mini for medium-complexity prose generation.
        AITask.DESCRIPTION_GENERATION: "gpt-5.4-mini",
        AITask.AI_HELP: "gpt-5.4-mini",
        # GPT-5.4 Nano for short structured output (cheapest current tier).
        AITask.DEVICE_NAMING: "gpt-5.4-nano",
        AITask.SITE_IDENTITY: "gpt-5.4-nano",
    },
    "circuit": {
        # See module docstring — Rocky's dev appkey constrains us to
        # gpt-5-nano in practice. Adjust per deployment if the appkey
        # was granted broader entitlements.
        AITask.CHAT: "gpt-5-nano",
        AITask.SCENARIO_GENERATION: "gpt-5-nano",
        AITask.SCENARIO_REVIEW: "gpt-5-nano",
        AITask.DESCRIPTION_GENERATION: "gpt-5-nano",
        AITask.AI_HELP: "gpt-5-nano",
        AITask.DEVICE_NAMING: "gpt-5-nano",
        AITask.SITE_IDENTITY: "gpt-5-nano",
    },
}


# Fallback model per provider when the task isn't in the map or no
# task is given. Keeps the legacy "pick one model from settings"
# behaviour working when the router can't decide.
FALLBACK_MODEL: dict[str, str] = {
    "anthropic": "claude-opus-4-8",
    "openai": "gpt-5.5",
    "circuit": "gpt-5-nano",
}


def select_model(provider: str, task: AITask | None) -> str | None:
    """Return the best model for ``provider``/``task``.

    Returns ``None`` if the provider isn't in the routing table — the
    caller should then fall back to the legacy ``<provider>_model``
    setting or :data:`FALLBACK_MODEL`. Returns the provider's fallback
    when ``task`` is ``None`` so plain ``select_model(p, None)`` still
    yields a usable answer.
    """
    if provider not in TASK_MODEL_MAP:
        return None
    if task is None:
        return FALLBACK_MODEL.get(provider)
    return TASK_MODEL_MAP[provider].get(task, FALLBACK_MODEL.get(provider))


def list_routing(provider: str) -> list[tuple[str, str]]:
    """Return ``[(task_value, model), ...]`` for diagnostics / UI display."""
    mapping = TASK_MODEL_MAP.get(provider, {})
    return [(task.value, model) for task, model in mapping.items()]


__all__ = ["AITask", "TASK_MODEL_MAP", "FALLBACK_MODEL", "select_model", "list_routing"]
