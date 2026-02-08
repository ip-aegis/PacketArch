# Adding New Industry Verticals to PacketArch

**A Complete Developer's Guide to Creating Realistic OT Traffic**

This document provides exhaustive documentation for adding new industry verticals to PacketArch. The goal is traffic that is:
- **Realistic** - Authentic protocol behavior with vendor-specific characteristics
- **Properly Fingerprinted** - TCP stack, timing, and identity responses match real devices
- **Detectable by Cyber Vision** - Protocol identities include firmware versions for CVE detection

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Vertical Templates](#2-vertical-templates)
3. [Vendor Fingerprints](#3-vendor-fingerprints)
4. [MAC/OUI Assignment](#4-macoui-assignment)
5. [CVE Vulnerabilities](#5-cve-vulnerabilities)
6. [Traffic Generation Pipeline](#6-traffic-generation-pipeline)
7. [Step-by-Step Checklist](#7-step-by-step-checklist)

---

## 1. Architecture Overview

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PACKETARCH DATA FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  VERTICAL TEMPLATE │     │  SCENARIO CREATED  │     │  TRAFFIC GENERATED │
│                    │────▶│                    │────▶│                    │
│  - Device specs    │     │  - Devices with    │     │  - Real packets    │
│  - Flow specs      │     │    fingerprints    │     │    via Scapy       │
│  - Zone specs      │     │  - MAC addresses   │     │  - Identity        │
│  - Phase specs     │     │  - IP addresses    │     │    responses       │
│                    │     │  - CVE overrides   │     │  - Timing/jitter   │
└────────────────────┘     └────────────────────┘     └────────────────────┘
         │                          │                          │
         │                          │                          │
         ▼                          ▼                          ▼
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  VENDOR OUI DB     │     │  FINGERPRINT       │     │  CYBER VISION      │
│                    │     │  APPLICATOR        │     │  DETECTION         │
│  - MAC prefixes    │     │                    │     │                    │
│  - Device type     │     │  - TCP stack       │     │  - Device ID       │
│    mappings        │     │  - Protocol IDs    │     │  - Firmware vers.  │
│                    │     │  - Response timing │     │  - CVE matching    │
└────────────────────┘     └────────────────────┘     └────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Vertical Templates** | `backend/app/scenario_templates/` | Define device/flow/zone specifications |
| **Vendor Fingerprints** | `backend/app/services/vendor_fingerprints/` | TCP stack, protocol identities, timing |
| **OUI Database** | `backend/app/protocol_engines/vendor_oui.py` | MAC address prefix mappings |
| **CVE Data** | `backend/app/services/cve_data/` | Vulnerability definitions + variants |
| **CVE Models** | `backend/app/models/vulnerable_fingerprint.py` | Database schema for CVE overrides |
| **Fingerprint Applicator** | `backend/app/protocol_engines/fingerprint_applicator.py` | Apply fingerprints to packets |
| **Traffic Generator** | `backend/app/protocol_engines/unified_orchestrator.py` | Real-time packet generation |
| **Protocol Engines** | `backend/app/protocol_engines/{protocol}/` | Protocol-specific packet construction |

### Detection Requirements for Cyber Vision

Cyber Vision identifies devices and vulnerabilities by parsing:

| Protocol | Detection Method | Key Fields |
|----------|------------------|------------|
| **Modbus TCP** | FC 43 Read Device ID | vendor_name, product_code, major_minor_revision |
| **EtherNet/IP** | ListIdentity Response | vendor_id, device_type, product_code, revision, product_name |
| **PROFINET** | DCP Identify Response | station_name, vendor_id, device_id, SW version in OEM block |
| **S7comm** | SZL Read Response | order_code, firmware_version, serial_number |
| **SNMP** | GetResponse sysDescr | Complete device description with firmware version |
| **BACnet/IP** | I-Am Response | vendor_id, vendor_name, model_name, firmware_revision |

**Critical**: For CVE detection, the firmware version in protocol responses must match vulnerable versions.

---

## 2. Vertical Templates

### Directory Structure

```
backend/app/scenario_templates/
├── __init__.py                 # Template registry and aggregation
├── base.py                     # Base types, learned patterns, timing profiles
├── phases.py                   # Phase templates and presets
├── manufacturing.py            # Manufacturing vertical (5 templates)
├── water.py                    # Water/Wastewater vertical
├── energy.py                   # Energy/Power vertical
├── oil_gas.py                  # Oil & Gas vertical
├── transportation.py           # Transportation ITS vertical
└── building_automation.py      # Building Automation/BMS vertical
```

### Template Structure

Each vertical template file exports a dictionary named `{VERTICAL}_TEMPLATES`:

```python
# backend/app/scenario_templates/your_vertical.py
"""Your Vertical industry scenario templates."""

from typing import Any

YOUR_VERTICAL_TEMPLATES: dict[str, dict[str, Any]] = {
    "template_key": {
        # REQUIRED FIELDS
        "name": "Display Name",                    # Human-readable name
        "description": "Template description",     # What this template simulates
        "vertical": "your_vertical",               # Vertical identifier (lowercase)
        "devices": [...],                          # List of device specifications
        "flows": [...],                            # List of data flow specifications
        "zones": [...],                            # List of network zone specifications
        "total_duration_ms": 300000,               # Traffic duration in milliseconds

        # OPTIONAL FIELDS
        "suggested_anomalies": {...},              # Anomaly injection guidance
        "pcap_learning_hints": [...],              # PCAP learning guidance
        "external_comms": {...},                   # C2/exfil/exploit config for security testing
    },
}
```

### Device Specification Schema

```python
{
    # REQUIRED
    "type": str,                    # Device category - see list below
    "vendor": str,                  # Vendor name (lowercase): "siemens", "rockwell", etc.
    "count": int,                   # Number of instances to create (1-100)
    "zone": str,                    # Zone ID where device is placed
    "name_pattern": str,            # Name format: "PLC-{n:03d}" produces "PLC-001"
    "protocols": list[str],         # Protocols: ["modbus_tcp", "ethernet_ip", "profinet", etc.]

    # OPTIONAL - Enhanced realism
    "fingerprint_model": str,       # Specific model: "1756-L85E", "CPU 1517-3 PN/DP"
    "role": str,                    # Device role: "Process Controller", "HMI Panel"
    "error_config": dict,           # Error injection: exception_rate, timeout_rate
    "cve_ids": list[str],           # CVE IDs: ["CVE-2022-1159", "CVE-2023-28489"]
}
```

**Device Types Reference:**

| Category | Types |
|----------|-------|
| **Control Layer** | `plc`, `safety_plc`, `rtu`, `gateway`, `master_station` |
| **I/O & Actuation** | `drive`, `servo`, `io_module`, `remote_io`, `actuator`, `valve` |
| **Human Interface** | `hmi`, `engineering_station`, `scada_server`, `historian` |
| **Monitoring** | `sensor`, `meter`, `camera`, `weather_station`, `protection_relay` |
| **Infrastructure** | `switch`, `router`, `firewall` |
| **Transportation** | `traffic_controller`, `dms`, `dynamic_message_sign`, `radar_sensor`, `toll_system`, `rsu` |
| **Building Automation** | `bac`, `ahu_controller`, `vav_controller`, `chiller_controller`, `boiler_controller`, `energy_meter`, `thermostat`, `room_controller` |

### Flow Specification Schema

```python
{
    # REQUIRED
    "protocol": str,                # Protocol: "modbus_tcp", "ethernet_ip", "profinet", "snmp", etc.
    "pattern": str,                 # Pattern: "poll", "cyclic_io", "subscription", "spontaneous"
    "interval_ms": int,             # Polling/sending interval (1-60000 ms)
    "source_types": list[str],      # Source device types: ["plc", "hmi"]
    "target_types": list[str],      # Target device types: ["drive", "sensor"]

    # OPTIONAL
    "jitter_ms": int,               # Jitter magnitude (default: 0)
    "jitter_type": str,             # "uniform", "gaussian", "exponential" (default: "uniform")
}
```

**Protocol Reference:**

| Protocol | Typical Patterns | Interval Range | Industries |
|----------|------------------|----------------|------------|
| `modbus_tcp` | poll | 100-5000ms | Water, Oil & Gas, Energy |
| `ethernet_ip` | cyclic_io, poll, explicit | 2-500ms | Manufacturing (Rockwell) |
| `profinet` | cyclic_io, acyclic | 1-100ms | Manufacturing (Siemens) |
| `dnp3` | poll, integrity, spontaneous | 2500-60000ms | Water, Energy, Utilities |
| `s7comm_plus` | poll, subscription | 50-2000ms | Manufacturing (Siemens) |
| `snmp` | poll | 30000-60000ms | Infrastructure, ITS |
| `bacnet` | poll, subscription | 5000-30000ms | Building Automation/BMS |
| `opc_ua` | subscription | 500-10000ms | Enterprise connectivity |
| `iec104` | spontaneous, gi, command | 0-60000ms | Energy/Power |

### Zone Specification Schema

```python
{
    # REQUIRED
    "id": str,                      # Unique zone identifier: "process", "field"
    "name": str,                    # Display name: "Process Control Zone"
    "level": int,                   # Purdue Model level (0-5)
    "subnet_offset": int,           # Offset within allocated /16 range (0-254)
    "vlan": int,                    # VLAN ID (1-4094)

    # OPTIONAL
    "subnet": str,                  # Override subnet: "10.1.2.0/24"
    "security_level": str,          # "minimal", "standard", "high", "critical"
}
```

**Purdue Model Levels:**

| Level | Name | Examples |
|-------|------|----------|
| 0 | Safety/Emergency | ESD systems, Safety PLCs |
| 1 | Field/Process | Sensors, Actuators, Drives |
| 2 | Process Control | PLCs, RTUs, Local Controllers |
| 3 | Supervisory | SCADA Servers, MES |
| 4 | Enterprise | Corporate IT, Cloud |
| 5 | External | Internet, Partners |

### Registration in `__init__.py`

After creating your template file, register it:

```python
# backend/app/scenario_templates/__init__.py

from .your_vertical import YOUR_VERTICAL_TEMPLATES

VERTICAL_TEMPLATES: dict[str, dict[str, Any]] = {
    "manufacturing": MANUFACTURING_TEMPLATES,
    "water": WATER_TEMPLATES,
    "energy": ENERGY_TEMPLATES,
    "oil_gas": OIL_GAS_TEMPLATES,
    "transportation": TRANSPORTATION_TEMPLATES,
    "building_automation": BUILDING_AUTOMATION_TEMPLATES,
    "your_vertical": YOUR_VERTICAL_TEMPLATES,  # ADD THIS LINE
}
```

### Example: Minimal Template

```python
# backend/app/scenario_templates/utilities.py
"""Utilities industry scenario templates."""

from typing import Any

UTILITIES_TEMPLATES: dict[str, dict[str, Any]] = {
    "smart_substation": {
        "name": "Smart Grid Substation",
        "description": "Distribution substation with SCADA and metering",
        "vertical": "utilities",

        "devices": [
            {
                "type": "rtu",
                "vendor": "ge",
                "count": 1,
                "zone": "control",
                "name_pattern": "RTU-{n:03d}",
                "protocols": ["dnp3", "modbus_tcp"],
                "fingerprint_model": "PACSystems RX3i",
                "role": "Substation RTU",
            },
            {
                "type": "meter",
                "vendor": "schneider",
                "count": 8,
                "zone": "field",
                "name_pattern": "METER-{n:03d}",
                "protocols": ["modbus_tcp"],
                "role": "Power Meter",
            },
            {
                "type": "protection_relay",
                "vendor": "ge",
                "count": 4,
                "zone": "field",
                "name_pattern": "RELAY-{n:03d}",
                "protocols": ["modbus_tcp", "dnp3"],
                "role": "Protective Relay",
            },
        ],

        "flows": [
            {
                "protocol": "modbus_tcp",
                "pattern": "poll",
                "interval_ms": 5000,
                "source_types": ["rtu"],
                "target_types": ["meter"],
            },
            {
                "protocol": "dnp3",
                "pattern": "poll",
                "interval_ms": 30000,
                "source_types": ["rtu"],
                "target_types": ["protection_relay"],
            },
        ],

        "zones": [
            {"id": "control", "name": "Control Zone", "level": 2, "subnet_offset": 0, "vlan": 100},
            {"id": "field", "name": "Field Zone", "level": 1, "subnet_offset": 1, "vlan": 101},
        ],

        "total_duration_ms": 300000,
    },
}
```

---

## 3. Vendor Fingerprints

### Overview

Vendor fingerprints make traffic "hyper-realistic" by encoding vendor-specific device characteristics. When the traffic generator builds packets, fingerprints control:

1. **TCP stack behavior** - TTL, window size, MSS, options
2. **Protocol identity responses** - What the device reports in identification requests
3. **Response timing** - Realistic delay distributions
4. **Error behavior** - Exception rates, timeout rates

### Directory Structure

```
backend/app/services/vendor_fingerprints/
├── __init__.py                 # Registration and exports
├── rockwell.py                 # Rockwell (ControlLogix, CompactLogix, PowerFlex, etc.)
├── siemens.py                  # Siemens (S7-1500, SINAMICS, etc.)
├── schneider.py                # Schneider Electric (M580, Altivar, etc.)
├── specialty.py                # Misc OT devices
├── transportation.py           # ITS devices (traffic controllers, DMS, etc.)
└── building_automation.py      # BMS devices (controllers, AHUs, VAVs, etc.)
```

### Complete Fingerprint Structure (11 Components)

Use the Rockwell implementation as the reference. A complete fingerprint has:

```python
{
    # ========== IDENTIFICATION ==========
    "vendor": "Rockwell",                        # Vendor name
    "vendor_family": "ControlLogix",             # Product line
    "model": "1756-L85E",                        # Model number
    "firmware_version": "33.011",                # Firmware version
    "oui_prefixes": ["00:00:BC", "00:1D:9C"],    # MAC OUI prefixes
    "is_builtin": True,                          # Built-in fingerprint

    # ========== 1. TCP STACK CHARACTERISTICS ==========
    "tcp_stack": {
        "ttl": 128,                              # Time-To-Live (64 for Linux/VxWorks, 128 for Windows)
        "window_size": 64240,                    # Initial TCP window size
        "mss": 1460,                             # Maximum Segment Size
        "window_scaling": 8,                     # Window scaling factor
        "sack_permitted": True,                  # Selective ACK support
        "timestamps_enabled": True,              # TCP timestamps
        "nop_padding": True,                     # NOP padding in options
        "df_flag": True,                         # Don't Fragment flag
    },

    # ========== 2. MODBUS IDENTITY (FC 43) ==========
    "modbus_identity": {
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1756-L85E/B",
        "major_minor_revision": "33.011",        # CRITICAL: Firmware version
        "vendor_url": "http://www.rockwellautomation.com",
        "product_name": "1756-L85E Logix5585E Controller",
        "model_name": "ControlLogix 5585E",
    },

    # ========== 3. ETHERNET/IP IDENTITY ==========
    "ethernet_ip_identity": {
        "vendor_id": 1,                          # ODVA Vendor ID (1 = Rockwell)
        "device_type": 14,                       # CIP Device Type (14 = PLC)
        "product_code": 85,                      # Product identifier
        "revision_major": 33,                    # Firmware major
        "revision_minor": 11,                    # Firmware minor
        "serial_number": 0x1A2B3C4D,             # 32-bit serial
        "product_name": "1756-L85E/B LOGIX5585E",
        "state": 3,                              # Device state (3 = running)
        "status": 0x0030,                        # Status flags
    },

    # ========== 4. CIP IDENTITY OBJECT (Deep Fingerprinting) ==========
    "cip_identity_object": {
        "status": 0x0030,                        # Owned + configured
        "configuration_consistency_value": 0xA5B6C7D8,  # Config hash
        "heartbeat_interval": 250,               # Heartbeat in ms
        "active_language": "English",
        "supported_languages": ["English"],
        "protection_mode": 0,                    # 0 = no protection, 1 = password
        "maximum_cip_connections": 64,           # Max concurrent connections
    },

    # ========== 5. PROFINET IDENTITY ==========
    "profinet_identity": {
        "vendor_id": 0x002A,                     # PROFINET vendor ID
        "device_id": 0x0001,
        "station_name": "device-name",
        "device_role": 1,                        # 1 = IO device
        "software_revision": "V3.0.0",           # CRITICAL: Firmware version
        "hardware_revision": "1.0",
        "serial_number": "SN-12345",
    },

    # ========== 6. S7 IDENTITY (for Siemens devices) ==========
    # (In protocol_quirks for Siemens devices)
    "protocol_quirks": {
        "s7_identity": {
            "order_code": "6ES7 516-3AN01-0AB0",  # MLFB order code
            "firmware_version": "V3.0.0",         # CRITICAL: Firmware
            "serial_number": "S V-P92001234",
            "module_type": "CPU 1516-3 PN/DP",
        },
        # Other quirks...
        "modbus_max_registers": 125,
        "cip_connection_timeout_multiplier": 32,
    },

    # ========== 7. SNMP IDENTITY (for ITS/Infrastructure) ==========
    "snmp_identity": {
        "sys_descr": "Econolite Cobalt ATC V2.1.5",  # CRITICAL: Full device description
        "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.1",
        "sys_name": "COBALT-ATC-001",
        "sys_location": "Main St & 5th Ave",
        "sys_contact": "admin@traffic.local",
        "sys_services": 72,
        "ntcip_device_type": "asc",              # Traffic signal controller
        "max_phases": 16,
        "max_detectors": 64,
    },

    # ========== 8. RESPONSE TIMING ==========
    "response_timing": {
        "min_ms": 0.3,                           # Minimum response time
        "max_ms": 12.0,                          # Maximum response time
        "mean_ms": 2.5,                          # Mean response time
        "std_dev_ms": 1.8,                       # Standard deviation
        "distribution": "gaussian",              # Distribution type
        "outlier_probability": 0.004,            # 0.4% outliers
        "outlier_multiplier": 4.0,               # Outliers 4x slower
    },

    # ========== 9. ERROR BEHAVIOR ==========
    "error_behavior": {
        "supported_exception_codes": [1, 2, 3, 4, 6],  # Modbus exceptions
        "exception_probability": 0.0004,         # 0.04% error rate
        "timeout_probability": 0.0001,           # 0.01% timeout rate
        "retry_behavior": True,
        "max_retries": 3,
    },

    # ========== 10. ASSEMBLY OBJECTS (EtherNet/IP I/O) ==========
    "assembly_objects": {
        "input": {"instance": 100, "size_bytes": 500},
        "output": {"instance": 101, "size_bytes": 500},
        "config": {"instance": 102, "size_bytes": 64},
    },

    # ========== 11. SAFETY CONFIG (for safety devices) ==========
    "cip_safety": {
        "safety_network_number": 1,
        "safety_signature": 0x1A2B3C4D5E6F,
        "configuration_signature": 0x6F5E4D3C2B1A,
        "tunid": (1, 1, 0, 0),
        "snn_format": "time_based",
    },
    "safety_config": {
        "sil_level": "SIL3",
        "category": "Cat4",
        "safety_watchdog_ms": 50,
    },
}
```

### TCP Stack Patterns by Device Type

| Device Type | TTL | Window | Timestamps | OS Basis |
|-------------|-----|--------|------------|----------|
| ControlLogix (high-end) | 128 | 64240 | Yes | Windows embedded |
| CompactLogix | 128 | 32768 | Yes | Windows embedded |
| PowerFlex Drives | 64 | 16384 | No | VxWorks |
| PanelView HMI | 64 | 32768 | No | Linux |
| Siemens S7-1500 | 64 | 65535 | Yes | Custom RTOS |
| MicroLogix (legacy) | 64 | 8192 | No | Older embedded |
| Traffic Controllers | 64 | 32768 | No | Linux embedded |

### Response Timing Distributions

| Distribution | Use Case | Characteristics |
|--------------|----------|-----------------|
| `gaussian` | Most PLCs | Symmetric, well-behaved |
| `lognormal` | HMIs | Long tail (human interaction) |
| `exponential` | Network queues | Right-skewed |
| `gamma` | Variable latency | Shape-controlled |
| `uniform` | Simple devices | Even distribution |

### Registering New Fingerprints

```python
# backend/app/services/vendor_fingerprints/__init__.py

from .your_vendor import get_your_vendor_fingerprints

def get_all_vendor_fingerprints() -> list[dict]:
    """Get all vendor fingerprints from all modules."""
    all_fps = []
    all_fps.extend(get_rockwell_fingerprints())
    all_fps.extend(get_siemens_fingerprints())
    all_fps.extend(get_your_vendor_fingerprints())  # ADD THIS
    return all_fps
```

### Fingerprint Application (fingerprint_applicator.py)

The `FingerprintApplicator` class (`backend/app/protocol_engines/fingerprint_applicator.py`) applies fingerprints to packet generation:

```python
class FingerprintApplicator:
    def __init__(self, fingerprint: dict, vulnerability_override: dict | None = None):
        # Loads fingerprint data
        # Applies CVE overrides if present

    # TCP stack
    def get_tcp_options(self) -> TcpOptions  # TTL, window, MSS, etc.

    # Timing
    def get_response_delay(self) -> TimingSample  # Sampled from distribution

    # Errors
    def should_inject_error(self) -> bool
    def get_random_exception_code(self) -> int

    # Protocol identities
    def build_modbus_mei_response(self, device_id_code: int) -> bytes
    def build_enip_list_identity_response(self, socket_addr) -> bytes
    def build_profinet_dcp_identify_response(self) -> bytes
    def build_s7_szl_response(self, szl_id: int) -> bytes
    def build_snmp_identity_response(self) -> dict

    # CIP deep fingerprinting
    def get_cip_identity_object(self) -> dict
```

---

## 4. MAC/OUI Assignment

### File Location

`backend/app/protocol_engines/vendor_oui.py`

### VENDOR_OUIS Dictionary

Add your vendor's OUI prefixes (first 3 bytes of MAC address):

```python
VENDOR_OUIS: dict[str, list[str]] = {
    # Industrial Automation
    "siemens": [
        "00:0E:8C",  # Siemens AG
        "00:1B:1B",  # Siemens Building Technologies
        "00:1C:06",  # Siemens AG A&D
        "74:DA:EA",  # Siemens Industrial
    ],
    "rockwell": [
        "00:00:BC",  # Allen-Bradley (legacy)
        "00:1D:9C",  # Rockwell Automation
        "B4:8C:9D",  # Rockwell Automation
    ],

    # Transportation/ITS
    "siemens_its": [
        "00:1F:F8",  # Siemens AG (ITS division)
        "00:0E:8C",  # Siemens AG
    ],
    "econolite": [
        "00:19:FA",  # Econolite Control Products
    ],
    "daktronics": [
        "00:06:D3",  # Daktronics Inc
    ],

    # ADD YOUR VENDOR HERE
    "your_vendor": [
        "XX:XX:XX",  # Your vendor OUI prefix
    ],
}
```

**Finding OUI Prefixes:**
- IEEE OUI Registry: https://standards-oui.ieee.org/
- Wireshark OUI Lookup: https://www.wireshark.org/tools/oui-lookup.html
- Capture real device traffic and inspect MAC addresses

### DEVICE_TYPE_VENDORS Mapping

Map device types to their typical vendors:

```python
DEVICE_TYPE_VENDORS: dict[str, list[str]] = {
    "plc": ["siemens", "rockwell", "schneider", "abb", "omron", "mitsubishi"],
    "hmi": ["siemens", "rockwell", "schneider", "advantech"],
    "drive": ["siemens", "abb", "rockwell", "schneider"],
    "traffic_controller": ["econolite", "siemens_its", "mccain"],
    "dms": ["daktronics"],
    "radar_sensor": ["wavetronix"],
    # ADD YOUR MAPPINGS
    "your_device_type": ["your_vendor", "alternative_vendor"],
}
```

### MAC Generation Functions

```python
def get_oui_for_vendor(vendor: str) -> str:
    """Get random OUI for a vendor."""
    vendor_lower = vendor.lower().replace(" ", "_").replace("-", "_")
    if vendor_lower in VENDOR_OUIS:
        return random.choice(VENDOR_OUIS[vendor_lower])
    return random.choice(DEFAULT_OUIS)  # Falls back to locally administered

def generate_mac_address(vendor: str | None = None, device_type: str | None = None) -> str:
    """Generate complete MAC address with appropriate OUI."""
    if vendor:
        oui = get_oui_for_vendor(vendor)
    elif device_type:
        oui = get_oui_for_device_type(device_type)
    else:
        oui = random.choice(DEFAULT_OUIS)

    # Generate random NIC portion (last 3 bytes)
    last_bytes = [random.randint(0, 255) for _ in range(3)]
    return f"{oui}:{last_bytes[0]:02x}:{last_bytes[1]:02x}:{last_bytes[2]:02x}"
```

### Usage in Template Creation

When scenarios are created from templates (`backend/app/api/routes/templates.py`):

```python
# Line ~383-386
device["network"]["macAddress"] = generate_mac_address(
    vendor=device_spec.get("vendor"),
    device_type=device_spec.get("type"),
)
```

---

## 5. CVE Vulnerabilities

### Overview

CVE data enables PacketArch to simulate vulnerable devices. When a device is assigned a CVE, its protocol identity responses include the vulnerable firmware version, which Cyber Vision detects.

### Directory Structure

```
backend/app/services/cve_data/
├── __init__.py                 # Aggregates all CVE data
├── rockwell_cves.py            # Rockwell/Allen-Bradley CVEs
├── siemens_cves.py             # Siemens CVEs
├── schneider_cves.py           # Schneider Electric CVEs
├── transportation_cves.py      # Transportation/ITS CVEs
└── building_automation_cves.py # Building Automation/BMS CVEs
```

### CVE Data Structure

```python
# backend/app/services/cve_data/your_vertical_cves.py

YOUR_VERTICAL_CVES: list[dict] = [
    {
        # ========== CVE IDENTIFICATION ==========
        "cve_id": "CVE-2024-12345",
        "title": "Vendor Product Vulnerability Title",
        "description": "Detailed description of the vulnerability...",

        # ========== SEVERITY ==========
        "severity": "critical",                   # critical, high, medium, low
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",

        # ========== AFFECTED PRODUCTS ==========
        "vendor": "YourVendor",
        "product_family": "Product Line",
        "affected_models": ["Model-A", "Model-B", "Model-C"],
        "affected_firmware_min": None,            # Minimum affected version (or None)
        "affected_firmware_max": "V2.1.0",        # Maximum affected version
        "fixed_firmware_version": "V2.2.0",       # Version that fixes the CVE

        # ========== DETECTION ==========
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",  # or "snmp_sysdescr"

        # ========== REFERENCES ==========
        "advisory_url": "https://vendor.com/security/advisory",
        "references": [
            "https://nvd.nist.gov/vuln/detail/CVE-2024-12345",
        ],
        "mitre_techniques": ["T0866", "T0882"],

        # ========== EXPLOIT INFO ==========
        "exploit_available": True,
        "exploit_complexity": "low",              # low, medium, high
        "published_date": datetime(2024, 1, 15),

        # ========== VULNERABLE VARIANTS ==========
        "vulnerable_variants": [
            {
                "firmware_version": "V2.1.0",
                "display_name": "Product Model-A V2.1.0 (CVE-2024-12345)",

                # Protocol identity overrides - WHAT THE DEVICE REPORTS
                "modbus_identity_override": {
                    "vendor_name": "YourVendor",
                    "product_code": "Model-A",
                    "major_minor_revision": "2.1.0",  # VULNERABLE VERSION
                },

                "ethernet_ip_identity_override": {
                    "vendor_id": 123,
                    "device_type": 14,
                    "revision_major": 2,
                    "revision_minor": 1,
                    "product_name": "Model-A V2.1.0",
                },

                "cip_identity_override": {
                    "protection_mode": 0,            # Vulnerable config
                    "configuration_consistency_value": 0xDEAD0000,
                },

                "snmp_identity_override": {
                    "sys_descr": "YourVendor Model-A Controller V2.1.0",
                    "sys_object_id": "1.3.6.1.4.1.XXXX.1.1.1",
                    "sys_name": "MODEL-A-001",
                },
            },
            # Additional vulnerable firmware versions...
        ],
    },
]
```

### Database Models

**CVE Vulnerability Model** (`backend/app/models/cve_vulnerability.py`):
- Stores CVE metadata (ID, title, severity, affected products)

**Vulnerable Fingerprint Variant** (`backend/app/models/vulnerable_fingerprint.py`):
- Stores protocol identity overrides for each vulnerable firmware version
- Linked to CVE via foreign key
- Columns for: `modbus_identity_override`, `ethernet_ip_identity_override`, `profinet_identity_override`, `s7_identity_override`, `cip_identity_override`, `snmp_identity_override`, `bacnet_identity_override`

### Registering CVE Data

```python
# backend/app/services/cve_data/__init__.py

from .rockwell_cves import ROCKWELL_CVES
from .siemens_cves import SIEMENS_CVES
from .transportation_cves import TRANSPORTATION_CVES
from .building_automation_cves import BUILDING_AUTOMATION_CVES
from .your_vertical_cves import YOUR_VERTICAL_CVES  # ADD THIS

ALL_CVES: list[dict] = [
    *ROCKWELL_CVES,
    *SIEMENS_CVES,
    *TRANSPORTATION_CVES,
    *BUILDING_AUTOMATION_CVES,
    *YOUR_VERTICAL_CVES,  # ADD THIS
]
```

### Seeding CVE Data

CVE data is seeded via `backend/app/services/seed_data.py`:

```python
async def seed_cve_vulnerabilities(db: AsyncSession) -> int:
    """Seed CVE vulnerabilities from Python data files."""
    from app.services.cve_data import ALL_CVES
    # Creates CVEVulnerability records

async def seed_vulnerable_variants(db: AsyncSession) -> int:
    """Seed vulnerable fingerprint variants from CVE data."""
    # Creates VulnerableFingerprintVariant records with protocol overrides
```

After adding CVE data, run database migration or restart backend to seed:

```bash
docker compose restart backend
# Check logs for: "Seeded X CVE vulnerabilities"
```

### How CVEs Flow to Protocol Responses

```
1. Template specifies cve_ids: ["CVE-2024-12345"]
   ↓
2. Template creation looks up VulnerableFingerprintVariant
   ↓
3. Scenario device gets:
   - vulnerableVariantId
   - cveIdentityOverrides (modbus, ethernet_ip, cip, snmp, etc.)
   ↓
4. Traffic generator creates FingerprintApplicator with vulnerability_override
   ↓
5. Fingerprint applicator merges CVE overrides into base fingerprint:
   self.modbus_identity.update(modbus_identity_override)
   ↓
6. Protocol response includes vulnerable firmware version:
   FC 43 response: "major_minor_revision": "2.1.0"
   ↓
7. Cyber Vision parses response, matches CVE, alerts
```

---

## 6. Traffic Generation Pipeline

### Overview

The traffic generation pipeline converts scenario definitions into real network packets:

```
Scenario JSON → Docker Container → Scapy Packets → Network Interface → Cyber Vision
```

### Key Files

| File | Purpose |
|------|---------|
| `docker/packetarch-agent/app/main.py` | Container entry point, parses scenario |
| `backend/app/protocol_engines/unified_orchestrator.py` | Real-time packet generation and injection |
| `backend/app/protocol_engines/fingerprint_applicator.py` | Apply fingerprints to packets |

### Container Initialization (entrypoint.py)

```python
# docker/packetarch-agent/app/main.py

def main():
    # 1. Load scenario from environment
    scenario = json.loads(os.environ["SCENARIO_JSON"])

    # 2. Parse devices and flows
    devices = scenario["definition"]["devices"]
    flows = scenario["definition"]["flows"]

    # 3. Build device contexts with fingerprints
    for device_id, device_def in devices.items():
        fingerprint = build_device_fingerprint(device_def, protocol)
        # Merges base fingerprint + CVE overrides

        context = DeviceContext(
            device_id=device_id,
            mac_address=device_def["network"]["macAddress"],
            ip_address=device_def["network"]["ipAddress"],
            vendor_fingerprint=fingerprint,
            vulnerability_override=device_def.get("cveIdentityOverrides"),
        )

    # 4. Create orchestrator and run
    orchestrator = LiveTrafficOrchestrator(interface="eth0")
    orchestrator.add_flow(flow_context)
    orchestrator.run()
```

### Real-Time Packet Generation (unified_orchestrator.py)

The orchestrator uses a **heap-based event queue** for precise timing:

```python
# backend/app/protocol_engines/unified_orchestrator.py

class LiveTrafficOrchestrator:
    def __init__(self, interface: str):
        self.interface = interface
        self.event_queue = []  # Heap of (timestamp, event)

    def run(self):
        # 1. Discovery sequences first (t=0ms)
        self._generate_discovery_sequences(0)

        # 2. TCP handshakes
        for flow in self.flows:
            self._generate_startup(flow, startup_time)

        # 3. Main event loop
        while self.event_queue and self._running:
            event_time, _, event = heapq.heappop(self.event_queue)

            # Wait until event time
            sleep_until(event_time)

            if event[0] == "packet":
                self._send_packet(event[1])
            elif event[0] == "poll":
                self._generate_poll_cycle(flow, event_time)
```

### Discovery Sequences (Critical for Cyber Vision)

Discovery happens at t=0ms BEFORE normal traffic:

```python
def _generate_discovery_sequences(self, time_ms):
    """Generate protocol-specific discovery for Cyber Vision detection."""

    for flow in self.flows:
        if protocol == "ethernet_ip":
            # EtherNet/IP ListIdentity (broadcast-like)
            # Device responds with vendor_id, product_name, revision

        elif protocol == "profinet":
            # PROFINET DCP Identify (multicast)
            # Device responds with station_name, firmware in OEM block

        elif protocol == "modbus_tcp":
            # Modbus FC 43 in first poll cycle
            # Device responds with vendor_name, product_code, revision

        elif protocol == "snmp":
            # SNMP GetRequest for system OIDs
            # Device responds with sysDescr containing firmware
```

### Packet Construction with Fingerprints

**TCP Packet:**
```python
def _build_tcp_packet(self, src, dst, payload, seq, ack, flags):
    packet = (
        Ether(src=src.mac_address, dst=dst.mac_address)
        / IP(src=src.ip_address, dst=dst.ip_address,
             ttl=src.get_tcp_ttl())  # FROM FINGERPRINT
        / TCP(sport=src.port, dport=dst.port, seq=seq, ack=ack, flags=flags,
              window=src.get_tcp_window_size())  # FROM FINGERPRINT
    )
    if payload:
        packet = packet / Raw(load=payload)
    return bytes(packet)
```

**Modbus FC 43 Response:**
```python
def _build_modbus_device_id_response(self, transaction_id, unit_id, fingerprint):
    modbus_identity = fingerprint.get("modbus_identity", {})

    objects = [
        (0x00, modbus_identity.get("vendor_name")),
        (0x01, modbus_identity.get("product_code")),
        (0x02, modbus_identity.get("major_minor_revision")),  # FIRMWARE VERSION
        (0x03, modbus_identity.get("vendor_url")),
        (0x04, modbus_identity.get("product_name")),
        (0x05, modbus_identity.get("model_name")),
    ]
    # Build MEI response bytes...
```

**SNMP GetResponse:**
```python
def _build_snmp_get_response(self, fingerprint):
    snmp_identity = fingerprint.get("snmp_identity", {})

    # sysDescr (1.3.6.1.2.1.1.1.0) is critical for CV
    sys_descr = snmp_identity.get("sys_descr")
    # "Econolite Cobalt ATC V2.1.5" - CV parses firmware version
```

### Timing and Jitter

```python
def _apply_jitter(self, interval_ms, timing_model):
    jitter_min = timing_model.get("jitter_min_ms", 0)
    jitter_max = timing_model.get("jitter_max_ms", 50)
    jitter = random.uniform(jitter_min, jitter_max)
    return interval_ms + jitter

def _get_response_delay(self, fingerprint):
    # Uses fingerprint applicator to sample from distribution
    timing_sample = fingerprint_applicator.get_response_delay()
    return timing_sample.delay_ms
```

### Network Injection

```python
def _send_packet(self, packet_bytes):
    """Send raw packet to network interface via Scapy."""
    sendp(Raw(packet_bytes), iface=self.interface, verbose=False)
```

---

## 7. Step-by-Step Checklist

### Complete Checklist for Adding a New Vertical

#### Phase 1: Research & Planning

- [ ] **Identify target devices** - What OT equipment exists in this vertical?
- [ ] **Document protocols used** - Modbus, EtherNet/IP, DNP3, SNMP, etc.
- [ ] **Find OUI prefixes** - MAC address prefixes for major vendors
- [ ] **Research CVEs** - Known vulnerabilities with firmware versions
- [ ] **Capture real traffic** (optional) - For timing and behavior reference

#### Phase 2: OUI/MAC Assignment

**File**: `backend/app/protocol_engines/vendor_oui.py`

- [ ] Add vendor entries to `VENDOR_OUIS` dictionary
- [ ] Add device type mappings to `DEVICE_TYPE_VENDORS` dictionary
- [ ] Test MAC generation:
  ```python
  from app.protocol_engines.vendor_oui import generate_mac_address
  mac = generate_mac_address(vendor="your_vendor")
  # Should NOT return "02:00:00:xx:xx:xx"
  ```

#### Phase 3: Vendor Fingerprints

**File**: `backend/app/services/vendor_fingerprints/your_vertical.py`

- [ ] Create fingerprint file with device definitions
- [ ] Include all 11 components (or applicable subset):
  - [ ] Basic identification (vendor, model, firmware)
  - [ ] TCP stack characteristics
  - [ ] Modbus identity (if applicable)
  - [ ] EtherNet/IP identity (if applicable)
  - [ ] PROFINET identity (if applicable)
  - [ ] S7 identity (if applicable)
  - [ ] SNMP identity (if applicable)
  - [ ] BACnet identity (if applicable - for BMS devices)
  - [ ] Response timing distribution
  - [ ] Error behavior
  - [ ] Assembly objects (if applicable)
  - [ ] Safety config (if applicable)
- [ ] Register in `__init__.py`

#### Phase 4: CVE Vulnerabilities

**File**: `backend/app/services/cve_data/your_vertical_cves.py`

- [ ] Create CVE data file
- [ ] For each CVE, include:
  - [ ] CVE identification and metadata
  - [ ] Affected products and firmware versions
  - [ ] Vulnerable variants with protocol identity overrides
- [ ] Register in `backend/app/services/cve_data/__init__.py`
- [ ] Restart backend to seed data

#### Phase 5: Vertical Template

**File**: `backend/app/scenario_templates/your_vertical.py`

- [ ] Create template file
- [ ] Define at least one template with:
  - [ ] Device specifications (with fingerprint_model, cve_ids)
  - [ ] Flow specifications (protocol, interval, source/target types)
  - [ ] Zone specifications (Purdue levels, subnets)
- [ ] Register in `backend/app/scenario_templates/__init__.py`

#### Phase 6: Testing

- [ ] **API Test** - List templates via API:
  ```bash
  curl http://localhost:8001/api/v1/templates/list?vertical=your_vertical
  ```

- [ ] **Create Scenario** - Create scenario from template:
  ```bash
  curl -X POST http://localhost:8001/api/v1/templates/create \
    -H "Content-Type: application/json" \
    -d '{"vertical": "your_vertical", "template_name": "your_template", "scenario_name": "Test"}'
  ```

- [ ] **Verify MACs** - Check devices have realistic MACs (not `02:00:00:xx:xx:xx`)

- [ ] **Deploy Traffic** - Deploy to traffic generator and run

- [ ] **Verify Discovery** - Check protocol identity responses contain correct firmware

- [ ] **Cyber Vision Detection** - Confirm CV detects devices and CVEs

#### Phase 7: Documentation

- [ ] Add vertical description to CLAUDE.md if needed
- [ ] Document any vertical-specific behaviors or quirks

---

### Common Pitfalls and Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| MAC shows `02:00:00:xx:xx:xx` | Vendor not in VENDOR_OUIS | Add OUI prefixes for vendor |
| CV doesn't detect device | Discovery sequence missing | Check protocol generates identity response |
| CVE not detected | Firmware version mismatch | Verify vulnerable_variant has correct override |
| Timing unrealistic | Wrong distribution | Use captured traffic to calibrate |
| Protocol errors | Missing identity fields | Check fingerprint has all required fields |

---

### File Quick Reference

| Task | File |
|------|------|
| Add vendor MAC prefixes | `backend/app/protocol_engines/vendor_oui.py` |
| Add vendor fingerprints | `backend/app/services/vendor_fingerprints/{vendor}.py` |
| Add CVE data | `backend/app/services/cve_data/{vertical}_cves.py` |
| Add scenario template | `backend/app/scenario_templates/{vertical}.py` |
| Register fingerprints | `backend/app/services/vendor_fingerprints/__init__.py` |
| Register CVEs | `backend/app/services/cve_data/__init__.py` |
| Register templates | `backend/app/scenario_templates/__init__.py` |
| Fingerprint application | `backend/app/protocol_engines/fingerprint_applicator.py` |
| Traffic generation | `backend/app/protocol_engines/unified_orchestrator.py` |
| Database seeding | `backend/app/services/seed_data.py` |

---

## Appendix A: Protocol Identity Field Reference

### Modbus FC 43 Read Device Identification

| Object ID | Field | Example |
|-----------|-------|---------|
| 0x00 | VendorName | "Rockwell Automation" |
| 0x01 | ProductCode | "1756-L85E/B" |
| 0x02 | MajorMinorRevision | "33.011" |
| 0x03 | VendorUrl | "http://www.rockwellautomation.com" |
| 0x04 | ProductName | "ControlLogix 5585E" |
| 0x05 | ModelName | "1756-L85E Logix5585E" |
| 0x06 | UserApplicationName | "MyApplication" |

### EtherNet/IP ListIdentity Response

| Field | Type | Example |
|-------|------|---------|
| VendorID | UINT | 1 (Rockwell) |
| DeviceType | UINT | 14 (PLC) |
| ProductCode | UINT | 85 |
| RevisionMajor | USINT | 33 |
| RevisionMinor | USINT | 11 |
| SerialNumber | UDINT | 0x1A2B3C4D |
| ProductName | STRING | "1756-L85E/B LOGIX5585E" |
| State | USINT | 3 (Running) |

### SNMP System MIB-II

| OID | Field | Example |
|-----|-------|---------|
| 1.3.6.1.2.1.1.1.0 | sysDescr | "Econolite Cobalt ATC V2.1.5" |
| 1.3.6.1.2.1.1.2.0 | sysObjectID | "1.3.6.1.4.1.1206.4.2.1.1" |
| 1.3.6.1.2.1.1.5.0 | sysName | "COBALT-ATC-001" |
| 1.3.6.1.2.1.1.6.0 | sysLocation | "Main St & 5th Ave" |
| 1.3.6.1.2.1.1.4.0 | sysContact | "admin@traffic.local" |

---

## Appendix B: Example Rockwell Fingerprint (Reference)

```python
# backend/app/services/vendor_fingerprints/rockwell.py

ROCKWELL_CONTROLLOGIX_L85E = {
    "vendor": "Rockwell",
    "vendor_family": "ControlLogix",
    "model": "1756-L85E",
    "firmware_version": "33.011",
    "oui_prefixes": ["00:00:BC", "00:1D:9C", "5C:88:16"],
    "is_builtin": True,

    "tcp_stack": {
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "window_scaling": 8,
        "sack_permitted": True,
        "timestamps_enabled": True,
        "df_flag": True,
    },

    "modbus_identity": {
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1756-L85E/B",
        "major_minor_revision": "33.011",
        "vendor_url": "http://www.rockwellautomation.com",
        "product_name": "1756-L85E Logix5585E Controller",
        "model_name": "ControlLogix 5585E",
    },

    "ethernet_ip_identity": {
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 85,
        "revision_major": 33,
        "revision_minor": 11,
        "serial_number": 0x1A2B3C4D,
        "product_name": "1756-L85E/B LOGIX5585E",
        "state": 3,
        "status": 0x0030,
    },

    "cip_identity_object": {
        "status": 0x0030,
        "configuration_consistency_value": 0xA5B6C7D8,
        "heartbeat_interval": 250,
        "active_language": "English",
        "supported_languages": ["English"],
        "protection_mode": 0,
        "maximum_cip_connections": 64,
    },

    "response_timing": {
        "min_ms": 0.3,
        "max_ms": 12.0,
        "mean_ms": 2.5,
        "std_dev_ms": 1.8,
        "distribution": "gaussian",
        "outlier_probability": 0.004,
        "outlier_multiplier": 4.0,
    },

    "error_behavior": {
        "supported_exception_codes": [1, 2, 3, 4, 6],
        "exception_probability": 0.0004,
        "timeout_probability": 0.0001,
        "retry_behavior": True,
        "max_retries": 3,
    },

    "assembly_objects": {
        "input": {"instance": 100, "size_bytes": 500},
        "output": {"instance": 101, "size_bytes": 500},
        "config": {"instance": 102, "size_bytes": 64},
    },

    "protocol_quirks": {
        "enip_encap_timeout_ms": 10000,
        "cip_connection_timeout_multiplier": 32,
        "forward_open_max_connections": 64,
    },
}
```

---

*Document created: January 2026*
*PacketArch Version: 1.0*
