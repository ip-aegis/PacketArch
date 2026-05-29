# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Conduit schemas for IEC 62443 zone-to-zone communication boundaries."""

from enum import Enum

from pydantic import BaseModel, Field


class ConduitDirection(str, Enum):
    """Direction of allowed traffic through a conduit."""

    BIDIRECTIONAL = "bidirectional"
    A_TO_B = "a_to_b"
    B_TO_A = "b_to_a"


class SecurityLevel(str, Enum):
    """IEC 62443 security level targets."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceSeverity(str, Enum):
    """Severity of a compliance finding.

    BLOCKING is set when the active cell-isolation mode will actually
    drop the offending flow at runtime (vs WARNING, which is advisory).
    """

    WARNING = "warning"
    BLOCKING = "blocking"


class ComplianceFindingReason(str, Enum):
    """Reason a flow is non-compliant with conduit rules."""

    NO_CONDUIT = "no_conduit"
    PROTOCOL_NOT_ALLOWED = "protocol_not_allowed"
    WRONG_DIRECTION = "wrong_direction"


class ScenarioConduit(BaseModel):
    """A conduit defining allowed communication between two zones."""

    id: str
    name: str = Field(..., min_length=1, max_length=255)
    source_zone_id: str
    target_zone_id: str
    direction: ConduitDirection = ConduitDirection.BIDIRECTIONAL
    allowed_protocols: list[str] = Field(default_factory=list)
    security_level: SecurityLevel = SecurityLevel.STANDARD
    description: str | None = None
    auto_generated: bool = False


class ComplianceFinding(BaseModel):
    """A single conduit compliance finding for a flow."""

    flow_id: str
    flow_name: str
    source_zone_id: str | None
    target_zone_id: str | None
    protocol: str
    severity: ComplianceSeverity = ComplianceSeverity.WARNING
    reason: ComplianceFindingReason
    conduit_id: str | None = None


class ConduitComplianceResponse(BaseModel):
    """Response for the conduit compliance endpoint."""

    findings: list[ComplianceFinding] = Field(default_factory=list)
    total_flows: int = 0
    compliant_flows: int = 0
    non_compliant_flows: int = 0
