"""Base types for enhanced scenario templates.

This module provides base types for scenario templates that integrate
with Sprint 1-6 capabilities including:
- Vendor fingerprint references for hyper-realistic device emulation
- Suggested anomalies for testing
- PCAP learning hints for pattern extraction
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorConfig:
    """Error injection configuration for a device."""

    exception_rate: float = 0.001  # Probability of exception response
    timeout_rate: float = 0.0005  # Probability of timeout
    retry_behavior: bool = True  # Whether device implements retries
    max_retries: int = 3


@dataclass
class EnhancedDeviceSpec:
    """Enhanced device specification with fingerprint and error config.

    Extends the basic device spec with:
    - fingerprint_model: Links to DeviceTemplate for hyper-realism
    - error_config: Configures error injection rates
    - cve_ids: List of CVE identifiers for vulnerable firmware emulation
    """

    type: str
    vendor: str
    count: int
    zone: str
    name_pattern: str
    protocols: list[str]
    # Link to vendor fingerprint for hyper-realism
    # Maps to DeviceTemplate.model (e.g., "1756-L83E", "S7-1500")
    fingerprint_model: str | None = None
    # Error injection configuration
    error_config: ErrorConfig | None = None
    # Additional metadata
    role: str | None = None  # e.g., "Process Controller", "Safety Controller"
    # CVE associations for vulnerable firmware emulation
    # List of CVE IDs (e.g., ["CVE-2022-1159", "CVE-2021-22681"])
    cve_ids: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format used by existing templates."""
        result = {
            "type": self.type,
            "vendor": self.vendor,
            "count": self.count,
            "zone": self.zone,
            "name_pattern": self.name_pattern,
            "protocols": self.protocols,
        }
        if self.fingerprint_model:
            result["fingerprint_model"] = self.fingerprint_model
        if self.error_config:
            result["error_config"] = {
                "exception_rate": self.error_config.exception_rate,
                "timeout_rate": self.error_config.timeout_rate,
                "retry_behavior": self.error_config.retry_behavior,
                "max_retries": self.error_config.max_retries,
            }
        if self.role:
            result["role"] = self.role
        if self.cve_ids:
            result["cve_ids"] = self.cve_ids
        return result


@dataclass
class SuggestedAnomalies:
    """Suggested anomalies for a vertical template.

    Categorized by anomaly type for easy filtering in UI.
    """

    timing: list[str] = field(default_factory=list)  # e.g., ["delayed_response", "timeout"]
    protocol: list[str] = field(default_factory=list)  # e.g., ["modbus_exception", "cip_error"]
    sequence: list[str] = field(default_factory=list)  # e.g., ["duplicate", "out_of_order"]
    payload: list[str] = field(default_factory=list)  # e.g., ["value_spike", "corrupted_data"]
    network: list[str] = field(default_factory=list)  # e.g., ["packet_loss", "jitter_spike"]
    security: list[str] = field(default_factory=list)  # e.g., ["unauthorized_write", "scan"]

    def to_dict(self) -> dict[str, list[str]]:
        """Convert to dictionary format."""
        return {
            "timing": self.timing,
            "protocol": self.protocol,
            "sequence": self.sequence,
            "payload": self.payload,
            "network": self.network,
            "security": self.security,
        }

    def all_anomalies(self) -> list[str]:
        """Get all anomaly types as a flat list."""
        return (
            self.timing
            + self.protocol
            + self.sequence
            + self.payload
            + self.network
            + self.security
        )


@dataclass
class PcapLearningHint:
    """Hint for PCAP learning - suggests which patterns to extract.

    Helps guide users on which PCAP flows would be most valuable
    to capture and learn from.
    """

    protocol: str  # e.g., "modbus_tcp", "profinet"
    flow_type: str  # e.g., "plc_to_drive", "hmi_polling"
    priority: str = "medium"  # "high", "medium", "low"
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "protocol": self.protocol,
            "flow_type": self.flow_type,
            "priority": self.priority,
        }
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class LearnedTimingProfile:
    """Learned timing profile from PCAP analysis."""

    source: str = "learned"  # "learned" or "synthetic"
    confidence: float = 0.8
    sample_count: int = 0
    distribution: str = "gaussian"  # "gaussian", "uniform", "exponential"
    params: dict = field(default_factory=dict)  # Distribution parameters

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "source": self.source,
            "confidence": self.confidence,
            "sample_count": self.sample_count,
            "distribution": self.distribution,
            "params": self.params,
        }


