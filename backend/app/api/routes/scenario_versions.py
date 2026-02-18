"""Scenario version routes for version history, diff, and rollback."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import delete as sql_delete, func, select

from app.api.deps import CurrentUser, DBSession
from app.api.helpers import get_or_404_where, paginate
from app.core.exceptions import NotFoundError, ValidationError
from app.models.scenario import Scenario
from app.models.scenario_version import ScenarioVersion
from app.schemas.scenario_version import (
    CreateVersionRequest,
    DiffEntry,
    DiffSummaryResponse,
    RollbackResponse,
    UpdateVersionRequest,
    VersionDetail,
    VersionDiffResponse,
    VersionListResponse,
    VersionSummary,
)
from app.services.scenario_diff import compute_definition_diff

router = APIRouter(
    prefix="/scenarios/{scenario_id}/versions",
    tags=["Scenario Versions"],
)

MAX_VERSIONS_PER_SCENARIO = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_scenario_for_user(
    db: DBSession, scenario_id: uuid.UUID, user_id: uuid.UUID
) -> Scenario:
    """Fetch a scenario owned by the current user or raise NotFoundError."""
    return await get_or_404_where(
        db, Scenario,
        Scenario.id == scenario_id,
        Scenario.user_id == user_id,
        resource_name="Scenario",
        identifier=str(scenario_id),
    )


async def _next_version_number(
    db: DBSession, scenario_id: uuid.UUID
) -> int:
    """Get the next version number for a scenario."""
    result = await db.execute(
        select(func.max(ScenarioVersion.version_number)).where(
            ScenarioVersion.scenario_id == scenario_id
        )
    )
    max_num = result.scalar()
    return (max_num or 0) + 1


async def _prune_old_versions(
    db: DBSession, scenario_id: uuid.UUID
) -> None:
    """Delete oldest versions if count exceeds MAX_VERSIONS_PER_SCENARIO."""
    count_result = await db.execute(
        select(func.count(ScenarioVersion.id)).where(
            ScenarioVersion.scenario_id == scenario_id
        )
    )
    total = count_result.scalar() or 0

    if total > MAX_VERSIONS_PER_SCENARIO:
        excess = total - MAX_VERSIONS_PER_SCENARIO
        oldest = await db.execute(
            select(ScenarioVersion.id)
            .where(ScenarioVersion.scenario_id == scenario_id)
            .order_by(ScenarioVersion.version_number.asc())
            .limit(excess)
        )
        ids_to_delete = [row[0] for row in oldest.all()]

        if ids_to_delete:
            await db.execute(
                sql_delete(ScenarioVersion).where(
                    ScenarioVersion.id.in_(ids_to_delete)
                )
            )


async def create_version_snapshot(
    db: DBSession,
    scenario: Scenario,
    source: str,
    user_id: uuid.UUID | None,
    label: str | None = None,
) -> ScenarioVersion:
    """Create a version snapshot from the current scenario state.

    Args:
        db: Database session.
        scenario: The scenario to snapshot.
        source: Version source ("manual", "auto", "rollback").
        user_id: The user who triggered the version creation.
        label: Optional user-provided label.

    Returns:
        The newly created ScenarioVersion.
    """
    next_num = await _next_version_number(db, scenario.id)

    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    version = ScenarioVersion(
        scenario_id=scenario.id,
        version_number=next_num,
        name=scenario.name,
        description=scenario.description,
        definition=scenario.definition,
        addressing_config=scenario.addressing_config,
        total_duration_ms=scenario.total_duration_ms,
        source=source,
        label=label,
        device_count=len(devices),
        flow_count=len(flows),
        created_by=user_id,
    )
    db.add(version)
    await db.flush()

    # Auto-prune
    await _prune_old_versions(db, scenario.id)

    return version


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=VersionListResponse)
async def list_versions(
    scenario_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> VersionListResponse:
    """List version history for a scenario (newest first)."""
    await _get_scenario_for_user(db, scenario_id, current_user.id)

    query = (
        select(ScenarioVersion)
        .where(ScenarioVersion.scenario_id == scenario_id)
        .order_by(ScenarioVersion.version_number.desc())
    )
    versions, total = await paginate(db, query, page, page_size)

    return VersionListResponse(
        items=[VersionSummary.model_validate(v) for v in versions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=VersionSummary, status_code=201)
async def create_version(
    scenario_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    request: CreateVersionRequest | None = None,
) -> VersionSummary:
    """Create an explicit version snapshot of the current scenario state."""
    scenario = await _get_scenario_for_user(db, scenario_id, current_user.id)

    label = request.label if request else None
    version = await create_version_snapshot(
        db, scenario, source="manual", user_id=current_user.id, label=label
    )

    await db.commit()
    await db.refresh(version)

    return VersionSummary.model_validate(version)


@router.get("/diff", response_model=VersionDiffResponse)
async def diff_versions(
    scenario_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    base: int = Query(..., description="Base version number"),
    compare: int = Query(..., description="Compare version number"),
) -> VersionDiffResponse:
    """Compute a structured diff between two versions."""
    await _get_scenario_for_user(db, scenario_id, current_user.id)

    base_version = await get_or_404_where(
        db, ScenarioVersion,
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version_number == base,
        resource_name="Version",
        identifier=str(base),
    )
    compare_version = await get_or_404_where(
        db, ScenarioVersion,
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version_number == compare,
        resource_name="Version",
        identifier=str(compare),
    )

    # Compute diff
    base_meta = {
        "name": base_version.name,
        "description": base_version.description,
        "total_duration_ms": base_version.total_duration_ms,
    }
    compare_meta = {
        "name": compare_version.name,
        "description": compare_version.description,
        "total_duration_ms": compare_version.total_duration_ms,
    }

    changes, summary = compute_definition_diff(
        base_version.definition or {},
        compare_version.definition or {},
        base_meta,
        compare_meta,
    )

    return VersionDiffResponse(
        scenario_id=scenario_id,
        base_version=base,
        compare_version=compare,
        changes=[DiffEntry(**c) for c in changes],
        summary=summary,
    )


@router.post("/diff-summary", response_model=DiffSummaryResponse)
async def summarize_diff(
    scenario_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    base: int = Query(..., description="Base version number"),
    compare: int = Query(..., description="Compare version number"),
) -> DiffSummaryResponse:
    """Generate an AI plain-English summary of changes between two versions."""
    from app.api.routes.ai_help import _extract_response_text, _get_ai_provider

    await _get_scenario_for_user(db, scenario_id, current_user.id)

    base_version = await get_or_404_where(
        db, ScenarioVersion,
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version_number == base,
        resource_name="Version",
        identifier=str(base),
    )
    compare_version = await get_or_404_where(
        db, ScenarioVersion,
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version_number == compare,
        resource_name="Version",
        identifier=str(compare),
    )

    base_meta = {
        "name": base_version.name,
        "description": base_version.description,
        "total_duration_ms": base_version.total_duration_ms,
    }
    compare_meta = {
        "name": compare_version.name,
        "description": compare_version.description,
        "total_duration_ms": compare_version.total_duration_ms,
    }

    changes, summary = compute_definition_diff(
        base_version.definition or {},
        compare_version.definition or {},
        base_meta,
        compare_meta,
    )

    if not changes:
        return DiffSummaryResponse(summary="No changes between these versions.")

    # Serialize changes to a compact representation for the AI
    import json

    changes_text = json.dumps(changes, indent=None, default=str)

    messages = [
        {
            "role": "system",
            "content": (
                "You summarize OT network scenario changes as a concise plain-English changelog. "
                "Output 2-5 bullet points using markdown. Each bullet should describe what changed "
                "and why it matters. Use device names and protocol names when available. "
                "Do not repeat the raw field names — translate them into human-readable descriptions."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Summarize these changes between version {base} and version {compare}:\n\n"
                f"Summary: {summary}\n\n"
                f"Changes:\n{changes_text}"
            ),
        },
    ]

    provider = await _get_ai_provider(db)
    response = await provider.chat(messages=messages, max_tokens=1024)
    result = _extract_response_text(response)

    if not result:
        result = f"{summary.get('added', 0)} added, {summary.get('removed', 0)} removed, {summary.get('modified', 0)} modified."

    return DiffSummaryResponse(summary=result)


@router.get("/{version_id}", response_model=VersionDetail)
async def get_version(
    scenario_id: uuid.UUID,
    version_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> VersionDetail:
    """Get full version detail including definition."""
    await _get_scenario_for_user(db, scenario_id, current_user.id)

    version = await get_or_404_where(
        db, ScenarioVersion,
        ScenarioVersion.id == version_id,
        ScenarioVersion.scenario_id == scenario_id,
        resource_name="Version",
        identifier=str(version_id),
    )
    return VersionDetail.model_validate(version)


@router.patch("/{version_id}", response_model=VersionSummary)
async def update_version_label(
    scenario_id: uuid.UUID,
    version_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    request: UpdateVersionRequest,
) -> VersionSummary:
    """Update a version's label."""
    await _get_scenario_for_user(db, scenario_id, current_user.id)

    version = await get_or_404_where(
        db, ScenarioVersion,
        ScenarioVersion.id == version_id,
        ScenarioVersion.scenario_id == scenario_id,
        resource_name="Version",
        identifier=str(version_id),
    )

    version.label = request.label
    await db.commit()
    await db.refresh(version)

    return VersionSummary.model_validate(version)


