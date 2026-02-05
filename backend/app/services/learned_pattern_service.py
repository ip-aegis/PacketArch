"""Learned Pattern Service.

Provides functionality to query and apply learned patterns from PCAP analysis
to scenarios and traffic generation.
"""

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learned_protocol_pattern import LearnedProtocolPattern
from app.models.device_template import DeviceTemplate, TemplateSource
from app.models.learned_sequence import LearnedSequence


class LearnedPatternService:
    """Service for managing and applying learned patterns."""

    # Protocol mappings for matching
    PROTOCOL_ALIASES = {
        "modbus": ["modbus_tcp", "modbus"],
        "s7": ["s7comm", "s7"],
        "ethernet_ip": ["ethernet_ip", "enip", "cip"],
        "profinet": ["profinet", "pn"],
        "dnp3": ["dnp3"],
        "opcua": ["opcua", "opc_ua"],
    }

    @staticmethod
    def normalize_protocol(protocol: str) -> str:
        """Normalize protocol name to canonical form."""
        protocol_lower = protocol.lower().strip()
        for canonical, aliases in LearnedPatternService.PROTOCOL_ALIASES.items():
            if protocol_lower in aliases:
                return canonical
        return protocol_lower

    @staticmethod
    async def get_protocol_patterns(
        db: AsyncSession,
        protocol: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[LearnedProtocolPattern]:
        """Get learned protocol patterns, optionally filtered.

        Args:
            db: Database session
            protocol: Filter by protocol (normalized)
            min_confidence: Minimum confidence score

        Returns:
            List of matching LearnedProtocolPattern objects
        """
        query = select(LearnedProtocolPattern).where(
            LearnedProtocolPattern.confidence >= min_confidence
        )

        if protocol:
            normalized = LearnedPatternService.normalize_protocol(protocol)
            query = query.where(LearnedProtocolPattern.protocol == normalized)

        query = query.order_by(LearnedProtocolPattern.confidence.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_timing_model(
        db: AsyncSession,
        protocol: str,
    ) -> dict[str, Any] | None:
        """Get timing model from learned patterns for a protocol.

        Returns aggregated timing statistics across all learned patterns
        for realistic traffic generation.

        Args:
            db: Database session
            protocol: Protocol name

        Returns:
            Timing model dict or None if no patterns found
        """
        patterns = await LearnedPatternService.get_protocol_patterns(db, protocol)

        if not patterns:
            return None

        # Aggregate timing data across patterns
        all_timings = []
        for pattern in patterns:
            if pattern.timing_distributions:
                all_timings.append(pattern.timing_distributions)

        if not all_timings:
            return None

        # Calculate aggregate statistics
        # For now, use the highest-confidence pattern's timing
        best_pattern = patterns[0]  # Already sorted by confidence
        return {
            "protocol": protocol,
            "source_pattern_id": str(best_pattern.id),
            "timing": best_pattern.timing_distributions,
            "confidence": best_pattern.confidence,
        }

    @staticmethod
    async def get_function_code_distribution(
        db: AsyncSession,
        protocol: str,
    ) -> dict[str, Any] | None:
        """Get function code distribution for a protocol.

        Returns the distribution of function codes observed in learned
        traffic for realistic traffic generation.

        Args:
            db: Database session
            protocol: Protocol name

        Returns:
            Function code distribution dict or None
        """
        patterns = await LearnedPatternService.get_protocol_patterns(db, protocol)

        if not patterns:
            return None

        # Use highest-confidence pattern
        best_pattern = patterns[0]
        if not best_pattern.function_codes:
            return None

        return {
            "protocol": protocol,
            "source_pattern_id": str(best_pattern.id),
            "function_codes": best_pattern.function_codes,
            "sample_count": best_pattern.sample_count,
            "confidence": best_pattern.confidence,
        }

    @staticmethod
    async def get_address_patterns(
        db: AsyncSession,
        protocol: str,
    ) -> dict[str, Any] | None:
        """Get address/register patterns for a protocol.

        Returns the observed address ranges and access patterns
        for realistic traffic generation.

        Args:
            db: Database session
            protocol: Protocol name

        Returns:
            Address patterns dict or None
        """
        patterns = await LearnedPatternService.get_protocol_patterns(db, protocol)

        if not patterns:
            return None

        best_pattern = patterns[0]
        if not best_pattern.address_patterns:
            return None

        return {
            "protocol": protocol,
            "source_pattern_id": str(best_pattern.id),
            "address_patterns": best_pattern.address_patterns,
            "sample_count": best_pattern.sample_count,
            "confidence": best_pattern.confidence,
        }

    @staticmethod
    async def get_fingerprints_for_protocol(
        db: AsyncSession,
        protocol: str,
        role: str | None = None,
    ) -> list[DeviceTemplate]:
        """Get learned device fingerprints that use a specific protocol.

        Args:
            db: Database session
            protocol: Protocol name
            role: Optional filter by device role (master, slave, both)

        Returns:
            List of matching DeviceTemplate records (source=pcap_learned)
        """
        query = select(DeviceTemplate).where(
            DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
            DeviceTemplate.active_protocols.contains([protocol]),
        )

        if role:
            query = query.where(DeviceTemplate.role == role)

        query = query.order_by(DeviceTemplate.confidence.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_tcp_signature_model(
        db: AsyncSession,
        protocol: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any] | None:
        """Get aggregated TCP signature data for realistic packet crafting.

        Args:
            db: Database session
            protocol: Optional protocol filter
            role: Optional role filter

        Returns:
            TCP signature model or None
        """
        query = select(DeviceTemplate).where(
            DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
            DeviceTemplate.tcp_signature.isnot(None),
        )

        if protocol:
            query = query.where(
                DeviceTemplate.active_protocols.contains([protocol])
            )

        if role:
            query = query.where(DeviceTemplate.role == role)

        query = query.order_by(DeviceTemplate.confidence.desc()).limit(10)
        result = await db.execute(query)
        fingerprints = list(result.scalars().all())

        if not fingerprints:
            return None

        # Collect unique TCP signatures from fingerprint templates
        signatures = []
        for fp in fingerprints:
            if fp.tcp_signature:
                signatures.append({
                    "fingerprint_id": str(fp.id),
                    "signature": fp.tcp_signature,
                    "vendor": fp.vendor,
                    "device_type": fp.device_type,
                    "oui_patterns": fp.oui_patterns,
                    "observation_count": fp.sample_count or 0,
                })

        return {
            "protocol": protocol,
            "role": role,
            "signatures": signatures,
            "count": len(signatures),
        }

    @staticmethod
    async def get_response_timing_model(
        db: AsyncSession,
        protocol: str,
        role: str = "slave",
    ) -> dict[str, Any] | None:
        """Get response timing model for simulating realistic device responses.

        Args:
            db: Database session
            protocol: Protocol name
            role: Device role (typically "slave" for responders)

        Returns:
            Response timing model or None
        """
        fingerprints = await LearnedPatternService.get_fingerprints_for_protocol(
            db, protocol, role
        )

        if not fingerprints:
            return None

        # Aggregate response timings from fingerprint templates
        all_timings = []
        for fp in fingerprints:
            if fp.response_timings and protocol in fp.response_timings:
                timing = dict(fp.response_timings[protocol])  # Copy to avoid mutating
                timing["fingerprint_id"] = str(fp.id)
                timing["vendor"] = fp.inferred_vendor
                timing["device_type"] = fp.device_type
                all_timings.append(timing)

        if not all_timings:
            return None

        # Calculate aggregate statistics
        mean_values = [t.get("mean_ms", 0) for t in all_timings if "mean_ms" in t]
        min_values = [t.get("min_ms", 0) for t in all_timings if "min_ms" in t]
        max_values = [t.get("max_ms", 0) for t in all_timings if "max_ms" in t]

        return {
            "protocol": protocol,
            "role": role,
            "aggregate": {
                "mean_ms": sum(mean_values) / len(mean_values) if mean_values else 0,
                "min_ms": min(min_values) if min_values else 0,
                "max_ms": max(max_values) if max_values else 0,
            },
            "individual_timings": all_timings,
            "device_count": len(all_timings),
        }

    @staticmethod
    async def get_sequences_for_protocol(
        db: AsyncSession,
        protocol: str,
        sequence_type: str | None = None,
    ) -> list[LearnedSequence]:
        """Get learned sequences for a protocol.

        Args:
            db: Database session
            protocol: Protocol name
            sequence_type: Optional filter (startup, poll_cycle, etc.)

        Returns:
            List of matching sequences
        """
        query = select(LearnedSequence).where(
            LearnedSequence.protocol == protocol
        )

        if sequence_type:
            query = query.where(LearnedSequence.sequence_type == sequence_type)

        query = query.order_by(LearnedSequence.confidence.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_startup_sequence(
        db: AsyncSession,
        protocol: str,
    ) -> dict[str, Any] | None:
        """Get startup sequence for a protocol.

        Args:
            db: Database session
            protocol: Protocol name

        Returns:
            Startup sequence data or None
        """
        sequences = await LearnedPatternService.get_sequences_for_protocol(
            db, protocol, "startup"
        )

        if not sequences:
            return None

        best_sequence = sequences[0]
        return {
            "protocol": protocol,
            "sequence_id": str(best_sequence.id),
            "name": best_sequence.name,
            "steps": best_sequence.steps,
            "step_count": best_sequence.step_count,
            "average_duration_ms": best_sequence.average_duration_ms,
            "confidence": best_sequence.confidence,
        }

    @staticmethod
    async def get_poll_cycle_pattern(
        db: AsyncSession,
        protocol: str,
    ) -> dict[str, Any] | None:
        """Get poll cycle pattern for a protocol.

        Args:
            db: Database session
            protocol: Protocol name

        Returns:
            Poll cycle pattern data or None
        """
        sequences = await LearnedPatternService.get_sequences_for_protocol(
            db, protocol, "poll_cycle"
        )

        if not sequences:
            return None

        best_sequence = sequences[0]
        return {
            "protocol": protocol,
            "sequence_id": str(best_sequence.id),
            "name": best_sequence.name,
            "steps": best_sequence.steps,
            "step_count": best_sequence.step_count,
            "repetition_interval_ms": best_sequence.repetition_interval_ms,
            "repetition_jitter_ms": best_sequence.repetition_jitter_ms,
            "confidence": best_sequence.confidence,
        }

    @staticmethod
    async def suggest_patterns_for_device(
        db: AsyncSession,
        device_type: str,
        protocol: str,
    ) -> dict[str, Any]:
        """Suggest learned patterns that match a device configuration.

        Args:
            db: Database session
            device_type: Type of device (plc, hmi, rtu, etc.)
            protocol: Protocol the device uses

        Returns:
            Dict with suggested patterns for each category
        """
        normalized_protocol = LearnedPatternService.normalize_protocol(protocol)

        # Determine expected role based on device type
        role_mapping = {
            "plc": "slave",
            "rtu": "slave",
            "io_module": "slave",
            "sensor": "slave",
            "actuator": "slave",
            "hmi": "master",
            "scada": "master",
            "engineering_station": "master",
            "historian": "master",
        }
        expected_role = role_mapping.get(device_type.lower(), "both")

        # Get protocol patterns
        protocol_patterns = await LearnedPatternService.get_protocol_patterns(
            db, normalized_protocol
        )

        # Get fingerprints for role
        fingerprints = await LearnedPatternService.get_fingerprints_for_protocol(
            db, normalized_protocol, expected_role
        )
        if not fingerprints:
            # Fallback to any role
            fingerprints = await LearnedPatternService.get_fingerprints_for_protocol(
                db, normalized_protocol
            )

        # Get sequences
        sequences = await LearnedPatternService.get_sequences_for_protocol(
            db, normalized_protocol
        )

        return {
            "device_type": device_type,
            "protocol": normalized_protocol,
            "expected_role": expected_role,
            "suggestions": {
                "protocol_patterns": [
                    {
                        "id": str(p.id),
                        "sample_count": p.sample_count,
                        "confidence": p.confidence,
                        "has_function_codes": p.function_codes is not None,
                        "has_address_patterns": p.address_patterns is not None,
                        "has_timing": p.timing_distributions is not None,
                    }
                    for p in protocol_patterns[:5]
                ],
                "fingerprints": [
                    {
                        "id": str(f.id),
                        "name": f.name,
                        "vendor": f.inferred_vendor,
                        "device_type": f.device_type,
                        "role": f.role,
                        "has_tcp_signature": f.tcp_signature is not None,
                        "has_response_timings": f.response_timings is not None,
                        "observation_count": f.observation_count,
                        "confidence": f.confidence,
                    }
                    for f in fingerprints[:5]
                ],
                "sequences": [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "sequence_type": s.sequence_type,
                        "step_count": s.step_count,
                        "confidence": s.confidence,
                    }
                    for s in sequences[:5]
                ],
            },
        }

    @staticmethod
    async def get_pattern_stats(db: AsyncSession) -> dict[str, Any]:
        """Get statistics about available learned patterns.

        Args:
            db: Database session

        Returns:
            Statistics about patterns by protocol
        """
        # Count patterns by protocol
        pattern_result = await db.execute(
            select(
                LearnedProtocolPattern.protocol,
                func.count(LearnedProtocolPattern.id).label("count"),
                func.avg(LearnedProtocolPattern.confidence).label("avg_confidence"),
            ).group_by(LearnedProtocolPattern.protocol)
        )
        pattern_stats = {
            row[0]: {"count": row[1], "avg_confidence": float(row[2] or 0)}
            for row in pattern_result.fetchall()
        }

        # Count fingerprints by protocol
        fingerprint_result = await db.execute(
            select(DeviceTemplate).where(
                DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
            )
        )
        fingerprints = fingerprint_result.scalars().all()

        fingerprint_by_protocol: dict[str, int] = {}
        for fp in fingerprints:
            if fp.active_protocols:
                for proto in fp.active_protocols:
                    fingerprint_by_protocol[proto] = fingerprint_by_protocol.get(proto, 0) + 1

        # Count sequences by protocol and type
        sequence_result = await db.execute(
            select(
                LearnedSequence.protocol,
                LearnedSequence.sequence_type,
                func.count(LearnedSequence.id).label("count"),
            ).group_by(LearnedSequence.protocol, LearnedSequence.sequence_type)
        )
        sequence_stats: dict[str, dict[str, int]] = {}
        for row in sequence_result.fetchall():
            proto = row[0]
            seq_type = row[1]
            count = row[2]
            if proto not in sequence_stats:
                sequence_stats[proto] = {}
            sequence_stats[proto][seq_type] = count

        return {
            "protocol_patterns": pattern_stats,
            "device_fingerprints": fingerprint_by_protocol,
            "sequences": sequence_stats,
        }
