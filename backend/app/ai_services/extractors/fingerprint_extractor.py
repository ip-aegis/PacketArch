"""Device fingerprint extraction from PCAP traffic.

Extracts TCP stack signatures, vendor patterns, and response timing profiles,
then AGGREGATES observations into generic fingerprint templates.

Fingerprints are NOT tied to specific IP addresses - they capture vendor
characteristics that can be applied to any matching device.
"""

import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Packet

from app.ai_services.extractors.snmp_vendor import (
    extract_model_from_snmp,
    extract_vendor_from_snmp,
    get_vendor_confidence,
)

logger = logging.getLogger(__name__)


@dataclass
class TCPSignature:
    """TCP/IP stack fingerprint."""

    ttl: int | None = None
    window_size: int | None = None
    mss: int | None = None
    window_scaling: int | None = None
    sack_permitted: bool = False
    timestamps_enabled: bool = False
    df_flag: bool = False
    ecn_support: bool = False
    option_order: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "ttl": self.ttl,
            "window_size": self.window_size,
            "mss": self.mss,
            "window_scaling": self.window_scaling,
            "sack_permitted": self.sack_permitted,
            "timestamps_enabled": self.timestamps_enabled,
            "df_flag": self.df_flag,
            "ecn_support": self.ecn_support,
            "option_order": self.option_order,
        }

    def get_signature_key(self) -> str:
        """Generate a key for grouping similar signatures."""
        # Group by TTL range, window size range, and key options
        ttl_group = "unknown"
        if self.ttl:
            if self.ttl <= 64:
                ttl_group = "linux"  # Linux typically uses 64
            elif self.ttl <= 128:
                ttl_group = "windows"  # Windows typically uses 128
            else:
                ttl_group = "other"

        win_group = "unknown"
        if self.window_size:
            if self.window_size < 8192:
                win_group = "small"
            elif self.window_size < 32768:
                win_group = "medium"
            elif self.window_size < 65535:
                win_group = "large"
            else:
                win_group = "max"

        options_key = f"mss{self.mss or 0}_ws{self.window_scaling or 0}_sack{self.sack_permitted}_ts{self.timestamps_enabled}"

        return f"{ttl_group}_{win_group}_{options_key}"


class OUIMapper:
    """Map MAC OUI prefixes to vendors.

    Delegates to the authoritative OUI database in vendor_oui.py.
    This consolidates all OUI lookups to a single source of truth.

    NOTE: OUI-based vendor detection is a fallback. Many OT devices use embedded
    NICs from other vendors (e.g., a Johnson Controls device with a Cisco NIC).
    Protocol-based detection (SNMP, BACnet, etc.) is more reliable.
    """

    @classmethod
    def get_oui(cls, mac_address: str) -> str | None:
        """Extract OUI from MAC address.

        Args:
            mac_address: MAC address in format XX:XX:XX:XX:XX:XX

        Returns:
            OUI prefix (first 3 octets) or None
        """
        if not mac_address:
            return None
        parts = mac_address.upper().replace("-", ":").split(":")
        if len(parts) >= 3:
            return ":".join(parts[:3])
        return None

    @classmethod
    def lookup_vendor(cls, mac_address: str) -> str | None:
        """Look up vendor from MAC address.

        Delegates to the authoritative OUI database in vendor_oui.py.

        Args:
            mac_address: MAC address in format XX:XX:XX:XX:XX:XX

        Returns:
            Vendor name (human-readable) or None if not found
        """
        from app.protocol_engines.vendor_oui import get_vendor_for_oui

        oui = cls.get_oui(mac_address)
        if oui:
            return get_vendor_for_oui(oui, human_readable=True)
        return None


