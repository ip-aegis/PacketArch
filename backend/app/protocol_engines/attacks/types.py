# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Data types for the live attack simulation system.

Defines the playbook model: AttackPlaybook → KillChainStage → AttackAction,
plus runtime AttackState for status reporting.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttackAction:
    """A single attack action that generates packets.

    Each action maps to a registered generator in action_registry.py
    via the ``action_type`` key.
    """

    action_id: str
    """Unique within the playbook, e.g. ``recon_port_scan``."""

    name: str
    """Human-readable label, e.g. ``OT Port Scan``."""

    action_type: str
    """Registry key that maps to a packet generator function."""

    parameters: dict[str, Any] = field(default_factory=dict)
    """Action-specific params forwarded to the generator."""

    target_selector: str = "any"
    """Device targeting: ``any``, ``plc``, ``hmi``, ``rtu``, ``ews``, ``relay``."""

    mitre_technique: str = ""
    """MITRE ATT&CK for ICS technique ID, e.g. ``T0846``."""

    description: str = ""

    expected_cv_detection: str = ""
    """What Cisco Cyber Vision should flag when this action runs."""

    repeat_count: int = 1
    """How many times to execute this action within the stage."""

    repeat_interval_ms: int = 0
    """Delay between repeats (ms)."""

    delay_after_ms: int = 0
    """Delay before the next action in the same stage (ms)."""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AttackAction:
        return cls(
            action_id=d.get("action_id", ""),
            name=d.get("name", ""),
            action_type=d.get("action_type", ""),
            parameters=d.get("parameters", {}),
            target_selector=d.get("target_selector", "any"),
            mitre_technique=d.get("mitre_technique", ""),
            description=d.get("description", ""),
            expected_cv_detection=d.get("expected_cv_detection", ""),
            repeat_count=d.get("repeat_count", 1),
            repeat_interval_ms=d.get("repeat_interval_ms", 0),
            delay_after_ms=d.get("delay_after_ms", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "action_type": self.action_type,
            "parameters": self.parameters,
            "target_selector": self.target_selector,
            "mitre_technique": self.mitre_technique,
            "description": self.description,
            "expected_cv_detection": self.expected_cv_detection,
            "repeat_count": self.repeat_count,
            "repeat_interval_ms": self.repeat_interval_ms,
            "delay_after_ms": self.delay_after_ms,
        }


@dataclass
class KillChainStage:
    """A kill-chain stage containing ordered attack actions."""

    stage_id: str
    """Identifier, e.g. ``reconnaissance``, ``initial_access``."""

    name: str
    """Display name, e.g. ``Network Reconnaissance``."""

    duration_seconds: int = 300
    """Default duration when running in live mode."""

    actions: list[AttackAction] = field(default_factory=list)

    color: str = "#ff4d4f"
    """UI timeline segment color."""

    description: str = ""

    expected_cv_alerts: list[str] = field(default_factory=list)
    """Human-readable list of alerts CV should raise during this stage."""

    mitre_tactics: list[str] = field(default_factory=list)
    """MITRE ATT&CK tactic IDs, e.g. ``TA0043`` (Reconnaissance)."""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> KillChainStage:
        actions = [AttackAction.from_dict(a) for a in d.get("actions", [])]
        return cls(
            stage_id=d.get("stage_id", ""),
            name=d.get("name", ""),
            duration_seconds=d.get("duration_seconds", 300),
            actions=actions,
            color=d.get("color", "#ff4d4f"),
            description=d.get("description", ""),
            expected_cv_alerts=d.get("expected_cv_alerts", []),
            mitre_tactics=d.get("mitre_tactics", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "duration_seconds": self.duration_seconds,
            "actions": [a.to_dict() for a in self.actions],
            "color": self.color,
            "description": self.description,
            "expected_cv_alerts": self.expected_cv_alerts,
            "mitre_tactics": self.mitre_tactics,
        }


@dataclass
class AttackPlaybook:
    """A multi-stage attack playbook modeled on real ICS attack campaigns.

    Playbooks are defined as Python dataclasses (not DB models) in
    ``playbooks.py``, following the same pattern as ``PHASE_TEMPLATES``
    and ``BEACON_PATTERNS``.
    """

    playbook_id: str
    """Unique key, e.g. ``triton_like``."""

    name: str
    """Display name, e.g. ``TRITON-like Safety System Attack``."""

    description: str = ""

    mitre_software_id: str = ""
    """MITRE ATT&CK software ID, e.g. ``S0609``."""

    severity: str = "high"
    """``low`` | ``medium`` | ``high`` | ``critical``."""

    category: str = "apt"
    """``apt`` | ``insider`` | ``reconnaissance``."""

    stages: list[KillChainStage] = field(default_factory=list)

    required_protocols: list[str] = field(default_factory=list)
    """Protocols the scenario must have for this playbook to be compatible."""

    industry_verticals: list[str] = field(default_factory=list)
    """Verticals this playbook is designed for."""

    reference_url: str = ""
    """External reference (e.g. MITRE page)."""

    @property
    def total_duration_seconds(self) -> int:
        return sum(s.duration_seconds for s in self.stages)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AttackPlaybook:
        stages = [KillChainStage.from_dict(s) for s in d.get("stages", [])]
        return cls(
            playbook_id=d.get("playbook_id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            mitre_software_id=d.get("mitre_software_id", ""),
            severity=d.get("severity", "high"),
            category=d.get("category", "apt"),
            stages=stages,
            required_protocols=d.get("required_protocols", []),
            industry_verticals=d.get("industry_verticals", []),
            reference_url=d.get("reference_url", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "description": self.description,
            "mitre_software_id": self.mitre_software_id,
            "severity": self.severity,
            "category": self.category,
            "stages": [s.to_dict() for s in self.stages],
            "required_protocols": self.required_protocols,
            "industry_verticals": self.industry_verticals,
            "reference_url": self.reference_url,
            "total_duration_seconds": self.total_duration_seconds,
        }


@dataclass
class AttackState:
    """Runtime snapshot of an active attack playbook for status reporting."""

    playbook_id: str = ""
    playbook_name: str = ""
    current_stage_index: int = 0
    current_stage_id: str = ""
    current_stage_name: str = ""
    current_stage_color: str = "#ff4d4f"
    is_active: bool = False
    is_paused: bool = False
    is_completed: bool = False
    stage_started_at: float = 0.0
    stage_progress_pct: float = 0.0
    stage_remaining_s: float = 0.0
    stages_completed: int = 0
    total_stages: int = 0
    actions_completed: int = 0
    attack_packets_generated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "playbook_name": self.playbook_name,
            "is_active": self.is_active,
            "is_paused": self.is_paused,
            "is_completed": self.is_completed,
            "current_stage": self.current_stage_id,
            "current_stage_name": self.current_stage_name,
            "current_stage_color": self.current_stage_color,
            "current_stage_index": self.current_stage_index,
            "stage_progress_pct": round(self.stage_progress_pct, 1),
            "stage_remaining_s": round(self.stage_remaining_s, 0),
            "stages_completed": self.stages_completed,
            "total_stages": self.total_stages,
            "actions_completed": self.actions_completed,
            "attack_packets_generated": self.attack_packets_generated,
        }


@dataclass
class ActionReport:
    """Per-action telemetry captured during execution.

    Aggregated into ``StageReport`` and ultimately the post-run
    ``AttackReport``. Used by the after-action report view to show
    exactly what each action did.
    """

    action_id: str = ""
    action_name: str = ""
    action_type: str = ""
    mitre_technique: str = ""
    expected_cv_detection: str = ""
    description: str = ""
    fired_at: float = 0.0
    """Epoch seconds when the action first fired."""

    fire_count: int = 0
    """How many times the action ran (≥1 for repeating actions)."""

    packets_emitted: int = 0
    targets_hit: list[str] = field(default_factory=list)
    """Device IDs the action targeted."""

    iocs: dict[str, Any] = field(default_factory=dict)
    """Protocol-specific indicators-of-compromise captured.

    Examples: ``{"attacker_ip": "203.0.113.1", "target_ports": [502, 102],
    "register_addresses": [4000, 4001], "function_codes": [3, 6],
    "snmp_communities": ["public", "private"]}``.
    """

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_name": self.action_name,
            "action_type": self.action_type,
            "mitre_technique": self.mitre_technique,
            "expected_cv_detection": self.expected_cv_detection,
            "description": self.description,
            "fired_at": self.fired_at,
            "fire_count": self.fire_count,
            "packets_emitted": self.packets_emitted,
            "targets_hit": self.targets_hit,
            "iocs": self.iocs,
        }


@dataclass
class StageReport:
    """Per-stage telemetry captured during execution."""

    stage_id: str = ""
    stage_name: str = ""
    color: str = "#ff4d4f"
    description: str = ""
    planned_duration_s: int = 0
    started_at: float = 0.0
    completed_at: float | None = None
    actual_duration_s: float = 0.0
    actions: list[ActionReport] = field(default_factory=list)
    packets_emitted: int = 0
    mitre_tactics: list[str] = field(default_factory=list)
    expected_cv_alerts: list[str] = field(default_factory=list)
    status: str = "pending"
    """``pending`` | ``in_progress`` | ``completed`` | ``skipped``."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "color": self.color,
            "description": self.description,
            "planned_duration_s": self.planned_duration_s,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "actual_duration_s": self.actual_duration_s,
            "actions": [a.to_dict() for a in self.actions],
            "packets_emitted": self.packets_emitted,
            "mitre_tactics": self.mitre_tactics,
            "expected_cv_alerts": self.expected_cv_alerts,
            "status": self.status,
        }


@dataclass
class AttackReport:
    """Structured after-action report for a playbook run.

    Built incrementally by ``AttackOrchestrator`` as the attack
    progresses. Fully populated when the playbook completes (naturally
    or via STOP). Persisted into ``scenario.definition['attack_history'][]``
    so the report survives deployment teardown.
    """

    playbook_id: str = ""
    playbook_name: str = ""
    mitre_software_id: str = ""
    severity: str = ""
    category: str = ""
    started_at: float = 0.0
    completed_at: float | None = None
    status: str = "in_progress"
    """``in_progress`` | ``completed`` | ``stopped`` | ``failed``."""

    intensity: float = 1.0
    auto_advance: bool = True
    attacker_ip: str = ""
    target_device_count: int = 0
    stages: list[StageReport] = field(default_factory=list)

    # Aggregate totals (derived from stages, included here for cheap
    # UI rendering without summing client-side).
    total_packets: int = 0
    total_actions: int = 0
    total_stages: int = 0
    stages_completed: int = 0
    techniques_used: list[str] = field(default_factory=list)
    tactics_covered: list[str] = field(default_factory=list)
    targets_hit: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "playbook_name": self.playbook_name,
            "mitre_software_id": self.mitre_software_id,
            "severity": self.severity,
            "category": self.category,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "intensity": self.intensity,
            "auto_advance": self.auto_advance,
            "attacker_ip": self.attacker_ip,
            "target_device_count": self.target_device_count,
            "stages": [s.to_dict() for s in self.stages],
            "total_packets": self.total_packets,
            "total_actions": self.total_actions,
            "total_stages": self.total_stages,
            "stages_completed": self.stages_completed,
            "techniques_used": self.techniques_used,
            "tactics_covered": self.tactics_covered,
            "targets_hit": self.targets_hit,
        }


@dataclass
class AttackPlaybookConfig:
    """User-facing configuration when applying a playbook to a scenario.

    Stored in ``scenario.definition["attack_playbook"]``.
    """

    playbook_id: str
    target_device_ids: list[str] = field(default_factory=list)
    stage_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Map of stage_id → overrides (duration_seconds, enabled, rate_multiplier)."""

    auto_advance: bool = True
    """Automatically progress through stages vs manual trigger."""

    start_mode: str = "with_deployment"
    """``with_deployment`` (auto-start on deploy) or ``manual``."""

    intensity: float = 1.0
    """Global rate multiplier 0.1–3.0."""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AttackPlaybookConfig:
        if not d:
            return cls(playbook_id="")
        return cls(
            playbook_id=d.get("playbook_id", ""),
            target_device_ids=d.get("target_device_ids", []),
            stage_overrides=d.get("stage_overrides", {}),
            auto_advance=d.get("auto_advance", True),
            start_mode=d.get("start_mode", "with_deployment"),
            intensity=d.get("intensity", 1.0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "target_device_ids": self.target_device_ids,
            "stage_overrides": self.stage_overrides,
            "auto_advance": self.auto_advance,
            "start_mode": self.start_mode,
            "intensity": self.intensity,
        }
