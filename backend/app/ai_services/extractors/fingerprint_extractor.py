"""Device fingerprint extraction from PCAP traffic.

Extracts TCP stack signatures, MAC OUI mappings, and response timing profiles.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy import stats
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Packet

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


class OUIMapper:
    """Map MAC OUI prefixes to vendors.

    Uses common industrial automation vendor OUIs.
    """

    # Common OT/industrial vendor OUI prefixes
    OUI_DATABASE: dict[str, str] = {
        # Siemens
        "00:0E:8C": "Siemens",
        "00:1B:1B": "Siemens",
        "00:1C:06": "Siemens",
        "00:30:DE": "Siemens",
        "9C:8E:99": "Siemens",
        "64:00:6A": "Siemens",
        # Rockwell Automation / Allen-Bradley
        "00:00:BC": "Rockwell Automation",
        "00:1D:9C": "Rockwell Automation",
        "00:01:FA": "Rockwell Automation",
        "5C:88:16": "Rockwell Automation",
        "B0:86:7B": "Rockwell Automation",
        # Schneider Electric
        "00:00:54": "Schneider Electric",
        "00:80:F4": "Schneider Electric",
        "00:20:D5": "Schneider Electric",
        "00:0B:AB": "Schneider Electric",
        # ABB
        "00:21:99": "ABB",
        "00:24:FB": "ABB",
        "50:1C:BF": "ABB",
        # Honeywell
        "00:02:E8": "Honeywell",
        "00:A0:F8": "Honeywell",
        "00:03:6D": "Honeywell",
        # Emerson / Fisher-Rosemount
        "00:0E:83": "Emerson",
        "00:A0:3D": "Emerson",
        "00:1E:C0": "Emerson",
        # GE
        "00:21:50": "GE",
        "00:50:C9": "GE",
        "00:04:A3": "GE",
        # Phoenix Contact
        "00:A0:45": "Phoenix Contact",
        "F8:DC:7A": "Phoenix Contact",
        # Beckhoff
        "00:01:05": "Beckhoff",
        # Wago
        "00:30:DE": "WAGO",
        "00:A0:6C": "WAGO",
        # Pilz
        "00:10:60": "Pilz",
        # SEL (Schweitzer Engineering)
        "00:30:A7": "SEL",
        # Moxa
        "00:90:E8": "Moxa",
        # Advantech
        "00:D0:C9": "Advantech",
        "70:72:CF": "Advantech",
        # HMS Industrial Networks
        "00:30:11": "HMS Industrial Networks",
        # B&R Automation
        "00:60:65": "B&R Automation",
        # Mitsubishi Electric
        "00:01:C0": "Mitsubishi Electric",
        "00:06:FA": "Mitsubishi Electric",
        # Omron
        "00:00:30": "Omron",
        "00:19:FA": "Omron",
        # Yokogawa
        "00:00:76": "Yokogawa",
        "00:80:9A": "Yokogawa",
        # Festo
        "00:0E:F4": "Festo",
    }

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

        Args:
            mac_address: MAC address in format XX:XX:XX:XX:XX:XX

        Returns:
            Vendor name or None if not found
        """
        oui = cls.get_oui(mac_address)
        if oui:
            return cls.OUI_DATABASE.get(oui)
        return None


@dataclass
class DeviceStats:
    """Statistics tracked per device during extraction."""

    ip_address: str
    mac_address: str | None = None
    first_seen: float | None = None
    last_seen: float | None = None
    packets_sent: int = 0
    packets_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    tcp_signatures: list[TCPSignature] = field(default_factory=list)
    response_times: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    communication_partners: set[str] = field(default_factory=set)
    protocols_used: set[str] = field(default_factory=set)
    ports_used: dict[str, set[int]] = field(default_factory=lambda: {"tcp": set(), "udp": set()})
    request_timestamps: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))