@dataclass
class EnhancedFlowSpec:
    """Enhanced flow specification."""

    protocol: str
    pattern: str  # e.g., "poll", "cyclic_io", "subscription"
    interval_ms: int
    source_types: list[str]
    target_types: list[str]
    # Optional timing profile from learned patterns
    timing_profile: str | None = None  # Reference to learned pattern name
    # Jitter configuration
    jitter_ms: int = 0
    jitter_type: str = "uniform"  # "uniform", "gaussian", "exponential"
    # Learned pattern flags - when True, dynamic lookup applies learned values
    learned_function_codes: bool = False
    learned_address_ranges: bool = False
    learned_timing_profile: str | None = None  # Reference to LEARNED_TIMING_PROFILES

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "protocol": self.protocol,
            "pattern": self.pattern,
            "interval_ms": self.interval_ms,
            "source_types": self.source_types,
            "target_types": self.target_types,
        }
        if self.timing_profile:
            result["timing_profile"] = self.timing_profile
        if self.jitter_ms > 0:
            result["jitter_ms"] = self.jitter_ms
            result["jitter_type"] = self.jitter_type
        if self.learned_function_codes:
            result["learned_function_codes"] = True
        if self.learned_address_ranges:
            result["learned_address_ranges"] = True
        if self.learned_timing_profile:
            result["learned_timing_profile"] = self.learned_timing_profile
        return result


@dataclass
class EnhancedZoneSpec:
    """Enhanced zone specification."""

    id: str
    name: str
    level: int  # Purdue model level (0-5)
    subnet: str
    vlan: int
    # Optional security configuration
    security_level: str = "standard"  # "minimal", "standard", "high", "critical"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "subnet": self.subnet,
            "vlan": self.vlan,
            "security_level": self.security_level,
        }


@dataclass
class ExternalCommsSpec:
    """External communications configuration for template scenarios.

    Configures IDS-triggering traffic patterns including:
    - C2 beaconing (HTTP, HTTPS, DNS protocols)
    - Data exfiltration (HTTP, DNS tunneling)
    - Exploit attempts (Modbus attacks, S7 attacks, buffer overflows)
    - Network reconnaissance (port scans)
    """

    # C2 beaconing configuration
    enable_c2: bool = False
    c2_protocol: str = "http"  # "http", "https", "dns"
    c2_pattern: str = "jittered_1m"  # Beacon pattern name from c2_patterns.py

    # Data exfiltration configuration
    enable_exfil: bool = False
    exfil_protocol: str = "http"  # "http", "dns"
    exfil_data_size: int = 1024  # Bytes to simulate exfiltrating

    # Exploit attempts configuration
    enable_exploits: bool = False
    exploit_patterns: list[str] = field(default_factory=list)  # Pattern names from exploit_patterns.py

    # Reconnaissance configuration
    enable_recon: bool = False
    scan_ot_ports: bool = True  # Use OT-specific port list

    # Targeting: which device types can be "compromised"
    target_device_types: list[str] = field(default_factory=lambda: ["hmi", "plc"])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "enable_c2": self.enable_c2,
            "c2_protocol": self.c2_protocol,
            "c2_pattern": self.c2_pattern,
            "enable_exfil": self.enable_exfil,
            "exfil_protocol": self.exfil_protocol,
            "exfil_data_size": self.exfil_data_size,
            "enable_exploits": self.enable_exploits,
            "exploit_patterns": self.exploit_patterns,
            "enable_recon": self.enable_recon,
            "scan_ot_ports": self.scan_ot_ports,
            "target_device_types": self.target_device_types,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExternalCommsSpec":
        """Create from dictionary."""
        return cls(
            enable_c2=data.get("enable_c2", False),
            c2_protocol=data.get("c2_protocol", "http"),
            c2_pattern=data.get("c2_pattern", "jittered_1m"),
            enable_exfil=data.get("enable_exfil", False),
            exfil_protocol=data.get("exfil_protocol", "http"),
            exfil_data_size=data.get("exfil_data_size", 1024),
            enable_exploits=data.get("enable_exploits", False),
            exploit_patterns=data.get("exploit_patterns", []),
            enable_recon=data.get("enable_recon", False),
            scan_ot_ports=data.get("scan_ot_ports", True),
            target_device_types=data.get("target_device_types", ["hmi", "plc"]),
        )


