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

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Factory for creating AI providers based on settings."""

    @staticmethod
    async def create(db: "AsyncSession") -> AIProvider:
        """Create an AI provider based on system settings.

        Args:
            db: Database session

        Returns:
            Configured AI provider

        Raises:
            ValueError: If provider is not configured or unknown
        """
        from app.models.settings import SystemSetting
        from app.core.encryption import decrypt_value

        # Get provider setting
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "ai_provider")
        )
        provider_setting = result.scalar_one_or_none()
        provider = provider_setting.value if provider_setting else "anthropic"

        if provider == "anthropic":
            # Get Anthropic API key
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == "anthropic_api_key")
            )
            api_key_setting = result.scalar_one_or_none()
            if not api_key_setting or not api_key_setting.value:
                raise ValueError("Anthropic API key not configured")

            api_key = decrypt_value(api_key_setting.value)

            # Get model setting
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == "anthropic_model")
            )
            model_setting = result.scalar_one_or_none()
            model = model_setting.value if model_setting else "claude-opus-4-7"

            logger.info(f"Creating Anthropic provider with model: {model}")
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

            # Get model setting
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == "openai_model")
            )
            model_setting = result.scalar_one_or_none()
            model = model_setting.value if model_setting else "gpt-4.1"

            logger.info(f"Creating OpenAI provider with model: {model}")
            return OpenAIProvider(api_key=api_key, model=model)

        elif provider == "circuit":
            # CIRCUIT is Cisco's internal LLM gateway. Credentials may be
            # supplied via env (CIRCUIT_CLIENT_ID / CIRCUIT_CLIENT_SECRET /
            # CIRCUIT_APP_KEY) which take precedence, or via encrypted
            # system_settings (circuit_client_id / circuit_client_secret /
            # circuit_app_key) the admin UI manages. Env wins so dev
            # machines can override without touching the DB.
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
                or (await _setting("circuit_model"))
                or "gpt-4.1"
            )

            logger.info(f"Creating CIRCUIT provider with model: {model}")
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
    "AnthropicProvider",
    "CircuitProvider",
    "OpenAIProvider",
]