class FingerprintExtractor:
    """Extract device fingerprints from PCAP traffic.

    Analyzes packets to build device profiles including:
    - TCP stack signatures from SYN/SYN-ACK packets
    - MAC OUI to vendor mapping
    - Response timing distributions per protocol
    - Communication patterns
    """

    def __init__(self):
        self.devices: dict[str, DeviceStats] = {}
        self.pending_requests: dict[str, tuple[str, float]] = {}  # (src_ip, dst_ip) -> (protocol, timestamp)

    def reset(self):
        """Reset extractor state for new analysis."""
        self.devices = {}
        self.pending_requests = {}

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

        # Ensure both devices are tracked
        self._ensure_device(src_ip, packet, is_sender=True)
        self._ensure_device(dst_ip, packet, is_sender=False)

        # Update device statistics
        src_device = self.devices[src_ip]
        dst_device = self.devices[dst_ip]

        # Update timestamps
        if src_device.first_seen is None or timestamp < src_device.first_seen:
            src_device.first_seen = timestamp
        if timestamp > (src_device.last_seen or 0):
            src_device.last_seen = timestamp

        # Update packet/byte counts
        pkt_len = len(packet)
        src_device.packets_sent += 1
        src_device.bytes_sent += pkt_len
        dst_device.packets_received += 1
        dst_device.bytes_received += pkt_len

        # Track communication partners
        src_device.communication_partners.add(dst_ip)
        dst_device.communication_partners.add(src_ip)

        # Track protocols
        if protocol:
            src_device.protocols_used.add(protocol)
            dst_device.protocols_used.add(protocol)

        # Process TCP-specific data
        if packet.haslayer(TCP):
            tcp_layer = packet[TCP]
            src_device.ports_used["tcp"].add(tcp_layer.sport)
            dst_device.ports_used["tcp"].add(tcp_layer.dport)

            # Extract TCP signature from SYN packets
            if tcp_layer.flags.S and not tcp_layer.flags.A:  # SYN only
                sig = self._extract_tcp_signature(packet)
                if sig:
                    src_device.tcp_signatures.append(sig)
            elif tcp_layer.flags.S and tcp_layer.flags.A:  # SYN-ACK
                sig = self._extract_tcp_signature(packet)
                if sig:
                    src_device.tcp_signatures.append(sig)

        # Process UDP ports
        if packet.haslayer(UDP):
            udp_layer = packet[UDP]
            src_device.ports_used["udp"].add(udp_layer.sport)
            dst_device.ports_used["udp"].add(udp_layer.dport)

        # Track request/response timing
        if protocol:
            self._track_response_timing(src_ip, dst_ip, protocol, timestamp)

    def _ensure_device(self, ip: str, packet: Packet, is_sender: bool) -> None:
        """Ensure device is tracked, extracting MAC if available."""
        if ip not in self.devices:
            mac = None
            if packet.haslayer(Ether):
                ether = packet[Ether]
                mac = ether.src if is_sender else ether.dst
            self.devices[ip] = DeviceStats(ip_address=ip, mac_address=mac)
        elif self.devices[ip].mac_address is None and packet.haslayer(Ether):
            ether = packet[Ether]
            self.devices[ip].mac_address = ether.src if is_sender else ether.dst

    def _extract_tcp_signature(self, packet: Packet) -> TCPSignature | None:
        """Extract TCP stack signature from packet.

        Args:
            packet: Packet with TCP layer

        Returns:
            TCPSignature or None
        """
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
        """Track request/response timing for response time analysis.

        Simple heuristic: track pairs and calculate deltas.
        """
        key = (src_ip, dst_ip)
        reverse_key = (dst_ip, src_ip)

        # Check if this is a response to a pending request
        if reverse_key in self.pending_requests:
            req_protocol, req_time = self.pending_requests[reverse_key]
            if req_protocol == protocol:
                delay = (timestamp - req_time) * 1000  # Convert to ms
                if 0 < delay < 10000:  # Sanity check: 0-10s
                    # Attribute response time to the responder
                    self.devices[src_ip].response_times[protocol].append(delay)
                del self.pending_requests[reverse_key]

        # Store this as a potential request
        self.pending_requests[key] = (protocol, timestamp)

        # Limit pending requests to prevent memory growth
        if len(self.pending_requests) > 10000:
            # Remove oldest entries
            items = sorted(self.pending_requests.items(), key=lambda x: x[1][1])
            self.pending_requests = dict(items[-5000:])

    def build_fingerprints(self) -> list[dict[str, Any]]:
        """Build fingerprint data from extracted statistics.

        Returns:
            List of dictionaries ready for LearnedDeviceFingerprint model
        """
        fingerprints = []

        for ip, device in self.devices.items():
            # Skip devices with very few packets
            total_packets = device.packets_sent + device.packets_received
            if total_packets < 2:
                continue

            # Determine device role
            role = self._determine_role(device)

            # Aggregate TCP signatures (use most common values)
            tcp_sig = self._aggregate_tcp_signatures(device.tcp_signatures)

            # Build response timing distributions
            response_timings = {}
            for protocol, times in device.response_times.items():
                if len(times) >= 3:
                    response_timings[protocol] = self._fit_timing_distribution(times)

            # Build ports used dict
            ports_used = {
                "tcp": sorted(device.ports_used["tcp"]),
                "udp": sorted(device.ports_used["udp"]),
            }

            # Calculate confidence
            confidence = self._calculate_confidence(device)

            fingerprint = {
                "ip_address": ip,
                "mac_address": device.mac_address,
                "mac_oui": OUIMapper.get_oui(device.mac_address) if device.mac_address else None,
                "inferred_vendor": OUIMapper.lookup_vendor(device.mac_address)
                if device.mac_address
                else None,
                "tcp_signature": tcp_sig.to_dict() if tcp_sig else None,
                "response_timings": response_timings if response_timings else None,
                "role": role,
                "communication_partners": sorted(device.communication_partners),
                "active_protocols": sorted(device.protocols_used),
                "ports_used": ports_used,
                "packets_sent": device.packets_sent,
                "packets_received": device.packets_received,
                "bytes_sent": device.bytes_sent,
                "bytes_received": device.bytes_received,
                "first_seen": datetime.fromtimestamp(device.first_seen, tz=timezone.utc)
                if device.first_seen
                else None,
                "last_seen": datetime.fromtimestamp(device.last_seen, tz=timezone.utc)
                if device.last_seen
                else None,
                "confidence": confidence,
            }

            fingerprints.append(fingerprint)

        return fingerprints

    def _determine_role(self, device: DeviceStats) -> str:
        """Determine if device is master, slave, or both.

        Based on packet ratio and response time presence.
        """
        sent = device.packets_sent
        received = device.packets_received

        if sent == 0 and received == 0:
            return "unknown"

        # Check if device has response times (indicates it responds to requests)
        has_response_times = any(len(times) > 0 for times in device.response_times.values())

        ratio = sent / max(received, 1)

        if ratio > 2 and not has_response_times:
            return "master"  # Sends much more than receives
        elif ratio < 0.5 and has_response_times:
            return "slave"  # Receives much more and responds
        elif has_response_times:
            return "both"  # Has response times but balanced traffic
        else:
            return "unknown"

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

    def _fit_timing_distribution(self, times: list[float]) -> dict[str, Any]:
        """Fit a statistical distribution to timing data.

        Args:
            times: List of timing values in milliseconds

        Returns:
            Dictionary with distribution parameters
        """
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
        """Find best-fitting distribution for data.

        Args:
            data: NumPy array of values

        Returns:
            Dictionary with distribution type and parameters
        """
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
                # Fit distribution
                params = dist.fit(data)

                # KS test
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

    def _calculate_confidence(self, device: DeviceStats) -> float:
        """Calculate confidence score for device fingerprint.

        Based on:
        - Total packets (more = higher confidence)
        - Presence of TCP signatures
        - Presence of response timing data
        """
        import math

        total_packets = device.packets_sent + device.packets_received

        # Base confidence from packet count
        if total_packets <= 1:
            return 0.0

        packet_confidence = min(1.0, math.log10(total_packets) / 4)

        # Bonus for TCP signatures
        sig_bonus = 0.1 if device.tcp_signatures else 0

        # Bonus for response timing data
        timing_bonus = 0.1 if any(len(t) > 0 for t in device.response_times.values()) else 0

        # Bonus for MAC address
        mac_bonus = 0.1 if device.mac_address else 0

        return min(1.0, packet_confidence + sig_bonus + timing_bonus + mac_bonus)