@router.delete("/{version_id}")
async def delete_version(
    scenario_id: uuid.UUID,
    version_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Delete a single version."""
    await _get_scenario_for_user(db, scenario_id, current_user.id)

    version = await get_or_404_where(
        db, ScenarioVersion,
        ScenarioVersion.id == version_id,
        ScenarioVersion.scenario_id == scenario_id,
        resource_name="Version",
        identifier=str(version_id),
    )

    await db.delete(version)
    await db.commit()

    return {"message": f"Version {version.version_number} deleted"}


@router.post("/rollback", response_model=RollbackResponse)
async def rollback_to_version(
    scenario_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    version: int = Query(..., description="Version number to rollback to"),
) -> RollbackResponse:
    """Rollback a scenario to a previous version.

    Creates a safety snapshot of the current state before restoring.
    """
    scenario = await _get_scenario_for_user(db, scenario_id, current_user.id)

    target_version = await get_or_404_where(
        db, ScenarioVersion,
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version_number == version,
        resource_name="Version",
        identifier=str(version),
    )

    # Create safety snapshot of current state
    await create_version_snapshot(
        db,
        scenario,
        source="rollback",
        user_id=current_user.id,
        label=f"Before rollback to v{version}",
    )

    # Restore scenario to target version state
    scenario.name = target_version.name
    scenario.description = target_version.description
    scenario.definition = target_version.definition
    scenario.addressing_config = target_version.addressing_config
    scenario.total_duration_ms = target_version.total_duration_ms
    scenario.version += 1
    scenario.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Get the new version number (safety snapshot number)
    latest_result = await db.execute(
        select(func.max(ScenarioVersion.version_number)).where(
            ScenarioVersion.scenario_id == scenario_id
        )
    )
    new_version_number = latest_result.scalar() or 0

    return RollbackResponse(
        scenario_id=scenario_id,
        rolled_back_to_version=version,
        new_version_number=new_version_number,
        message=f"Scenario restored to version {version}. A backup was saved as v{new_version_number}.",
    )
