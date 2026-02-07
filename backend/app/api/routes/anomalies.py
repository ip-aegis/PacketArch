"""Anomaly API routes for anomaly template management and injection.

This module provides REST API endpoints for:
- Listing anomaly templates (previously MCP-only)
- Suggesting anomalies for scenarios based on vertical/protocols
- Creating and managing anomaly campaigns
"""

import uuid
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.core.exceptions import NotFoundError, ValidationError
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import CurrentUser, DBSession
from app.models.anomaly_template import AnomalyCategory, AnomalySeverity, AnomalyTemplate
from app.models.scenario import Scenario
from app.scenario_templates import get_template

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


# ========== Response Models ==========


class AnomalyTemplateResponse(BaseModel):
    """Anomaly template response."""

    id: str
    name: str
    description: str | None
    category: str
    severity: str
    anomaly_type: str
    target_protocols: list[str] | None
    target_device_types: list[str] | None
    injection_probability: float
    injection_mode: str
    parameters: dict[str, Any] | None
    tags: list[str] | None
    is_builtin: bool


class AnomalyTemplateListResponse(BaseModel):
    """List of anomaly templates."""

    templates: list[AnomalyTemplateResponse]
    count: int
    categories: list[str]


class SuggestedAnomalyResponse(BaseModel):
    """Suggested anomaly for a scenario."""

    template_id: str
    name: str
    category: str
    severity: str
    relevance_score: int
    reasons: list[str]


class ScenarioAnomalySuggestionResponse(BaseModel):
    """Anomaly suggestions for a scenario."""

    scenario_id: str
    vertical: str
    protocols: list[str]
    device_types: list[str]
    template_suggestions: list[dict[str, Any]]
    suggestions: list[SuggestedAnomalyResponse]


class AnomalyCampaignResponse(BaseModel):
    """Anomaly campaign configuration."""

    id: str
    name: str
    start_time_ms: float
    duration_ms: float | None
    target_flow_ids: list[str] | None
    anomaly_types: list[str]
    templates: list[dict[str, Any]]


class CreateCampaignRequest(BaseModel):
    """Request to create an anomaly campaign."""

    name: str = Field(..., min_length=1, max_length=200)
    anomaly_types: list[str] = Field(..., min_items=1)
    start_time_ms: float = Field(..., ge=0)
    duration_ms: float | None = Field(None, ge=0)
    target_flow_ids: list[str] | None = None


class CreateCampaignResponse(BaseModel):
    """Response after creating a campaign."""

    success: bool
    campaign_id: str
    name: str
    anomaly_count: int
    templates: list[dict[str, Any]]


class VerticalAnomaliesResponse(BaseModel):
    """Suggested anomalies for a vertical template."""

    vertical: str
    template_name: str
    suggested_anomalies: dict[str, list[str]]
    pcap_learning_hints: list[dict[str, Any]]


# ========== API Endpoints ==========


@router.get("/templates", response_model=AnomalyTemplateListResponse)
async def list_anomaly_templates(
    _current_user: CurrentUser,
    db: DBSession,
    category: str | None = Query(None, description="Filter by category"),
    severity: str | None = Query(None, description="Filter by severity"),
    protocol: str | None = Query(None, description="Filter by target protocol"),
) -> AnomalyTemplateListResponse:
    """List available anomaly templates.

    Args:
        category: Filter by category (timing, protocol, sequence, payload, network, security)
        severity: Filter by severity (low, medium, high, critical)
        protocol: Filter by target protocol

    Returns:
        List of anomaly templates
    """
    query = select(AnomalyTemplate).where(AnomalyTemplate.is_active == True)

    if category:
        try:
            query = query.where(AnomalyTemplate.category == AnomalyCategory(category))
        except ValueError:
            raise ValidationError(f"Invalid category: {category}")

    if severity:
        try:
            query = query.where(AnomalyTemplate.severity == AnomalySeverity(severity))
        except ValueError:
            raise ValidationError(f"Invalid severity: {severity}")

    query = query.order_by(AnomalyTemplate.category, AnomalyTemplate.name)

    result = await db.execute(query)
    templates = result.scalars().all()

    # Filter by protocol if specified
    if protocol:
        templates = [
            t for t in templates
            if t.target_protocols is None or protocol in t.target_protocols
        ]

    return AnomalyTemplateListResponse(
        templates=[
            AnomalyTemplateResponse(
                id=str(t.id),
                name=t.name,
                description=t.description,
                category=t.category.value,
                severity=t.severity.value,
                anomaly_type=t.anomaly_type,
                target_protocols=t.target_protocols,
                target_device_types=t.target_device_types,
                injection_probability=t.injection_probability,
                injection_mode=t.injection_mode,
                parameters=t.parameters,
                tags=t.tags,
                is_builtin=t.is_builtin,
            )
            for t in templates
        ],
        count=len(templates),
        categories=[c.value for c in AnomalyCategory],
    )


