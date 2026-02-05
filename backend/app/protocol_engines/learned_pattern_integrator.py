"""Learned pattern integrator for protocol engines.

Transforms learned patterns from PCAP analysis into formats usable by
protocol engines for realistic traffic generation.
"""

import random
from dataclasses import dataclass
from typing import Any

from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY


@dataclass
class LearnedTimingConfig:
    """Timing configuration derived from learned patterns."""

    mean_response_ms: float = 2.0
    min_response_ms: float = 0.5
    max_response_ms: float = 10.0
    std_dev_ms: float = 1.0
    poll_interval_ms: float = 100.0
    poll_jitter_ms: float = 10.0

    def sample_response_delay(self) -> float:
        """Sample a response delay using the learned distribution."""
        # Use normal distribution clamped to min/max
        delay = random.gauss(self.mean_response_ms, self.std_dev_ms)
        return max(self.min_response_ms, min(self.max_response_ms, delay))

    def sample_poll_interval(self) -> float:
        """Sample a poll interval with jitter."""
        return self.poll_interval_ms + random.uniform(-self.poll_jitter_ms, self.poll_jitter_ms)


@dataclass
class LearnedFunctionCodeConfig:
    """Function code configuration derived from learned patterns."""

    distribution: dict[int, float]  # function_code -> probability

    def sample_function_code(self) -> int:
        """Sample a function code based on learned distribution."""
        if not self.distribution:
            return 3  # Default to read holding registers

        # Weighted random selection
        codes = list(self.distribution.keys())
        weights = list(self.distribution.values())
        total = sum(weights)
        weights = [w / total for w in weights]  # Normalize

        return random.choices(codes, weights=weights, k=1)[0]


@dataclass
class LearnedAddressConfig:
    """Address/register configuration derived from learned patterns."""

    ranges: list[dict]  # [{start, end, access_count}]
    common_addresses: list[int]

    def sample_address_range(self) -> tuple[int, int]:
        """Sample an address range based on learned patterns."""
        if self.ranges:
            # Weight by access count
            total_access = sum(r.get("access_count", 1) for r in self.ranges)
            weights = [r.get("access_count", 1) / total_access for r in self.ranges]
            selected = random.choices(self.ranges, weights=weights, k=1)[0]
            return selected.get("start", 0), selected.get("end", 100)

        return 0, 100  # Default range


