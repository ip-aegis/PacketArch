# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""AI provider implementations."""

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.mcp_server.ai_providers.base import AIProvider
from app.mcp_server.ai_providers.anthropic_provider import AnthropicProvider
from app.mcp_server.ai_providers.circuit_provider import CircuitProvider
from app.mcp_server.ai_providers.openai_provider import OpenAIProvider
from app.mcp_server.ai_providers.model_router import (
    AITask,
    FALLBACK_MODEL,
    select_model,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Factory for creating AI providers based on settings.

    The user picks a provider in Settings (Anthropic | OpenAI | CIRCUIT);
    PacketArch picks the best model from that provider for each task
    via :mod:`app.mcp_server.ai_providers.model_router`. Callers should
    pass the :class:`AITask` they're about to execute so the right model
    is chosen — call sites that don't pass a task get the provider's
    fallback model.
    """

    @staticmethod
    async def create(
        db: "AsyncSession",
        task: AITask | None = None,
    ) -> AIProvider:
        """Create an AI provider for ``task``.

        Resolution order for the model:

        1. ``model_router.select_model(provider, task)`` — the
           recommended model for this task on the chosen provider.
           Always used when ``task`` is given.
        2. Legacy ``<provider>_model`` system_settings row — only
           consulted when ``task`` is ``None`` (back-compat for callers
           that haven't migrated yet).
        3. :data:`model_router.FALLBACK_MODEL` for the provider.

        Args:
            db: Database session.
            task: Which AI task this provider will run. Drives model
                selection — see ``model_router.TASK_MODEL_MAP``.

        Returns:
            Configured AI provider.

        Raises:
            ValueError: If provider isn't configured / unknown.
        """
        from app.models.settings import SystemSetting
        from app.core.encryption import decrypt_value

        # Get provider setting
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "ai_provider")
        )
        provider_setting = result.scalar_one_or_none()
        provider = provider_setting.value if provider_setting else "anthropic"

        async def _legacy_model(key: str) -> str | None:
            r = await db.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            s = r.scalar_one_or_none()
            return s.value if s and s.value else None

        async def _resolve_model(legacy_key: str) -> str:
            """Pick a model name using router → legacy setting → fallback."""
            if task is not None:
                routed = select_model(provider, task)
                if routed:
                    return routed
            legacy = await _legacy_model(legacy_key)
            if legacy:
                return legacy
            return FALLBACK_MODEL.get(provider) or ""

        if provider == "anthropic":
            # Get Anthropic API key
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == "anthropic_api_key")
            )
            api_key_setting = result.scalar_one_or_none()
            if not api_key_setting or not api_key_setting.value:
                raise ValueError("Anthropic API key not configured")

            api_key = decrypt_value(api_key_setting.value)
            model = await _resolve_model("anthropic_model") or "claude-opus-5"

            logger.info(
                "Creating Anthropic provider for task=%s with model: %s",
                task.value if task else "unspecified", model,
            )
            return AnthropicProvider(api_key=api_key, model=model)

        elif provider == "openai":
            # Get OpenAI API key
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == "openai_api_key")
            )
            api_key_setting = result.scalar_one_or_none()
            if not api_key_setting or not api_key_setting.value:
                raise ValueError("OpenAI API key not configured")

            api_key = decrypt_value(api_key_setting.value)
            model = await _resolve_model("openai_model") or "gpt-5.6-sol"

            logger.info(
                "Creating OpenAI provider for task=%s with model: %s",
                task.value if task else "unspecified", model,
            )
            return OpenAIProvider(api_key=api_key, model=model)

        elif provider == "circuit":
            # CIRCUIT is Cisco's internal LLM gateway. Credentials may be
            # supplied via env (CIRCUIT_CLIENT_ID / CIRCUIT_CLIENT_SECRET /
            # CIRCUIT_APP_KEY) which take precedence, or via encrypted
            # system_settings (circuit_client_id / circuit_client_secret /
            # circuit_app_key) the admin UI manages. Env wins so dev
            # machines can override without touching the DB.
            #
            # Note: CIRCUIT_MODEL env var still wins when set, since it's
            # an explicit operator override. UI / task router only applies
            # when env is unset.
            import os

            async def _setting(key: str) -> str | None:
                r = await db.execute(
                    select(SystemSetting).where(SystemSetting.key == key)
                )
                s = r.scalar_one_or_none()
                if not s or not s.value:
                    return None
                # Some CIRCUIT settings (e.g. client_id, app_key) are not
                # encrypted because they're not secrets in the
                # password-equivalent sense, only client_secret is.
                if key == "circuit_client_secret":
                    return decrypt_value(s.value)
                return s.value

            client_id = (
                os.getenv("CIRCUIT_CLIENT_ID")
                or await _setting("circuit_client_id")
            )
            client_secret = (
                os.getenv("CIRCUIT_CLIENT_SECRET")
                or await _setting("circuit_client_secret")
            )
            app_key = (
                os.getenv("CIRCUIT_APP_KEY")
                or await _setting("circuit_app_key")
            )
            if not (client_id and client_secret and app_key):
                missing = [
                    name for name, val in (
                        ("CLIENT_ID", client_id),
                        ("CLIENT_SECRET", client_secret),
                        ("APP_KEY", app_key),
                    ) if not val
                ]
                raise ValueError(
                    "CIRCUIT credentials not fully configured (missing: "
                    f"{', '.join(missing)})"
                )

            model = (
                os.getenv("CIRCUIT_MODEL")
                or (await _resolve_model("circuit_model"))
                or "gpt-5-nano"
            )

            logger.info(
                "Creating CIRCUIT provider for task=%s with model: %s",
                task.value if task else "unspecified", model,
            )
            return CircuitProvider(
                client_id=client_id,
                client_secret=client_secret,
                app_key=app_key,
                model=model,
            )

        else:
            raise ValueError(f"Unknown AI provider: {provider}")


__all__ = [
    "AIProvider",
    "AIProviderFactory",
    "AITask",
    "AnthropicProvider",
    "CircuitProvider",
    "OpenAIProvider",
    "select_model",
]