@router.get("/templates/{template_id}", response_model=AnomalyTemplateResponse)
async def get_anomaly_template(
    template_id: str,
    _current_user: CurrentUser,
    db: DBSession,
) -> AnomalyTemplateResponse:
    """Get a specific anomaly template by ID.

    Args:
        template_id: Template UUID

    Returns:
        Anomaly template details

    Raises:
        HTTPException: If template not found
    """
    try:
        template_uuid = uuid.UUID(template_id)
    except ValueError:
        raise ValidationError("Invalid template ID format")

    result = await db.execute(
        select(AnomalyTemplate).where(
            AnomalyTemplate.id == template_uuid,
            AnomalyTemplate.is_active == True,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise NotFoundError("Anomaly template")

    return AnomalyTemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description,
        category=template.category.value,
        severity=template.severity.value,
        anomaly_type=template.anomaly_type,
        target_protocols=template.target_protocols,
        target_device_types=template.target_device_types,
        injection_probability=template.injection_probability,
        injection_mode=template.injection_mode,
        parameters=template.parameters,
        tags=template.tags,
        is_builtin=template.is_builtin,
    )


@router.get("/suggest/{scenario_id}", response_model=ScenarioAnomalySuggestionResponse)
async def suggest_anomalies_for_scenario(
    scenario_id: str,
    _current_user: CurrentUser,
    db: DBSession,
    max_suggestions: int = Query(15, ge=1, le=50),
) -> ScenarioAnomalySuggestionResponse:
    """Suggest appropriate anomalies for a scenario.

    Analyzes the scenario's devices, protocols, and industry vertical
    to suggest relevant anomaly types for testing.

    Args:
        scenario_id: Scenario UUID
        max_suggestions: Maximum number of suggestions to return

    Returns:
        Anomaly suggestions with relevance scores
    """
    try:
        scenario_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise ValidationError("Invalid scenario ID format")

    # Get scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_uuid)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    # Analyze scenario
    definition = scenario.definition
    flows = definition.get("flows", {})
    devices = definition.get("devices", {})

    # Get protocols and device types
    protocols = set()
    device_types = set()
    for flow in flows.values():
        protocols.add(flow.get("protocol", ""))
    for device in devices.values():
        device_types.add(device.get("type", ""))

    # Get template-based suggestions if available
    template_suggestions = []
    if scenario.vertical:
        template = get_template(scenario.vertical, "default")
        if template and "suggested_anomalies" in template:
            template_suggestions = template.get("suggested_anomalies", {})

    # Find matching anomaly templates from database
    query = select(AnomalyTemplate).where(AnomalyTemplate.is_active == True)
    result = await db.execute(query)
    all_templates = result.scalars().all()

    suggestions = []
    for template in all_templates:
        relevance_score = 0
        reasons = []

        # Check protocol match
        if template.target_protocols:
            matching_protocols = protocols & set(template.target_protocols)
            if matching_protocols:
                relevance_score += 3
                reasons.append(f"Matches protocols: {matching_protocols}")
        else:
            relevance_score += 1  # Generic template

        # Check device type match
        if template.target_device_types:
            matching_types = device_types & set(template.target_device_types)
            if matching_types:
                relevance_score += 2
                reasons.append(f"Matches device types: {matching_types}")

        # Add vertical-specific suggestions
        if scenario.vertical == "manufacturing" and template.category.value in ["timing", "protocol"]:
            relevance_score += 1
            reasons.append("Relevant for manufacturing testing")
        if scenario.vertical in ["energy", "water"] and template.category.value == "security":
            relevance_score += 2
            reasons.append("Critical infrastructure security testing")
        if scenario.vertical == "oil_gas" and template.category.value in ["timing", "network"]:
            relevance_score += 1
            reasons.append("Relevant for remote SCADA testing")

        if relevance_score > 0:
            suggestions.append(SuggestedAnomalyResponse(
                template_id=str(template.id),
                name=template.name,
                category=template.category.value,
                severity=template.severity.value,
                relevance_score=relevance_score,
                reasons=reasons,
            ))

    # Sort by relevance
    suggestions.sort(key=lambda x: x.relevance_score, reverse=True)

    return ScenarioAnomalySuggestionResponse(
        scenario_id=scenario_id,
        vertical=scenario.vertical or "unknown",
        protocols=list(protocols),
        device_types=list(device_types),
        template_suggestions=template_suggestions,
        suggestions=suggestions[:max_suggestions],
    )


@router.get("/vertical/{vertical}", response_model=VerticalAnomaliesResponse)
async def get_vertical_anomalies(
    vertical: str,
    _current_user: CurrentUser,
    template_name: str = Query("default", description="Template name within vertical"),
) -> VerticalAnomaliesResponse:
    """Get suggested anomalies for a vertical template.

    Returns the suggested_anomalies and pcap_learning_hints from
    the enhanced vertical templates.

    Args:
        vertical: Industry vertical (manufacturing, water, energy, oil_gas)
        template_name: Specific template name

    Returns:
        Suggested anomalies and PCAP learning hints
    """
    template = get_template(vertical, template_name)

    if not template:
        raise NotFoundError("Template", f"{vertical}/{template_name}")

    return VerticalAnomaliesResponse(
        vertical=vertical,
        template_name=template.get("name", template_name),
        suggested_anomalies=template.get("suggested_anomalies", {}),
        pcap_learning_hints=template.get("pcap_learning_hints", []),
    )


@router.post("/campaigns/{scenario_id}", response_model=CreateCampaignResponse)
async def create_anomaly_campaign(
    scenario_id: str,
    request: CreateCampaignRequest,
    _current_user: CurrentUser,
    db: DBSession,
) -> CreateCampaignResponse:
    """Create an anomaly injection campaign for a scenario.

    Sets up a coordinated anomaly campaign that will inject specified
    anomaly types during traffic generation.

    Args:
        scenario_id: Scenario UUID
        request: Campaign configuration

    Returns:
        Created campaign details
    """
    try:
        scenario_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise ValidationError("Invalid scenario ID format")

    # Get scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_uuid)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    # Find anomaly templates
    templates = []
    for anomaly_type in request.anomaly_types:
        result = await db.execute(
            select(AnomalyTemplate).where(
                AnomalyTemplate.anomaly_type == anomaly_type,
                AnomalyTemplate.is_active == True,
            )
        )
        template = result.scalar_one_or_none()
        if template:
            templates.append({
                "id": str(template.id),
                "name": template.name,
                "type": template.anomaly_type,
                "category": template.category.value,
                "severity": template.severity.value,
                "parameters": template.parameters,
            })

    # Update scenario definition with campaign
    definition = scenario.definition.copy()
    campaigns = definition.get("anomaly_campaigns", [])

    campaign_id = str(uuid.uuid4())
    campaign = {
        "id": campaign_id,
        "name": request.name,
        "start_time_ms": request.start_time_ms,
        "duration_ms": request.duration_ms,
        "target_flow_ids": request.target_flow_ids,
        "anomaly_types": request.anomaly_types,
        "templates": templates,
    }
    campaigns.append(campaign)
    definition["anomaly_campaigns"] = campaigns

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()

    return CreateCampaignResponse(
        success=True,
        campaign_id=campaign_id,
        name=request.name,
        anomaly_count=len(templates),
        templates=templates,
    )


@router.get("/campaigns/{scenario_id}", response_model=list[AnomalyCampaignResponse])
async def list_scenario_campaigns(
    scenario_id: str,
    _current_user: CurrentUser,
    db: DBSession,
) -> list[AnomalyCampaignResponse]:
    """List anomaly campaigns for a scenario.

    Args:
        scenario_id: Scenario UUID

    Returns:
        List of configured campaigns
    """
    try:
        scenario_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise ValidationError("Invalid scenario ID format")

    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_uuid)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    campaigns = scenario.definition.get("anomaly_campaigns", [])

    return [
        AnomalyCampaignResponse(
            id=c["id"],
            name=c["name"],
            start_time_ms=c["start_time_ms"],
            duration_ms=c.get("duration_ms"),
            target_flow_ids=c.get("target_flow_ids"),
            anomaly_types=c["anomaly_types"],
            templates=c.get("templates", []),
        )
        for c in campaigns
    ]


