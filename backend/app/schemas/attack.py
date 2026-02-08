"""Pydantic schemas for attack simulation API."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class AttackActionOut(BaseModel):
    """Attack action response schema."""

    action_id: str
    name: str
    action_type: str
    parameters: dict[str, Any] = {}
    target_selector: str = "any"
    mitre_technique: str = ""
    description: str = ""
    expected_cv_detection: str = ""
    repeat_count: int = 1


class KillChainStageOut(BaseModel):
    """Kill-chain stage response schema."""

    stage_id: str
    name: str
    duration_seconds: int = 300
    actions: list[AttackActionOut] = []
    color: str = "#ff4d4f"
    description: str = ""
    expected_cv_alerts: list[str] = []
    mitre_tactics: list[str] = []


class AttackPlaybookOut(BaseModel):
    """Attack playbook response schema."""

    playbook_id: str
    name: str
    description: str = ""
    mitre_software_id: str = ""
    severity: str = "high"
    category: str = "apt"
    stages: list[KillChainStageOut] = []
    required_protocols: list[str] = []
    industry_verticals: list[str] = []
    reference_url: str = ""
    total_duration_seconds: int = 0


class AttackPlaybookSummary(BaseModel):
    """Abbreviated playbook info for list endpoints."""

    playbook_id: str
    name: str
    description: str = ""
    severity: str = "high"
    category: str = "apt"
    stage_count: int = 0
    total_duration_seconds: int = 0
    required_protocols: list[str] = []
    industry_verticals: list[str] = []
    mitre_software_id: str = ""


class StartAttackRequest(BaseModel):
    """Request body for starting an attack."""

    playbook_id: str = Field(..., description="Playbook ID to execute")


class PauseAttackRequest(BaseModel):
    """Request body for pausing/resuming an attack."""

    paused: bool = Field(..., description="True to pause, False to resume")


class AttackStateResponse(BaseModel):
    """Current attack state response."""

    playbook_id: str = ""
    playbook_name: str = ""
    is_active: bool = False
    is_paused: bool = False
    is_completed: bool = False
    current_stage: str = ""
    current_stage_name: str = ""
    current_stage_color: str = "#ff4d4f"
    current_stage_index: int = 0
    stage_progress_pct: float = 0.0
    stage_remaining_s: float = 0.0
    stages_completed: int = 0
    total_stages: int = 0
    actions_completed: int = 0
    attack_packets_generated: int = 0