# Mapping of fingerprint models to their vendors
# This helps the UI suggest appropriate fingerprints for each vendor
# Updated with comprehensive vendor-specific device profiles
FINGERPRINT_MODEL_MAP: dict[str, list[str]] = {
    "rockwell": [
        # PLCs (ControlLogix)
        "1756-L85E", "1756-L84E", "1756-L83E", "1756-L82E", "1756-L81E", "1756-L73",
        # PLCs (CompactLogix)
        "1769-L33ER", "1769-L30ERM", "1769-L24ER-QB1B",
        # PLCs (MicroLogix - legacy)
        "1766-L32BWA", "1763-L16BWA",
        # Safety PLCs (GuardLogix)
        "1756-L83ES", "1756-L73S",
        # Safety PLCs (Compact GuardLogix)
        "1769-L33ERMS", "1769-L32ES", "1769-L31ES",
        # Drives (PowerFlex catalog numbers)
        "25B-D030N104",   # PowerFlex 525
        "20F-D052N103",   # PowerFlex 753
        # Servos (Kinetix catalog numbers)
        "2198-D012-ERS3", # Kinetix 5500
        # HMIs (PanelView catalog numbers)
        "2711P-T10C22D9P", # PanelView Plus 7
        "2711R-T7T",       # PanelView 800
        # Remote I/O
        "1734-AENT",       # Point I/O
        "5094-AEN2TR",     # FLEX 5000
        # Network Infrastructure (Stratix catalog numbers)
        "1783-BMS10CGL",   # Stratix 5700
    ],
    "siemens": [
        # PLCs
        "CPU 1517-3 PN/DP", "CPU 1511-1 PN",
        "CPU 315-2 PN/DP", "CPU 416-3 PN/DP",
        # Safety PLCs
        "CPU 1516F-3 PN/DP", "CPU 1214FC",
        # Drives & Servos
        "SINAMICS G120C", "SINAMICS S120", "SINAMICS G115D",
        # HMIs
        "KTP900 Basic", "TP1200 Comfort",
        # Remote I/O & Infrastructure
        "ET 200SP IM155-6 PN", "ET 200MP IM155-5 PN",
        "SCALANCE XB208", "RF200",
    ],
    "schneider": [
        # PLCs
        "BMEH586040", "BMXP3420302", "TM251MESE", "TM262L20MESE8T",
        # Safety PLCs & I/O
        "BMEP586040S", "TM5CSLC100FS",
        # Drives & Servos
        "ATV930", "ATV320", "LXM32",
        # HMIs
        "HMIST6700", "HMISTM6",
        # Remote I/O & Infrastructure
        "TM3DI32K", "STB NIP 2311",
        "TCSESM083F2CU0", "OsiSense XU",
    ],
    # Specialty vendors - sensors, analyzers, instrumentation
    "sick": [
        # Vision & Scanners
        "Inspector P631", "CLV650-0120",
    ],
    "yokogawa": [
        # Analyzers & Transmitters
        "TDLS8000", "EJA530A", "GC8000",
    ],
    "endress+hauser": [
        # Flow & Level Instrumentation
        "Promag 400", "FMP50", "CM442",
    ],
    "honeywell": [
        # Process Analytics & Tank Gauging
        "Optiflex 6000", "Pipeline LDS", "UDA2182",
    ],
    "abb": [
        # Protection Relays & Drives
        "REF615", "REX640", "ACS880-01", "M2BAX 180MLB",
    ],
    "emerson": [
        # Valves & DCS
        "DVC6200", "3051S", "5700", "MD Plus",
    ],
    "ge": ["IC695CPE400", "IS420UCSBH1A"],
}


# Default error configurations by device type
DEFAULT_ERROR_CONFIGS: dict[str, ErrorConfig] = {
    "plc": ErrorConfig(exception_rate=0.0005, timeout_rate=0.0002),
    "rtu": ErrorConfig(exception_rate=0.001, timeout_rate=0.001),  # Higher for remote devices
    "hmi": ErrorConfig(exception_rate=0.0003, timeout_rate=0.0001),
    "drive": ErrorConfig(exception_rate=0.0008, timeout_rate=0.0003),
    "sensor": ErrorConfig(exception_rate=0.001, timeout_rate=0.0005),
    "safety_plc": ErrorConfig(exception_rate=0.0001, timeout_rate=0.0001),  # Very reliable
}


def get_default_error_config(device_type: str) -> ErrorConfig:
    """Get the default error configuration for a device type."""
    return DEFAULT_ERROR_CONFIGS.get(device_type, ErrorConfig())


def get_fingerprint_models_for_vendor(vendor: str) -> list[str]:
    """Get available fingerprint models for a vendor."""
    return FINGERPRINT_MODEL_MAP.get(vendor.lower(), [])


# =============================================================================
# LEARNED DEFAULTS FROM PCAP ANALYSIS
# =============================================================================
# These values were extracted from 264 training PCAPs containing real OT traffic.
# They provide realistic defaults for timing, function codes, and address ranges.

