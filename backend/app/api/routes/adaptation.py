"""REST API endpoints for adaptive traffic management."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.services.adaptation_service import adaptation_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/adaptation", tags=["adaptation"])


class DirectiveRequest(BaseModel):
    """Request body for sending adaptation directives."""

    directives: list[dict[str, Any]] = Field(
        ...,
        description="List of directives to send",
        min_length=1,
    )
    ttl_seconds: int = Field(
        300,
        description="Time-to-live for directives in seconds",
        ge=0,
        le=86400,
    )


class ScheduleOverrideRequest(BaseModel):
    """Request body for schedule phase override."""

    phase_name: str = Field(..., description="Phase name to force")


class ProtocolRateRequest(BaseModel):
    """Request body for protocol rate adjustment."""

    protocol: str = Field(..., description="Protocol name (e.g. 'modbus_tcp')")
    multiplier: float = Field(..., description="Rate multiplier (>1 = more traffic)", gt=0.0, le=10.0)
    reason: str = Field("", description="Human-readable reason")
    ttl_seconds: int = Field(300, ge=0, le=86400)


class ForcePhaseRequest(BaseModel):
    """Request body for forcing a deployment phase."""

    phase_id: str = Field(..., description="Phase ID to force (e.g. 'steady_state')")


class PhasePauseRequest(BaseModel):
    """Request body for pausing/resuming phase cycling."""

    paused: bool = Field(..., description="True to pause, False to resume")


@router.post("/{scenario_id}/directives")
async def send_directives(scenario_id: str, request: DirectiveRequest, _user: CurrentUser) -> dict[str, Any]:
    """Send adaptation directives to a running scenario.

    Directives adjust traffic behavior mid-deployment without restarting.

    Directive types:
    - `adjust_protocol_rate`: Change traffic rate for a protocol
    - `adjust_flow_rate`: Change traffic rate for a specific flow
    - `set_schedule_phase`: Force a specific schedule phase
    - `reset_adaptations`: Clear all active directives
    """
    success = await adaptation_service.send_directives(
        scenario_id,
        request.directives,
        request.ttl_seconds,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {"status": "ok", "directives_sent": len(request.directives)}


@router.get("/{scenario_id}/state")
async def get_adaptation_state(scenario_id: str, _user: CurrentUser) -> dict[str, Any]:
    """Get current adaptation state for a running scenario."""
    state = adaptation_service.get_adaptation_state(scenario_id)
    if state is None:
        return {"enabled": False, "message": "No adaptation data available"}
    return state


@router.post("/{scenario_id}/schedule-override")
async def set_schedule_override(
    scenario_id: str, request: ScheduleOverrideRequest, _user: CurrentUser,
) -> dict[str, Any]:
    """Override the traffic schedule phase for a running scenario.

    Forces the scenario into a specific schedule phase regardless of
    the current time of day. Useful for demos where you want to show
    specific traffic patterns on demand.
    """
    success = await adaptation_service.set_schedule_override(
        scenario_id, request.phase_name,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {"status": "ok", "phase": request.phase_name}


@router.post("/{scenario_id}/protocol-rate")
async def adjust_protocol_rate(
    scenario_id: str, request: ProtocolRateRequest, _user: CurrentUser,
) -> dict[str, Any]:
    """Adjust traffic rate for a specific protocol.

    Multiplier > 1.0 increases traffic (shorter poll intervals).
    Multiplier < 1.0 decreases traffic (longer poll intervals).
    """
    success = await adaptation_service.adjust_protocol_rate(
        scenario_id,
        request.protocol,
        request.multiplier,
        request.reason,
        request.ttl_seconds,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {
        "status": "ok",
        "protocol": request.protocol,
        "multiplier": request.multiplier,
    }


@router.delete("/{scenario_id}/directives")
async def clear_directives(scenario_id: str, _user: CurrentUser) -> dict[str, Any]:
    """Clear all active adaptation directives for a running scenario.

    Resets traffic to default behavior (schedule + micro-variations only).
    """
    success = await adaptation_service.clear_directives(scenario_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {"status": "ok", "message": "All directives cleared"}


# ------------------------------------------------------------------
# Deployment phase control
# ------------------------------------------------------------------


@router.post("/{scenario_id}/phase/skip")
async def skip_to_next_phase(scenario_id: str, _user: CurrentUser) -> dict[str, Any]:
    """Skip to the next deployment phase.

    Immediately advances the phase scheduler to the next phase in sequence.
    """
    success = await adaptation_service.skip_phase(scenario_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {"status": "ok", "message": "Skipped to next phase"}


@router.post("/{scenario_id}/phase/force")
async def force_phase(
    scenario_id: str, request: ForcePhaseRequest, _user: CurrentUser,
) -> dict[str, Any]:
    """Force a specific deployment phase.

    Overrides the phase scheduler to run a specific phase regardless
    of elapsed time. The override is cleared when skip is called.
    """
    success = await adaptation_service.force_phase(scenario_id, request.phase_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    return {"status": "ok", "phase_id": request.phase_id}


@router.post("/{scenario_id}/phase/pause")
async def toggle_phase_cycling(
    scenario_id: str, request: PhasePauseRequest, _user: CurrentUser,
) -> dict[str, Any]:
    """Pause or resume deployment phase cycling.

    When paused, the current phase continues indefinitely until
    resumed or a skip/force is issued.
    """
    success = await adaptation_service.toggle_phase_pause(
        scenario_id, request.paused,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for scenario {scenario_id}",
        )
    action = "paused" if request.paused else "resumed"
    return {"status": "ok", "message": f"Phase cycling {action}"}