@router.delete("/campaigns/{scenario_id}/{campaign_id}")
async def delete_anomaly_campaign(
    scenario_id: str,
    campaign_id: str,
    _current_user: CurrentUser,
    db: DBSession,
) -> dict[str, Any]:
    """Delete an anomaly campaign from a scenario.

    Args:
        scenario_id: Scenario UUID
        campaign_id: Campaign UUID

    Returns:
        Success status
    """
    try:
        scenario_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise ValidationError("Invalid scenario ID format")

    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_uuid)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    # Remove campaign
    definition = scenario.definition.copy()
    campaigns = definition.get("anomaly_campaigns", [])
    campaigns = [c for c in campaigns if c.get("id") != campaign_id]
    definition["anomaly_campaigns"] = campaigns

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()

    return {"success": True, "deleted": campaign_id}


# ========== External Communication Endpoints ==========


class ExternalCommPatternResponse(BaseModel):
    """External communication pattern response."""

    name: str
    display_name: str
    description: str
    pattern_type: str
    base_interval_ms: int
    mitre_technique: str


class ExternalExploitPatternResponse(BaseModel):
    """Exploit pattern response."""

    name: str
    display_name: str
    description: str
    target_protocol: str
    target_port: int
    mitre_technique: str
    cve_reference: str | None