class LearnedPatternIntegrator:
    """Integrates learned patterns into protocol engine configurations."""

    @staticmethod
    def extract_tcp_signature(learned_fingerprint: dict | None) -> dict[str, Any]:
        """Extract TCP signature configuration from learned fingerprint.

        Args:
            learned_fingerprint: Fingerprint data from scenario definition

        Returns:
            TCP signature config for FingerprintApplicator
        """
        if not learned_fingerprint:
            return {}

        tcp_sig = learned_fingerprint.get("tcp_signature", {})
        if not tcp_sig:
            return {}

        return {
            "ttl": tcp_sig.get("ttl", 64),
            "window_size": tcp_sig.get("window_size", 65535),
            "mss": tcp_sig.get("mss", 1460),
            "options": tcp_sig.get("options", []),
            "df_flag": tcp_sig.get("df_flag", True),
            "vendor": learned_fingerprint.get("inferred_vendor"),
        }

    @staticmethod
    def extract_timing_config(
        learned_fingerprint: dict | None,
        learned_pattern: dict | None,
        protocol: str,
    ) -> LearnedTimingConfig:
        """Extract timing configuration from learned data.

        Args:
            learned_fingerprint: Device fingerprint with response timings
            learned_pattern: Protocol pattern with timing distributions
            protocol: Protocol name for lookup

        Returns:
            LearnedTimingConfig with timing parameters
        """
        config = LearnedTimingConfig()

        # Extract from fingerprint response timings
        if learned_fingerprint:
            response_timings = learned_fingerprint.get("response_timings", {})
            proto_timing = response_timings.get(protocol, {})

            if proto_timing:
                config.mean_response_ms = proto_timing.get("mean_ms", config.mean_response_ms)
                config.min_response_ms = proto_timing.get("min_ms", config.min_response_ms)
                config.max_response_ms = proto_timing.get("max_ms", config.max_response_ms)
                config.std_dev_ms = proto_timing.get("std_ms", config.std_dev_ms)

        # Extract from protocol pattern timing distributions
        if learned_pattern:
            timing_dist = learned_pattern.get("timing_distributions", {})
            if timing_dist:
                # Handle various timing format possibilities
                inter_packet = timing_dist.get("inter_packet_timing", {})
                if inter_packet:
                    config.poll_interval_ms = inter_packet.get("mean_ms", config.poll_interval_ms)
                    config.poll_jitter_ms = inter_packet.get("std_ms", config.poll_jitter_ms)

                response_timing = timing_dist.get("response_timing", {})
                if response_timing:
                    config.mean_response_ms = response_timing.get("mean_ms", config.mean_response_ms)
                    config.min_response_ms = response_timing.get("min_ms", config.min_response_ms)
                    config.max_response_ms = response_timing.get("max_ms", config.max_response_ms)

        return config

    @staticmethod
    def extract_function_code_config(
        learned_pattern: dict | None,
    ) -> LearnedFunctionCodeConfig | None:
        """Extract function code distribution from learned pattern.

        Uses standardized normalization to handle various input formats.

        Args:
            learned_pattern: Protocol pattern with function code data

        Returns:
            LearnedFunctionCodeConfig or None
        """
        if not learned_pattern:
            return None

        function_codes = learned_pattern.get("function_codes", {})
        if not function_codes:
            return None

        # Use standardized normalization
        from app.ai_services.pattern_normalizers import extract_function_code_probabilities

        distribution = extract_function_code_probabilities(function_codes)

        if not distribution:
            return None

        return LearnedFunctionCodeConfig(distribution=distribution)

    @staticmethod
    def extract_address_config(
        learned_pattern: dict | None,
    ) -> LearnedAddressConfig | None:
        """Extract address/register patterns from learned pattern.

        Args:
            learned_pattern: Protocol pattern with address data

        Returns:
            LearnedAddressConfig or None
        """
        if not learned_pattern:
            return None

        address_patterns = learned_pattern.get("address_patterns", {})
        if not address_patterns:
            return None

        ranges = []
        common_addresses = []

        # Extract register ranges
        register_ranges = address_patterns.get("register_ranges", [])
        if isinstance(register_ranges, list):
            for r in register_ranges:
                if isinstance(r, dict):
                    ranges.append({
                        "start": r.get("start", r.get("min", 0)),
                        "end": r.get("end", r.get("max", 100)),
                        "access_count": r.get("access_count", r.get("count", 1)),
                    })

        # Extract common addresses
        common = address_patterns.get("common_addresses", [])
        if isinstance(common, list):
            common_addresses = [int(a) for a in common if isinstance(a, (int, float))]

        # Also check for holding_registers, input_registers formats
        for reg_type in ["holding_registers", "input_registers", "coils", "discrete_inputs"]:
            reg_data = address_patterns.get(reg_type, {})
            if isinstance(reg_data, dict) and "ranges" in reg_data:
                for r in reg_data["ranges"]:
                    if isinstance(r, dict):
                        ranges.append({
                            "start": r.get("start", 0),
                            "end": r.get("end", 100),
                            "access_count": r.get("count", 1),
                        })

        if not ranges and not common_addresses:
            return None

        return LearnedAddressConfig(ranges=ranges, common_addresses=common_addresses)

    @staticmethod
    def build_flow_config(
        base_config: dict,
        learned_pattern: dict | None,
        use_learned_function_codes: bool = True,
        use_learned_addresses: bool = True,
    ) -> dict:
        """Build flow configuration using learned patterns.

        Args:
            base_config: Base flow configuration
            learned_pattern: Learned protocol pattern data
            use_learned_function_codes: Whether to use learned function codes
            use_learned_addresses: Whether to use learned addresses

        Returns:
            Enhanced flow configuration
        """
        config = dict(base_config)

        if not learned_pattern:
            return config

        # Apply learned function codes
        if use_learned_function_codes:
            fc_config = LearnedPatternIntegrator.extract_function_code_config(learned_pattern)
            if fc_config:
                # Store distribution for sampling during generation
                config["learned_function_code_distribution"] = fc_config.distribution
                # Optionally override static function code
                if "function_code" not in config or config.get("use_dynamic_function_codes"):
                    config["function_code"] = fc_config.sample_function_code()

        # Apply learned addresses
        if use_learned_addresses:
            addr_config = LearnedPatternIntegrator.extract_address_config(learned_pattern)
            if addr_config:
                config["learned_address_config"] = {
                    "ranges": addr_config.ranges,
                    "common_addresses": addr_config.common_addresses,
                }
                # Optionally set start address from learned ranges
                if "start_address" not in config and addr_config.ranges:
                    start, end = addr_config.sample_address_range()
                    config["start_address"] = start
                    config["quantity"] = min(end - start + 1, 125)  # Max 125 for Modbus

        return config

    @staticmethod
    def build_timing_model(
        base_timing: dict,
        learned_fingerprint: dict | None,
        learned_pattern: dict | None,
        protocol: str,
    ) -> dict:
        """Build timing model using learned patterns.

        Args:
            base_timing: Base timing model
            learned_fingerprint: Device fingerprint data
            learned_pattern: Protocol pattern data
            protocol: Protocol name

        Returns:
            Enhanced timing model
        """
        timing = dict(base_timing)

        timing_config = LearnedPatternIntegrator.extract_timing_config(
            learned_fingerprint, learned_pattern, protocol
        )

        # Merge learned timing
        timing["learned_timing"] = {
            "mean_response_ms": timing_config.mean_response_ms,
            "min_response_ms": timing_config.min_response_ms,
            "max_response_ms": timing_config.max_response_ms,
            "std_dev_ms": timing_config.std_dev_ms,
            "poll_interval_ms": timing_config.poll_interval_ms,
            "poll_jitter_ms": timing_config.poll_jitter_ms,
        }

        # Update poll interval if learned
        if timing_config.poll_interval_ms:
            timing["poll_interval_ms"] = timing_config.poll_interval_ms
            timing["poll_jitter_ms"] = timing_config.poll_jitter_ms

        return timing

    @staticmethod
    def build_vendor_fingerprint(
        base_fingerprint: dict,
        learned_fingerprint: dict | None,
    ) -> dict:
        """Build vendor fingerprint using learned data.

        Merges learned fingerprint data including:
        - TCP stack signature (TTL, window size, MSS, options)
        - Response timing distributions
        - Vendor information
        - Protocol-specific identities (firmware, model, serial, etc.)

        The protocol_identities from PCAP learning are mapped to the identity
        builder keys (e.g., modbus_identity, s7_identity) so they can be used
        when generating protocol-level identification responses.

        Args:
            base_fingerprint: Base vendor fingerprint
            learned_fingerprint: Learned device fingerprint

        Returns:
            Enhanced vendor fingerprint with learned data merged
        """
        fingerprint = dict(base_fingerprint)

        if not learned_fingerprint:
            return fingerprint

        # Merge TCP signature
        tcp_sig = LearnedPatternIntegrator.extract_tcp_signature(learned_fingerprint)
        if tcp_sig:
            fingerprint["tcp"] = {
                **fingerprint.get("tcp", {}),
                **tcp_sig,
            }

        # Merge response timing
        response_timings = learned_fingerprint.get("response_timings", {})
        if response_timings:
            fingerprint["timing"] = {
                **fingerprint.get("timing", {}),
                "response": response_timings,
            }

        # Add vendor info
        vendor = learned_fingerprint.get("inferred_vendor")
        if vendor:
            fingerprint["vendor"] = vendor

        # Merge protocol identities for identity builders
        # This enables learned firmware/model/serial from PCAPs to flow
        # into traffic generation for protocol-level identification responses
        protocol_identities = learned_fingerprint.get("protocol_identities", {})
        if protocol_identities:
            for proto_name, identity_data in protocol_identities.items():
                if not identity_data:
                    continue

                # Map protocol name to identity builder key
                identity_key = PROTOCOL_TO_IDENTITY_KEY.get(
                    proto_name.lower()
                )

                if identity_key:
                    # Merge with existing identity data (learned data takes precedence)
                    existing = fingerprint.get(identity_key, {})
                    fingerprint[identity_key] = {
                        **existing,
                        **identity_data,
                        "_source": "learned_pcap",  # Mark as learned for debugging
                    }

        return fingerprint
