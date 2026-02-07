"""Business logic for Learning API - PCAP processing and pattern management.

This module contains the background processing logic and helper functions
that were extracted from the learning routes file.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_services.pcap_analyzer import PcapAnalyzer
from app.models.device_template import DeviceTemplate, TemplateSource
from app.models.learned_pattern import DistributionType, LearnedPattern, PatternType
from app.models.learned_protocol_pattern import LearnedProtocolPattern
from app.models.learned_sequence import LearnedSequence
from app.models.pcap_capture import PcapCapture, ProcessingStatus
from app.schemas.learning import DeviceFingerprintResponse

logger = logging.getLogger(__name__)


def template_to_fingerprint_response(fp: DeviceTemplate) -> DeviceFingerprintResponse:
    """Convert DeviceTemplate to DeviceFingerprintResponse for API backward compat."""
    return DeviceFingerprintResponse(
        id=str(fp.id),
        pcap_capture_id=str(fp.source_pcap_id) if fp.source_pcap_id else None,
        inferred_vendor=fp.vendor,
        device_type=fp.device_type,
        oui_patterns=fp.oui_patterns,
        tcp_signature=fp.tcp_signature,
        response_timings=fp.response_timings,
        protocol_identities=fp.protocol_identities,
        role=fp.role or "unknown",
        active_protocols=fp.active_protocols,
        typical_ports=fp.typical_ports,
        observation_count=fp.sample_count or 0,
        total_packets_analyzed=0,
        confidence=fp.confidence or 0.0,
        consistency_score=fp.consistency_score or 1.0,
        name=fp.name,
        tags=fp.tags,
        created_at=fp.created_at,
    )


async def process_pcap(capture_id: str) -> None:
    """Process a PCAP file in the background.

    This function creates its own database session since it runs
    as a background task outside the request lifecycle.
    """
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        try:
            # Get capture record
            result = await db.execute(
                select(PcapCapture).where(PcapCapture.id == uuid.UUID(capture_id))
            )
            capture = result.scalar_one_or_none()

            if not capture:
                logger.error(f"Capture {capture_id} not found")
                return

            # Update status
            capture.status = ProcessingStatus.PROCESSING
            await db.commit()

            # Analyze PCAP
            analyzer = PcapAnalyzer()
            results = analyzer.analyze_file(capture.file_path)

            if "error" in results:
                capture.status = ProcessingStatus.FAILED
                capture.error_message = results["error"]
                await db.commit()
                return

            # Update capture with results
            capture.packet_count = results["packet_count"]
            capture.flow_count = results["flow_count"]
            capture.capture_duration_ms = results["capture_duration_ms"]
            capture.protocol_stats = results["protocol_stats"]
            capture.devices_detected = results["devices_detected"]
            capture.status = ProcessingStatus.COMPLETED
            capture.processed_at = datetime.utcnow()

            # Collect all objects for batch insert
            new_objects: list = []

            # Create learned patterns (timing)
            for pattern_data in results.get("timing_patterns", []):
                new_objects.append(LearnedPattern(
                    pcap_capture_id=capture.id,
                    name=pattern_data["name"],
                    pattern_type=PatternType(pattern_data["pattern_type"]),
                    protocol=pattern_data["protocol"],
                    source_ip=pattern_data.get("source_ip"),
                    destination_ip=pattern_data.get("destination_ip"),
                    source_port=pattern_data.get("source_port"),
                    destination_port=pattern_data.get("destination_port"),
                    distribution_type=DistributionType(pattern_data["distribution_type"]),
                    timing_params=pattern_data.get("timing_params"),
                    sample_count=pattern_data["sample_count"],
                    min_value=pattern_data.get("min_value"),
                    max_value=pattern_data.get("max_value"),
                    mean_value=pattern_data.get("mean_value"),
                    std_dev=pattern_data.get("std_dev"),
                    fit_score=pattern_data.get("fit_score"),
                    confidence=pattern_data.get("confidence", 0),
                ))

            # Create learned patterns (payload)
            for pattern_data in results.get("payload_patterns", []):
                new_objects.append(LearnedPattern(
                    pcap_capture_id=capture.id,
                    name=pattern_data["name"],
                    pattern_type=PatternType(pattern_data["pattern_type"]),
                    protocol=pattern_data["protocol"],
                    source_ip=pattern_data.get("source_ip"),
                    destination_ip=pattern_data.get("destination_ip"),
                    payload_patterns=pattern_data.get("payload_patterns"),
                    sample_count=pattern_data["sample_count"],
                    confidence=pattern_data.get("confidence", 0),
                ))

            # Store enhanced protocol patterns
            for proto_data in results.get("protocol_patterns", []):
                # S7-specific fields go in protocol_metadata
                s7_metadata = {}
                if proto_data.get("pdu_sizes"):
                    s7_metadata["pdu_sizes"] = proto_data["pdu_sizes"]
                if proto_data.get("rack_slot_configs"):
                    s7_metadata["rack_slot_configs"] = proto_data["rack_slot_configs"]
                if proto_data.get("memory_areas"):
                    s7_metadata["memory_areas"] = proto_data["memory_areas"]

                new_objects.append(LearnedProtocolPattern(
                    pcap_capture_id=capture.id,
                    protocol=proto_data["protocol"],
                    function_codes=proto_data.get("function_codes"),
                    address_patterns=proto_data.get("address_patterns"),
                    payload_structures=proto_data.get("payload_structures"),
                    request_response_pairs=proto_data.get("request_response_pairs"),
                    unit_id_distribution=proto_data.get("unit_id_distribution"),
                    exception_patterns=proto_data.get("exception_patterns"),
                    device_identities=proto_data.get("device_identities"),
                    protocol_metadata=s7_metadata if s7_metadata else None,
                    sample_count=proto_data.get("packet_count", proto_data.get("sample_count", 0)),
                ))

            # Store device fingerprint templates (aggregated, not per-device)
            for fp_data in results.get("device_fingerprints", []):
                # Get role value - ensure lowercase for PostgreSQL enum
                role_str = fp_data.get("role", "unknown").lower()
                if role_str not in ("master", "slave", "both", "unknown"):
                    role_str = "unknown"

                new_objects.append(DeviceTemplate(
                    source=TemplateSource.PCAP_LEARNED.value,
                    source_pcap_id=capture.id,
                    vendor=fp_data.get("inferred_vendor"),
                    device_type=fp_data.get("device_type"),
                    oui_patterns=fp_data.get("oui_patterns"),
                    tcp_signature=fp_data.get("tcp_signature"),
                    response_timings=fp_data.get("response_timings"),
                    protocol_identities=fp_data.get("protocol_identities"),
                    role=role_str,
                    active_protocols=fp_data.get("active_protocols", []),
                    typical_ports=fp_data.get("typical_ports"),
                    sample_count=fp_data.get("observation_count", 1),
                    confidence=fp_data.get("confidence", 0.0),
                    consistency_score=fp_data.get("consistency_score", 1.0),
                    name=fp_data.get("name"),
                    is_active=True,
                ))

            # Store learned sequences
            valid_sequence_types = {
                "startup", "shutdown", "poll_cycle", "write_sequence",
                "error_recovery", "state_transition", "heartbeat", "alarm"
            }
            for seq_data in results.get("learned_sequences", []):
                seq_type = seq_data.get("sequence_type", "").lower()
                if seq_type not in valid_sequence_types:
                    continue  # Skip invalid sequence types

                new_objects.append(LearnedSequence(
                    pcap_capture_id=capture.id,
                    name=seq_data["name"],
                    sequence_type=seq_type,
                    protocol=seq_data["protocol"],
                    initiator_ip=seq_data.get("initiator_ip"),
                    responder_ip=seq_data.get("responder_ip"),
                    steps=seq_data.get("steps"),
                    step_count=seq_data.get("step_count", 0),
                    average_duration_ms=seq_data.get("average_duration_ms"),
                    timing_variance=seq_data.get("timing_variance"),
                    inter_step_timings=seq_data.get("inter_step_timings"),
                    repetition_interval_ms=seq_data.get("repetition_interval_ms"),
                    repetition_jitter_ms=seq_data.get("repetition_jitter_ms"),
                    occurrence_count=seq_data.get("occurrence_count", 0),
                    confidence=seq_data.get("confidence", 0.0),
                ))

            # Batch insert all objects
            if new_objects:
                db.add_all(new_objects)
            await db.commit()

            # Invalidate fingerprint cache so new learned data is visible
            from app.services.fingerprint_cache import invalidate_fingerprint_cache
            invalidate_fingerprint_cache()

            logger.info(f"Successfully processed PCAP {capture_id}")

        except Exception as e:
            logger.exception(f"Failed to process PCAP {capture_id}: {e}")
            try:
                result = await db.execute(
                    select(PcapCapture).where(PcapCapture.id == uuid.UUID(capture_id))
                )
                capture = result.scalar_one_or_none()
                if capture:
                    capture.status = ProcessingStatus.FAILED
                    capture.error_message = str(e)
                    await db.commit()
            except Exception:
                pass


async def apply_session_patterns_to_scenario(
    db: AsyncSession,
    session,
    scenario,
    apply_fingerprints: bool,
    apply_timing: bool,
    apply_sequences: bool,
    min_confidence: float,
) -> dict:
    """Apply learned patterns from a session to a scenario.

    Args:
        db: Database session
        session: LearningSession instance
        scenario: Scenario instance
        apply_fingerprints: Whether to apply fingerprint data
        apply_timing: Whether to apply timing data
        apply_sequences: Whether to apply sequence data
        min_confidence: Minimum confidence threshold

    Returns:
        Dict with counts of applied patterns
    """
    # Get all fingerprints from captures in this session (single query)
    capture_ids = [c.id for c in session.pcap_captures]
    if capture_ids:
        fps_result = await db.execute(
            select(DeviceTemplate).where(
                DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
                DeviceTemplate.source_pcap_id.in_(capture_ids),
                DeviceTemplate.confidence >= min_confidence,
            )
        )
        fingerprints = list(fps_result.scalars().all())
    else:
        fingerprints = []

    # Get all sequences from captures in this session (single query)
    sequences = []
    if apply_sequences and capture_ids:
        seqs_result = await db.execute(
            select(LearnedSequence).where(
                LearnedSequence.pcap_capture_id.in_(capture_ids),
                LearnedSequence.confidence >= min_confidence,
            )
        )
        sequences = list(seqs_result.scalars().all())

    # Apply patterns to scenario devices
    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    devices_updated = 0
    patterns_applied = 0
    fingerprints_applied = 0
    sequences_applied = 0

    # Build device -> protocol mapping from flows
    device_protocols: dict[str, set[str]] = {}
    for flow in flows.values():
        source_id = flow.get("sourceDeviceId") or flow.get("source_device_id")
        target_id = flow.get("targetDeviceId") or flow.get("target_device_id")
        protocol = flow.get("protocol", "").lower()

        if protocol:
            if source_id:
                device_protocols.setdefault(source_id, set()).add(protocol)
            if target_id:
                device_protocols.setdefault(target_id, set()).add(protocol)

    # Apply fingerprints to matching devices
    for device_id, device in devices.items():
        protocols = device_protocols.get(device_id, set())

        if not protocols:
            continue

        device_updated = False

        # Find best matching fingerprint
        for fp in fingerprints:
            fp_protocols = set(fp.active_protocols or [])
            if not protocols.intersection(fp_protocols):
                continue

            # Apply fingerprint data
            if apply_fingerprints:
                if fp.tcp_signature:
                    device.setdefault("learned_fingerprint", {})["tcp_signature"] = fp.tcp_signature
                if fp.response_timings and apply_timing:
                    device.setdefault("learned_fingerprint", {})["response_timings"] = fp.response_timings
                if fp.protocol_identities:
                    device.setdefault("learned_fingerprint", {})["protocol_identities"] = fp.protocol_identities
                fingerprints_applied += 1
                device_updated = True
                break  # Use first matching fingerprint

        # Apply sequences
        if apply_sequences:
            device_sequences = []
            for seq in sequences:
                if seq.protocol.lower() in protocols:
                    device_sequences.append({
                        "id": str(seq.id),
                        "name": seq.name,
                        "type": str(seq.sequence_type),
                        "protocol": seq.protocol,
                        "steps": seq.steps,
                    })
                    sequences_applied += 1

            if device_sequences:
                device["learned_sequences"] = device_sequences
                device_updated = True

        if device_updated:
            devices_updated += 1
            patterns_applied += 1

    # Update scenario
    definition["devices"] = devices
    scenario.definition = definition
    scenario.version += 1

    await db.flush()

    return {
        "devices_updated": devices_updated,
        "patterns_applied": patterns_applied,
        "fingerprints_applied": fingerprints_applied,
        "sequences_applied": sequences_applied,
    }
