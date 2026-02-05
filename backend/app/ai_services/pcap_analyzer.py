"""PCAP analyzer service for extracting traffic patterns.

This module provides comprehensive PCAP analysis including:
- Flow extraction and grouping
- Inter-arrival time analysis
- Protocol-specific pattern extraction
- Statistical distribution fitting
- Deep protocol analysis (Modbus, S7)
- Device fingerprinting
- Sequence learning
"""

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats
from scapy.all import rdpcap, TCP, UDP, IP, Ether
from scapy.layers.inet import ICMP

from app.models.learned_pattern import DistributionType, PatternType
from app.ai_services.extractors import (
    BACnetExtractor,
    EtherNetIPExtractor,
    FingerprintExtractor,
    ModbusExtractor,
    ProfinetExtractor,
    S7Extractor,
    SequenceLearner,
)

logger = logging.getLogger(__name__)


# Protocol port mappings for OT protocols
OT_PROTOCOL_PORTS = {
    502: "modbus_tcp",
    44818: "ethernet_ip",
    2222: "ethernet_ip_io",
    47808: "bacnet_ip",
    34964: "profinet_dcp",
    4840: "opc_ua",
    20000: "dnp3",
    2404: "iec_104",
}

# PROFINET is identified by EtherType, not port
PROFINET_ETHERTYPE = 0x8892


@dataclass
class FlowKey:
    """Unique identifier for a network flow."""

    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str  # TCP or UDP

    def __hash__(self):
        return hash((self.src_ip, self.dst_ip, self.src_port, self.dst_port, self.protocol))

    def reversed(self) -> "FlowKey":
        """Get the reverse flow key."""
        return FlowKey(
            src_ip=self.dst_ip,
            dst_ip=self.src_ip,
            src_port=self.dst_port,
            dst_port=self.src_port,
            protocol=self.protocol,
        )


@dataclass
class FlowData:
    """Data collected for a single flow."""

    key: FlowKey
    packets: list = field(default_factory=list)
    timestamps: list = field(default_factory=list)
    sizes: list = field(default_factory=list)
    directions: list = field(default_factory=list)  # "request" or "response"

    @property
    def packet_count(self) -> int:
        return len(self.packets)

    @property
    def inter_arrival_times(self) -> list[float]:
        """Calculate inter-arrival times in milliseconds."""
        if len(self.timestamps) < 2:
            return []
        times = sorted(self.timestamps)
        return [(times[i + 1] - times[i]) * 1000 for i in range(len(times) - 1)]

    @property
    def request_response_delays(self) -> list[float]:
        """Calculate request-response delays in milliseconds."""
        delays = []
        last_request_time = None

        for ts, direction in zip(self.timestamps, self.directions):
            if direction == "request":
                last_request_time = ts
            elif direction == "response" and last_request_time is not None:
                delays.append((ts - last_request_time) * 1000)
                last_request_time = None

        return delays


@dataclass
class DistributionFit:
    """Result of fitting a statistical distribution."""

    distribution_type: DistributionType
    params: dict[str, float]
    ks_statistic: float
    p_value: float
    mean: float
    std: float
    min_val: float
    max_val: float


