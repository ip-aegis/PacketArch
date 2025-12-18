"""AI Scenario Preview Service.

Stores temporary scenario previews in Redis for the AI creation wizard.
Previews expire after 30 minutes and are deleted when used to create a scenario.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Preview TTL: 30 minutes
PREVIEW_TTL_SECONDS = 1800

# Redis key prefix
PREVIEW_PREFIX = "ai_scenario_preview:"


class AIScenarioPreviewService:
    """Service for managing AI scenario previews in Redis."""

    _redis_pool: redis.ConnectionPool | None = None
    _redis_client: redis.Redis | None = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get or create Redis client with connection pool.

        Returns:
            Redis async client
        """
        if cls._redis_client is None:
            settings = get_settings()
            redis_url = str(settings.redis_url)
            cls._redis_pool = redis.ConnectionPool.from_url(
                redis_url,
                decode_responses=True,
                max_connections=10,
            )
            cls._redis_client = redis.Redis(connection_pool=cls._redis_pool)
            logger.info(f"Initialized Redis connection pool for AI previews: {redis_url}")
        return cls._redis_client

    @classmethod
    async def store_preview(
        cls,
        user_id: str,
        preview_data: dict[str, Any],
    ) -> str:
        """Store a scenario preview.

        Args:
            user_id: User ID who owns the preview
            preview_data: Preview data including devices, flows, etc.

        Returns:
            Preview ID
        """
        client = await cls.get_client()
        preview_id = str(uuid4())
        created_at = datetime.utcnow().isoformat()

        data = {
            "id": preview_id,
            "user_id": user_id,
            "created_at": created_at,
            **preview_data,
        }

        key = f"{PREVIEW_PREFIX}{preview_id}"
        await client.setex(key, PREVIEW_TTL_SECONDS, json.dumps(data))

        logger.info(f"Stored AI scenario preview {preview_id} for user {user_id}")
        return preview_id

    @classmethod
    async def get_preview(
        cls,
        preview_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Get preview by ID, validating ownership.

        Args:
            preview_id: Preview UUID
            user_id: User ID to validate ownership

        Returns:
            Preview data or None if not found/not authorized
        """
        client = await cls.get_client()
        key = f"{PREVIEW_PREFIX}{preview_id}"
        data = await client.get(key)

        if data is None:
            return None

        preview = json.loads(data)

        # Validate ownership
        if preview.get("user_id") != user_id:
            logger.warning(
                f"User {user_id} attempted to access preview {preview_id} "
                f"owned by {preview.get('user_id')}"
            )
            return None

        return preview

    @classmethod
    async def delete_preview(cls, preview_id: str) -> bool:
        """Delete a preview (typically after creating scenario from it).

        Args:
            preview_id: Preview UUID

        Returns:
            True if deleted
        """
        client = await cls.get_client()
        key = f"{PREVIEW_PREFIX}{preview_id}"
        deleted = await client.delete(key)
        if deleted:
            logger.info(f"Deleted AI scenario preview {preview_id}")
        return bool(deleted)

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection pool."""
        if cls._redis_client:
            await cls._redis_client.close()
            cls._redis_client = None
        if cls._redis_pool:
            await cls._redis_pool.disconnect()
            cls._redis_pool = None
            logger.info("Closed Redis connection pool for AI previews")