class ExternalTemplateResponse(BaseModel):
    """External communication anomaly template."""

    id: str
    name: str
    description: str | None
    anomaly_type: str
    severity: str
    external_target_type: str | None
    external_protocol: str | None
    external_port: int | None
    external_ip_pool: str | None
    mitre_technique: str | None
    ids_trigger_patterns: list[str] | None


class ExternalCommTypesResponse(BaseModel):
    """Available external communication types."""

    beacon_patterns: list[ExternalCommPatternResponse]
    exploit_patterns: list[ExternalExploitPatternResponse]
    external_templates: list[ExternalTemplateResponse]


@router.get("/external/types", response_model=ExternalCommTypesResponse)
async def get_external_communication_types(
    _current_user: CurrentUser,
    db: DBSession,
) -> ExternalCommTypesResponse:
    """Get available external communication types and patterns.

    Returns:
        Available C2 beacon patterns, exploit patterns, and external templates
    """
    from app.protocol_engines.external.c2_patterns import list_beacon_patterns
    from app.protocol_engines.external.exploit_patterns import list_exploit_patterns

    # Get beacon patterns from engine
    beacon_patterns = [
        ExternalCommPatternResponse(
            name=p["name"],
            display_name=p["display_name"],
            description=p["description"],
            pattern_type=p["pattern_type"],
            base_interval_ms=p["base_interval_ms"],
            mitre_technique=p["mitre_technique"],
        )
        for p in list_beacon_patterns()
    ]

    # Get exploit patterns from engine
    exploit_patterns = [
        ExternalExploitPatternResponse(
            name=p["name"],
            display_name=p["display_name"],
            description=p["description"],
            target_protocol=p["target_protocol"],
            target_port=p["target_port"],
            mitre_technique=p["mitre_technique"],
            cve_reference=p.get("cve_reference"),
        )
        for p in list_exploit_patterns()
    ]

    # Get external communication templates from database
    result = await db.execute(
        select(AnomalyTemplate).where(
            AnomalyTemplate.category == AnomalyCategory.EXTERNAL_COMMUNICATION,
            AnomalyTemplate.is_active == True,
        )
    )
    templates = result.scalars().all()

    external_templates = [
        ExternalTemplateResponse(
            id=str(t.id),
            name=t.name,
            description=t.description,
            anomaly_type=t.anomaly_type,
            severity=t.severity.value,
            external_target_type=t.external_target_type,
            external_protocol=t.external_protocol,
            external_port=t.external_port,
            external_ip_pool=t.external_ip_pool,
            mitre_technique=t.mitre_technique,
            ids_trigger_patterns=t.ids_trigger_patterns,
        )
        for t in templates
    ]

    return ExternalCommTypesResponse(
        beacon_patterns=beacon_patterns,
        exploit_patterns=exploit_patterns,
        external_templates=external_templates,
    )