class PcapAnalyzer:
    """Analyzer for extracting patterns from PCAP files."""

    def __init__(self):
        self.flows: dict[FlowKey, FlowData] = {}
        self.capture_start: float = 0
        self.capture_end: float = 0
        self.packet_count: int = 0

        # Enhanced extractors
        self.fingerprint_extractor = FingerprintExtractor()
        self.modbus_extractor = ModbusExtractor()
        self.s7_extractor = S7Extractor()
        self.bacnet_extractor = BACnetExtractor()
        self.ethernet_ip_extractor = EtherNetIPExtractor()
        self.profinet_extractor = ProfinetExtractor()
        self.sequence_learner = SequenceLearner()

    def analyze_file(self, file_path: str | Path, enhanced: bool = True) -> dict[str, Any]:
        """Analyze a PCAP file and extract all patterns.

        Args:
            file_path: Path to PCAP file
            enhanced: If True, run enhanced analysis with deep extractors

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing PCAP file: {file_path}")

        # Reset extractors for new analysis
        self._reset_extractors()

        # Read PCAP file
        packets = rdpcap(str(file_path))
        self.packet_count = len(packets)

        if self.packet_count == 0:
            return {"error": "Empty PCAP file"}

        # Extract flows
        self._extract_flows(packets)

        # Get file hash
        file_hash = self._calculate_file_hash(file_path)

        # Calculate capture duration
        if self.capture_end > self.capture_start:
            duration_ms = (self.capture_end - self.capture_start) * 1000
        else:
            duration_ms = 0

        # Analyze protocol distribution
        protocol_stats = self._analyze_protocol_distribution()

        # Extract devices
        devices = self._extract_devices()

        # Extract timing patterns
        timing_patterns = self._extract_timing_patterns()

        # Extract payload patterns
        payload_patterns = self._extract_payload_patterns()

        result = {
            "file_hash": file_hash,
            "packet_count": self.packet_count,
            "flow_count": len(self.flows),
            "capture_duration_ms": duration_ms,
            "protocol_stats": protocol_stats,
            "devices_detected": devices,
            "timing_patterns": timing_patterns,
            "payload_patterns": payload_patterns,
        }

        # Run enhanced analysis if requested
        if enhanced:
            enhanced_results = self._run_enhanced_analysis(packets)
            result.update(enhanced_results)

        return result

    def _reset_extractors(self) -> None:
        """Reset all extractors for a new analysis."""
        self.fingerprint_extractor.reset()
        self.modbus_extractor.reset()
        self.s7_extractor.reset()
        self.bacnet_extractor.reset()
        self.ethernet_ip_extractor.reset()
        self.profinet_extractor.reset()
        self.sequence_learner.reset()

    def _run_enhanced_analysis(self, packets) -> dict[str, Any]:
        """Run enhanced analysis using deep extractors.

        Args:
            packets: List of scapy packets

        Returns:
            Dictionary with enhanced analysis results
        """
        logger.info("Running enhanced PCAP analysis...")

        # Process each packet through extractors
        for pkt in packets:
            protocol = None

            # Try Modbus extractor
            if self.modbus_extractor.can_handle(pkt):
                protocol = "modbus_tcp"
                packet_info = self.modbus_extractor.extract_packet_info(pkt)
                if packet_info:
                    self.sequence_learner.add_packet(packet_info)

            # Try S7 extractor
            elif self.s7_extractor.can_handle(pkt):
                protocol = "s7comm"
                packet_info = self.s7_extractor.extract_packet_info(pkt)
                if packet_info:
                    self.sequence_learner.add_packet(packet_info)

            # Try BACnet extractor
            elif self.bacnet_extractor.can_handle(pkt):
                protocol = "bacnet_ip"
                packet_info = self.bacnet_extractor.extract_packet_info(pkt)
                if packet_info:
                    self.sequence_learner.add_packet(packet_info)

            # Try EtherNet/IP extractor
            elif self.ethernet_ip_extractor.can_handle(pkt):
                protocol = "ethernet_ip"
                packet_info = self.ethernet_ip_extractor.extract_packet_info(pkt)
                if packet_info:
                    self.sequence_learner.add_packet(packet_info)

            # Try PROFINET extractor
            elif self.profinet_extractor.can_handle(pkt):
                protocol = "profinet"
                packet_info = self.profinet_extractor.extract_packet_info(pkt)
                if packet_info:
                    self.sequence_learner.add_packet(packet_info)

            # Process through fingerprint extractor (all packets)
            self.fingerprint_extractor.process_packet(pkt, protocol=protocol)

        # Build patterns from extractors
        protocol_patterns = []

        # Modbus patterns
        modbus_patterns = self.modbus_extractor.build_patterns()
        if modbus_patterns and modbus_patterns.get("sample_count", 0) > 0:
            modbus_patterns["protocol"] = "modbus_tcp"
            modbus_patterns["packet_count"] = modbus_patterns.get("sample_count", 0)
            protocol_patterns.append(modbus_patterns)

        # S7 patterns
        s7_patterns = self.s7_extractor.build_patterns()
        if s7_patterns and s7_patterns.get("sample_count", 0) > 0:
            s7_patterns["protocol"] = "s7comm"
            s7_patterns["packet_count"] = s7_patterns.get("sample_count", 0)
            protocol_patterns.append(s7_patterns)

        # BACnet patterns
        bacnet_patterns = self.bacnet_extractor.build_patterns()
        if bacnet_patterns and bacnet_patterns.get("sample_count", 0) > 0:
            bacnet_patterns["protocol"] = "bacnet_ip"
            bacnet_patterns["packet_count"] = bacnet_patterns.get("sample_count", 0)
            protocol_patterns.append(bacnet_patterns)

        # EtherNet/IP patterns
        enip_patterns = self.ethernet_ip_extractor.build_patterns()
        if enip_patterns and enip_patterns.get("sample_count", 0) > 0:
            enip_patterns["protocol"] = "ethernet_ip"
            enip_patterns["packet_count"] = enip_patterns.get("sample_count", 0)
            protocol_patterns.append(enip_patterns)

        # PROFINET patterns
        profinet_patterns = self.profinet_extractor.build_patterns()
        if profinet_patterns and profinet_patterns.get("sample_count", 0) > 0:
            profinet_patterns["protocol"] = "profinet"
            profinet_patterns["packet_count"] = profinet_patterns.get("sample_count", 0)
            protocol_patterns.append(profinet_patterns)

        # Device fingerprints
        device_fingerprints = self.fingerprint_extractor.build_fingerprints()

        # Learned sequences
        self.sequence_learner.analyze_flows()
        learned_sequences = self.sequence_learner.build_sequences()

        logger.info(
            f"Enhanced analysis complete: "
            f"{len(protocol_patterns)} protocol patterns, "
            f"{len(device_fingerprints)} device fingerprints, "
            f"{len(learned_sequences)} sequences"
        )

        return {
            "protocol_patterns": protocol_patterns,
            "device_fingerprints": device_fingerprints,
            "learned_sequences": learned_sequences,
        }

    def _extract_flows(self, packets) -> None:
        """Extract flows from packets."""
        self.flows.clear()
        self.capture_start = float("inf")
        self.capture_end = 0

        for pkt in packets:
            ts = float(pkt.time)
            self.capture_start = min(self.capture_start, ts)
            self.capture_end = max(self.capture_end, ts)

            # Check for IP layer
            if not pkt.haslayer(IP):
                # Check for PROFINET (Layer 2)
                if pkt.haslayer(Ether) and pkt[Ether].type == PROFINET_ETHERTYPE:
                    # Handle PROFINET separately
                    self._handle_profinet_packet(pkt, ts)
                continue

            ip = pkt[IP]

            # TCP flows
            if pkt.haslayer(TCP):
                tcp = pkt[TCP]
                key = FlowKey(
                    src_ip=ip.src,
                    dst_ip=ip.dst,
                    src_port=tcp.sport,
                    dst_port=tcp.dport,
                    protocol="TCP",
                )
                self._add_to_flow(key, pkt, ts)

            # UDP flows
            elif pkt.haslayer(UDP):
                udp = pkt[UDP]
                key = FlowKey(
                    src_ip=ip.src,
                    dst_ip=ip.dst,
                    src_port=udp.sport,
                    dst_port=udp.dport,
                    protocol="UDP",
                )
                self._add_to_flow(key, pkt, ts)

    def _add_to_flow(self, key: FlowKey, pkt, ts: float) -> None:
        """Add a packet to a flow."""
        # Check if this is a response (reverse flow exists)
        reverse_key = key.reversed()
        is_response = reverse_key in self.flows

        if is_response:
            # Add to existing flow as response
            flow = self.flows[reverse_key]
            direction = "response"
        else:
            # Create or get forward flow
            if key not in self.flows:
                self.flows[key] = FlowData(key=key)
            flow = self.flows[key]
            direction = "request"

        flow.packets.append(pkt)
        flow.timestamps.append(ts)
        flow.sizes.append(len(pkt))
        flow.directions.append(direction)

    def _handle_profinet_packet(self, pkt, ts: float) -> None:
        """Handle PROFINET Layer 2 packets."""
        # Create a synthetic flow key for PROFINET
        ether = pkt[Ether]
        key = FlowKey(
            src_ip=ether.src,  # Use MAC as IP placeholder
            dst_ip=ether.dst,
            src_port=0,
            dst_port=0,
            protocol="PROFINET",
        )

        if key not in self.flows:
            self.flows[key] = FlowData(key=key)

        flow = self.flows[key]
        flow.packets.append(pkt)
        flow.timestamps.append(ts)
        flow.sizes.append(len(pkt))
        flow.directions.append("request")  # Simplified for RT data

    def _identify_ot_protocol(self, flow: FlowData) -> str:
        """Identify the OT protocol for a flow."""
        key = flow.key

        if key.protocol == "PROFINET":
            return "profinet"

        # Check port mappings
        for port in [key.src_port, key.dst_port]:
            if port in OT_PROTOCOL_PORTS:
                return OT_PROTOCOL_PORTS[port]

        return "unknown"

    def _analyze_protocol_distribution(self) -> dict[str, Any]:
        """Analyze protocol distribution across flows."""
        protocol_counts = defaultdict(int)
        protocol_packets = defaultdict(int)

        for flow in self.flows.values():
            protocol = self._identify_ot_protocol(flow)
            protocol_counts[protocol] += 1
            protocol_packets[protocol] += flow.packet_count

        return {
            "flow_counts": dict(protocol_counts),
            "packet_counts": dict(protocol_packets),
        }

    def _extract_devices(self) -> dict[str, Any]:
        """Extract device information from flows."""
        devices = {}

        for flow in self.flows.values():
            for ip in [flow.key.src_ip, flow.key.dst_ip]:
                if ip not in devices:
                    devices[ip] = {
                        "ip": ip,
                        "protocols": set(),
                        "ports": set(),
                    }

                protocol = self._identify_ot_protocol(flow)
                devices[ip]["protocols"].add(protocol)

                if flow.key.src_ip == ip:
                    devices[ip]["ports"].add(flow.key.src_port)
                else:
                    devices[ip]["ports"].add(flow.key.dst_port)

        # Convert sets to lists for JSON serialization
        for ip in devices:
            devices[ip]["protocols"] = list(devices[ip]["protocols"])
            devices[ip]["ports"] = list(devices[ip]["ports"])

        return devices

    def _extract_timing_patterns(self) -> list[dict[str, Any]]:
        """Extract timing patterns from flows."""
        patterns = []

        for flow in self.flows.values():
            protocol = self._identify_ot_protocol(flow)
            if protocol == "unknown":
                continue

            # Inter-arrival times
            iat = flow.inter_arrival_times
            if len(iat) >= 10:  # Need sufficient samples
                fit = self._fit_distribution(iat)
                if fit:
                    patterns.append({
                        "name": f"{protocol}_iat_{flow.key.src_ip}_{flow.key.dst_ip}",
                        "pattern_type": PatternType.TIMING.value,
                        "protocol": protocol,
                        "source_ip": flow.key.src_ip,
                        "destination_ip": flow.key.dst_ip,
                        "source_port": flow.key.src_port,
                        "destination_port": flow.key.dst_port,
                        "distribution_type": fit.distribution_type.value,
                        "timing_params": fit.params,
                        "sample_count": len(iat),
                        "min_value": fit.min_val,
                        "max_value": fit.max_val,
                        "mean_value": fit.mean,
                        "std_dev": fit.std,
                        "fit_score": fit.p_value,
                        "confidence": self._calculate_confidence(len(iat), fit.p_value),
                    })

            # Request-response delays
            rrd = flow.request_response_delays
            if len(rrd) >= 10:
                fit = self._fit_distribution(rrd)
                if fit:
                    patterns.append({
                        "name": f"{protocol}_response_delay_{flow.key.src_ip}_{flow.key.dst_ip}",
                        "pattern_type": PatternType.TIMING.value,
                        "protocol": protocol,
                        "source_ip": flow.key.src_ip,
                        "destination_ip": flow.key.dst_ip,
                        "source_port": flow.key.src_port,
                        "destination_port": flow.key.dst_port,
                        "distribution_type": fit.distribution_type.value,
                        "timing_params": fit.params,
                        "sample_count": len(rrd),
                        "min_value": fit.min_val,
                        "max_value": fit.max_val,
                        "mean_value": fit.mean,
                        "std_dev": fit.std,
                        "fit_score": fit.p_value,
                        "confidence": self._calculate_confidence(len(rrd), fit.p_value),
                    })

        return patterns

    def _extract_payload_patterns(self) -> list[dict[str, Any]]:
        """Extract payload patterns from flows."""
        patterns = []

        for flow in self.flows.values():
            protocol = self._identify_ot_protocol(flow)
            if protocol == "unknown":
                continue

            # Analyze payload sizes
            sizes = flow.sizes
            if len(sizes) >= 10:
                patterns.append({
                    "name": f"{protocol}_payload_size_{flow.key.src_ip}_{flow.key.dst_ip}",
                    "pattern_type": PatternType.PAYLOAD.value,
                    "protocol": protocol,
                    "source_ip": flow.key.src_ip,
                    "destination_ip": flow.key.dst_ip,
                    "payload_patterns": {
                        "size_distribution": {
                            "min": min(sizes),
                            "max": max(sizes),
                            "mean": float(np.mean(sizes)),
                            "std": float(np.std(sizes)),
                        },
                        "common_sizes": self._find_common_values(sizes),
                    },
                    "sample_count": len(sizes),
                    "confidence": min(1.0, len(sizes) / 100),
                })

        return patterns

    def _fit_distribution(self, data: list[float]) -> DistributionFit | None:
        """Fit statistical distributions to data and return best fit."""
        if len(data) < 5:
            return None

        arr = np.array(data)
        arr = arr[arr > 0]  # Remove zeros for log-based distributions

        if len(arr) < 5:
            return None

        # Distributions to try
        distributions = [
            ("gaussian", stats.norm, DistributionType.GAUSSIAN),
            ("lognormal", stats.lognorm, DistributionType.LOGNORMAL),
            ("exponential", stats.expon, DistributionType.EXPONENTIAL),
            ("gamma", stats.gamma, DistributionType.GAMMA),
        ]

        best_fit = None
        best_pvalue = 0

        for name, dist, dist_type in distributions:
            try:
                # Fit distribution
                params = dist.fit(arr)

                # Kolmogorov-Smirnov test
                ks_stat, p_value = stats.kstest(arr, dist.cdf, args=params)

                if p_value > best_pvalue:
                    best_pvalue = p_value

                    # Build params dict based on distribution
                    if dist_type == DistributionType.GAUSSIAN:
                        params_dict = {"mean": params[0], "std": params[1]}
                    elif dist_type == DistributionType.LOGNORMAL:
                        params_dict = {"s": params[0], "loc": params[1], "scale": params[2]}
                    elif dist_type == DistributionType.EXPONENTIAL:
                        params_dict = {"loc": params[0], "scale": params[1]}
                    elif dist_type == DistributionType.GAMMA:
                        params_dict = {"a": params[0], "loc": params[1], "scale": params[2]}
                    else:
                        params_dict = {"params": list(params)}

                    best_fit = DistributionFit(
                        distribution_type=dist_type,
                        params=params_dict,
                        ks_statistic=float(ks_stat),
                        p_value=float(p_value),
                        mean=float(np.mean(arr)),
                        std=float(np.std(arr)),
                        min_val=float(np.min(arr)),
                        max_val=float(np.max(arr)),
                    )

            except Exception as e:
                logger.debug(f"Failed to fit {name}: {e}")
                continue

        return best_fit

    def _calculate_confidence(self, sample_count: int, fit_score: float) -> float:
        """Calculate confidence score based on sample size and fit quality."""
        # Sample size contribution (0-0.5)
        sample_conf = min(0.5, sample_count / 200)

        # Fit quality contribution (0-0.5)
        fit_conf = min(0.5, fit_score)

        return sample_conf + fit_conf

    def _find_common_values(self, values: list, top_n: int = 5) -> list[dict]:
        """Find most common values in a list."""
        from collections import Counter

        counter = Counter(values)
        total = len(values)

        return [
            {"value": val, "count": count, "percentage": count / total * 100}
            for val, count in counter.most_common(top_n)
        ]

    @staticmethod
    def _calculate_file_hash(file_path: str | Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
