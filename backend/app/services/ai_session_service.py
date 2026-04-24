# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""AI Session Service using Redis for persistent storage.

This service manages AI assistant sessions with Redis backend,
enabling session persistence across server restarts and
supporting distributed deployments.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Session TTL: 24 hours
SESSION_TTL_SECONDS = 86400

# Redis key prefixes
SESSION_PREFIX = "ai_session:"
SCENARIO_SESSION_PREFIX = "ai_session_scenario:"  # Format: ai_session_scenario:{user_id}:{scenario_id}
PENDING_ACTION_PREFIX = "ai_pending_action:"


class AISessionService:
    """Service for managing AI assistant sessions in Redis."""

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
            logger.info(f"Initialized Redis connection pool for AI sessions: {redis_url}")
        return cls._redis_client

    @classmethod
    async def create_session(cls, user_id: str) -> dict[str, Any]:
        """Create a new AI session.

        Args:
            user_id: User ID who owns the session

        Returns:
            Session data including session_id and created_at
        """
        client = await cls.get_client()
        session_id = str(uuid4())
        created_at = datetime.utcnow().isoformat()

        session_data = {
            "id": session_id,
            "user_id": user_id,
            "messages": [],
            "created_at": created_at,
            "sanitizer_mappings": {},
        }

        key = f"{SESSION_PREFIX}{session_id}"
        await client.setex(
            key,
            SESSION_TTL_SECONDS,
            json.dumps(session_data),
        )

        logger.info(f"Created AI session {session_id} for user {user_id}")
        return session_data

    @classmethod
    async def get_session(cls, session_id: str) -> dict[str, Any] | None:
        """Get session by ID.

        Args:
            session_id: Session UUID

        Returns:
            Session data or None if not found
        """
        client = await cls.get_client()
        key = f"{SESSION_PREFIX}{session_id}"
        data = await client.get(key)

        if data is None:
            return None

        return json.loads(data)

    @classmethod
    async def update_session(
        cls,
        session_id: str,
        messages: list[dict] | None = None,
        sanitizer_mappings: dict | None = None,
    ) -> bool:
        """Update session data.

        Args:
            session_id: Session UUID
            messages: Updated messages list (optional)
            sanitizer_mappings: Updated sanitizer mappings (optional)

        Returns:
            True if updated, False if session not found
        """
        client = await cls.get_client()
        key = f"{SESSION_PREFIX}{session_id}"

        # Get existing session
        data = await client.get(key)
        if data is None:
            return False

        session = json.loads(data)

        # Update fields if provided
        if messages is not None:
            session["messages"] = messages
        if sanitizer_mappings is not None:
            session["sanitizer_mappings"] = sanitizer_mappings

        # Save back with refreshed TTL
        await client.setex(key, SESSION_TTL_SECONDS, json.dumps(session))
        return True

    @classmethod
    async def append_message(cls, session_id: str, message: dict) -> bool:
        """Append a message to session history.

        Args:
            session_id: Session UUID
            message: Message dict with role and content

        Returns:
            True if appended, False if session not found
        """
        session = await cls.get_session(session_id)
        if session is None:
            return False

        session["messages"].append(message)
        return await cls.update_session(session_id, messages=session["messages"])

    @classmethod
    async def delete_session(cls, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session UUID

        Returns:
            True if deleted, False if not found
        """
        client = await cls.get_client()
        key = f"{SESSION_PREFIX}{session_id}"
        deleted = await client.delete(key)
        if deleted:
            logger.info(f"Deleted AI session {session_id}")
        return bool(deleted)

    @classmethod
    async def validate_session(cls, session_id: str, user_id: str) -> dict[str, Any] | None:
        """Validate session exists and belongs to user.

        Args:
            session_id: Session UUID
            user_id: User ID to validate ownership

        Returns:
            Session data if valid, None if invalid
        """
        session = await cls.get_session(session_id)
        if session is None:
            return None
        if session.get("user_id") != user_id:
            return None
        return session

    # ==================== Scenario-Scoped Sessions ====================
    # These methods manage AI sessions that persist per user+scenario combination.
    # Unlike regular sessions that are deleted on panel close, these persist
    # until explicitly cleared or TTL expires.

    @classmethod
    def _get_scenario_session_key(cls, user_id: str, scenario_id: str) -> str:
        """Get Redis key for a scenario-scoped session.

        Args:
            user_id: User ID
            scenario_id: Scenario UUID

        Returns:
            Redis key string
        """
        return f"{SCENARIO_SESSION_PREFIX}{user_id}:{scenario_id}"

    @classmethod
    async def get_session_for_scenario(
        cls, user_id: str, scenario_id: str
    ) -> dict[str, Any] | None:
        """Get existing session for a specific scenario.

        Args:
            user_id: User ID
            scenario_id: Scenario UUID

        Returns:
            Session data if exists, None otherwise
        """
        client = await cls.get_client()
        key = cls._get_scenario_session_key(user_id, scenario_id)
        data = await client.get(key)

        if data is None:
            return None

        return json.loads(data)

    @classmethod
    async def get_or_create_session_for_scenario(
        cls, user_id: str, scenario_id: str
    ) -> dict[str, Any]:
        """Get existing session for scenario or create new one.

        This is the primary method for opening the AI panel in Scenario Studio.
        It ensures conversation history persists across page refreshes.

        Args:
            user_id: User ID
            scenario_id: Scenario UUID

        Returns:
            Session data (existing or newly created)
        """
        # Check for existing session
        existing = await cls.get_session_for_scenario(user_id, scenario_id)
        if existing is not None:
            # Refresh TTL on access
            client = await cls.get_client()
            key = cls._get_scenario_session_key(user_id, scenario_id)
            await client.expire(key, SESSION_TTL_SECONDS)
            logger.info(f"Resumed AI session for scenario {scenario_id} (user {user_id})")
            return existing

        # Create new session
        client = await cls.get_client()
        session_id = str(uuid4())
        created_at = datetime.utcnow().isoformat()

        session_data = {
            "id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "messages": [],
            "created_at": created_at,
            "sanitizer_mappings": {},
        }

        key = cls._get_scenario_session_key(user_id, scenario_id)
        await client.setex(
            key,
            SESSION_TTL_SECONDS,
            json.dumps(session_data),
        )

        logger.info(f"Created new AI session {session_id} for scenario {scenario_id} (user {user_id})")
        return session_data

    @classmethod
    async def update_session_for_scenario(
        cls,
        user_id: str,
        scenario_id: str,
        messages: list[dict] | None = None,
        sanitizer_mappings: dict | None = None,
    ) -> bool:
        """Update a scenario-scoped session.

        Args:
            user_id: User ID
            scenario_id: Scenario UUID
            messages: Updated messages list (optional)
            sanitizer_mappings: Updated sanitizer mappings (optional)

        Returns:
            True if updated, False if session not found
        """
        client = await cls.get_client()
        key = cls._get_scenario_session_key(user_id, scenario_id)

        data = await client.get(key)
        if data is None:
            return False

        session = json.loads(data)

        if messages is not None:
            session["messages"] = messages
        if sanitizer_mappings is not None:
            session["sanitizer_mappings"] = sanitizer_mappings

        await client.setex(key, SESSION_TTL_SECONDS, json.dumps(session))
        return True

    @classmethod
    async def append_message_for_scenario(
        cls, user_id: str, scenario_id: str, message: dict
    ) -> bool:
        """Append a message to a scenario-scoped session.

        Args:
            user_id: User ID
            scenario_id: Scenario UUID
            message: Message dict with role and content

        Returns:
            True if appended, False if session not found
        """
        session = await cls.get_session_for_scenario(user_id, scenario_id)
        if session is None:
            return False

        session["messages"].append(message)
        return await cls.update_session_for_scenario(
            user_id, scenario_id, messages=session["messages"]
        )

    @classmethod
    async def delete_session_for_scenario(cls, user_id: str, scenario_id: str) -> bool:
        """Delete a scenario-scoped session (clear conversation).

        Args:
            user_id: User ID
            scenario_id: Scenario UUID

        Returns:
            True if deleted, False if not found
        """
        client = await cls.get_client()
        key = cls._get_scenario_session_key(user_id, scenario_id)
        deleted = await client.delete(key)
        if deleted:
            logger.info(f"Cleared AI conversation for scenario {scenario_id} (user {user_id})")
        return bool(deleted)

    @classmethod
    async def refresh_ttl(cls, session_id: str) -> bool:
        """Refresh session TTL.

        Args:
            session_id: Session UUID

        Returns:
            True if refreshed, False if not found
        """
        client = await cls.get_client()
        key = f"{SESSION_PREFIX}{session_id}"
        return bool(await client.expire(key, SESSION_TTL_SECONDS))

    # Pending Actions Management

    @classmethod
    async def store_pending_action(
        cls,
        action_id: str,
        user_id: str,
        session_id: str,
        action_type: str,
        params: dict,
        description: str,
    ) -> dict[str, Any]:
        """Store a pending action for user approval.

        Args:
            action_id: Unique action ID
            user_id: User who will approve/reject
            session_id: Associated session ID
            action_type: Type of action (tool name)
            params: Action parameters
            description: Human-readable description

        Returns:
            Pending action data
        """
        client = await cls.get_client()

        action_data = {
            "id": action_id,
            "user_id": user_id,
            "session_id": session_id,
            "action_type": action_type,
            "params": params,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
        }

        key = f"{PENDING_ACTION_PREFIX}{action_id}"
        # Pending actions expire after 1 hour
        await client.setex(key, 3600, json.dumps(action_data))
        return action_data

    @classmethod
    async def get_pending_action(cls, action_id: str) -> dict[str, Any] | None:
        """Get pending action by ID.

        Args:
            action_id: Action UUID

        Returns:
            Action data or None if not found/expired
        """
        client = await cls.get_client()
        key = f"{PENDING_ACTION_PREFIX}{action_id}"
        data = await client.get(key)
        return json.loads(data) if data else None

    @classmethod
    async def delete_pending_action(cls, action_id: str) -> bool:
        """Delete a pending action (after accept/reject).

        Args:
            action_id: Action UUID

        Returns:
            True if deleted
        """
        client = await cls.get_client()
        key = f"{PENDING_ACTION_PREFIX}{action_id}"
        return bool(await client.delete(key))

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection pool."""
        if cls._redis_client:
            await cls._redis_client.close()
            cls._redis_client = None
        if cls._redis_pool:
            await cls._redis_pool.disconnect()
            cls._redis_pool = None
            logger.info("Closed Redis connection pool for AI sessions")
