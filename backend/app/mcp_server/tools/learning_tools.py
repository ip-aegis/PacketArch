"""Learned pattern tools for MCP.

This module provides tools for:
- Listing learned fingerprints from PCAP analysis
- Applying learned fingerprints to devices
- Listing learned communication sequences
- Applying sequences to flows
- Auto-applying patterns to scenarios
"""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario
from app.models.device_template import DeviceTemplate, TemplateSource
from app.models.learned_sequence import LearnedSequence
from app.models.learned_protocol_pattern import LearnedProtocolPattern
from app.services.learned_pattern_service import LearnedPatternService


async def list_learned_fingerprints(
    db: AsyncSession,
    protocol_filter: str | None = None,
    vendor_filter: str | None = None,
) -> str:
    """List device fingerprints learned from PCAP analysis.

    Args:
        db: Database session
        protocol_filter: Filter by protocol
        vendor_filter: Filter by inferred vendor

    Returns:
        JSON string with fingerprints list
    """
    query = select(DeviceTemplate).where(
        DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
    )

    if protocol_filter:
        normalized = LearnedPatternService.normalize_protocol(protocol_filter)
        query = query.where(
            DeviceTemplate.active_protocols.contains([normalized])
        )

    if vendor_filter:
        query = query.where(
            DeviceTemplate.vendor.ilike(f"%{vendor_filter}%")
        )

    query = query.order_by(DeviceTemplate.confidence.desc())
    result = await db.execute(query)
    fingerprints = list(result.scalars().all())

    fingerprint_list = [
        {
            "id": str(fp.id),
            "name": fp.name,
            "inferred_vendor": fp.vendor,
            "device_type": fp.device_type,
            "role": fp.role,
            "active_protocols": fp.active_protocols,
            "oui_patterns": fp.oui_patterns,
            "observation_count": fp.sample_count or 0,
            "confidence": fp.confidence,
            "has_tcp_signature": fp.tcp_signature is not None,
            "has_response_timings": fp.response_timings is not None,
        }
        for fp in fingerprints
    ]

    return json.dumps({
        "fingerprints": fingerprint_list,
        "count": len(fingerprint_list),
    })


async def apply_learned_fingerprint_to_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    learned_fingerprint_id: str,
) -> str:
    """Apply a learned fingerprint (from PCAP analysis) to a device.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        learned_fingerprint_id: Learned fingerprint UUID

    Returns:
        JSON string with result
    """
    # Get the learned fingerprint (now stored as DeviceTemplate)
    fp_result = await db.execute(
        select(DeviceTemplate).where(
            DeviceTemplate.id == uuid.UUID(learned_fingerprint_id),
            DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
        )
    )
    fingerprint = fp_result.scalar_one_or_none()

    if not fingerprint:
        return json.dumps({"error": f"Learned fingerprint {learned_fingerprint_id} not found"})

    # Get scenario
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Apply learned fingerprint data (template, not specific device)
    device["learned_fingerprint"] = {
        "id": str(fingerprint.id),
        "name": fingerprint.name,
        "inferred_vendor": fingerprint.vendor,
        "device_type": fingerprint.device_type,
        "confidence": fingerprint.confidence,
        "oui_patterns": fingerprint.oui_patterns,
    }

    # Apply TCP signature if available
    if fingerprint.tcp_signature:
        device["tcp_stack"] = fingerprint.tcp_signature

    # Apply response timings if available
    if fingerprint.response_timings:
        # Get the first protocol's timing as the main timing
        for protocol, timing in fingerprint.response_timings.items():
            device["response_timing"] = {
                "protocol": protocol,
                "mean_ms": timing.get("mean_ms"),
                "min_ms": timing.get("min_ms"),
                "max_ms": timing.get("max_ms"),
                "std_dev_ms": timing.get("std_ms"),
            }
            break

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "applied_fingerprint": {
            "id": str(fingerprint.id),
            "inferred_vendor": fingerprint.vendor,
            "protocols": fingerprint.active_protocols,
        },
    })


async def list_learned_sequences(
    db: AsyncSession,
    protocol_filter: str | None = None,
    sequence_type_filter: str | None = None,
) -> str:
    """List communication sequences learned from PCAPs.

    Args:
        db: Database session
        protocol_filter: Filter by protocol
        sequence_type_filter: Filter by sequence type (startup, poll_cycle, shutdown)

    Returns:
        JSON string with sequences list
    """
    query = select(LearnedSequence)

    if protocol_filter:
        normalized = LearnedPatternService.normalize_protocol(protocol_filter)
        query = query.where(LearnedSequence.protocol == normalized)

    if sequence_type_filter:
        query = query.where(LearnedSequence.sequence_type == sequence_type_filter)

    query = query.order_by(LearnedSequence.confidence.desc())
    result = await db.execute(query)
    sequences = list(result.scalars().all())

    sequence_list = [
        {
            "id": str(seq.id),
            "name": seq.name,
            "protocol": seq.protocol,
            "sequence_type": seq.sequence_type,
            "step_count": seq.step_count,
            "average_duration_ms": seq.average_duration_ms,
            "repetition_interval_ms": seq.repetition_interval_ms,
            "confidence": seq.confidence,
            "pcap_capture_id": str(seq.pcap_capture_id) if seq.pcap_capture_id else None,
        }
        for seq in sequences
    ]

    return json.dumps({
        "sequences": sequence_list,
        "count": len(sequence_list),
    })