@router.get("/external/templates", response_model=list[ExternalTemplateResponse])
async def list_external_templates(
    _current_user: CurrentUser,
    db: DBSession,
    target_type: str | None = Query(None, description="Filter by target type (c2_server, exfil_destination, attacker_source)"),
) -> list[ExternalTemplateResponse]:
    """List external communication anomaly templates.

    Args:
        target_type: Optional filter by external target type

    Returns:
        List of external communication templates
    """
    query = select(AnomalyTemplate).where(
        AnomalyTemplate.category == AnomalyCategory.EXTERNAL_COMMUNICATION,
        AnomalyTemplate.is_active == True,
    )

    if target_type:
        query = query.where(AnomalyTemplate.external_target_type == target_type)

    result = await db.execute(query)
    templates = result.scalars().all()

    return [
        ExternalTemplateResponse(
            id=str(t.id),
            name=t.name,
            description=t.description,
            anomaly_type=t.anomaly_type,
            severity=t.severity.value,
            external_target_type=t.external_target_type,
            external_protocol=t.external_protocol,
            external_port=t.external_port,
            external_ip_pool=t.external_ip_pool,
            mitre_technique=t.mitre_technique,
            ids_trigger_patterns=t.ids_trigger_patterns,
        )
        for t in templates
    ]


@router.get("/external/ip-pools")
async def get_external_ip_pools(
    _current_user: CurrentUser,
) -> dict[str, Any]:
    """Get information about external IP pools.

    Returns RFC 5737 TEST-NET ranges used for external traffic simulation.
    """
    return {
        "test_net_1": {
            "range": "192.0.2.0/24",
            "description": "TEST-NET-1 - Used for C2 servers",
            "purpose": "c2_server",
        },
        "test_net_2": {
            "range": "198.51.100.0/24",
            "description": "TEST-NET-2 - Used for exfiltration destinations",
            "purpose": "exfil_destination",
        },
        "test_net_3": {
            "range": "203.0.113.0/24",
            "description": "TEST-NET-3 - Used for attack sources",
            "purpose": "attacker_source",
        },
        "realistic": {
            "description": "Historical malicious IPs from threat intelligence",
            "warning": "Use only in isolated test environments",
        },
    }


# ========== External Campaign Endpoints ==========


class CreateExternalCampaignRequest(BaseModel):
    """Request to create an external communication campaign."""

    name: str = Field(..., min_length=1, max_length=200)
    internal_device_ips: list[str] = Field(..., min_items=1, description="Internal device IPs to 'compromise'")
    event_types: list[str] = Field(..., min_items=1, description="Types: c2_beacon, dns_tunnel, http_exfil, exploit, port_scan")
    start_time_ms: float = Field(0, ge=0)
    duration_ms: float = Field(300000, ge=1000)
    use_realistic_ips: bool = Field(False, description="Use realistic IPs vs TEST-NET")
    c2_pattern: str | None = Field(None, description="C2 beaconing pattern name")
    c2_protocol: str | None = Field("http", description="C2 protocol: http, https, dns")
    beacon_count: int = Field(10, ge=1, le=100)
    exfil_data_size: int = Field(1024, ge=1, le=1048576)
    exploit_pattern: str | None = Field(None, description="Exploit pattern name")
    scan_type: str = Field("syn", description="Port scan type: syn, fin, xmas, null")
    scan_ot_ports: bool = Field(True, description="Scan OT-specific ports")


class ExternalCampaignResponse(BaseModel):
    """External campaign creation response."""

    success: bool
    campaign_id: str
    name: str
    event_count: int
    event_types: list[str]
    internal_devices: list[str]
    start_time_ms: float
    duration_ms: float


