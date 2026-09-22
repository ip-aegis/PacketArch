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

The same table also carries the per-task *effort* level
(:data:`TASK_EFFORT`). Effort is the primary cost/quality lever on
current-generation Claude models and its default is not uniform —
Opus 5.5 defaults to ``medium`` where Opus 5 defaulted to ``high`` —
so PacketArch states it explicitly rather than inheriting whatever
the model of the day happens to pick.

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
        # Flagship Opus 5.5 for the heavy lifters — tool use,
        # multi-turn reasoning, design review. Newer AND cheaper than
        # Opus 5 ($4/$20 per M vs $5/$25, cache reads $0.20 vs $0.50).
        AITask.CHAT: "claude-opus-5-5",
        AITask.SCENARIO_GENERATION: "claude-opus-5-5",
        AITask.SCENARIO_REVIEW: "claude-opus-5-5",
        # Sonnet 5 for medium-complexity prose generation (current-gen
        # balanced tier; adaptive thinking on, manual budget_tokens removed).
        AITask.DESCRIPTION_GENERATION: "claude-sonnet-5",
        AITask.AI_HELP: "claude-sonnet-5",
        # Haiku 4.5 for short structured output where Opus would be
        # massive overkill.
        AITask.DEVICE_NAMING: "claude-haiku-4-5",
        AITask.SITE_IDENTITY: "claude-haiku-4-5",
    },
    "openai": {
        # GPT-5.6 family, mirroring the Anthropic current-gen tiers
        # (Sol↔Opus, Terra↔Sonnet, Luna↔Haiku).
        # Sol — frontier flagship for the heavy lifters.
        AITask.CHAT: "gpt-5.6-sol",
        AITask.SCENARIO_GENERATION: "gpt-5.6-sol",
        AITask.SCENARIO_REVIEW: "gpt-5.6-sol",
        # Terra — balanced intelligence/cost for medium-complexity prose.
        AITask.DESCRIPTION_GENERATION: "gpt-5.6-terra",
        AITask.AI_HELP: "gpt-5.6-terra",
        # Luna — efficient, high-volume tier for short structured output.
        AITask.DEVICE_NAMING: "gpt-5.6-luna",
        AITask.SITE_IDENTITY: "gpt-5.6-luna",
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
    "anthropic": "claude-opus-5-5",
    "openai": "gpt-5.6-sol",
    "circuit": "gpt-5-nano",
}


# Task → ``output_config.effort`` level.
#
# Effort trades thoroughness against token spend WITHIN one model, and
# it is the lever to reach for before swapping models. Two reasons this
# table exists rather than letting the model default:
#
# 1. The default is not stable across models. Opus 5.5 defaults to
#    ``medium``; Opus 5 and everything before it defaulted to ``high``.
#    Silently inheriting that would have made the 5.5 upgrade look like
#    a quality regression.
# 2. The tasks genuinely differ. Designing a 40-device scenario that has
#    to satisfy five realism dimensions deserves ``high``; inventing a
#    site name does not.
#
# Providers that don't understand effort ignore it — only the Anthropic
# provider consumes this today, and it drops the key for models whose
# API rejects it (Haiku 4.5, Sonnet 4.5).
TASK_EFFORT: dict[AITask, str] = {
    AITask.CHAT: "high",
    AITask.SCENARIO_GENERATION: "high",
    AITask.SCENARIO_REVIEW: "high",
    AITask.DESCRIPTION_GENERATION: "medium",
    AITask.AI_HELP: "medium",
    AITask.DEVICE_NAMING: "low",
    AITask.SITE_IDENTITY: "low",
}


def select_effort(task: AITask | None) -> str | None:
    """Return the effort level for ``task``, or ``None`` when unknown.

    ``None`` means "say nothing about effort" — the provider then omits
    ``output_config.effort`` entirely and the model's own default
    applies. That is the right behaviour for a caller that didn't
    declare a task.
    """
    if task is None:
        return None
    return TASK_EFFORT.get(task)


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


__all__ = [
    "AITask",
    "TASK_MODEL_MAP",
    "TASK_EFFORT",
    "FALLBACK_MODEL",
    "select_model",
    "select_effort",
    "list_routing",
]
