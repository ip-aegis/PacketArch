"""AI-powered generation tools for MCP.

These tools enable natural language scenario generation and anomaly injection
through the MCP interface.
"""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario
from app.models.anomaly_template import AnomalyTemplate, AnomalyCategory

# Maximum devices per scenario to prevent runaway generation
MAX_DEVICES_PER_SCENARIO = 100


async def generate_scenario_from_nl(
    db: AsyncSession,
    user_id: str,
    description: str,
    name: str | None = None,
    duration_ms: int = 300000,
) -> str:
    """Generate a complete scenario from natural language description.

    This tool uses AI to parse a natural language description of an OT
    environment and generate a complete scenario with devices, flows,
    and appropriate protocols.

    Args:
        db: Database session
        user_id: User ID creating the scenario
        description: Natural language description of the scenario
            Example: "A manufacturing plant with 5 Rockwell PLCs,
            2 HMIs, and 10 VFDs using EtherNet/IP"
        name: Optional scenario name
        duration_ms: Scenario duration in milliseconds

    Returns:
        JSON string with generated scenario details
    """
    from app.ai_services.scenario_generator import ScenarioGenerator

    generator = ScenarioGenerator()

    # Generate from description
    scenario = generator.generate_from_description(
        description=description,
        name=name,
        duration_ms=duration_ms,
    )

    # Enforce device limit
    if len(scenario.devices) > MAX_DEVICES_PER_SCENARIO:
        return json.dumps({
            "error": f"Generated scenario exceeds device limit ({len(scenario.devices)} > {MAX_DEVICES_PER_SCENARIO}). Please request fewer devices.",
            "requested_devices": len(scenario.devices),
            "max_allowed": MAX_DEVICES_PER_SCENARIO
        })

    # Convert to database format
    devices = {}
    for d in scenario.devices:
        devices[d.device_id] = {
            "id": d.device_id,
            "name": d.name,
            "type": d.device_type,
            "protocols": d.protocols,
            "position": {"x": 100, "y": 100},  # Will be laid out by frontend
            "zoneId": d.zone,
            "network": {
                "macAddress": d.mac_address,
                "ipAddress": d.ip_address,
                "subnetMask": "255.255.255.0",
            },
            "vendor": d.vendor,
        }

    flows = {}
    for f in scenario.flows:
        flows[f.flow_id] = {
            "id": f.flow_id,
            "name": f.description,
            "sourceDeviceId": f.source_device_id,
            "targetDeviceId": f.destination_device_id,
            "protocol": f.protocol,
            "timing": {"intervalMs": f.poll_interval_ms, "jitterMs": 50},
            "protocolConfig": {},
            "phases": {
                "startup": True,
                "steadyState": True,
                "maintenance": False,
                "shutdown": True,
            },
        }

    zones = {}
    for z in scenario.zones:
        zones[z["name"]] = {
            "id": z["name"],
            "name": z["name"].replace("_", " ").title(),
            "type": "network",
            "position": {"x": 50, "y": 50},
            "dimensions": {"width": 800, "height": 400},
            "deviceIds": z.get("device_ids", []),
        }

    # Create database scenario
    db_scenario = Scenario(
        user_id=uuid.UUID(user_id),
        name=scenario.name,
        description=description,
        vertical=scenario.vertical,
        total_duration_ms=duration_ms,
        definition={
            "devices": devices,
            "flows": flows,
            "zones": zones,
            "phases": [],
            "events": [],
        },
        version=1,
    )

    db.add(db_scenario)
    await db.commit()
    await db.refresh(db_scenario)

    # Build response with optional warnings
    response = {
        "success": True,
        "scenario_id": str(db_scenario.id),
        "name": scenario.name,
        "vertical": scenario.vertical,
        "device_count": len(devices),
        "flow_count": len(flows),
        "zone_count": len(zones),
        "extracted_entities": scenario.metadata.get("extracted_entities", []),
    }

    # Add warning if no flows were generated
    if len(devices) > 0 and len(flows) == 0:
        response["warning"] = (
            "No traffic flows were generated. Devices may not communicate. "
            "Consider adding flows manually or re-generating with controller devices (PLCs/RTUs)."
        )

    return json.dumps(response)


async def suggest_vertical_template(description: str) -> str:
    """Suggest an industry vertical based on description.

    Analyzes the description and suggests the most appropriate
    industry vertical template (manufacturing, water, energy, oil_gas).

    Args:
        description: Natural language description

    Returns:
        JSON string with suggested vertical and confidence
    """
    from app.ai_services.scenario_generator import ScenarioGenerator

    generator = ScenarioGenerator()
    suggestion = generator.suggest_vertical(description)

    return json.dumps(suggestion)


async def suggest_patterns_for_scenario(
    db: AsyncSession,
    scenario_id: str,
) -> str:
    """Suggest learned patterns that could be applied to a scenario.

    Analyzes the scenario's protocols and devices, then finds
    matching learned patterns from PCAP analysis.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string with pattern suggestions
    """
    from app.models.learned_pattern import LearnedPattern, PatternType

    # Get scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    # Get protocols used in scenario
    protocols = set()
    flows = scenario.definition.get("flows", {})
    for flow in flows.values():
        protocols.add(flow.get("protocol", ""))

    # Find matching patterns
    timing_query = select(LearnedPattern).where(
        LearnedPattern.pattern_type == PatternType.TIMING,
        LearnedPattern.is_active == True,
        LearnedPattern.protocol.in_(protocols),
    ).order_by(LearnedPattern.confidence.desc()).limit(10)

    result = await db.execute(timing_query)
    timing_patterns = result.scalars().all()

    payload_query = select(LearnedPattern).where(
        LearnedPattern.pattern_type == PatternType.PAYLOAD,
        LearnedPattern.is_active == True,
        LearnedPattern.protocol.in_(protocols),
    ).order_by(LearnedPattern.confidence.desc()).limit(10)

    result = await db.execute(payload_query)
    payload_patterns = result.scalars().all()

    return json.dumps({
        "scenario_id": scenario_id,
        "protocols_in_scenario": list(protocols),
        "timing_patterns": [
            {
                "id": str(p.id),
                "name": p.name,
                "protocol": p.protocol,
                "distribution_type": p.distribution_type.value if p.distribution_type else None,
                "mean_value": p.mean_value,
                "confidence": p.confidence,
            }
            for p in timing_patterns
        ],
        "payload_patterns": [
            {
                "id": str(p.id),
                "name": p.name,
                "protocol": p.protocol,
                "sample_count": p.sample_count,
                "confidence": p.confidence,
            }
            for p in payload_patterns
        ],
    })


