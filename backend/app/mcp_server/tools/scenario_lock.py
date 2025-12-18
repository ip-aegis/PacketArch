"""Safe scenario update utility with optimistic locking.

This module provides a wrapper for safely updating scenario definitions
with proper concurrency handling to prevent lost updates from SQLAlchemy
session caching issues.
"""

import copy
import json
import uuid
from typing import Any, Callable, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario

T = TypeVar("T")


async def safe_update_scenario(
    db: AsyncSession,
    scenario_id: str,
    update_fn: Callable[[dict], T],
) -> tuple[Scenario | None, T | dict]:
    """Safely update scenario definition with optimistic locking.

    This function handles the common pattern of:
    1. Fetching a scenario
    2. Refreshing to get latest DB state (avoids stale session cache)
    3. Deep copying the definition to prevent mutation issues
    4. Applying an update function
    5. Saving with version increment

    Args:
        db: Database session
        scenario_id: Scenario UUID string
        update_fn: Function that takes definition dict and returns result data.
                   The function should modify the definition dict in place.

    Returns:
        Tuple of (scenario, result_data) where:
        - scenario is the updated Scenario object (or None if not found)
        - result_data is whatever the update_fn returned (or error dict)

    Example:
        def add_my_device(definition: dict) -> dict:
            devices = definition.setdefault("devices", {})
            device_id = "device_123"
            devices[device_id] = {"id": device_id, "name": "My Device"}
            return {"success": True, "device_id": device_id}

        scenario, result = await safe_update_scenario(db, scenario_id, add_my_device)
    """
    # Fetch scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return None, {"error": "Scenario not found"}

    # Refresh to get latest state from DB (critical for avoiding stale cache)
    await db.refresh(scenario)

    # Deep copy to prevent any mutation issues with nested dicts
    definition = copy.deepcopy(scenario.definition)

    # Apply the update function
    result_data = update_fn(definition)

    # Check if update_fn indicated an error (convention: return dict with "error" key)
    if isinstance(result_data, dict) and "error" in result_data:
        # Don't commit, just return the error
        return scenario, result_data

    # Save the updated definition
    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return scenario, result_data


async def get_scenario_device_count(db: AsyncSession, scenario_id: str) -> int:
    """Get current device count for a scenario.

    Useful for pre-checking limits before operations.

    Args:
        db: Database session
        scenario_id: Scenario UUID string

    Returns:
        Number of devices, or 0 if scenario not found
    """
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return 0

    await db.refresh(scenario)
    devices = scenario.definition.get("devices", {})
    return len(devices)


async def get_scenario_flow_count(db: AsyncSession, scenario_id: str) -> int:
    """Get current flow count for a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID string

    Returns:
        Number of flows, or 0 if scenario not found
    """
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return 0

    await db.refresh(scenario)
    flows = scenario.definition.get("flows", {})
    return len(flows)