async def apply_sequence_to_flow(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    sequence_id: str,
) -> str:
    """Apply a learned sequence pattern to a flow.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        sequence_id: Learned sequence UUID

    Returns:
        JSON string with result
    """
    # Get the learned sequence
    seq_result = await db.execute(
        select(LearnedSequence).where(
            LearnedSequence.id == uuid.UUID(sequence_id)
        )
    )
    sequence = seq_result.scalar_one_or_none()

    if not sequence:
        return json.dumps({"error": f"Learned sequence {sequence_id} not found"})

    # Get scenario
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Apply sequence data
    flow["learned_sequence"] = {
        "id": str(sequence.id),
        "name": sequence.name,
        "sequence_type": sequence.sequence_type,
        "confidence": sequence.confidence,
    }

    # Apply timing from sequence
    if sequence.repetition_interval_ms:
        if "timing" not in flow:
            flow["timing"] = {}
        flow["timing"]["intervalMs"] = sequence.repetition_interval_ms

    if sequence.repetition_jitter_ms:
        if "realism" not in flow:
            flow["realism"] = {}
        flow["realism"]["timing_jitter_ms"] = sequence.repetition_jitter_ms

    # Apply steps as operations
    if sequence.steps:
        flow["learned_steps"] = sequence.steps

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "applied_sequence": {
            "id": str(sequence.id),
            "name": sequence.name,
            "sequence_type": sequence.sequence_type,
            "step_count": sequence.step_count,
        },
    })


async def auto_apply_learned_patterns(
    db: AsyncSession,
    scenario_id: str,
    match_threshold: float = 0.5,
) -> str:
    """Intelligently apply all relevant learned patterns to a scenario.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        match_threshold: Minimum confidence for pattern matching (0.0-1.0)

    Returns:
        JSON string with result
    """
    # Get scenario
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    devices_updated = 0
    flows_updated = 0
    patterns_applied = []

    # Get all learned fingerprints above threshold
    fp_result = await db.execute(
        select(DeviceTemplate).where(
            DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
            DeviceTemplate.confidence >= match_threshold,
        ).order_by(DeviceTemplate.confidence.desc())
    )
    fingerprints = list(fp_result.scalars().all())

    # Get all learned sequences above threshold
    seq_result = await db.execute(
        select(LearnedSequence).where(
            LearnedSequence.confidence >= match_threshold
        ).order_by(LearnedSequence.confidence.desc())
    )
    sequences = list(seq_result.scalars().all())

    # Match fingerprints to devices by protocol
    for device_id, device in devices.items():
        device_protocols = device.get("protocols", [])
        if not device_protocols:
            continue

        # Skip if already has learned fingerprint
        if device.get("learned_fingerprint"):
            continue

        # Find matching fingerprint
        for fp in fingerprints:
            if fp.active_protocols:
                # Check for protocol overlap
                matching_protocols = set(device_protocols) & set(fp.active_protocols)
                if matching_protocols:
                    # Apply fingerprint template
                    device = device.copy()
                    device["learned_fingerprint"] = {
                        "id": str(fp.id),
                        "name": fp.name,
                        "inferred_vendor": fp.vendor,
                        "device_type": fp.device_type,
                        "confidence": fp.confidence,
                        "oui_patterns": fp.oui_patterns,
                    }

                    if fp.tcp_signature:
                        device["tcp_stack"] = fp.tcp_signature

                    if fp.response_timings:
                        for protocol, timing in fp.response_timings.items():
                            if protocol in matching_protocols:
                                device["response_timing"] = {
                                    "protocol": protocol,
                                    "mean_ms": timing.get("mean_ms"),
                                    "std_dev_ms": timing.get("std_ms"),
                                }
                                break

                    devices[device_id] = device
                    devices_updated += 1
                    patterns_applied.append({
                        "type": "fingerprint",
                        "target": device_id,
                        "pattern_id": str(fp.id),
                        "confidence": fp.confidence,
                    })
                    break

    # Match sequences to flows by protocol
    for flow_id, flow in flows.items():
        flow_protocol = flow.get("protocol")
        if not flow_protocol:
            continue

        # Skip if already has learned sequence
        if flow.get("learned_sequence"):
            continue

        # Find matching poll_cycle sequence
        for seq in sequences:
            if seq.protocol == LearnedPatternService.normalize_protocol(flow_protocol):
                if seq.sequence_type == "poll_cycle":
                    # Apply sequence
                    flow = flow.copy()
                    flow["learned_sequence"] = {
                        "id": str(seq.id),
                        "name": seq.name,
                        "sequence_type": seq.sequence_type,
                        "confidence": seq.confidence,
                    }

                    if seq.repetition_interval_ms:
                        if "timing" not in flow:
                            flow["timing"] = {}
                        flow["timing"]["intervalMs"] = seq.repetition_interval_ms

                    if seq.repetition_jitter_ms:
                        if "realism" not in flow:
                            flow["realism"] = {}
                        flow["realism"]["timing_jitter_ms"] = seq.repetition_jitter_ms

                    flows[flow_id] = flow
                    flows_updated += 1
                    patterns_applied.append({
                        "type": "sequence",
                        "target": flow_id,
                        "pattern_id": str(seq.id),
                        "confidence": seq.confidence,
                    })
                    break

    definition["devices"] = devices
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "devices_updated": devices_updated,
        "flows_updated": flows_updated,
        "patterns_applied": patterns_applied,
        "match_threshold": match_threshold,
    })