async def inject_anomaly_campaign(
    db: AsyncSession,
    scenario_id: str,
    campaign_name: str,
    anomaly_types: list[str],
    start_time_ms: float,
    duration_ms: float | None = None,
    target_flow_ids: list[str] | None = None,
) -> str:
    """Configure an anomaly injection campaign for a scenario.

    Sets up a coordinated anomaly campaign that will inject specified
    anomaly types during traffic generation.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        campaign_name: Name for the campaign
        anomaly_types: List of anomaly types to include
            (e.g., ["timeout", "delayed", "modbus_exception"])
        start_time_ms: Campaign start time in milliseconds
        duration_ms: Campaign duration (None for single injection)
        target_flow_ids: Specific flows to target (None for all)

    Returns:
        JSON string with campaign configuration
    """
    # Get scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    # Find anomaly templates
    templates = []
    for anomaly_type in anomaly_types:
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

    campaign = {
        "id": str(uuid.uuid4()),
        "name": campaign_name,
        "start_time_ms": start_time_ms,
        "duration_ms": duration_ms,
        "target_flow_ids": target_flow_ids,
        "anomaly_types": anomaly_types,
        "templates": templates,
    }
    campaigns.append(campaign)
    definition["anomaly_campaigns"] = campaigns

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()

    return json.dumps({
        "success": True,
        "campaign_id": campaign["id"],
        "name": campaign_name,
        "anomaly_count": len(templates),
        "templates": templates,
    })


async def list_anomaly_templates(
    db: AsyncSession,
    category: str | None = None,
    severity: str | None = None,
) -> str:
    """List available anomaly templates.

    Args:
        db: Database session
        category: Filter by category (timing, protocol, sequence, etc.)
        severity: Filter by severity (low, medium, high, critical)

    Returns:
        JSON string with template list
    """
    query = select(AnomalyTemplate).where(AnomalyTemplate.is_active == True)

    if category:
        query = query.where(AnomalyTemplate.category == AnomalyCategory(category))

    if severity:
        from app.models.anomaly_template import AnomalySeverity
        query = query.where(AnomalyTemplate.severity == AnomalySeverity(severity))

    query = query.order_by(AnomalyTemplate.category, AnomalyTemplate.name)

    result = await db.execute(query)
    templates = result.scalars().all()

    return json.dumps({
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "severity": t.severity.value,
                "anomaly_type": t.anomaly_type,
                "target_protocols": t.target_protocols,
                "injection_probability": t.injection_probability,
                "tags": t.tags,
            }
            for t in templates
        ],
        "count": len(templates),
    })


async def analyze_scenario_for_anomalies(
    db: AsyncSession,
    scenario_id: str,
) -> str:
    """Analyze a scenario and suggest appropriate anomalies.

    Examines the scenario's devices, protocols, and industry vertical
    to suggest relevant anomaly types for testing.

    Args:
        db: Database session
        scenario_id: Scenario UUID

    Returns:
        JSON string with anomaly suggestions
    """
    # Get scenario
    result = await db.execute(
        select(Scenario).where(Scenario.id == uuid.UUID(scenario_id))
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

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

    # Find matching anomaly templates
    suggestions = []

    # Protocol-specific anomalies
    query = select(AnomalyTemplate).where(
        AnomalyTemplate.is_active == True,
    )
    result = await db.execute(query)
    all_templates = result.scalars().all()

    for template in all_templates:
        relevance_score = 0
        reasons = []

        # Check protocol match
        if template.target_protocols:
            if protocols & set(template.target_protocols):
                relevance_score += 3
                reasons.append(f"Matches protocols: {protocols & set(template.target_protocols)}")
        else:
            relevance_score += 1  # Generic template

        # Check device type match
        if template.target_device_types:
            if device_types & set(template.target_device_types):
                relevance_score += 2
                reasons.append(f"Matches device types: {device_types & set(template.target_device_types)}")

        # Add vertical-specific suggestions
        if scenario.vertical == "manufacturing" and template.category.value in ["timing", "protocol"]:
            relevance_score += 1
        if scenario.vertical in ["energy", "water"] and template.category.value == "security":
            relevance_score += 2
            reasons.append("Critical infrastructure security testing")

        if relevance_score > 0:
            suggestions.append({
                "template_id": str(template.id),
                "name": template.name,
                "category": template.category.value,
                "severity": template.severity.value,
                "relevance_score": relevance_score,
                "reasons": reasons,
            })

    # Sort by relevance
    suggestions.sort(key=lambda x: x["relevance_score"], reverse=True)

    return json.dumps({
        "scenario_id": scenario_id,
        "vertical": scenario.vertical,
        "protocols": list(protocols),
        "device_types": list(device_types),
        "suggestions": suggestions[:15],  # Top 15 suggestions
    })