LEARNED_DEFAULTS: dict[str, dict[str, Any]] = {
    "dnp3": {
        "poll_interval_ms": 2500,  # Typical SCADA polling (2.5s)
        "jitter_ms": 500,
        "jitter_type": "exponential",  # WAN/satellite links
        "response_time_ms": {"mean": 50, "min": 10, "max": 200},
        "sample_count": 828,
    },
    "ethernet_ip": {
        "poll_interval_ms": 20,  # Fast I/O (20ms)
        "jitter_ms": 5,
        "jitter_type": "gaussian",  # LAN, deterministic
        "response_time_ms": {"mean": 5, "min": 1, "max": 15},
        "sample_count": 18374,
    },
    "modbus_tcp": {
        "poll_interval_ms": 100,  # Typical Modbus polling
        "jitter_ms": 10,
        "jitter_type": "gaussian",
        "response_time_ms": {"mean": 5, "min": 1, "max": 50},
        # Function code distribution from 67,696 samples
        "function_codes": {
            1: {"name": "read_coils", "frequency": 0.097},
            2: {"name": "read_discrete_inputs", "frequency": 0.039},
            3: {"name": "read_holding_registers", "frequency": 0.107},
            4: {"name": "read_input_registers", "frequency": 0.638},
            5: {"name": "write_single_coil", "frequency": 0.041},
            6: {"name": "write_single_register", "frequency": 0.015},
            15: {"name": "write_multiple_coils", "frequency": 0.063},
        },
        # Address ranges from learned patterns
        "address_ranges": {
            "coils": {"start": 0, "end": 65535},
            "discrete_inputs": {"start": 0, "end": 1213},
            "input_registers": {"start": 0, "end": 62464},
            "holding_registers": {"start": 0, "end": 51200},
        },
        "sample_count": 67696,
    },
    "s7comm": {
        "poll_interval_ms": 50,  # Fast S7 polling
        "jitter_ms": 5,
        "jitter_type": "gaussian",
        "response_time_ms": {"mean": 10, "min": 1, "max": 100},
        # Function code distribution from 189,510 samples
        "function_codes": {
            0: {"name": "cpu_services", "frequency": 0.020},
            4: {"name": "read_var", "frequency": 0.591},
            5: {"name": "write_var", "frequency": 0.024},
            27: {"name": "download_block", "frequency": 0.364},
            240: {"name": "setup_communication", "frequency": 0.001},
        },
        # Address ranges
        "address_ranges": {
            "db": {"start": 0, "end": 8016},
            "flags": {"start": 0, "end": 128},
            "inputs": {"start": 0, "end": 128},
            "outputs": {"start": 0, "end": 128},
            "timer": {"start": 0, "end": 100},
            "counter": {"start": 0, "end": 100},
        },
        "sample_count": 189510,
    },
    "profinet": {
        "poll_interval_ms": 4,  # PROFINET RT cycle time
        "jitter_ms": 1,
        "jitter_type": "gaussian",  # Deterministic
        "response_time_ms": {"mean": 1, "min": 0.5, "max": 3},
        "sample_count": 0,  # Limited PROFINET training data
    },
}


# Learned timing profiles for reference in templates
LEARNED_TIMING_PROFILES: dict[str, LearnedTimingProfile] = {
    "modbus_realistic": LearnedTimingProfile(
        source="learned",
        confidence=0.85,
        sample_count=67696,
        distribution="gaussian",
        params={"mean": 100, "std": 10, "min": 50, "max": 200},
    ),
    "s7comm_realistic": LearnedTimingProfile(
        source="learned",
        confidence=0.90,
        sample_count=189510,
        distribution="gaussian",
        params={"mean": 50, "std": 5, "min": 20, "max": 100},
    ),
    "dnp3_scada": LearnedTimingProfile(
        source="learned",
        confidence=0.75,
        sample_count=828,
        distribution="exponential",
        params={"mean": 2500, "std": 500, "min": 1000, "max": 10000},
    ),
    "ethernet_ip_fast": LearnedTimingProfile(
        source="learned",
        confidence=0.80,
        sample_count=18374,
        distribution="gaussian",
        params={"mean": 20, "std": 5, "min": 10, "max": 50},
    ),
    "profinet_cyclic": LearnedTimingProfile(
        source="learned",
        confidence=0.70,
        sample_count=500,
        distribution="gaussian",
        params={"mean": 4, "std": 0.5, "min": 1, "max": 8},
    ),
}


def get_learned_defaults(protocol: str) -> dict[str, Any]:
    """Get learned defaults for a protocol.

    Args:
        protocol: Protocol name (normalized, e.g., 'modbus_tcp', 's7comm')

    Returns:
        Dict with timing, function codes, address ranges, etc.
    """
    # Normalize protocol name
    protocol = protocol.lower()
    if protocol in ("modbus", "modbus-tcp"):
        protocol = "modbus_tcp"
    elif protocol in ("s7", "s7-comm"):
        protocol = "s7comm"
    elif protocol in ("enip", "cip"):
        protocol = "ethernet_ip"
    elif protocol in ("pn", "profinet-rt"):
        protocol = "profinet"

    return LEARNED_DEFAULTS.get(protocol, {})


def get_learned_timing_profile(name: str) -> LearnedTimingProfile | None:
    """Get a learned timing profile by name."""
    return LEARNED_TIMING_PROFILES.get(name)
