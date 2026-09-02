# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Per-(provider, model) token pricing for AI cost accounting.

Prices are expressed in USD per **1 million** tokens. Values come from
each provider's public pricing page (Anthropic / OpenAI) or the
upstream-model pricing for CIRCUIT (Cisco's gateway re-bills at
upstream rates for internal-cost purposes). They are intentionally
kept in code rather than DB — prices change rarely and tracking them
in git history is more useful than a settings UI.

When ``get_price()`` returns ``None`` the audit row stores
``total_cost_usd=NULL`` instead of fabricating a number. The admin
dashboard surfaces those rows as "unpriced" rather than $0 so the
operator can fix the table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelPrice:
    """USD per 1M tokens, per usage category."""

    input: float
    output: float
    # Anthropic-specific. OpenAI/CIRCUIT use ``input`` for cached reads
    # implicitly (their automatic cache discount is reflected in
    # ``prompt_tokens`` returned by the API).
    cache_read: float = 0.0
    cache_write: float = 0.0


# Keys are (provider, model). Provider strings match what the audit
# recorder writes (``anthropic`` / ``openai`` / ``circuit``).
PRICE_TABLE: dict[tuple[str, str], ModelPrice] = {
    # Anthropic — verified 2026-05-14 against claude.com/docs/.../pricing.
    # Cache write rate is the **5-minute** tier (1.25x input). The 1-hour
    # tier (2x input) is not currently used by PacketArch.
    #
    # Opus 4.5 / 4.6 / 4.7 / 4.8: $5 / $25 per M (NEW tokenizer in 4.7 can
    # use ~35% more tokens for the same text — that's a token-count effect,
    # not a per-token price change). 4.8 holds the same per-token tier.
    ("anthropic", "claude-opus-4-8"): ModelPrice(
        input=5.0, output=25.0, cache_read=0.5, cache_write=6.25,
    ),
    ("anthropic", "claude-opus-4-7"): ModelPrice(
        input=5.0, output=25.0, cache_read=0.5, cache_write=6.25,
    ),
    ("anthropic", "claude-opus-4-6"): ModelPrice(
        input=5.0, output=25.0, cache_read=0.5, cache_write=6.25,
    ),
    ("anthropic", "claude-opus-4-5-20251101"): ModelPrice(
        input=5.0, output=25.0, cache_read=0.5, cache_write=6.25,
    ),
    # Opus 4.1: legacy higher-priced tier still available.
    ("anthropic", "claude-opus-4-1"): ModelPrice(
        input=15.0, output=75.0, cache_read=1.5, cache_write=18.75,
    ),
    # Sonnet 5: $3 / $15 per M standard (intro $2 / $10 through 2026-08-31;
    # we bill at standard to avoid under-reporting cost).
    ("anthropic", "claude-sonnet-5"): ModelPrice(
        input=3.0, output=15.0, cache_read=0.3, cache_write=3.75,
    ),
    # Sonnet 4.5 / 4.6: $3 / $15 per M.
    ("anthropic", "claude-sonnet-4-6"): ModelPrice(
        input=3.0, output=15.0, cache_read=0.3, cache_write=3.75,
    ),
    ("anthropic", "claude-sonnet-4-5-20250929"): ModelPrice(
        input=3.0, output=15.0, cache_read=0.3, cache_write=3.75,
    ),
    ("anthropic", "claude-sonnet-4-5"): ModelPrice(
        input=3.0, output=15.0, cache_read=0.3, cache_write=3.75,
    ),
    # Haiku 4.5: $1 / $5 per M.
    ("anthropic", "claude-haiku-4-5-20251001"): ModelPrice(
        input=1.0, output=5.0, cache_read=0.1, cache_write=1.25,
    ),
    ("anthropic", "claude-haiku-4-5"): ModelPrice(
        input=1.0, output=5.0, cache_read=0.1, cache_write=1.25,
    ),
    # Haiku 3.5: retired on the Claude API but still callable via Bedrock /
    # Vertex AI, so we keep the entry for completeness.
    ("anthropic", "claude-haiku-3-5"): ModelPrice(
        input=0.80, output=4.0, cache_read=0.08, cache_write=1.0,
    ),
    # OpenAI — verified 2026-05-14 against multiple sources for the GPT-5.4 /
    # GPT-5.5 generation. Older models cross-checked against historical rates.
    # OpenAI's automatic prompt-caching discount lives in the input column
    # already (the API returns cached tokens with a reduced count), so we
    # don't break it out as cache_read here.
    # GPT-5.6 family — verified 2026-07-23 against developers.openai.com.
    ("openai", "gpt-5.6-sol"): ModelPrice(input=5.0, output=30.0),
    ("openai", "gpt-5.6-terra"): ModelPrice(input=2.5, output=15.0),
    ("openai", "gpt-5.6-luna"): ModelPrice(input=1.0, output=6.0),
    ("openai", "gpt-5.5"): ModelPrice(input=5.0, output=30.0),
    ("openai", "gpt-5.5-pro"): ModelPrice(input=30.0, output=180.0),
    ("openai", "gpt-5.4"): ModelPrice(input=2.5, output=15.0),
    ("openai", "gpt-5.4-mini"): ModelPrice(input=0.75, output=4.5),
    ("openai", "gpt-5.4-nano"): ModelPrice(input=0.20, output=1.25),
    ("openai", "gpt-5"): ModelPrice(input=1.25, output=10.0),
    ("openai", "gpt-5-mini"): ModelPrice(input=0.25, output=2.0),
    ("openai", "gpt-5-nano"): ModelPrice(input=0.05, output=0.40),
    ("openai", "gpt-4.1"): ModelPrice(input=2.0, output=8.0),
    ("openai", "gpt-4.1-mini"): ModelPrice(input=0.4, output=1.6),
    ("openai", "gpt-4o"): ModelPrice(input=2.5, output=10.0),
    ("openai", "gpt-4o-mini"): ModelPrice(input=0.15, output=0.6),
    ("openai", "o3"): ModelPrice(input=2.0, output=8.0),
    ("openai", "o4-mini"): ModelPrice(input=1.10, output=4.40),
    # CIRCUIT (Cisco internal gateway) — zero-cost in this table by
    # design. The actual CIRCUIT billing model isn't documented to
    # PacketArch operators (internal cost-center vs per-token resale
    # varies by appkey), so we track CIRCUIT *tokens* faithfully but
    # report $0 cost rather than guess. A future monthly-quota
    # feature will let operators rationalize usage by token volume
    # independent of dollar cost. To enable dollar accounting for
    # CIRCUIT later, replace these with real per-appkey rates.
    ("circuit", "gpt-4.1"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gpt-4.1-mini"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gpt-4o"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gpt-4o-mini"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gpt-5"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gpt-5-mini"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gpt-5-nano"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gpt-5-chat"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "o3"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "o3-mini"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "o4-mini"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "claude-opus-4-8"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "claude-opus-4-7"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "claude-opus-4-6"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "claude-sonnet-5"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "claude-sonnet-4-6"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "claude-haiku-4-5"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gemini-3.1-pro"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gemini-3.1-flash-lite"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gemini-3-pro"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gemini-3-flash"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gemini-2.5-pro"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gemini-2.5-flash"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "llama-3-70b"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "llama-3-8b"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "gemma-4-26b-a4b-it-maas"): ModelPrice(input=0.0, output=0.0),
    ("circuit", "cisco-deep-network"): ModelPrice(input=0.0, output=0.0),
}


# Avoid spamming the logs when the same unknown model is hit repeatedly.
_warned_unknown: set[tuple[str, str]] = set()


def get_price(provider: str, model: str) -> ModelPrice | None:
    """Return pricing for ``(provider, model)`` or ``None`` if unknown."""
    key = (provider.lower(), model)
    price = PRICE_TABLE.get(key)
    if price is None and key not in _warned_unknown:
        logger.warning(
            "No price configured for %s/%s — call will be recorded "
            "with total_cost_usd=NULL. Add an entry to "
            "app/ai_services/pricing.py to capture spend.",
            provider, model,
        )
        _warned_unknown.add(key)
    return price


def compute_cost_usd(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float | None:
    """Compute the per-call cost in USD or ``None`` if pricing is unknown.

    Anthropic billing: cached-read tokens are billed at the
    ``cache_read`` rate INSTEAD of ``input`` (the API already
    subtracts them from ``input_tokens``), and ``cache_write`` is an
    additional cost on top of the input the first time the prefix is
    written. We trust the provider's split and add the categories.
    """
    price = get_price(provider, model)
    if price is None:
        return None

    cost = (
        input_tokens * price.input
        + output_tokens * price.output
        + cache_read_tokens * price.cache_read
        + cache_write_tokens * price.cache_write
    ) / 1_000_000.0
    # Avoid negative zeros / tiny floats in storage.
    return round(cost, 8)