@dataclass
class DeviceObservation:
    """Internal observation data tracked per device during extraction.

    This is temporary data used during packet processing, NOT stored in database.
    """

    # Internal tracking only - NOT stored
    _internal_ip: str = ""

    # Vendor identification
    oui: str | None = None
    inferred_vendor: str | None = None

    # TCP signatures observed
    tcp_signatures: list[TCPSignature] = field(default_factory=list)

    # Response times by protocol (ms)
    response_times: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    # Protocols observed
    protocols_used: set[str] = field(default_factory=set)

    # Ports used
    ports_used: dict[str, set[int]] = field(default_factory=lambda: {"tcp": set(), "udp": set()})

    # Packet counts
    packets_sent: int = 0
    packets_received: int = 0

    # Protocol identity info captured from protocol messages
    protocol_identities: dict[str, dict] = field(default_factory=dict)

    # Role tracking
    request_count: int = 0
    response_count: int = 0


class FingerprintExtractor:
    """Extract and aggregate device fingerprints from PCAP traffic.

    Analyzes packets to build GENERIC fingerprint templates:
    - TCP stack signatures from SYN/SYN-ACK packets
    - Vendor identification from OUI patterns
    - Response timing distributions per protocol
    - Behavioral patterns (role, protocols)

    Multiple device observations are AGGREGATED into unified templates
    based on signature similarity.
    """

    def __init__(self):
        self._observations: dict[str, DeviceObservation] = {}  # IP -> observation (internal only)
        self._pending_requests: dict[str, tuple[str, float]] = {}

    def reset(self):
        """Reset extractor state for new analysis."""
        self._observations = {}
        self._pending_requests = {}

    def process_packet(self, packet: Packet, protocol: str | None = None) -> None:
        """Process a packet to extract fingerprint data.

        Args:
            packet: Scapy packet to process
            protocol: Optional protocol name if already identified
        """
        if not packet.haslayer(IP):
            return

        ip_layer = packet[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst
        timestamp = float(packet.time)

        # Ensure both devices are tracked internally
        self._ensure_observation(src_ip, packet, is_sender=True)
        self._ensure_observation(dst_ip, packet, is_sender=False)

        src_obs = self._observations[src_ip]
        dst_obs = self._observations[dst_ip]

        # Update packet counts
        src_obs.packets_sent += 1
        dst_obs.packets_received += 1

        # Track protocols
        if protocol:
            src_obs.protocols_used.add(protocol)
            dst_obs.protocols_used.add(protocol)

        # Process TCP-specific data
        if packet.haslayer(TCP):
            tcp_layer = packet[TCP]
            src_obs.ports_used["tcp"].add(tcp_layer.sport)
            dst_obs.ports_used["tcp"].add(tcp_layer.dport)

            # Extract TCP signature from SYN packets
            if tcp_layer.flags.S and not tcp_layer.flags.A:  # SYN only
                sig = self._extract_tcp_signature(packet)
                if sig:
                    src_obs.tcp_signatures.append(sig)
            elif tcp_layer.flags.S and tcp_layer.flags.A:  # SYN-ACK
                sig = self._extract_tcp_signature(packet)
                if sig:
                    src_obs.tcp_signatures.append(sig)

        # Process UDP ports
        if packet.haslayer(UDP):
            udp_layer = packet[UDP]
            src_obs.ports_used["udp"].add(udp_layer.sport)
            dst_obs.ports_used["udp"].add(udp_layer.dport)

        # Track request/response timing
        if protocol:
            self._track_response_timing(src_ip, dst_ip, protocol, timestamp)

    def add_protocol_identity(self, ip: str, protocol: str, identity: dict) -> None:
        """Add protocol-specific identity info for a device.

        Called by protocol extractors when they find identity information
        (e.g., Modbus device ID, S7 SZL, EtherNet/IP ListIdentity).

        Args:
            ip: Device IP (internal tracking only)
            protocol: Protocol name
            identity: Identity information dict
        """
        if ip in self._observations:
            # Merge identity, don't overwrite
            if protocol not in self._observations[ip].protocol_identities:
                self._observations[ip].protocol_identities[protocol] = {}
            self._observations[ip].protocol_identities[protocol].update(identity)

    def _ensure_observation(self, ip: str, packet: Packet, is_sender: bool) -> None:
        """Ensure device observation exists, extracting OUI if available."""
        if ip not in self._observations:
            obs = DeviceObservation(_internal_ip=ip)

            # Extract OUI and vendor from MAC
            if packet.haslayer(Ether):
                ether = packet[Ether]
                mac = ether.src if is_sender else ether.dst
                obs.oui = OUIMapper.get_oui(mac)
                obs.inferred_vendor = OUIMapper.lookup_vendor(mac)

            self._observations[ip] = obs

        elif self._observations[ip].oui is None and packet.haslayer(Ether):
            # Try to get OUI if we don't have it yet
            ether = packet[Ether]
            mac = ether.src if is_sender else ether.dst
            self._observations[ip].oui = OUIMapper.get_oui(mac)
            self._observations[ip].inferred_vendor = OUIMapper.lookup_vendor(mac)

    def _extract_tcp_signature(self, packet: Packet) -> TCPSignature | None:
        """Extract TCP stack signature from packet."""
        if not packet.haslayer(TCP) or not packet.haslayer(IP):
            return None

        ip_layer = packet[IP]
        tcp_layer = packet[TCP]

        sig = TCPSignature(
            ttl=ip_layer.ttl,
            window_size=tcp_layer.window,
            df_flag=bool(ip_layer.flags.DF),
        )

        # Parse TCP options
        option_order = []
        if tcp_layer.options:
            for opt in tcp_layer.options:
                opt_name = opt[0] if isinstance(opt, tuple) else str(opt)
                option_order.append(opt_name)

                if opt_name == "MSS" and len(opt) > 1:
                    sig.mss = opt[1]
                elif opt_name == "WScale" and len(opt) > 1:
                    sig.window_scaling = opt[1]
                elif opt_name == "SAckOK":
                    sig.sack_permitted = True
                elif opt_name == "Timestamp":
                    sig.timestamps_enabled = True

        sig.option_order = option_order

        # Check ECN
        if hasattr(tcp_layer.flags, "E") and tcp_layer.flags.E:
            sig.ecn_support = True

        return sig

    def _track_response_timing(
        self, src_ip: str, dst_ip: str, protocol: str, timestamp: float
    ) -> None:
        """Track request/response timing for response time analysis."""
        key = (src_ip, dst_ip)
        reverse_key = (dst_ip, src_ip)

        # Check if this is a response to a pending request
        if reverse_key in self._pending_requests:
            req_protocol, req_time = self._pending_requests[reverse_key]
            if req_protocol == protocol:
                delay = (timestamp - req_time) * 1000  # Convert to ms
                if 0 < delay < 10000:  # Sanity check: 0-10s
                    self._observations[src_ip].response_times[protocol].append(delay)
                    self._observations[src_ip].response_count += 1
                del self._pending_requests[reverse_key]

        # Store this as a potential request
        self._pending_requests[key] = (protocol, timestamp)
        self._observations[src_ip].request_count += 1

        # Limit pending requests to prevent memory growth
        if len(self._pending_requests) > 10000:
            items = sorted(self._pending_requests.items(), key=lambda x: x[1][1])
            self._pending_requests = dict(items[-5000:])

    def build_fingerprints(self) -> list[dict[str, Any]]:
        """Build aggregated fingerprint templates from observations.

        Aggregates multiple device observations into unified templates based on:
        - TCP signature similarity
        - Vendor identification
        - Protocol patterns

        Returns:
            List of fingerprint template dictionaries ready for storage
        """
        # First, filter observations to those with meaningful data
        valid_observations = []
        for obs in self._observations.values():
            total_packets = obs.packets_sent + obs.packets_received
            if total_packets < 5:  # Need minimum packets
                continue
            valid_observations.append(obs)

        if not valid_observations:
            return []

        # Group observations by similarity
        groups = self._group_observations(valid_observations)

        # Build fingerprint template for each group
        fingerprints = []
        for group_key, group_obs in groups.items():
            fingerprint = self._build_group_fingerprint(group_key, group_obs)
            if fingerprint:
                fingerprints.append(fingerprint)

        return fingerprints

    def _group_observations(
        self, observations: list[DeviceObservation]
    ) -> dict[str, list[DeviceObservation]]:
        """Group observations by signature similarity.

        Grouping criteria:
        1. Same vendor (from OUI or protocol identity)
        2. Similar TCP signature (TTL range, window size, options)
        3. Same protocol set
        """
        groups: dict[str, list[DeviceObservation]] = defaultdict(list)

        for obs in observations:
            group_key = self._get_group_key(obs)
            groups[group_key].append(obs)

        return dict(groups)

    def _get_group_key(self, obs: DeviceObservation) -> str:
        """Generate a grouping key for an observation.

        Vendor identification priority (highest to lowest):
        1. SNMP sysObjectID enterprise OID
        2. SNMP sysDescr pattern matching
        3. Protocol identity vendor fields (Modbus, EtherNet/IP, etc.)
        4. MAC OUI lookup
        """
        # Start with OUI-derived vendor (lowest priority)
        vendor = obs.inferred_vendor or "unknown"

        # Check protocol identities for vendor info (medium priority)
        for proto, proto_id in obs.protocol_identities.items():
            if isinstance(proto_id, dict):
                # SNMP identity - highest priority, use dedicated extractor
                if proto == "snmp":
                    snmp_vendor = extract_vendor_from_snmp(proto_id)
                    if snmp_vendor:
                        vendor = snmp_vendor
                        break
                # Other protocols - check vendor fields
                elif proto_id.get("vendor"):
                    vendor = proto_id["vendor"]
                elif proto_id.get("vendor_name"):
                    vendor = proto_id["vendor_name"]

        # TCP signature key
        tcp_key = "no_tcp"
        if obs.tcp_signatures:
            # Use the most common signature
            sig = self._aggregate_tcp_signatures(obs.tcp_signatures)
            if sig:
                tcp_key = sig.get_signature_key()

        # Protocol set
        proto_key = "_".join(sorted(obs.protocols_used)) or "no_proto"

        return f"{vendor}|{tcp_key}|{proto_key}"

    def _build_group_fingerprint(
        self, group_key: str, observations: list[DeviceObservation]
    ) -> dict[str, Any] | None:
        """Build a fingerprint template from a group of similar observations.

        Vendor identification priority (highest confidence wins):
        1. SNMP sysObjectID enterprise OID (95% confidence)
        2. SNMP sysDescr pattern matching (85% confidence)
        3. Protocol identity vendor fields (75% confidence)
        4. MAC OUI lookup (50% confidence)
        """
        if not observations:
            return None

        # Collect vendor candidates with confidence
        vendor_candidates: list[tuple[str, float]] = []

        # 1. Check SNMP identity for vendor (highest priority)
        for obs in observations:
            snmp_id = obs.protocol_identities.get("snmp")
            if snmp_id:
                snmp_vendor, confidence = get_vendor_confidence(
                    snmp_vendor=extract_vendor_from_snmp(snmp_id),
                    oui_vendor=obs.inferred_vendor,
                    snmp_identity=snmp_id,
                )
                if snmp_vendor:
                    vendor_candidates.append((snmp_vendor, confidence))

        # 2. Check other protocol identities for vendor
        for obs in observations:
            for proto, proto_id in obs.protocol_identities.items():
                if proto == "snmp":
                    continue  # Already handled above
                if isinstance(proto_id, dict):
                    vendor = proto_id.get("vendor") or proto_id.get("vendor_name")
                    if vendor:
                        vendor_candidates.append((vendor, 0.75))

        # 3. MAC OUI-derived vendors (lowest priority)
        for obs in observations:
            if obs.inferred_vendor:
                vendor_candidates.append((obs.inferred_vendor, 0.50))

        # Select vendor with highest confidence
        if vendor_candidates:
            # Sort by confidence descending, take highest
            vendor_candidates.sort(key=lambda x: x[1], reverse=True)
            inferred_vendor = vendor_candidates[0][0]
        else:
            inferred_vendor = None

        # Extract model info from SNMP if available
        model_info: dict[str, str | None] = {"model": None, "firmware_version": None, "device_type": None}
        for obs in observations:
            snmp_id = obs.protocol_identities.get("snmp")
            if snmp_id:
                extracted = extract_model_from_snmp(snmp_id)
                if extracted.get("model"):
                    model_info = extracted
                    break

        # Aggregate OUI patterns (unique OUIs seen)
        oui_patterns = list(set(obs.oui for obs in observations if obs.oui))

        # Aggregate TCP signatures
        all_tcp_sigs = []
        for obs in observations:
            all_tcp_sigs.extend(obs.tcp_signatures)
        tcp_sig = self._aggregate_tcp_signatures(all_tcp_sigs)

        # Aggregate response timings
        response_timings = self._aggregate_response_timings(observations)

        # Aggregate protocol identities (merge all)
        protocol_identities = self._aggregate_protocol_identities(observations)

        # Determine role
        role = self._determine_aggregate_role(observations)

        # Aggregate protocols
        all_protocols = set()
        for obs in observations:
            all_protocols.update(obs.protocols_used)

        # Aggregate ports
        typical_ports = self._aggregate_ports(observations)

        # Infer device type - prefer SNMP-extracted over protocol-inferred
        device_type = model_info.get("device_type") or self._infer_device_type(
            all_protocols, role, protocol_identities
        )

        # Get model and firmware from SNMP extraction
        model = model_info.get("model")
        firmware_version = model_info.get("firmware_version")

        # Calculate metrics
        total_packets = sum(obs.packets_sent + obs.packets_received for obs in observations)
        observation_count = len(observations)

        # Calculate confidence
        confidence = self._calculate_group_confidence(observations, tcp_sig, response_timings)

        # Calculate consistency score
        consistency = self._calculate_consistency(observations)

        # Generate name - include model if available
        name = self._generate_fingerprint_name(
            inferred_vendor, device_type, all_protocols, model=model
        )

        return {
            "inferred_vendor": inferred_vendor,
            "device_type": device_type,
            "model": model,
            "firmware_version": firmware_version,
            "oui_patterns": oui_patterns if oui_patterns else None,
            "tcp_signature": tcp_sig.to_dict() if tcp_sig else None,
            "response_timings": response_timings if response_timings else None,
            "protocol_identities": protocol_identities if protocol_identities else None,
            "role": role,
            "active_protocols": sorted(all_protocols) if all_protocols else None,
            "typical_ports": typical_ports if typical_ports else None,
            "observation_count": observation_count,
            "total_packets_analyzed": total_packets,
            "confidence": confidence,
            "consistency_score": consistency,
            "name": name,
        }

    def _aggregate_tcp_signatures(self, signatures: list[TCPSignature]) -> TCPSignature | None:
        """Aggregate multiple TCP signatures into one representative signature."""
        if not signatures:
            return None

        # Use most common values
        ttls = [s.ttl for s in signatures if s.ttl is not None]
        windows = [s.window_size for s in signatures if s.window_size is not None]
        mss_values = [s.mss for s in signatures if s.mss is not None]
        wscales = [s.window_scaling for s in signatures if s.window_scaling is not None]

        def most_common(lst):
            if not lst:
                return None
            return max(set(lst), key=lst.count)

        return TCPSignature(
            ttl=most_common(ttls),
            window_size=most_common(windows),
            mss=most_common(mss_values),
            window_scaling=most_common(wscales),
            sack_permitted=any(s.sack_permitted for s in signatures),
            timestamps_enabled=any(s.timestamps_enabled for s in signatures),
            df_flag=any(s.df_flag for s in signatures),
            ecn_support=any(s.ecn_support for s in signatures),
            option_order=signatures[0].option_order if signatures else [],
        )

    def _aggregate_response_timings(
        self, observations: list[DeviceObservation]
    ) -> dict[str, Any]:
        """Aggregate response timings from multiple observations."""
        combined_times: dict[str, list[float]] = defaultdict(list)

        for obs in observations:
            for protocol, times in obs.response_times.items():
                combined_times[protocol].extend(times)

        result = {}
        for protocol, times in combined_times.items():
            if len(times) >= 3:
                result[protocol] = self._fit_timing_distribution(times)

        return result

    def _aggregate_protocol_identities(
        self, observations: list[DeviceObservation]
    ) -> dict[str, dict]:
        """Aggregate protocol identities, keeping most complete info."""
        combined: dict[str, dict] = {}

        for obs in observations:
            for protocol, identity in obs.protocol_identities.items():
                if protocol not in combined:
                    combined[protocol] = {}

                # Merge, preferring non-None values
                for key, value in identity.items():
                    if value is not None:
                        # Skip IP-specific or instance-specific fields
                        if key.lower() in ("ip", "ip_address", "mac", "mac_address", "serial_number"):
                            continue
                        combined[protocol][key] = value

        return combined

    def _aggregate_ports(self, observations: list[DeviceObservation]) -> dict[str, list[int]]:
        """Aggregate typical ports used."""
        tcp_ports: set[int] = set()
        udp_ports: set[int] = set()

        for obs in observations:
            tcp_ports.update(obs.ports_used.get("tcp", set()))
            udp_ports.update(obs.ports_used.get("udp", set()))

        # Filter to well-known/typical ports (< 49152)
        tcp_typical = sorted([p for p in tcp_ports if p < 49152])
        udp_typical = sorted([p for p in udp_ports if p < 49152])

        return {
            "tcp": tcp_typical[:20],  # Limit to 20 most common
            "udp": udp_typical[:20],
        }

    def _determine_aggregate_role(self, observations: list[DeviceObservation]) -> str:
        """Determine typical role from observations."""
        roles = []

        for obs in observations:
            sent = obs.packets_sent
            received = obs.packets_received
            has_response_times = any(len(t) > 0 for t in obs.response_times.values())

            if sent == 0 and received == 0:
                roles.append("unknown")
            elif obs.response_count > obs.request_count * 2:
                roles.append("slave")
            elif obs.request_count > obs.response_count * 2 and not has_response_times:
                roles.append("master")
            elif has_response_times:
                roles.append("both")
            else:
                roles.append("unknown")

        if not roles:
            return "unknown"

        return max(set(roles), key=roles.count)

    def _infer_device_type(
        self, protocols: set[str], role: str, identities: dict[str, dict]
    ) -> str | None:
        """Infer device type from protocols, role, and identity info."""
        # Check protocol identities for device type hints
        for proto_id in identities.values():
            if isinstance(proto_id, dict):
                if proto_id.get("device_type"):
                    return proto_id["device_type"]
                if proto_id.get("product_type"):
                    return proto_id["product_type"]

        # Infer from protocols and role
        if "s7comm" in protocols or "profinet" in protocols:
            if role == "slave":
                return "PLC"
            elif role == "master":
                return "HMI/Engineering Station"

        if "modbus_tcp" in protocols:
            if role == "slave":
                return "PLC/RTU"
            elif role == "master":
                return "SCADA/HMI"

        if "ethernet_ip" in protocols:
            if role == "slave":
                return "PLC/Drive"
            elif role == "master":
                return "Controller"

        if "bacnet_ip" in protocols:
            if role == "slave":
                return "BACnet Device"
            elif role == "master":
                return "BACnet Controller"

        return None

    def _fit_timing_distribution(self, times: list[float]) -> dict[str, Any]:
        """Fit a statistical distribution to timing data."""
        if len(times) < 3:
            return {"error": "insufficient_samples"}

        arr = np.array(times)

        result = {
            "sample_count": len(times),
            "min_ms": float(np.min(arr)),
            "max_ms": float(np.max(arr)),
            "mean_ms": float(np.mean(arr)),
            "std_ms": float(np.std(arr)),
            "median_ms": float(np.median(arr)),
            "percentile_95": float(np.percentile(arr, 95)),
            "percentile_99": float(np.percentile(arr, 99)),
        }

        # Try to fit distributions
        if len(times) >= 10:
            best_fit = self._find_best_distribution(arr)
            if best_fit:
                result["distribution"] = best_fit

        return result

    def _find_best_distribution(self, data: np.ndarray) -> dict | None:
        """Find best-fitting distribution for data."""
        distributions = [
            ("gaussian", stats.norm),
            ("lognormal", stats.lognorm),
            ("exponential", stats.expon),
            ("gamma", stats.gamma),
        ]

        best_fit = None
        best_pvalue = 0

        for name, dist in distributions:
            try:
                params = dist.fit(data)
                ks_stat, p_value = stats.kstest(data, dist.cdf, params)

                if p_value > best_pvalue:
                    best_pvalue = p_value
                    best_fit = {
                        "type": name,
                        "params": [float(p) for p in params],
                        "ks_statistic": float(ks_stat),
                        "p_value": float(p_value),
                    }
            except Exception:
                continue

        return best_fit if best_pvalue > 0.01 else None

    def _calculate_group_confidence(
        self,
        observations: list[DeviceObservation],
        tcp_sig: TCPSignature | None,
        response_timings: dict,
    ) -> float:
        """Calculate confidence score for aggregated fingerprint."""
        from app.ai_services.confidence import (
            ConfidenceFactors,
            calculate_confidence,
        )

        # Total packets across all observations
        total_packets = sum(obs.packets_sent + obs.packets_received for obs in observations)

        # Coverage: how much data we have
        coverage = 0.5
        if tcp_sig:
            coverage += 0.2
        if response_timings:
            coverage += 0.2
        if any(obs.protocol_identities for obs in observations):
            coverage += 0.1

        # Diversity: number of unique observations
        diversity = min(1.0, len(observations) / 10)

        factors = ConfidenceFactors(
            sample_count=total_packets,
            coverage=coverage,
            diversity=diversity,
        )

        return calculate_confidence(factors)

    def _calculate_consistency(self, observations: list[DeviceObservation]) -> float:
        """Calculate how consistent observations were."""
        if len(observations) <= 1:
            return 1.0

        # Check TCP signature consistency
        all_sigs = []
        for obs in observations:
            for sig in obs.tcp_signatures:
                all_sigs.append(sig.get_signature_key())

        if all_sigs:
            unique_sigs = len(set(all_sigs))
            sig_consistency = 1.0 / unique_sigs
        else:
            sig_consistency = 0.5

        # Check vendor consistency
        vendors = [obs.inferred_vendor for obs in observations if obs.inferred_vendor]
        if vendors:
            unique_vendors = len(set(vendors))
            vendor_consistency = 1.0 / unique_vendors
        else:
            vendor_consistency = 0.5

        return (sig_consistency + vendor_consistency) / 2

    def _generate_fingerprint_name(
        self,
        vendor: str | None,
        device_type: str | None,
        protocols: set[str],
        model: str | None = None,
    ) -> str:
        """Generate a human-readable name for the fingerprint."""
        parts = []

        if vendor:
            parts.append(vendor)

        # Prefer model over generic device type
        if model:
            parts.append(model)
        elif device_type:
            parts.append(device_type)
        elif protocols:
            # Use protocol to suggest type
            if "s7comm" in protocols:
                parts.append("S7 Device")
            elif "modbus_tcp" in protocols:
                parts.append("Modbus Device")
            elif "ethernet_ip" in protocols:
                parts.append("EtherNet/IP Device")
            elif "profinet" in protocols:
                parts.append("PROFINET Device")
            elif "bacnet_ip" in protocols:
                parts.append("BACnet Device")
            elif "snmp" in protocols:
                parts.append("SNMP Device")
            else:
                parts.append("OT Device")

        if not parts:
            parts.append("Unknown Device")

        return " ".join(parts)
