# PacketArch Template Creation Guide

This guide provides a comprehensive reference for creating high-quality scenario templates with realistic protocol fingerprinting, vendor configurations, and traffic flows.

---

## Table of Contents

1. [Template Architecture Overview](#template-architecture-overview)
2. [Device Specification](#device-specification)
3. [Protocol Identity & Fingerprinting](#protocol-identity--fingerprinting)
4. [Vendor Fingerprint Database](#vendor-fingerprint-database)
5. [Traffic Flow Configuration](#traffic-flow-configuration)
6. [Timing Models](#timing-models)
7. [Zone & Network Topology](#zone--network-topology)
8. [Phase Definitions](#phase-definitions)
9. [Anomaly & Security Testing](#anomaly--security-testing)
10. [Complete Template Example](#complete-template-example)
11. [Checklist for Perfect Templates](#checklist-for-perfect-templates)

---

## Template Architecture Overview

Templates are defined in `backend/app/scenario_templates/` with the following structure:

| File | Purpose |
|------|---------|
| `base.py` | Core dataclasses, fingerprint maps, learned defaults |
| `phases.py` | Phase templates, presets, vertical variations |
| `manufacturing.py` | Manufacturing vertical templates |
| `water.py` | Water/Wastewater templates |
| `energy.py` | Energy/Power templates |
| `oil_gas.py` | Oil & Gas templates |
| `building_automation.py` | Building Automation/BMS templates |
| `transportation.py` | Transportation/ITS templates |
| `__init__.py` | Template registry and lookup functions |

### Template → Scenario Flow

```
Template Definition
       ↓
CreateFromTemplateRequest (API)
       ↓
IP Range Allocation (/16 per scenario)
       ↓
Zone Building (subnets, VLANs)
       ↓
Device Instantiation (fingerprints, CVEs)
       ↓
Flow Generation (SmartFlowGenerator or legacy)
       ↓
Phase Application
       ↓
Learned Pattern Enhancement (optional)
       ↓
Scenario Persisted to Database
```

---

## Device Specification

### EnhancedDeviceSpec Structure

```python
from app.scenario_templates.base import EnhancedDeviceSpec, ErrorConfig

device = EnhancedDeviceSpec(
    type="plc",                           # Device type (plc, hmi, drive, io_module, etc.)
    vendor="Siemens",                     # Vendor name
    count=4,                              # Number of instances
    zone="process",                       # Target zone ID
    name_pattern="PLC-{n:03d}",          # Naming pattern (supports {n}, {floor}, {type})
    protocols=["profinet", "s7comm"],     # List of protocols
    fingerprint_model="CPU 1517-3",       # Key into FINGERPRINT_MODEL_MAP
    error_config=ErrorConfig(             # Optional error simulation
        exception_rate=0.001,
        timeout_rate=0.0005,
        retry_behavior=True,
        max_retries=3
    ),
    role="Process Controller",            # Descriptive role
    cve_ids=["CVE-2019-13945"],          # Optional CVE vulnerabilities
)
```

### Device Types

| Type | Description | Typical Protocols |
|------|-------------|-------------------|
| `plc` | Programmable Logic Controller | Modbus, EtherNet/IP, PROFINET, S7comm |
| `hmi` | Human Machine Interface | EtherNet/IP, S7comm, OPC UA |
| `drive` | Variable Frequency Drive | PROFINET, EtherNet/IP, Modbus |
| `io_module` | Remote I/O Module | PROFINET, EtherNet/IP |
| `rtu` | Remote Terminal Unit | DNP3, Modbus |
| `sensor` | Field Sensor/Transmitter | Modbus, BACnet |
| `relay` | Protection Relay | DNP3, Modbus, IEC 104 |
| `meter` | Power/Flow Meter | Modbus, BACnet |
| `switch` | Network Switch | SNMP |
| `controller` | Building Controller | BACnet, Modbus |
| `atc` | Adaptive Traffic Controller | SNMP/NTCIP |

### Name Pattern Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `{n}` | 1, 2, 3... | Sequential counter |
| `{n:02d}` | 01, 02, 03... | Zero-padded counter |
| `{n:03d}` | 001, 002, 003... | Three-digit padded counter |
| `{floor}` | Floor variable | Multi-level indexing |
| `{type}` | Device type | From device spec |

### Error Configuration Profiles

Pre-defined error profiles based on device characteristics:

| Device Type | Exception Rate | Timeout Rate | Retry Behavior |
|-------------|---------------|--------------|----------------|
| PLC (modern) | 0.0005 | 0.0001 | Yes, 3 retries |
| PLC (legacy) | 0.002 | 0.001 | Yes, 5 retries |
| RTU (remote) | 0.001 | 0.005 | Yes, 3 retries |
| HMI | 0.0003 | 0.0001 | No |
| Safety PLC | 0.0001 | 0.00001 | Yes, 3 retries |
| I/O Module | 0.0008 | 0.0002 | No |

---

## Protocol Identity & Fingerprinting

The identity system provides realistic device identification responses for each protocol. Each protocol has a dedicated builder in `backend/app/protocol_engines/identity/`.

### Modbus TCP (Function Code 43 MEI)

```python
modbus_identity = {
    "vendor_name": "Siemens AG",                    # OID 0x00
    "product_code": "6ES7 517-3AP00-0AB0",         # OID 0x01 (order number)
    "major_minor_revision": "V3.0.3",              # OID 0x02 (firmware)
    "vendor_url": "http://www.siemens.com",        # OID 0x03
    "product_name": "CPU 1517-3 PN/DP",            # OID 0x04
    "model_name": "S7-1500",                       # OID 0x05
    "user_application_name": "Process Control",    # OID 0x06 (optional)
}
```

**Key Fields for Detection:**
- `vendor_name`: Primary vendor identification
- `product_code`: Model/order number (Siemens MLFB format)
- `major_minor_revision`: Firmware version for CVE matching

### EtherNet/IP (ListIdentity + CIP Identity Object)

```python
ethernet_ip_identity = {
    # Basic ListIdentity fields
    "vendor_id": 1,                    # ODVA-assigned (1=Rockwell)
    "device_type": 14,                 # CIP device type
    "product_code": 55,                # Vendor-specific product code
    "revision_major": 32,              # Firmware major version
    "revision_minor": 11,              # Firmware minor version
    "serial_number": 0x12345678,       # Device serial
    "product_name": "1756-L85E/B",     # Product name string
    "state": 3,                        # Operational state

    # Extended CIP Identity Object
    "cip_identity_object": {
        "status": 0x0030,
        "configuration_consistency_value": 0xABCD,
        "heartbeat_interval": 500,
        "active_language": "English",
        "supported_languages": ["English", "German", "French"],
        "protection_mode": 0,
        "maximum_cip_connections": 256,
    },

    # Connection Manager Object
    "connection_manager_object": {
        "max_concurrent_connections": 64,
        "connection_timeout_multiplier": 8,
    },

    # Assembly Objects (I/O configuration)
    "assembly_objects": {
        "input_assembly": {"instance": 101, "size": 32},
        "output_assembly": {"instance": 100, "size": 32},
        "config_assembly": {"instance": 102, "size": 16},
    },
}
```

**Key Fields for Detection:**
- `vendor_id`: ODVA vendor ID (1=Rockwell, 43=Siemens, etc.)
- `product_name`: Full product identifier
- `revision_major/minor`: Firmware version

### PROFINET (DCP Identify Response)

```python
profinet_identity = {
    # DCP Block (0x02, 0x01) - Device/Vendor ID
    "vendor_id": 0x002A,              # Siemens = 42 (0x002A)
    "device_id": 0x0303,              # Device-specific ID

    # DCP Block (0x02, 0x02) - Name of Station
    "station_name": "plc-cpu1517",    # DNS-like name (lowercase)

    # DCP Block (0x02, 0x03) - Device Type
    "device_type": "CPU 1517-3 PN/DP",

    # DCP Block (0x02, 0x04) - Device Role
    "device_role": 2,                 # 1=IO-device, 2=IO-controller

    # DCP Block (0x02, 0x05) - Software Release
    "sw_release": "V3.0.3",           # V prefix required

    # I&M0 Extended Data
    "im0_manufacturer": "Siemens AG",
    "im0_order_id": "6ES7 517-3AP00-0AB0",
    "im0_hw_revision": 2,
    "im0_sw_revision": "V3.0.3",

    # Protocol Quirks
    "profinet_cycle_time_us": 1000,   # Cycle time (500 for safety)
    "profisafe_enabled": False,
    "f_host_mode": "standard",
}
```

**Key Fields for Detection:**
- `vendor_id`: PROFINET vendor ID (0x002A = Siemens)
- `station_name`: Unique station identifier
- `sw_release`: Firmware version (V prefix required)

### S7comm (SZL System Status List)

```python
s7_identity = {
    # SZL 0x0011 - Module Identification
    "order_code": "6ES7 517-3AP00-0AB0",   # MLFB order number
    "serial_number": "S V-P92001234",       # Serial number
    "firmware_version": "V3.0.3",           # V prefix required
    "module_type": "CPU 1517-3 PN/DP",      # Module description

    # SZL 0x001C - Component Identification
    "component_name": "S7-1500 CPU",
    "copyright": "Siemens AG",
}
```

**Key Fields for Detection:**
- `order_code`: MLFB order number (matches Siemens catalog)
- `firmware_version`: V-prefixed version for CVE matching
- `module_type`: Human-readable module description

### SNMP (MIB-II System Group)

```python
snmp_identity = {
    # Standard MIB-II System Group
    "sys_descr": "Econolite Cobalt ATC V2.1.4",  # CRITICAL: Contains firmware
    "sys_object_id": "1.3.6.1.4.1.1206.4.2.1.1", # Vendor/device OID
    "sys_name": "INT-MAIN-5TH",                   # Device hostname
    "sys_location": "Main St & 5th Ave",          # Physical location
    "sys_contact": "admin@example.gov",           # Contact info
    "sys_services": 72,                           # Services bitmap

    # NTCIP-Specific (for traffic controllers)
    "ntcip_device_type": "asc",                   # asc, dms, ess, rms
    "max_phases": 8,
    "max_detectors": 64,
}
```

**Critical for Detection:**
- `sys_descr`: Primary identification string - **must contain firmware version**
- `sys_object_id`: Enterprise OID for vendor classification

**sys_descr Firmware Interpolation:**

The SNMP builder supports firmware interpolation in `sys_descr`:
```python
# Template approach (recommended)
"sys_descr_template": "Econolite Cobalt ATC {firmware_version}"
# Result: "Econolite Cobalt ATC 3.10"

# Pattern replacement
"sys_descr": "Controller V1.0.0"  # V1.0.0 replaced with new firmware
```

### BACnet/IP (I-Am Response)

```python
bacnet_identity = {
    # Critical for device classification
    "vendor_id": 5,                              # ASHRAE vendor ID
    "vendor_name": "Johnson Controls",
    "model_name": "NAE55 Network Automation Engine",  # CRITICAL
    "firmware_revision": "12.0.3",               # CRITICAL for CVE

    # Device instance (must be unique per network)
    "device_instance": 1,                        # 0-4194302

    # Protocol capabilities
    "max_apdu_length": 1476,                     # 480, 1024, 1476
    "segmentation_supported": 0,                 # 0=both, 1=tx, 2=rx, 3=none
    "protocol_version": 1,
    "protocol_revision": 19,

    # Device properties
    "application_software_version": "12.0.3",
    "system_status": 0,                          # 0=operational
    "object_name": "BACnet-Device",
    "object_types_supported": [0, 1, 2, 3, 4, 5, 8],  # AI,AO,AV,BI,BO,BV,Device
}
```

**Critical for Detection:**
- `model_name`: Primary device classification field
- `firmware_revision`: CVE matching field
- `vendor_id`: ASHRAE vendor ID (5=Johnson Controls, 17=Honeywell)

---

## Vendor Fingerprint Database

### FINGERPRINT_MODEL_MAP

The `FINGERPRINT_MODEL_MAP` in `base.py` maps model names to vendor fingerprints:

```python
FINGERPRINT_MODEL_MAP = {
    # Rockwell Automation
    "1756-L85E": "rockwell_controllogix_l85e",
    "1756-L83E": "rockwell_controllogix_l83e",
    "1769-L33ER": "rockwell_compactlogix_l33er",
    "PowerFlex 525": "rockwell_powerflex_525",
    "PowerFlex 753": "rockwell_powerflex_753",
    "PanelView Plus 7": "rockwell_panelview_plus7",

    # Siemens
    "CPU 1517-3": "siemens_s7_1517",
    "CPU 1516-3": "siemens_s7_1516",
    "CPU 1515-2": "siemens_s7_1515",
    "SINAMICS G120": "siemens_sinamics_g120",
    "ET 200SP": "siemens_et200sp",
    "KTP900 Basic": "siemens_ktp900",

    # Schneider Electric
    "M580": "schneider_m580",
    "M340": "schneider_m340",
    "M251": "schneider_m251",
    "Altivar ATV930": "schneider_atv930",
    "Magelis HMIGTO": "schneider_magelis",

    # Specialty Vendors
    "SICK CLV6xx": "sick_clv6xx",
    "Endress+Hauser Promag": "eh_promag",
    "Yokogawa GC8000": "yokogawa_gc8000",
    "ABB ACS880": "abb_acs880",
}
```

### Fingerprint Structure

Each fingerprint in `backend/app/services/vendor_fingerprints/` contains:

```python
fingerprint = {
    # Basic info
    "vendor": "Siemens",
    "vendor_family": "S7-1500",
    "model": "6ES7 517-3AP00-0AB0",
    "firmware_version": "V3.0.3",

    # MAC address prefixes (for realistic MACs)
    "oui_prefixes": ["00:0E:8C", "00:1B:1B", "00:1C:06"],

    # Protocol identities (see above sections)
    "modbus_identity": {...},
    "ethernet_ip_identity": {...},
    "profinet_identity": {...},
    "s7_identity": {...},
    "snmp_identity": {...},
    "bacnet_identity": {...},

    # TCP/IP stack characteristics
    "tcp_stack": {
        "ttl": 64,                    # Time-to-live
        "window_size": 29200,         # TCP window
        "mss": 1460,                  # Max segment size
        "window_scaling": 7,          # Window scale factor
        "sack_permitted": True,
        "timestamps": True,
    },

    # Response timing
    "response_timing": {
        "mean_ms": 1.8,
        "std_dev_ms": 1.2,
        "min_ms": 0.5,
        "max_ms": 50.0,
        "distribution": "gaussian",
    },

    # Error behavior
    "error_behavior": {
        "exception_probability": 0.0005,
        "timeout_probability": 0.0001,
        "retry_behavior": True,
    },

    # Protocol quirks
    "protocol_quirks": {
        "modbus_max_registers": 125,
        "profinet_cycle_time_us": 1000,
        "s7_max_pdu_size": 960,
    },
}
```

---

## Traffic Flow Configuration

### EnhancedFlowSpec Structure

```python
from app.scenario_templates.base import EnhancedFlowSpec

flow = EnhancedFlowSpec(
    protocol="profinet",              # Protocol name
    pattern="cyclic_io",              # Traffic pattern
    interval_ms=4,                    # Poll/cycle interval
    jitter_ms=1,                      # Timing variance
    jitter_type="gaussian",           # gaussian, uniform, exponential
    source_types=["plc"],             # Source device types
    target_types=["drive", "io_module"],  # Target device types
    learned_timing_profile=None,      # Optional learned profile reference
)
```

### Traffic Patterns

| Pattern | Description | Typical Protocols |
|---------|-------------|-------------------|
| `poll` | Request-response polling | Modbus, DNP3, SNMP |
| `cyclic_io` | Periodic I/O exchange | PROFINET, EtherNet/IP |
| `subscription` | Event-based updates | OPC UA |
| `safety` | Safety-rated communication | CIP Safety, PROFIsafe |
| `unsolicited` | Device-initiated reports | DNP3, IEC 104 |
| `gi` | General interrogation | IEC 104, DNP3 |
| `integrity` | Integrity poll | DNP3 |

### Protocol-Specific Intervals

| Protocol | Typical Range | Use Case |
|----------|--------------|----------|
| PROFINET | 1-8 ms | Motion control, fast I/O |
| PROFINET IRT | 0.25-1 ms | Isochronous motion |
| EtherNet/IP Implicit | 10-100 ms | Standard I/O |
| EtherNet/IP Explicit | 100-1000 ms | Configuration, diagnostics |
| CIP Safety | 4-20 ms | Safety I/O |
| S7comm | 50-500 ms | HMI updates |
| Modbus TCP | 100-2000 ms | SCADA polling |
| DNP3 | 1000-30000 ms | Wide-area SCADA |
| BACnet | 10000-60000 ms | Building automation |
| SNMP | 30000-300000 ms | Network monitoring |

### SmartFlowGenerator Patterns

The `SmartFlowGenerator` in `traffic_generator/flow_generator.py` supports:

| Pattern | Description |
|---------|-------------|
| `REALISTIC` | Role-based OT hierarchy (default) |
| `HIERARCHICAL` | Strict layered communication |
| `MESH` | All-to-all communication |
| `STAR` | Central hub topology |
| `TREE` | Hierarchical branching |

### Device Role Connections

```python
# Role → [Allowed target roles]
ROLE_CONNECTIONS = {
    SCADA: [CONTROLLER, HMI, GATEWAY, HISTORIAN],
    HMI: [CONTROLLER, SCADA],
    CONTROLLER: [FIELD_DEVICE, CONTROLLER, GATEWAY],
    FIELD_DEVICE: [],  # Responds only
    GATEWAY: [CONTROLLER, FIELD_DEVICE],
    HISTORIAN: [CONTROLLER, SCADA],
    ENGINEERING: [CONTROLLER, HMI, SCADA],
    SAFETY: [CONTROLLER, FIELD_DEVICE],
}
```

---

## Timing Models

### Distribution Types

| Distribution | Best For | Parameters |
|-------------|----------|------------|
| `gaussian` | Normal response times | mean_ms, std_dev_ms |
| `lognormal` | Occasional slow responses | mean_ms, std_dev_ms |
| `uniform` | Even distribution | min_ms, max_ms |
| `exponential` | Random arrivals | mean_ms |
| `gamma` | Flexible response modeling | mean_ms, std_dev_ms |
| `learned` | Replay from PCAP | samples list |

### Pre-configured Models

```python
# Fast modern devices (Siemens S7-1500, Rockwell ControlLogix)
FAST_DEVICE_TIMING = {
    "distribution": "gaussian",
    "mean_ms": 2,
    "std_dev_ms": 1,
    "min_ms": 0.5,
    "max_ms": 10,
    "outlier_probability": 0.005,
    "timeout_probability": 0.0001,
}

# Standard devices
DEFAULT_TIMING = {
    "distribution": "gaussian",
    "mean_ms": 10,
    "std_dev_ms": 5,
    "min_ms": 1,
    "max_ms": 50,
    "outlier_probability": 0.01,
    "timeout_probability": 0.0005,
}

# Legacy/slow devices (older RTUs, serial bridges)
SLOW_DEVICE_TIMING = {
    "distribution": "lognormal",
    "mean_ms": 100,
    "std_dev_ms": 50,
    "min_ms": 10,
    "max_ms": 500,
    "outlier_probability": 0.02,
    "timeout_probability": 0.002,
}

# Congested networks
NOISY_NETWORK_TIMING = {
    "distribution": "gamma",
    "mean_ms": 30,
    "std_dev_ms": 20,
    "min_ms": 5,
    "max_ms": 200,
    "outlier_probability": 0.05,
    "timeout_probability": 0.01,
}
```

### Learned Timing Defaults (from 264 PCAPs)

```python
LEARNED_DEFAULTS = {
    "modbus_tcp": {
        "poll_interval_ms": 100,
        "jitter_ms": 10,
        "jitter_type": "gaussian",
        "response_time_ms": 5,
        "sample_count": 67696,
    },
    "ethernet_ip": {
        "poll_interval_ms": 20,
        "jitter_ms": 5,
        "jitter_type": "gaussian",
        "response_time_ms": 5,
        "sample_count": 18374,
    },
    "profinet": {
        "poll_interval_ms": 4,
        "jitter_ms": 1,
        "jitter_type": "gaussian",
        "response_time_ms": 1,
        "sample_count": 500,
    },
    "s7comm": {
        "poll_interval_ms": 50,
        "jitter_ms": 5,
        "jitter_type": "gaussian",
        "response_time_ms": 10,
        "sample_count": 189510,
    },
    "dnp3": {
        "poll_interval_ms": 2500,
        "jitter_ms": 500,
        "jitter_type": "exponential",
        "response_time_ms": 50,
        "sample_count": 828,
    },
    "bacnet": {
        "poll_interval_ms": 60000,
        "jitter_ms": 5000,
        "jitter_type": "uniform",
        "response_time_ms": 100,
        "sample_count": 1200,
    },
}
```

---

## Zone & Network Topology

### Zone Definition

```python
zone = {
    "id": "process",                    # Unique zone ID
    "name": "Process Control Zone",     # Display name
    "level": 2,                         # Purdue model level (0-5)
    "subnet_offset": 2,                 # Creates 10.{n}.{offset}.0/24
    "vlan": 30,                         # VLAN ID
    "security_level": "standard",       # minimal, standard, high, critical
}
```

### Purdue Model Levels

| Level | Name | Typical Devices | Security |
|-------|------|-----------------|----------|
| 5 | Enterprise | Business systems | Standard |
| 4 | Site Business | MES, Historians | Standard |
| 3.5 | DMZ | Firewalls, Proxies | High |
| 3 | Site Operations | SCADA, HMI | High |
| 2 | Area Supervisory | PLCs, Controllers | High |
| 1 | Basic Control | I/O, Drives | Standard |
| 0 | Process | Sensors, Actuators | Minimal |

### IP Allocation

Each scenario receives a `/16` range: `10.{n}.0.0/16` where n = 1-254.

- Zone subnets: `10.{n}.{subnet_offset}.0/24`
- Device IPs start at offset 10: `10.{n}.{subnet_offset}.10`
- Gateway: `.1` address
- Reserved: `.0` (network), `.255` (broadcast)

---

## Phase Definitions

### Standard Phases

```python
STANDARD_PHASES = [
    {
        "name": "startup",
        "duration_percent": 5,
        "traffic_multiplier": 0.1,
        "color": "#52c41a",  # Green
        "behaviors": [
            "connection_establishment",
            "configuration_download",
            "device_discovery",
        ],
        "protocol_patterns": {
            "profinet": ["dcp_identify", "ar_establishment"],
            "ethernet_ip": ["register_session", "forward_open"],
            "modbus": ["initial_read", "cold_restart"],
        },
    },
    {
        "name": "steady_state",
        "duration_percent": 80,
        "traffic_multiplier": 1.0,
        "color": "#1890ff",  # Blue
        "behaviors": [
            "cyclic_io",
            "periodic_poll",
            "spontaneous_events",
            "heartbeat",
        ],
    },
    {
        "name": "maintenance",
        "duration_percent": 5,
        "traffic_multiplier": 0.3,
        "color": "#fa8c16",  # Orange
        "behaviors": [
            "firmware_update",
            "parameter_change",
            "diagnostics",
        ],
    },
    {
        "name": "shutdown",
        "duration_percent": 10,
        "traffic_multiplier": 0.2,
        "color": "#f5222d",  # Red
        "behaviors": [
            "state_save",
            "connection_teardown",
            "alarm_clear",
        ],
    },
]
```

### Phase Presets

| Preset | Phases |
|--------|--------|
| `standard` | startup → steady_state → shutdown |
| `with_maintenance` | startup → steady_state → maintenance → steady_state → shutdown |
| `continuous` | steady_state only |
| `full_lifecycle` | Complete 7-phase sequence |

### Vertical Variations

| Vertical | Startup | Steady State | Maintenance | Shutdown |
|----------|---------|--------------|-------------|----------|
| Manufacturing | 3% | 90% | 2% | 5% |
| Water/Wastewater | 8% | 80% | 7% | 5% |
| Energy/Power | 10% | 75% | 10% | 5% |
| Oil & Gas | 5% | 85% | 5% | 5% |

---

## Anomaly & Security Testing

### Anomaly Categories

```python
class SuggestedAnomalies:
    timing: list[str]     # delayed_response, timeout, watchdog_timeout
    protocol: list[str]   # modbus_exception, cip_error, profinet_alarm
    sequence: list[str]   # duplicate, out_of_order
    payload: list[str]    # value_spike, corrupted_data
    network: list[str]    # packet_loss, jitter_spike
    security: list[str]   # unauthorized_write, scan
```

### External Communications (Attack Simulation)

```python
external_comms = ExternalCommsSpec(
    # C2 Beaconing
    c2_beacon=C2BeaconSpec(
        enabled=True,
        protocol="https",           # http, https, dns
        beacon_interval_s=60,
        jitter_percent=20,
    ),

    # Data Exfiltration
    data_exfil=DataExfilSpec(
        enabled=True,
        protocol="dns",             # http, dns
        data_size_bytes=1024,
        interval_s=300,
    ),

    # Exploit Patterns
    exploits=ExploitSpec(
        enabled=True,
        exploit_types=["modbus_write_scan", "s7_stop_cpu"],
    ),

    # Reconnaissance
    recon=ReconSpec(
        enabled=True,
        scan_type="port_scan",
        target_ports=[502, 102, 44818, 47808],
    ),

    # Target device types for attacks
    target_device_types=["hmi", "plc", "historian"],
)
```

### CVE Integration

Devices can reference CVEs for realistic vulnerability emulation:

```python
device = EnhancedDeviceSpec(
    type="plc",
    vendor="Siemens",
    fingerprint_model="CPU 1517-3",
    cve_ids=[
        "CVE-2019-13945",  # S7-1500 DoS
        "CVE-2020-15782",  # Memory protection bypass
        "CVE-2022-38465",  # Key pair vulnerability
    ],
)
```

The CVEFingerprintService resolves CVE IDs to:
- Vulnerable firmware versions
- Protocol identity overrides
- Attack signatures

---

## CVE Vulnerable Firmware Fingerprinting

This section provides **prescriptive guidance** for configuring devices with CVE vulnerabilities that will be detected by security scanners like Cisco Cyber Vision.

### Overview: How CVE Fingerprinting Works

When you add `cve_ids` to a device specification, PacketArch:

1. **Looks up the CVE** in the `CVEVulnerability` table
2. **Finds a matching `VulnerableFingerprintVariant`** with the vulnerable firmware version
3. **Auto-derives protocol-specific firmware fields** from the single `firmware_version` source
4. **Merges explicit identity overrides** on top of derived fields
5. **Applies the complete override** to the `FingerprintApplicator` during traffic generation

The result: Device identity responses contain the exact vulnerable firmware version that security scanners detect.

### Step 1: Add CVE IDs to Device Specification

**Always specify CVE IDs in your device spec:**

```python
EnhancedDeviceSpec(
    type="plc",
    vendor="Rockwell",                    # MUST match CVE vendor field
    fingerprint_model="1756-L85E",        # Links to base fingerprint
    cve_ids=["CVE-2022-1159"],           # One or more CVE IDs
    # ... other fields
)
```

**Rules:**
- The `vendor` field **must exactly match** the CVE's vendor field (case-insensitive)
- You can specify multiple CVE IDs; the system selects the best matching variant
- If multiple variants exist, selection prioritizes: exact model match → highest severity

### Step 2: Understand the CVEVulnerability Structure

CVEs are stored with these key fields (see `backend/app/models/cve_vulnerability.py`):

```python
CVEVulnerability:
    cve_id: str                    # "CVE-2022-1159"
    vendor: str                    # "Rockwell"
    product_family: str            # "ControlLogix"
    affected_models: list[str]     # ["1756-L81E", "1756-L85E", ...]
    affected_firmware_max: str     # "32.011" - LAST vulnerable version
    fixed_firmware_version: str    # "33.011" - First patched version
    severity: CVESeverity          # critical, high, medium, low
    cvss_score: float              # 9.8
    cyber_vision_detectable: bool  # True for protocol-detectable CVEs
    detection_method: str          # "protocol_identity"
```

### Step 3: Create the VulnerableFingerprintVariant

For each CVE, create one or more `VulnerableFingerprintVariant` records that define the **exact protocol responses** for vulnerable devices.

**The `firmware_version` field is the SINGLE SOURCE OF TRUTH:**

```python
VulnerableFingerprintVariant:
    cve_vulnerability_id: UUID     # Links to CVEVulnerability
    firmware_version: str          # "32.011" - THE KEY FIELD
    display_name: str              # "ControlLogix L85E (CVE-2022-1159)"
    target_vendor: str             # "Rockwell"
    target_models: list[str]       # ["1756-L85E", "1756-L83E"]

    # Protocol-specific identity overrides (all optional - see below)
    modbus_identity_override: dict
    ethernet_ip_identity_override: dict
    profinet_identity_override: dict
    s7_identity_override: dict
    cip_identity_override: dict
    snmp_identity_override: dict
    bacnet_identity_override: dict
    snmp_sys_descr_template: str   # Template with {firmware_version}
```

### Step 4: Configure Protocol Identity Overrides

#### Automatic Firmware Derivation

When you set `firmware_version`, the system **automatically derives** protocol-specific firmware fields:

| Source | Modbus | EtherNet/IP | PROFINET | S7comm | SNMP | BACnet |
|--------|--------|-------------|----------|--------|------|--------|
| `firmware_version: "32.011"` | `major_minor_revision: "32.011"` | `revision_major: 32, revision_minor: 11` | `sw_release: "V32.011"` | `firmware_version: "V32.011"` | Interpolated in sys_descr | `firmware_revision: "32.011"` |
| `firmware_version: "V3.0.3"` | `major_minor_revision: "V3.0.3"` | `revision_major: 3, revision_minor: 0` | `sw_release: "V3.0.3"` | `firmware_version: "V3.0.3"` | Interpolated in sys_descr | `firmware_revision: "3.0.3"` |

**You only need to set `firmware_version` once** - all protocols get the correct format automatically.

#### Explicit Overrides for Non-Firmware Fields

Use protocol-specific override fields for **non-firmware** identity fields:

**Modbus Identity Override:**
```python
modbus_identity_override = {
    "vendor_name": "Rockwell Automation",    # Explicit
    "product_code": "1756-L85E",             # Explicit
    # major_minor_revision: AUTO-DERIVED from firmware_version
    "product_name": "1756-L85E/B LOGIX5585", # Explicit
    "model_name": "ControlLogix 5585E",      # Explicit
    "vendor_url": "www.rockwellautomation.com",
}
```

**EtherNet/IP Identity Override:**
```python
ethernet_ip_identity_override = {
    "vendor_id": 1,                          # ODVA Rockwell ID
    "device_type": 14,                       # CIP PLC type
    "product_code": 0x37,                    # Vendor-specific
    # revision_major/minor: AUTO-DERIVED from firmware_version
    "serial_number": 0x1234ABCD,
    "product_name": "1756-L85E/B LOGIX5585",
    "state": 3,                              # Operational
}
```

**CIP Identity Object Override (Deep Fingerprinting):**
```python
cip_identity_override = {
    "protection_mode": 0,                    # 0 = no protection (VULNERABLE!)
    "configuration_consistency_value": 0xDEAD0000,  # Indicates vulnerable config
    "heartbeat_interval": 250,
    "maximum_cip_connections": 64,
    "active_language": "English",
}
```

**PROFINET Identity Override:**
```python
profinet_identity_override = {
    "vendor_id": 0x002A,                     # Siemens PROFINET ID
    "device_id": 0x0500,
    "device_type": "CPU 1516-3 PN/DP",
    "order_id": "6ES7 516-3AN01-0AB0",
    # sw_release: AUTO-DERIVED with V prefix
}
```

**S7comm Identity Override:**
```python
s7_identity_override = {
    "order_code": "6ES7 516-3AN01-0AB0",     # MLFB order number
    "module_type": "CPU 1516-3 PN/DP",
    "serial_number": "S V-P92001234",
    # firmware_version: AUTO-DERIVED with V prefix
}
```

**SNMP Identity Override:**
```python
snmp_identity_override = {
    # sys_descr: Use snmp_sys_descr_template instead for firmware interpolation
    "sys_object_id": "1.3.6.1.4.1.4329.2.51.1516",
    "sys_name": "S7-1516-3-PN-DP",
    "sys_location": "Main Control Area",
    "sys_contact": "admin@example.com",
}

# Template for firmware interpolation in sys_descr
snmp_sys_descr_template = "Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP {firmware_version}"
# Result: "Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP V2.8.0"
```

**BACnet Identity Override:**
```python
bacnet_identity_override = {
    "vendor_id": 5,                          # Johnson Controls ASHRAE ID
    "vendor_name": "Johnson Controls",
    "model_name": "NAE55 Network Automation Engine",  # CRITICAL for detection
    # firmware_revision: AUTO-DERIVED from firmware_version
    "device_instance": 100001,
    "max_apdu_length": 1476,
}
```

### Step 5: Complete CVE Configuration Example

**Rockwell ControlLogix CVE-2022-1159 (Studio 5000 Code Execution):**

```python
# In backend/app/services/cve_data/rockwell_cves.py

ROCKWELL_CVES = [
    {
        "cve_id": "CVE-2022-1159",
        "title": "Rockwell Studio 5000 Logix Designer Code Execution",
        "vendor": "Rockwell",
        "product_family": "ControlLogix",
        "affected_models": ["1756-L81E", "1756-L82E", "1756-L83E", "1756-L85E"],
        "affected_firmware_max": "32.011",
        "fixed_firmware_version": "33.011",
        "severity": "critical",
        "cvss_score": 9.8,
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",

        "vulnerable_variants": [
            {
                # THE SINGLE SOURCE OF TRUTH
                "firmware_version": "32.011",

                "display_name": "ControlLogix L85E (CVE-2022-1159)",
                "target_vendor": "Rockwell",
                "target_models": ["1756-L85E", "1756-L83E"],

                # Modbus FC 43 response
                "modbus_identity_override": {
                    "vendor_name": "Rockwell Automation",
                    "product_code": "1756-L85E",
                    # major_minor_revision: AUTO "32.011"
                    "product_name": "1756-L85E/B LOGIX5585",
                    "model_name": "ControlLogix 5585E",
                },

                # EtherNet/IP ListIdentity
                "ethernet_ip_identity_override": {
                    "vendor_id": 1,
                    "device_type": 14,
                    "product_code": 0x37,
                    # revision_major: AUTO 32
                    # revision_minor: AUTO 11
                    "product_name": "1756-L85E/B LOGIX5585",
                },

                # CIP Identity Object (extended fingerprinting)
                "cip_identity_override": {
                    "protection_mode": 0,      # VULNERABLE: No protection
                    "configuration_consistency_value": 0xDEAD0000,
                    "maximum_cip_connections": 64,
                },
            },
        ],
    },
]
```

**Siemens S7-1500 CVE-2019-13945 (Cryptographic Vulnerability):**

```python
# In backend/app/services/cve_data/siemens_cves.py

SIEMENS_CVES = [
    {
        "cve_id": "CVE-2019-13945",
        "title": "Siemens S7-1500 CPU Cryptographic Vulnerability",
        "vendor": "Siemens",
        "product_family": "S7-1500",
        "affected_models": ["6ES7 516-3AN01-0AB0", "6ES7 517-3AP00-0AB0"],
        "affected_firmware_max": "V2.8.0",
        "fixed_firmware_version": "V2.8.1",
        "severity": "high",
        "cvss_score": 7.5,
        "cyber_vision_detectable": True,
        "detection_method": "protocol_identity",

        "vulnerable_variants": [
            {
                # THE SINGLE SOURCE OF TRUTH (with V prefix for Siemens)
                "firmware_version": "V2.8.0",

                "display_name": "S7-1516 CPU (CVE-2019-13945)",
                "target_vendor": "Siemens",
                "target_models": ["6ES7 516-3AN01-0AB0"],

                # S7comm SZL response
                "s7_identity_override": {
                    "order_code": "6ES7 516-3AN01-0AB0",
                    "module_type": "CPU 1516-3 PN/DP",
                    "serial_number": "S V-P92001234",
                    # firmware_version: AUTO "V2.8.0"
                },

                # PROFINET DCP response
                "profinet_identity_override": {
                    "vendor_id": 0x002A,       # Siemens
                    "device_id": 0x0500,
                    "device_type": "CPU 1516-3 PN/DP",
                    "order_id": "6ES7 516-3AN01-0AB0",
                    # sw_release: AUTO "V2.8.0"
                },

                # SNMP with firmware template
                "snmp_sys_descr_template": "Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP {firmware_version}",
                # Result: "Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP V2.8.0"
            },
        ],
    },
]
```

### Step 6: Using CVE Devices in Templates

**In your template file:**

```python
# backend/app/scenario_templates/manufacturing.py

DISCRETE_MANUFACTURING_TEMPLATE = {
    "name": "discrete_manufacturing_vulnerable",
    "display_name": "Vulnerable Manufacturing Plant",
    "description": "Manufacturing scenario with CVE-vulnerable devices for security testing",

    "devices": [
        # Vulnerable Rockwell PLCs
        EnhancedDeviceSpec(
            type="plc",
            vendor="Rockwell",
            count=4,
            zone="process",
            name_pattern="PLC-{n:03d}",
            protocols=["ethernet_ip", "modbus"],
            fingerprint_model="1756-L85E",
            cve_ids=["CVE-2022-1159"],        # STUDIO 5000 VULNERABILITY
            role="Process Controller",
        ),

        # Vulnerable Siemens PLCs
        EnhancedDeviceSpec(
            type="plc",
            vendor="Siemens",
            count=2,
            zone="process",
            name_pattern="S7-{n:03d}",
            protocols=["profinet", "s7comm"],
            fingerprint_model="CPU 1516-3",
            cve_ids=[
                "CVE-2019-13945",              # Crypto vulnerability
                "CVE-2020-15782",              # Memory protection bypass
            ],
            role="Safety Controller",
        ),

        # Legacy vulnerable devices (no patch available)
        EnhancedDeviceSpec(
            type="plc",
            vendor="Schneider",
            count=3,
            zone="field",
            name_pattern="M340-{n:03d}",
            protocols=["modbus"],
            fingerprint_model="M340",
            cve_ids=["CVE-2018-7760"],         # Hardcoded FTP credentials
            role="Legacy Controller",
        ),
    ],
    # ... zones, flows, etc.
}
```

### CVE Resolution Priority

When multiple CVE IDs are specified, the system selects a variant using this priority:

1. **Exact model match**: Variant's `target_models` contains `fingerprint_model`
2. **Product family match**: Variant's `target_vendor` matches device `vendor`
3. **Highest severity**: Among matching variants, select highest `cvss_score`

### Firmware Version Format by Vendor

**Always use the correct format for each vendor:**

| Vendor | Format | Example | Notes |
|--------|--------|---------|-------|
| Rockwell | Decimal | `32.011` | Major.Minor (zero-padded minor) |
| Siemens | V-prefix | `V2.8.0` or `V3.0.3` | Always starts with "V" |
| Schneider | Numeric | `3.10` or `3.10.2` | Semantic versioning |
| ABB | Numeric | `1.2.3` | Semantic versioning |
| Honeywell | Numeric | `12.0.3` | Semantic versioning |
| GE | Numeric | `8.10` | Major.Minor |
| SEL | Numeric | `R123` or `123` | Release number |

### Protocol Detection Fields (What Security Scanners Look For)

| Protocol | Primary Detection Field | Secondary Fields |
|----------|------------------------|------------------|
| **Modbus** | `major_minor_revision` | `product_code`, `vendor_name` |
| **EtherNet/IP** | `revision_major` + `revision_minor` | `product_name`, `vendor_id` |
| **PROFINET** | `sw_release` | `vendor_id`, `device_type` |
| **S7comm** | `firmware_version` | `order_code`, `module_type` |
| **SNMP** | `sys_descr` (contains firmware) | `sys_object_id` |
| **BACnet** | `firmware_revision` | `model_name`, `vendor_id` |

### Checklist for CVE Configuration

- [ ] CVE ID exists in `CVEVulnerability` table
- [ ] `VulnerableFingerprintVariant` created with correct `firmware_version`
- [ ] `firmware_version` uses correct vendor format (V-prefix for Siemens, etc.)
- [ ] Device `vendor` field matches CVE vendor (case-insensitive)
- [ ] Protocol identity overrides include all non-firmware fields
- [ ] For SNMP: `snmp_sys_descr_template` includes `{firmware_version}` placeholder
- [ ] For CIP: `cip_identity_override` includes `protection_mode: 0` if applicable
- [ ] `target_models` includes the `fingerprint_model` used in device spec
- [ ] CVE is marked `cyber_vision_detectable: True` if protocol-detectable

### Key Files for CVE Configuration

| Component | Path |
|-----------|------|
| CVE Vulnerability Model | `backend/app/models/cve_vulnerability.py` |
| Vulnerable Variant Model | `backend/app/models/vulnerable_fingerprint.py` |
| CVE Fingerprint Service | `backend/app/services/cve_fingerprint_service.py` |
| Firmware Version Deriver | `backend/app/protocol_engines/firmware_version_deriver.py` |
| Fingerprint Applicator | `backend/app/protocol_engines/fingerprint_applicator.py` |
| Rockwell CVE Data | `backend/app/services/cve_data/rockwell_cves.py` |
| Siemens CVE Data | `backend/app/services/cve_data/siemens_cves.py` |
| Schneider CVE Data | `backend/app/services/cve_data/schneider_cves.py` |

---

## Complete Template Example

```python
# backend/app/scenario_templates/example_vertical.py

from .base import (
    EnhancedDeviceSpec,
    EnhancedFlowSpec,
    ErrorConfig,
    SuggestedAnomalies,
    ExternalCommsSpec,
)

EXAMPLE_MANUFACTURING_TEMPLATE = {
    "name": "discrete_manufacturing",
    "display_name": "Discrete Manufacturing Plant",
    "description": "Modern discrete manufacturing with Siemens PLCs and drives",
    "vertical": "manufacturing",
    "total_duration_ms": 3600000,  # 1 hour

    # Zone definitions (Purdue model)
    "zones": [
        {
            "id": "enterprise",
            "name": "Enterprise Zone",
            "level": 4,
            "subnet_offset": 0,
            "vlan": 10,
            "security_level": "standard",
        },
        {
            "id": "dmz",
            "name": "Industrial DMZ",
            "level": 3.5,
            "subnet_offset": 1,
            "vlan": 20,
            "security_level": "high",
        },
        {
            "id": "process",
            "name": "Process Control Zone",
            "level": 2,
            "subnet_offset": 2,
            "vlan": 30,
            "security_level": "high",
        },
        {
            "id": "field",
            "name": "Field Device Zone",
            "level": 1,
            "subnet_offset": 3,
            "vlan": 40,
            "security_level": "standard",
        },
    ],

    # Device specifications
    "devices": [
        # Process Controllers
        EnhancedDeviceSpec(
            type="plc",
            vendor="Siemens",
            count=4,
            zone="process",
            name_pattern="PLC-{n:03d}",
            protocols=["profinet", "s7comm"],
            fingerprint_model="CPU 1517-3",
            error_config=ErrorConfig(
                exception_rate=0.0005,
                timeout_rate=0.0001,
            ),
            role="Process Controller",
            cve_ids=["CVE-2019-13945"],
        ),

        # HMI Panels
        EnhancedDeviceSpec(
            type="hmi",
            vendor="Siemens",
            count=3,
            zone="process",
            name_pattern="HMI-{n:03d}",
            protocols=["s7comm"],
            fingerprint_model="KTP900 Basic",
            role="Operator Interface",
        ),

        # Variable Frequency Drives
        EnhancedDeviceSpec(
            type="drive",
            vendor="Siemens",
            count=12,
            zone="field",
            name_pattern="VFD-{n:03d}",
            protocols=["profinet"],
            fingerprint_model="SINAMICS G120",
            error_config=ErrorConfig(
                exception_rate=0.001,
                timeout_rate=0.0005,
            ),
            role="Motor Drive",
        ),

        # Remote I/O
        EnhancedDeviceSpec(
            type="io_module",
            vendor="Siemens",
            count=18,
            zone="field",
            name_pattern="RIO-{n:03d}",
            protocols=["profinet"],
            fingerprint_model="ET 200SP",
            role="Remote I/O",
        ),

        # Network Infrastructure
        EnhancedDeviceSpec(
            type="switch",
            vendor="Siemens",
            count=3,
            zone="process",
            name_pattern="SW-{n:03d}",
            protocols=["snmp"],
            fingerprint_model="SCALANCE X208",
            role="Network Switch",
        ),
    ],

    # Traffic flows
    "flows": [
        # High-speed PROFINET I/O
        EnhancedFlowSpec(
            protocol="profinet",
            pattern="cyclic_io",
            interval_ms=4,
            jitter_ms=1,
            jitter_type="gaussian",
            source_types=["plc"],
            target_types=["drive", "io_module"],
        ),

        # HMI Updates
        EnhancedFlowSpec(
            protocol="s7comm",
            pattern="poll",
            interval_ms=500,
            jitter_ms=50,
            jitter_type="gaussian",
            source_types=["hmi"],
            target_types=["plc"],
        ),

        # Network Monitoring
        EnhancedFlowSpec(
            protocol="snmp",
            pattern="poll",
            interval_ms=30000,
            jitter_ms=5000,
            jitter_type="uniform",
            source_types=["switch"],
            target_types=["plc", "hmi"],
        ),
    ],

    # Suggested anomalies for testing
    "suggested_anomalies": SuggestedAnomalies(
        timing=["delayed_response", "timeout"],
        protocol=["s7_alarm", "profinet_diagnosis"],
        sequence=["duplicate"],
        payload=["value_spike"],
        network=["jitter_spike"],
        security=["unauthorized_write", "scan"],
    ),

    # External communications (attack simulation)
    "external_comms": ExternalCommsSpec(
        c2_beacon={
            "enabled": True,
            "protocol": "https",
            "beacon_interval_s": 60,
        },
        exploits={
            "enabled": True,
            "exploit_types": ["s7_stop_cpu"],
        },
        recon={
            "enabled": True,
            "scan_type": "port_scan",
        },
        target_device_types=["hmi", "plc"],
    ),
}
```

---

## Checklist for Perfect Templates

### Device Configuration
- [ ] Appropriate device types for the vertical
- [ ] Realistic vendor/model combinations
- [ ] Valid fingerprint_model keys from FINGERPRINT_MODEL_MAP
- [ ] Meaningful device roles
- [ ] Appropriate error configurations
- [ ] CVE IDs for security testing (when applicable)

### Protocol Fingerprinting
- [ ] All device protocols have corresponding identity fields
- [ ] Firmware versions match vendor conventions
  - Siemens: V-prefixed (V3.0.3)
  - Rockwell: Decimal (32.11)
  - Schneider/ABB/Honeywell: Semantic (1.2.3)
- [ ] Vendor IDs match ODVA/ASHRAE/PROFINET registrations
- [ ] Product codes match vendor catalogs (MLFB for Siemens, catalog # for Rockwell)
- [ ] SNMP sys_descr contains vendor, model, AND firmware version
- [ ] BACnet model_name and firmware_revision are set (critical for CVE detection)

### CVE Vulnerable Firmware (when security testing)
- [ ] CVE ID exists in CVEVulnerability table
- [ ] VulnerableFingerprintVariant created with correct firmware_version
- [ ] firmware_version uses correct vendor format:
  - Rockwell: `32.011` (no prefix)
  - Siemens: `V2.8.0` (V prefix required)
  - Others: `1.2.3` (semantic)
- [ ] Device vendor field EXACTLY matches CVE vendor (case-insensitive)
- [ ] Protocol identity overrides include ALL non-firmware fields
- [ ] SNMP: snmp_sys_descr_template includes `{firmware_version}` placeholder
- [ ] CIP: cip_identity_override includes `protection_mode: 0` for vulnerable configs
- [ ] target_models in variant includes the fingerprint_model from device spec
- [ ] CVE marked `cyber_vision_detectable: True` for protocol-detectable vulnerabilities
- [ ] Explicit overrides do NOT duplicate auto-derived firmware fields

### Traffic Flows
- [ ] Realistic poll intervals for each protocol
- [ ] Appropriate jitter configuration
- [ ] Source/target type pairings make sense
- [ ] Protocol matches device capabilities

### Network Topology
- [ ] Zones follow Purdue model
- [ ] VLAN assignments are logical
- [ ] Subnet offsets don't overlap
- [ ] Security levels appropriate

### Timing
- [ ] Response timing matches device class
- [ ] Jitter appropriate for network type
- [ ] Outlier/timeout probabilities realistic

### Phases
- [ ] Phase durations sum to 100%
- [ ] Traffic multipliers appropriate
- [ ] Behaviors match phase purpose

### Security Testing (if applicable)
- [ ] External comms configured
- [ ] Target device types appropriate
- [ ] CVEs are valid and resolvable
- [ ] Attack patterns match the CVE exploit type

---

## Key File Locations

| Component | Path |
|-----------|------|
| Template Base Types | `backend/app/scenario_templates/base.py` |
| Phase Definitions | `backend/app/scenario_templates/phases.py` |
| Template Registry | `backend/app/scenario_templates/__init__.py` |
| Template API | `backend/app/api/routes/templates.py` |
| Identity Builders | `backend/app/protocol_engines/identity/` |
| Timing Models | `backend/app/protocol_engines/timing/` |
| Flow Generator | `backend/app/traffic_generator/flow_generator.py` |
| Traffic Orchestrator | `backend/app/traffic_generator/orchestrator.py` |
| Vendor Fingerprints | `backend/app/services/vendor_fingerprints/` |
| CVE Vulnerability Model | `backend/app/models/cve_vulnerability.py` |
| Vulnerable Variant Model | `backend/app/models/vulnerable_fingerprint.py` |
| CVE Fingerprint Service | `backend/app/services/cve_fingerprint_service.py` |
| Firmware Version Deriver | `backend/app/protocol_engines/firmware_version_deriver.py` |
| Fingerprint Applicator | `backend/app/protocol_engines/fingerprint_applicator.py` |
| Rockwell CVE Data | `backend/app/services/cve_data/rockwell_cves.py` |
| Siemens CVE Data | `backend/app/services/cve_data/siemens_cves.py` |
| Schneider CVE Data | `backend/app/services/cve_data/schneider_cves.py` |
