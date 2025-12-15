"""Sequence learning from PCAP traffic.

Detects startup sequences, poll cycles, and state machine patterns.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from app.ai_services.extractors.base import ExtractedPacketInfo

logger = logging.getLogger(__name__)


@dataclass
class SequenceStep:
    """A single step in a sequence."""

    function_code: int | None
    direction: str  # request, response
    payload_size: int
    protocol: str
    metadata: dict = field(default_factory=dict)


@dataclass
class DetectedSequence:
    """A detected sequence pattern."""

    name: str
    sequence_type: str  # startup, poll_cycle, shutdown, etc.
    protocol: str
    initiator_ip: str
    responder_ip: str
    steps: list[SequenceStep]
    occurrence_count: int
    average_duration_ms: float
    timing_variance: float
    inter_step_timings: list[float]


class SequenceLearner:
    """Learn operation sequences from packet flow.

    Detects:
    - Startup sequences (TCP SYN + protocol handshake)
    - Poll cycles (repeating request/response patterns)
    - Shutdown sequences (disconnect patterns)
    - State machine transitions
    """

    def __init__(self):
        self.flows: dict[str, list[ExtractedPacketInfo]] = defaultdict(list)
        self.detected_sequences: list[DetectedSequence] = []

    def reset(self):
        """Reset learner state."""
        self.flows = defaultdict(list)
        self.detected_sequences = []

    def add_packet(self, packet_info: ExtractedPacketInfo) -> None:
        """Add a packet to the flow tracking.

        Args:
            packet_info: Extracted packet information
        """
        # Create bidirectional flow key
        ips = sorted([packet_info.src_ip, packet_info.dst_ip])
        flow_key = f"{ips[0]}_{ips[1]}_{packet_info.protocol}"
        self.flows[flow_key].append(packet_info)

    def analyze_flows(self) -> list[DetectedSequence]:
        """Analyze all flows to detect sequences.

        Returns:
            List of detected sequences
        """
        self.detected_sequences = []

        for flow_key, packets in self.flows.items():
            if len(packets) < 4:  # Need at least a few packets for pattern
                continue

            # Sort by timestamp
            packets = sorted(packets, key=lambda p: p.timestamp)

            # Detect different sequence types
            self._detect_startup_sequence(flow_key, packets)
            self._detect_poll_cycles(flow_key, packets)

        return self.detected_sequences

    def _detect_startup_sequence(
        self, flow_key: str, packets: list[ExtractedPacketInfo]
    ) -> None:
        """Detect startup/connection establishment sequences."""
        if len(packets) < 3:
            return

        protocol = packets[0].protocol

        # Look for protocol-specific startup indicators
        startup_indicators = {
            "modbus_tcp": self._check_modbus_startup,
            "s7comm": self._check_s7_startup,
        }

        checker = startup_indicators.get(protocol)
        if checker:
            startup = checker(packets)
            if startup:
                self.detected_sequences.append(startup)

    def _check_modbus_startup(
        self, packets: list[ExtractedPacketInfo]
    ) -> DetectedSequence | None:
        """Check for Modbus startup patterns.

        Look for:
        - FC43 (Read Device ID) at start
        - FC8 (Diagnostics) at start
        - Initial polling sequence
        """
        # Find first few request packets
        requests = [p for p in packets[:10] if p.direction == "request"]

        if not requests:
            return None

        # Check for device identification or diagnostics at start
        startup_fcs = {43, 8, 17}  # Read Device ID, Diagnostics, Report Server ID
        first_fcs = [p.function_code for p in requests[:3] if p.function_code]

        if any(fc in startup_fcs for fc in first_fcs):
            # Found startup indicator
            startup_packets = packets[:6]  # Take first 6 packets

            if len(startup_packets) < 2:
                return None

            steps = [
                SequenceStep(
                    function_code=p.function_code,
                    direction=p.direction,
                    payload_size=p.payload_size,
                    protocol=p.protocol,
                    metadata=p.metadata,
                )
                for p in startup_packets
            ]

            # Calculate timing
            timings = self._calculate_inter_step_timings(startup_packets)

            duration = (
                (startup_packets[-1].timestamp - startup_packets[0].timestamp) * 1000
                if len(startup_packets) > 1
                else 0
            )

            return DetectedSequence(
                name="modbus_startup",
                sequence_type="startup",
                protocol="modbus_tcp",
                initiator_ip=requests[0].src_ip,
                responder_ip=requests[0].dst_ip,
                steps=steps,
                occurrence_count=1,
                average_duration_ms=duration,
                timing_variance=np.var(timings) if timings else 0,
                inter_step_timings=timings,
            )

        return None

    def _check_s7_startup(
        self, packets: list[ExtractedPacketInfo]
    ) -> DetectedSequence | None:
        """Check for S7 startup patterns.

        Look for:
        - COTP CR/CC (Connection Request/Confirm)
        - S7 Setup Communication
        """
        # Look for COTP and Setup Communication
        startup_packets = []

        for p in packets[:10]:
            cotp_type = p.metadata.get("cotp_type")
            func_name = p.metadata.get("function_name", "")

            # COTP connection establishment
            if cotp_type in ["cr", "cc"]:
                startup_packets.append(p)
            # S7 Setup Communication
            elif func_name == "setup_communication":
                startup_packets.append(p)

            # Stop after we have enough
            if len(startup_packets) >= 4:
                break

        if len(startup_packets) < 2:
            return None

        steps = [
            SequenceStep(
                function_code=p.function_code,
                direction=p.direction,
                payload_size=p.payload_size,
                protocol=p.protocol,
                metadata=p.metadata,
            )
            for p in startup_packets
        ]

        timings = self._calculate_inter_step_timings(startup_packets)

        duration = (
            (startup_packets[-1].timestamp - startup_packets[0].timestamp) * 1000
            if len(startup_packets) > 1
            else 0
        )

        # Determine initiator (first request sender)
        requests = [p for p in startup_packets if p.direction == "request"]
        initiator = requests[0].src_ip if requests else startup_packets[0].src_ip
        responder = requests[0].dst_ip if requests else startup_packets[0].dst_ip

        return DetectedSequence(
            name="s7_startup",
            sequence_type="startup",
            protocol="s7comm",
            initiator_ip=initiator,
            responder_ip=responder,
            steps=steps,
            occurrence_count=1,
            average_duration_ms=duration,
            timing_variance=np.var(timings) if timings else 0,
            inter_step_timings=timings,
        )

    def _detect_poll_cycles(
        self, flow_key: str, packets: list[ExtractedPacketInfo]
    ) -> None:
        """Detect repeating poll cycle patterns."""
        if len(packets) < 10:
            return

        protocol = packets[0].protocol

        # Group into request/response pairs
        pairs = self._group_request_response_pairs(packets)

        if len(pairs) < 3:
            return

        # Look for repeating patterns in function codes
        fc_sequence = [
            (p[0].function_code if p[0].function_code else 0) for p in pairs
        ]

        # Find repeating patterns
        cycle = self._find_repeating_pattern(fc_sequence)

        if cycle and len(cycle) >= 2:
            # Found a poll cycle
            cycle_length = len(cycle)

            # Extract example cycle
            example_pairs = pairs[:cycle_length]
            steps = []
            for req, resp in example_pairs:
                steps.append(
                    SequenceStep(
                        function_code=req.function_code,
                        direction="request",
                        payload_size=req.payload_size,
                        protocol=req.protocol,
                        metadata=req.metadata,
                    )
                )
                if resp:
                    steps.append(
                        SequenceStep(
                            function_code=resp.function_code,
                            direction="response",
                            payload_size=resp.payload_size,
                            protocol=resp.protocol,
                            metadata=resp.metadata,
                        )
                    )

            # Calculate cycle timing
            cycle_times = []
            for i in range(0, len(pairs) - cycle_length, cycle_length):
                if i + cycle_length < len(pairs):
                    start = pairs[i][0].timestamp
                    end = pairs[i + cycle_length][0].timestamp
                    cycle_times.append((end - start) * 1000)

            avg_duration = np.mean(cycle_times) if cycle_times else 0
            timing_var = np.var(cycle_times) if len(cycle_times) > 1 else 0

            # Inter-step timings within cycle
            cycle_packets = [p for pair in example_pairs for p in pair if p]
            inter_timings = self._calculate_inter_step_timings(cycle_packets)

            # Calculate repetition interval
            repetition_interval = None
            if len(pairs) >= cycle_length * 2:
                intervals = []
                for i in range(len(pairs) - cycle_length):
                    intervals.append(
                        (pairs[i + cycle_length][0].timestamp - pairs[i][0].timestamp)
                        * 1000
                    )
                if intervals:
                    repetition_interval = np.mean(intervals)

            requests = [p[0] for p in pairs]
            initiator = requests[0].src_ip if requests else packets[0].src_ip
            responder = requests[0].dst_ip if requests else packets[0].dst_ip

            sequence = DetectedSequence(
                name=f"{protocol}_poll_cycle",
                sequence_type="poll_cycle",
                protocol=protocol,
                initiator_ip=initiator,
                responder_ip=responder,
                steps=steps,
                occurrence_count=len(pairs) // cycle_length,
                average_duration_ms=avg_duration,
                timing_variance=timing_var,
                inter_step_timings=inter_timings,
            )

            # Add repetition info to first step metadata
            if repetition_interval:
                sequence.steps[0].metadata["repetition_interval_ms"] = repetition_interval

            self.detected_sequences.append(sequence)

    def _group_request_response_pairs(
        self, packets: list[ExtractedPacketInfo]
    ) -> list[tuple[ExtractedPacketInfo, ExtractedPacketInfo | None]]:
        """Group packets into request/response pairs."""
        pairs = []
        pending_request = None

        for packet in packets:
            if packet.direction == "request":
                if pending_request:
                    # Previous request had no response
                    pairs.append((pending_request, None))
                pending_request = packet
            elif packet.direction == "response" and pending_request:
                pairs.append((pending_request, packet))
                pending_request = None

        if pending_request:
            pairs.append((pending_request, None))

        return pairs

    def _find_repeating_pattern(
        self, sequence: list[int], min_length: int = 1, max_length: int = 10
    ) -> list[int] | None:
        """Find the shortest repeating pattern in a sequence."""
        n = len(sequence)

        for pattern_len in range(min_length, min(max_length + 1, n // 2 + 1)):
            pattern = sequence[:pattern_len]
            is_repeating = True

            # Check if this pattern repeats
            matches = 0
            for i in range(0, n - pattern_len + 1, pattern_len):
                chunk = sequence[i : i + pattern_len]
                if chunk == pattern:
                    matches += 1
                else:
                    # Allow some tolerance
                    mismatches = sum(1 for a, b in zip(chunk, pattern) if a != b)
                    if mismatches > len(pattern) * 0.2:  # 20% tolerance
                        is_repeating = False
                        break

            if is_repeating and matches >= 3:
                return pattern

        return None

    def _calculate_inter_step_timings(
        self, packets: list[ExtractedPacketInfo]
    ) -> list[float]:
        """Calculate timing between consecutive steps."""
        if len(packets) < 2:
            return []

        timings = []
        for i in range(1, len(packets)):
            delta_ms = (packets[i].timestamp - packets[i - 1].timestamp) * 1000
            if 0 < delta_ms < 60000:  # Sanity check: 0-60s
                timings.append(delta_ms)

        return timings

    def build_sequences(self) -> list[dict[str, Any]]:
        """Build sequence data ready for LearnedSequence model.

        Returns:
            List of dictionaries with sequence data
        """
        sequences = []

        for seq in self.detected_sequences:
            # Build steps data
            steps_data = [
                {
                    "index": i,
                    "function_code": step.function_code,
                    "direction": step.direction,
                    "payload_size": step.payload_size,
                    "metadata": step.metadata,
                }
                for i, step in enumerate(seq.steps)
            ]

            # Extract repetition info if present
            repetition_interval = None
            repetition_jitter = None
            if seq.steps and "repetition_interval_ms" in seq.steps[0].metadata:
                repetition_interval = seq.steps[0].metadata["repetition_interval_ms"]
                # Estimate jitter from timing variance
                repetition_jitter = np.sqrt(seq.timing_variance) if seq.timing_variance else None

            # Calculate confidence based on occurrences and consistency
            confidence = min(
                1.0,
                (seq.occurrence_count / 10)  # More occurrences = higher confidence
                * (1.0 / (1.0 + seq.timing_variance / 1000))  # Lower variance = higher confidence
            )

            sequence_data = {
                "name": seq.name,
                "sequence_type": seq.sequence_type,
                "protocol": seq.protocol,
                "initiator_ip": seq.initiator_ip,
                "responder_ip": seq.responder_ip,
                "steps": steps_data,
                "average_duration_ms": seq.average_duration_ms,
                "timing_variance": seq.timing_variance,
                "inter_step_timings": {
                    "values": seq.inter_step_timings,
                    "mean": np.mean(seq.inter_step_timings) if seq.inter_step_timings else 0,
                    "std": np.std(seq.inter_step_timings) if len(seq.inter_step_timings) > 1 else 0,
                },
                "repetition_interval_ms": repetition_interval,
                "repetition_jitter_ms": repetition_jitter,
                "occurrence_count": seq.occurrence_count,
                "step_count": len(seq.steps),
                "confidence": confidence,
            }

            sequences.append(sequence_data)

        return sequences
