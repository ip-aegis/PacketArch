"""AI provider implementations."""

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.mcp_server.ai_providers.base import AIProvider
from app.mcp_server.ai_providers.anthropic_provider import AnthropicProvider
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
            model = model_setting.value if model_setting else "claude-opus-4-6"

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

        else:
            raise ValueError(f"Unknown AI provider: {provider}")


__all__ = [
    "AIProvider",
    "AIProviderFactory",
    "AnthropicProvider",
    "OpenAIProvider",
]