@router.post("/external/campaigns/{scenario_id}", response_model=ExternalCampaignResponse)
async def create_external_campaign(
    scenario_id: str,
    request: CreateExternalCampaignRequest,
    _current_user: CurrentUser,
    db: DBSession,
) -> ExternalCampaignResponse:
    """Create an external communication campaign for a scenario.

    Creates a campaign that generates external malicious traffic (C2 beaconing,
    data exfiltration, exploit attempts, port scans) during traffic generation.

    Args:
        scenario_id: Scenario UUID
        request: Campaign configuration

    Returns:
        Created campaign details
    """
    try:
        scenario_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise ValidationError("Invalid scenario ID format")

    # Get scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_uuid)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    # Validate event types
    valid_types = {"c2_beacon", "dns_tunnel", "http_exfil", "exploit", "port_scan"}
    invalid_types = set(request.event_types) - valid_types
    if invalid_types:
        raise ValidationError(f"Invalid event types: {invalid_types}. Valid types: {valid_types}")

    # Create campaign in scenario definition
    definition = scenario.definition.copy()
    external_campaigns = definition.get("external_campaigns", [])

    campaign_id = str(uuid.uuid4())
    campaign = {
        "id": campaign_id,
        "name": request.name,
        "internal_device_ips": request.internal_device_ips,
        "event_types": request.event_types,
        "start_time_ms": request.start_time_ms,
        "duration_ms": request.duration_ms,
        "use_realistic_ips": request.use_realistic_ips,
        "c2_pattern": request.c2_pattern,
        "c2_protocol": request.c2_protocol,
        "beacon_count": request.beacon_count,
        "exfil_data_size": request.exfil_data_size,
        "exploit_pattern": request.exploit_pattern,
        "scan_type": request.scan_type,
        "scan_ot_ports": request.scan_ot_ports,
    }
    external_campaigns.append(campaign)
    definition["external_campaigns"] = external_campaigns

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()

    # Calculate event count (one event per device per type)
    event_count = len(request.internal_device_ips) * len(request.event_types)

    return ExternalCampaignResponse(
        success=True,
        campaign_id=campaign_id,
        name=request.name,
        event_count=event_count,
        event_types=request.event_types,
        internal_devices=request.internal_device_ips,
        start_time_ms=request.start_time_ms,
        duration_ms=request.duration_ms,
    )


@router.get("/external/campaigns/{scenario_id}", response_model=list[ExternalCampaignResponse])
async def list_external_campaigns(
    scenario_id: str,
    _current_user: CurrentUser,
    db: DBSession,
) -> list[ExternalCampaignResponse]:
    """List external communication campaigns for a scenario.

    Args:
        scenario_id: Scenario UUID

    Returns:
        List of configured external campaigns
    """
    try:
        scenario_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise ValidationError("Invalid scenario ID format")

    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_uuid)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    campaigns = scenario.definition.get("external_campaigns", [])

    return [
        ExternalCampaignResponse(
            success=True,
            campaign_id=c["id"],
            name=c["name"],
            event_count=len(c.get("internal_device_ips", [])) * len(c.get("event_types", [])),
            event_types=c.get("event_types", []),
            internal_devices=c.get("internal_device_ips", []),
            start_time_ms=c.get("start_time_ms", 0),
            duration_ms=c.get("duration_ms", 300000),
        )
        for c in campaigns
    ]


@router.delete("/external/campaigns/{scenario_id}/{campaign_id}")
async def delete_external_campaign(
    scenario_id: str,
    campaign_id: str,
    _current_user: CurrentUser,
    db: DBSession,
) -> dict[str, Any]:
    """Delete an external communication campaign from a scenario.

    Args:
        scenario_id: Scenario UUID
        campaign_id: Campaign UUID

    Returns:
        Success status
    """
    try:
        scenario_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise ValidationError("Invalid scenario ID format")

    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_uuid)
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    # Remove campaign
    definition = scenario.definition.copy()
    campaigns = definition.get("external_campaigns", [])
    campaigns = [c for c in campaigns if c.get("id") != campaign_id]
    definition["external_campaigns"] = campaigns

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()

    return {"success": True, "deleted": campaign_id}
