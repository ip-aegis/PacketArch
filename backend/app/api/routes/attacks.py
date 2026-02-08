"""REST API endpoints for live attack simulation."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.attack import (
    AttackPlaybookOut,
    AttackPlaybookSummary,
    AttackStateResponse,
    PauseAttackRequest,
    StartAttackRequest,
)
from app.services.attack_service import attack_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attacks", tags=["attacks"])


# ------------------------------------------------------------------
# Playbook library
# ------------------------------------------------------------------


@router.get("/playbooks", response_model=list[AttackPlaybookSummary])
async def list_playbooks() -> list[dict[str, Any]]:
    """List all available attack playbooks.

    Returns abbreviated summaries suitable for a card grid UI.
    """
    playbooks = attack_service.get_all_playbooks()
    summaries = []
    for p in playbooks:
        summaries.append({
            "playbook_id": p["playbook_id"],
            "name": p["name"],
            "description": p["description"],
            "severity": p["severity"],
            "category": p["category"],
            "stage_count": len(p.get("stages", [])),
            "total_duration_seconds": p.get("total_duration_seconds", 0),
            "required_protocols": p.get("required_protocols", []),
            "industry_verticals": p.get("industry_verticals", []),
            "mitre_software_id": p.get("mitre_software_id", ""),
        })
    return summaries


@router.get("/playbooks/{playbook_id}", response_model=AttackPlaybookOut)
async def get_playbook(playbook_id: str) -> dict[str, Any]:
    """Get full playbook details including stages and actions."""
    playbook = attack_service.get_playbook_by_id(playbook_id)
    if not playbook:
        raise HTTPException(status_code=404, detail=f"Playbook '{playbook_id}' not found")
    return playbook


@router.get(
    "/playbooks/compatible/{scenario_id}",
    response_model=list[AttackPlaybookSummary],
)
async def get_compatible_playbooks(scenario_id: str) -> list[dict[str, Any]]:
    """List playbooks compatible with a scenario's protocols.

    Inspects the scenario's flows to determine which protocols are in use,
    then returns playbooks whose required_protocols overlap.
    """
    from app.core.database import async_session_maker
    from app.models.scenario import Scenario
    from sqlalchemy import select
    from uuid import UUID

    try:
        scenario_uuid = UUID(scenario_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario_id format")

    async with async_session_maker() as db:
        result = await db.execute(
            select(Scenario).where(Scenario.id == scenario_uuid)
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        # Extract protocols from flows
        definition = scenario.definition or {}
        flows = definition.get("flows", {})
        if isinstance(flows, list):
            protocols = list({f.get("protocol", "") for f in flows if f.get("protocol")})
        elif isinstance(flows, dict):
            protocols = list({f.get("protocol", "") for f in flows.values() if f.get("protocol")})
        else:
            protocols = []

    compatible = attack_service.get_compatible_playbooks(protocols)
    summaries = []
    for p in compatible:
        summaries.append({
            "playbook_id": p["playbook_id"],
            "name": p["name"],
            "description": p["description"],
            "severity": p["severity"],
            "category": p["category"],
            "stage_count": len(p.get("stages", [])),
            "total_duration_seconds": p.get("total_duration_seconds", 0),
            "required_protocols": p.get("required_protocols", []),
            "industry_verticals": p.get("industry_verticals", []),
            "mitre_software_id": p.get("mitre_software_id", ""),
        })
    return summaries


# ------------------------------------------------------------------
# Attack runtime control
# ------------------------------------------------------------------


@router.post("/{scenario_id}/start")
async def start_attack(scenario_id: str, request: StartAttackRequest) -> dict[str, Any]:
    """Start an attack playbook on a deployed scenario.

    The playbook must be configured in the scenario's definition
    (attack_playbook field) before deployment. This command triggers
    the attack orchestrator on the agent.
    """
    success = await attack_service.start_attack(scenario_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {"status": "ok", "playbook_id": request.playbook_id}


@router.post("/{scenario_id}/stop")
async def stop_attack(scenario_id: str) -> dict[str, Any]:
    """Stop the running attack playbook."""
    success = await attack_service.stop_attack(scenario_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {"status": "ok", "message": "Attack stopped"}


@router.post("/{scenario_id}/advance")
async def advance_stage(scenario_id: str) -> dict[str, Any]:
    """Advance to the next kill-chain stage."""
    success = await attack_service.advance_stage(scenario_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {"status": "ok", "message": "Advanced to next stage"}


@router.post("/{scenario_id}/pause")
async def pause_attack(
    scenario_id: str, request: PauseAttackRequest,
) -> dict[str, Any]:
    """Pause or resume the attack playbook."""
    success = await attack_service.pause_attack(scenario_id, request.paused)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    action = "paused" if request.paused else "resumed"
    return {"status": "ok", "message": f"Attack {action}"}


@router.get("/{scenario_id}/state", response_model=AttackStateResponse)
async def get_attack_state(scenario_id: str) -> dict[str, Any]:
    """Get current attack state for a running scenario."""
    state = attack_service.get_attack_state(scenario_id)
    if state is None:
        return {
            "is_active": False,
            "message": "No attack data available",
        }
    return state
