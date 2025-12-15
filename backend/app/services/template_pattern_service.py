"""Service to apply learned patterns to scenario templates.

This service enhances scenarios created from templates with learned patterns
extracted from PCAP analysis, providing hyper-realistic traffic generation.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.learned_pattern_service import LearnedPatternService
from app.scenario_templates.base import (
    LEARNED_DEFAULTS,
    get_learned_defaults,
)

logger = logging.getLogger(__name__)


class TemplatePatternService:
    """Service to apply learned patterns to scenario templates."""

    @staticmethod
    async def enhance_scenario_from_learned(
        db: AsyncSession,
        scenario_definition: dict,
        apply_timing: bool = True,
        apply_fingerprints: bool = True,
        apply_sequences: bool = True,
        apply_function_codes: bool = True,
        apply_address_patterns: bool = True,
    ) -> dict:
        """Enhance a scenario definition with learned patterns.

        Args:
            db: Database session
            scenario_definition: The scenario definition dict containing devices, flows, zones
            apply_timing: Whether to apply learned timing parameters
            apply_fingerprints: Whether to apply learned device fingerprints
            apply_sequences: Whether to apply learned operation sequences
            apply_function_codes: Whether to apply learned function code distributions
            apply_address_patterns: Whether to apply learned address patterns

        Returns:
            Enhanced scenario definition with learned patterns applied
        """
        logger.info("Enhancing scenario with learned patterns")

        # Track what protocols are in use
        protocols_in_use = set()

        # 1. Enhance device configurations
        devices = scenario_definition.get("devices", {})
        for device_id, device in devices.items():
            device_type = device.get("type", "")
            device_protocols = device.get("protocols", [])

            if not device_protocols:
                continue

            primary_protocol = device_protocols[0]
            protocols_in_use.add(primary_protocol)

            # Get suggestions for this device
            try:
                suggestions = await LearnedPatternService.suggest_patterns_for_device(
                    db, device_type, primary_protocol
                )

                if apply_fingerprints and suggestions.get("fingerprints"):
                    # Store the best matching fingerprint
                    best_fp = suggestions["fingerprints"][0]
                    device["learned_fingerprint"] = {
                        "id": best_fp.get("id"),
                        "tcp_signature": best_fp.get("tcp_signature"),
                        "response_timings": best_fp.get("response_timings"),
                        "inferred_vendor": best_fp.get("inferred_vendor"),
                        "role": best_fp.get("role"),
                    }
                    logger.debug(f"Applied fingerprint to device {device_id}")

            except Exception as e:
                logger.warning(f"Failed to get suggestions for device {device_id}: {e}")

        # 2. Enhance flow configurations
        flows = scenario_definition.get("flows", {})
        for flow_id, flow in flows.items():
            protocol = flow.get("protocol", "")
            if not protocol:
                continue

            protocols_in_use.add(protocol)

            # Get learned defaults for this protocol
            learned = get_learned_defaults(protocol)

            if apply_timing and learned:
                # Merge learned timing into flow
                timing = flow.get("timing", {})

                # Apply learned timing if available
                learned_timing = {
                    "source": "learned",
                    "protocol": protocol,
                }

                if "poll_interval_ms" in learned:
                    learned_timing["intervalMs"] = learned["poll_interval_ms"]
                if "jitter_ms" in learned:
                    learned_timing["jitterMs"] = learned["jitter_ms"]
                if "jitter_type" in learned:
                    learned_timing["jitterType"] = learned["jitter_type"]
                if "response_time_ms" in learned:
                    learned_timing["responseTimeMs"] = learned["response_time_ms"]

                flow["learned_timing"] = learned_timing

            # Apply function code distribution
            if apply_function_codes and learned and "function_codes" in learned:
                flow["learned_function_codes"] = learned["function_codes"]
                logger.debug(f"Applied function codes to flow {flow_id}")

            # Apply address patterns
            if apply_address_patterns and learned and "address_ranges" in learned:
                flow["learned_address_patterns"] = learned["address_ranges"]
                logger.debug(f"Applied address patterns to flow {flow_id}")

            # Try to get more specific patterns from database
            try:
                # Get timing model from learned patterns
                if apply_timing:
                    timing_model = await LearnedPatternService.get_timing_model(db, protocol)
                    if timing_model and timing_model.get("timing"):
                        # Merge with existing learned_timing
                        if "learned_timing" not in flow:
                            flow["learned_timing"] = {}
                        flow["learned_timing"]["db_timing"] = timing_model["timing"]
                        flow["learned_timing"]["confidence"] = timing_model.get("confidence", 0)

                # Get function code distribution
                if apply_function_codes:
                    fc_dist = await LearnedPatternService.get_function_code_distribution(
                        db, protocol
                    )
                    if fc_dist and fc_dist.get("function_codes"):
                        flow["learned_function_codes"] = fc_dist["function_codes"]

                # Get address patterns
                if apply_address_patterns:
                    addr_patterns = await LearnedPatternService.get_address_patterns(
                        db, protocol
                    )
                    if addr_patterns and addr_patterns.get("address_patterns"):
                        flow["learned_address_patterns"] = addr_patterns["address_patterns"]

            except Exception as e:
                logger.warning(f"Failed to get patterns for flow {flow_id}: {e}")

        # 3. Add learned sequences to scenario
        if apply_sequences:
            learned_sequences = {}

            for protocol in protocols_in_use:
                try:
                    # Get startup sequence
                    startup = await LearnedPatternService.get_startup_sequence(db, protocol)
                    if startup and startup.get("steps"):
                        if protocol not in learned_sequences:
                            learned_sequences[protocol] = {}
                        learned_sequences[protocol]["startup"] = startup

                    # Get poll cycle pattern
                    poll_cycle = await LearnedPatternService.get_poll_cycle_pattern(db, protocol)
                    if poll_cycle and poll_cycle.get("steps"):
                        if protocol not in learned_sequences:
                            learned_sequences[protocol] = {}
                        learned_sequences[protocol]["poll_cycle"] = poll_cycle

                except Exception as e:
                    logger.warning(f"Failed to get sequences for protocol {protocol}: {e}")

            if learned_sequences:
                scenario_definition["learned_sequences"] = learned_sequences
                logger.info(f"Added learned sequences for protocols: {list(learned_sequences.keys())}")

        # 4. Add metadata about learned pattern application
        scenario_definition["learned_patterns_applied"] = {
            "timing": apply_timing,
            "fingerprints": apply_fingerprints,
            "sequences": apply_sequences,
            "function_codes": apply_function_codes,
            "address_patterns": apply_address_patterns,
            "protocols_enhanced": list(protocols_in_use),
        }

        return scenario_definition

    @staticmethod
    def get_static_learned_defaults() -> dict[str, dict[str, Any]]:
        """Get the static learned defaults without database access.

        Useful for quick lookups when database access isn't needed.

        Returns:
            Dict of learned defaults by protocol
        """
        return LEARNED_DEFAULTS

    @staticmethod
    def merge_learned_with_template_flow(
        flow_spec: dict,
        protocol: str,
    ) -> dict:
        """Merge learned defaults into a template flow specification.

        This is used during template-to-scenario conversion to apply
        static learned defaults without database access.

        Args:
            flow_spec: The flow specification from template
            protocol: Protocol name

        Returns:
            Enhanced flow spec with learned defaults
        """
        learned = get_learned_defaults(protocol)
        if not learned:
            return flow_spec

        result = flow_spec.copy()

        # Apply learned timing if flow doesn't override
        if "interval_ms" not in flow_spec or flow_spec.get("use_learned_timing", False):
            if "poll_interval_ms" in learned:
                result["interval_ms"] = learned["poll_interval_ms"]

        if "jitter_ms" not in flow_spec or flow_spec.get("use_learned_timing", False):
            if "jitter_ms" in learned:
                result["jitter_ms"] = learned["jitter_ms"]
            if "jitter_type" in learned:
                result["jitter_type"] = learned["jitter_type"]

        # Add learned function codes and address patterns as flags
        if learned.get("function_codes"):
            result["learned_function_codes"] = True
        if learned.get("address_ranges"):
            result["learned_address_ranges"] = True

        return result

    @staticmethod
    async def get_pattern_stats_for_scenario(
        db: AsyncSession,
        scenario_definition: dict,
    ) -> dict:
        """Get statistics about available learned patterns for a scenario.

        Args:
            db: Database session
            scenario_definition: The scenario definition

        Returns:
            Dict with pattern availability statistics
        """
        stats = {
            "protocols": {},
            "total_patterns_available": 0,
            "total_fingerprints_available": 0,
            "total_sequences_available": 0,
        }

        # Collect protocols from flows
        protocols = set()
        for flow in scenario_definition.get("flows", {}).values():
            if flow.get("protocol"):
                protocols.add(flow["protocol"])

        # Get stats for each protocol
        try:
            pattern_stats = await LearnedPatternService.get_pattern_stats(db)

            for protocol in protocols:
                proto_stats = {
                    "has_timing": False,
                    "has_function_codes": False,
                    "has_address_patterns": False,
                    "has_fingerprints": False,
                    "has_sequences": False,
                    "static_defaults": protocol in LEARNED_DEFAULTS,
                }

                # Check static defaults
                learned = get_learned_defaults(protocol)
                if learned:
                    proto_stats["has_timing"] = True
                    proto_stats["has_function_codes"] = "function_codes" in learned
                    proto_stats["has_address_patterns"] = "address_ranges" in learned

                # Check database patterns
                if pattern_stats:
                    proto_key = protocol.lower()
                    if proto_key in pattern_stats.get("protocol_patterns", {}):
                        db_stats = pattern_stats["protocol_patterns"][proto_key]
                        proto_stats["pattern_count"] = db_stats.get("count", 0)
                        proto_stats["avg_confidence"] = db_stats.get("avg_confidence", 0)
                        stats["total_patterns_available"] += db_stats.get("count", 0)

                    if proto_key in pattern_stats.get("device_fingerprints", {}):
                        fp_count = pattern_stats["device_fingerprints"][proto_key]
                        proto_stats["has_fingerprints"] = fp_count > 0
                        proto_stats["fingerprint_count"] = fp_count
                        stats["total_fingerprints_available"] += fp_count

                    if proto_key in pattern_stats.get("sequences", {}):
                        seq_stats = pattern_stats["sequences"][proto_key]
                        proto_stats["has_sequences"] = True
                        proto_stats["sequence_types"] = list(seq_stats.keys())
                        stats["total_sequences_available"] += sum(
                            s.get("count", 0) for s in seq_stats.values()
                        )

                stats["protocols"][protocol] = proto_stats

        except Exception as e:
            logger.warning(f"Failed to get pattern stats: {e}")

        return stats
