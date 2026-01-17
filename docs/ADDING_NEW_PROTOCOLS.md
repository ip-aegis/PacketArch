# Adding New Protocols to PacketArch

This guide covers all steps necessary to ensure proper end-to-end fingerprinting when adding new protocols to PacketArch. The **primary goal** is ensuring devices appear correctly in security monitoring tools (Cisco Cyber Vision) with accurate vendor, model, firmware version, and CVE vulnerability detection.

---

## Table of Contents

1. [Fingerprinting Goals & Success Criteria](#1-fingerprinting-goals--success-criteria)
2. [Architecture Overview](#2-architecture-overview)
3. [Backend Components](#3-backend-components)
4. [Traffic Generator Components](#4-traffic-generator-components)
5. [Step-by-Step Implementation Checklist](#5-step-by-step-implementation-checklist)
6. [Protocol Reference Examples](#6-protocol-reference-examples)
   - [S7comm (Siemens)](#s7comm-siemens)
   - [EtherNet/IP (Rockwell)](#ethernetip-rockwell)
   - [PROFINET (Siemens)](#profinet-siemens)
   - [Rockwell EtherNet/IP (Reference Implementation)](#rockwell-ethernetip-reference-implementation)
7. [Verification & Troubleshooting](#7-verification--troubleshooting)

---

## 1. Fingerprinting Goals & Success Criteria

### Primary Goal

**Devices must be detected by Cisco Cyber Vision with complete identity information:**

- Device appears in Cyber Vision device inventory
- Vendor name correctly identified
- Model name correctly identified
- Firmware version visible and parseable
- CVE vulnerabilities flagged when present

### How Protocols Expose Identity

Each OT protocol has specific mechanisms for exposing device identity to passive network scanners:

| Protocol | Identity Mechanism | Key Fields for Detection |
|----------|-------------------|-------------------------|
| **Modbus TCP** | Function Code 43 (MEI) | `vendor_name`, `product_code`, `major_minor_revision` |
| **EtherNet/IP** | ListIdentity Response | `vendor_id`, `device_type`, `product_name`, `revision_major/minor` |
| **PROFINET** | DCP Identify Response | `vendor_id`, `device_id`, `station_name`, `sw_release` |
| **S7comm** | SZL Read Response | `order_code`, `module_type`, `firmware_version` |
| **SNMP** | sysDescr OID | Firmware embedded in description string |
| **BACnet** | I-Am Broadcast | `vendor_id`, `device_instance`, `firmware_revision` |
| **CIP** | Identity Object (0x01) | `vendor_id`, `product_code`, `revision_major/minor` |

### Critical Success Factors

When implementing a new protocol, ensure:

1. **Discovery packets are generated** - Without discovery, devices remain invisible
2. **Identity fields are populated** - Empty fields mean incomplete detection
3. **Firmware version is in correct format** - Each protocol has specific formatting requirements
4. **CVE overrides are applied** - Vulnerability detection requires correct firmware version

---

## 2. Architecture Overview

PacketArch uses a multi-layered fingerprinting system:

```
┌─────────────────────────────────────────────────────────────────┐
│ BASE FINGERPRINTS (backend/app/services/vendor_fingerprints/)   │
│ - All identity fields: vendor, model, firmware, serial         │
│ - Protocol identities: modbus, ethernet_ip, profinet, s7, etc. │
│ - TCP stack, timing, error behavior                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ CVE OVERRIDES (backend/app/services/cve_data/)                  │
│ - Only FIRMWARE-related protocol fields                         │
│ - Applied on top of base fingerprints                           │
│ - Uses firmware_version for auto-derivation                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO DEVICE                                                 │
│ - Combines base fingerprint + CVE override + device enrichment  │
│ - Exported as JSON in scenario definition                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ TRAFFIC GENERATOR                                               │
│ - DeviceContext.get_effective_identity() merges all layers      │
│ - Protocol engines generate packets with fingerprinted identity │
│ - Packets injected to network interface                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ CISCO CYBER VISION                                              │
│ - Passively monitors network traffic                            │
│ - Parses protocol identity fields                               │
│ - Creates device inventory with vendor/model/firmware           │
│ - Matches firmware against CVE database                         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Insight

- **Non-firmware fields** (vendor, model, serial, product_name) come from **base fingerprints**
- **Firmware version fields** come from **CVE overrides** (to simulate vulnerable versions)
- The `FirmwareVersionDeriver` auto-converts a single `firmware_version` to all protocol-specific formats

### Data Flow: Scenario to Traffic Generator

Understanding the complete data flow is critical for debugging fingerprinting issues:

```
1. SCENARIO CREATION (Backend)
   └── Device spec includes: vendorFingerprint, cveIds
   └── CVEFingerprintService.resolve_device_cve_config() merges CVE overrides
   └── Result: cveIdentityOverrides added to device spec

2. SCENARIO EXPORT (API)
   └── GET /api/v1/scenarios/{id}
   └── JSON includes: devices[].vendorFingerprint, devices[].cveIdentityOverrides

3. TRAFFIC GENERATOR ENTRYPOINT (entrypoint.py)
   └── parse_scenario() loads JSON
   └── build_device_fingerprint() merges fingerprint + CVE overrides
   └── create_flow_from_definition() creates DeviceContext with fingerprint

4. PACKET GENERATION (live_orchestrator.py)
   └── DeviceContext.vendor_fingerprint has merged fingerprint
   └── DeviceContext.vulnerability_override has CVE overrides
   └── get_effective_identity() merges both at packet build time
```

**Key Merge Points:**
- `entrypoint.py:build_device_fingerprint()` - First merge (adds cveIdentityOverrides to fingerprint)
- `DeviceContext.get_effective_identity()` - Second merge (applies vulnerability overrides at runtime)

**Debugging Checklist:**
1. Check scenario JSON has `cveIdentityOverrides` populated
2. Check entrypoint logs show CVE override merging
3. Check `get_effective_identity()` returns correct merged values

---

## 3. Backend Components

### 3.1 Database Models

#### VendorFingerprint Model

Location: `backend/app/models/vendor_fingerprint.py`

This model stores base device fingerprints with protocol-specific identity blocks:

```python
class VendorFingerprint(Base):
    __tablename__ = "vendor_fingerprints"

    # Basic identification
    vendor: Mapped[str] = mapped_column(String(100), nullable=False)
    vendor_family: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    firmware_version: Mapped[str | None] = mapped_column(String(50))

    # Protocol-specific identity responses (JSONB)
    modbus_identity: Mapped[dict | None] = mapped_column(JSONB)
    ethernet_ip_identity: Mapped[dict | None] = mapped_column(JSONB)
    profinet_identity: Mapped[dict | None] = mapped_column(JSONB)
    # ADD YOUR NEW PROTOCOL HERE:
    # your_protocol_identity: Mapped[dict | None] = mapped_column(JSONB)
```

**To add a new protocol:** Add a new JSONB column for your protocol identity.

#### VulnerableFingerprintVariant Model

Location: `backend/app/models/vulnerable_fingerprint.py`

This model stores CVE-specific identity overrides:

```python
class VulnerableFingerprintVariant(Base):
    __tablename__ = "vulnerable_fingerprint_variants"

    # Firmware version - single source of truth for auto-derivation
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Protocol identity overrides (JSONB) - only for non-firmware fields
    modbus_identity_override: Mapped[dict | None] = mapped_column(JSONB)
    ethernet_ip_identity_override: Mapped[dict | None] = mapped_column(JSONB)
    profinet_identity_override: Mapped[dict | None] = mapped_column(JSONB)
    s7_identity_override: Mapped[dict | None] = mapped_column(JSONB)
    snmp_identity_override: Mapped[dict | None] = mapped_column(JSONB)
    bacnet_identity_override: Mapped[dict | None] = mapped_column(JSONB)
    cip_identity_override: Mapped[dict | None] = mapped_column(JSONB)
    # ADD YOUR NEW PROTOCOL HERE:
    # your_protocol_identity_override: Mapped[dict | None] = mapped_column(JSONB)
```

### 3.2 Vendor Fingerprint Data Files

Location: `backend/app/services/vendor_fingerprints/`

Each vendor has a data file that defines device fingerprints. Example from `siemens.py`:

```python
def get_siemens_fingerprints() -> list[dict[str, Any]]:
    return [
        {
            "vendor": "Siemens",
            "vendor_family": "S7-1500",
            "model": "6ES7 517-3AP00-0AB0",
            "firmware_version": "V3.0.3",
            "oui_prefixes": ["00:0E:8C", "00:1B:1B"],

            # Protocol identity blocks - populated with ALL non-firmware fields
            "modbus_identity": {
                "vendor_name": "Siemens AG",
                "product_code": "6ES7 517-3AP00-0AB0",
                "major_minor_revision": "V3.0.3",  # Firmware field
                "product_name": "CPU 1517-3 PN/DP",
            },
            "profinet_identity": {
                "vendor_id": 0x002A,
                "device_id": 0x0303,
                "device_type": "CPU 1517-3 PN/DP",
                "station_name": "plc-cpu1517",
                "im0_sw_revision": "V3.0.3",  # Firmware field
            },
            # ADD YOUR NEW PROTOCOL IDENTITY BLOCK HERE:
            # "your_protocol_identity": {
            #     "field1": "value1",
            #     "field2": "value2",
            #     "firmware_field": "V3.0.3",
            # },

            "is_builtin": True,
        },
    ]
```

**Key Fields:**
- Non-firmware fields (vendor_name, product_code, device_type) - static device identity
- Firmware fields (major_minor_revision, im0_sw_revision) - may be overridden by CVE data

### 3.3 CVE Data Files

Location: `backend/app/services/cve_data/`

CVE data files define vulnerabilities and their vulnerable firmware variants:

```python
from datetime import datetime

SIEMENS_CVES: list[dict] = [
    {
        "cve_id": "CVE-2019-13945",
        "title": "Siemens S7-1500 CPU Cryptographic Vulnerability",
        "description": "...",
        "severity": "high",
        "cvss_score": 7.5,
        "vendor": "Siemens",
        "product_family": "S7-1500",
        "affected_models": ["6ES7 516-3AN01-0AB0"],
        "affected_firmware_max": "V2.8.0",
        "fixed_firmware_version": "V2.8.1",
        "cyber_vision_detectable": True,
        "published_date": datetime(2019, 12, 10),

        # Vulnerable variants - defines specific firmware versions to emulate
        "vulnerable_variants": [
            {
                # firmware_version is the SINGLE SOURCE OF TRUTH
                # All protocol-specific firmware fields are AUTO-DERIVED from this
                "firmware_version": "V2.8.0",
                "display_name": "S7-1516 CPU (CVE-2019-13945)",

                # Only include NON-FIRMWARE overrides if needed
                "s7_identity_override": {
                    "order_code": "6ES7 516-3AN01-0AB0",
                    "module_type": "CPU 1516-3 PN/DP",
                },
            },
        ],
    },
]
```

**Important:** Use `firmware_version` as the single source of truth. The `FirmwareVersionDeriver` automatically derives protocol-specific firmware fields.

### 3.4 FirmwareVersionDeriver

Location: `backend/app/protocol_engines/firmware_version_deriver.py`

This class auto-derives protocol-specific firmware fields from a single `firmware_version`:

```python
class FirmwareVersionDeriver:
    """Auto-derive protocol-specific identity fields from firmware_version."""

    def __init__(self, firmware_version: str, base_identity: dict = None):
        self.firmware_version = firmware_version
        self.parsed = FirmwareVersionParser.parse(firmware_version)
        self.base_identity = base_identity or {}

    def derive_modbus(self) -> dict:
        """Modbus: major_minor_revision as string."""
        return {"major_minor_revision": self.parsed.full_numeric}

    def derive_ethernet_ip(self) -> dict:
        """EtherNet/IP: revision_major/minor as integers."""
        return {
            "revision_major": self.parsed.major,
            "revision_minor": self.parsed.minor,
        }

    def derive_profinet(self) -> dict:
        """PROFINET: sw_release with V prefix."""
        return {"sw_release": f"V{self.parsed.full_numeric}"}

    def derive_s7(self) -> dict:
        """S7: firmware_version with V prefix."""
        return {"firmware_version": f"V{self.parsed.full_numeric}"}

    # ADD YOUR NEW PROTOCOL DERIVATION METHOD HERE:
    # def derive_your_protocol(self) -> dict:
    #     """YourProtocol: describe firmware field format."""
    #     return {"firmware_field": f"{self.parsed.major}.{self.parsed.minor}"}

    def derive_all(self, snmp_sys_descr_template: str = None) -> dict:
        """Derive ALL protocol identities."""
        return {
            "modbus_identity": self.derive_modbus(),
            "ethernet_ip_identity": self.derive_ethernet_ip(),
            "profinet_identity": self.derive_profinet(),
            "s7_identity": self.derive_s7(),
            "snmp_identity": self.derive_snmp(snmp_sys_descr_template),
            "bacnet_identity": self.derive_bacnet(),
            "cip_identity_object": self.derive_cip(),
            # ADD YOUR NEW PROTOCOL HERE:
            # "your_protocol_identity": self.derive_your_protocol(),
        }
```

### 3.5 Firmware Version Formats

Different protocols require different firmware version formats:

| Protocol | Field Name | Format | Example Input | Example Output |
|----------|-----------|--------|---------------|----------------|
| Modbus | `major_minor_revision` | String | "3.10" | "3.10" |
| EtherNet/IP | `revision_major`, `revision_minor` | Integers | "3.10" | 3, 10 |
| PROFINET | `sw_release` | V-prefixed string | "3.10" | "V3.10" |
| S7comm | `firmware_version` | V-prefixed string | "3.10" | "V3.10" |
| SNMP | `sys_descr` | Embedded in string | "3.10" | "Device V3.10" |
| BACnet | `firmware_revision` | String | "3.10" | "3.10" |
| CIP | `revision_major`, `revision_minor` | Integers | "3.10" | 3, 10 |

### 3.6 Seeding Logic

Location: `backend/app/services/seed_data.py`

Fingerprints and CVEs are loaded into the database at startup:

```python
from app.services.vendor_fingerprints import VENDOR_FINGERPRINTS
from app.services.cve_data import ALL_CVES

async def seed_vendor_fingerprints(session: AsyncSession) -> None:
    for fp_data in VENDOR_FINGERPRINTS:
        # Create VendorFingerprint record
        fingerprint = VendorFingerprint(**fp_data)
        session.add(fingerprint)

async def seed_cve_data(session: AsyncSession) -> None:
    for cve_data in ALL_CVES:
        # Create CVEVulnerability and VulnerableFingerprintVariant records
        ...
```

**To add a new protocol:** Ensure your vendor fingerprints and CVE data are imported in the respective `__init__.py` files.

---

## 4. Traffic Generator Components

Location: `docker/traffic-generator/app/live_orchestrator.py`

### 4.1 Protocol Constants

Define protocol-specific constants at the top of the file:

```python
# S7comm constants (Siemens S7 protocol)
S7_PORT = 102  # ISO-on-TCP

# TPKT header (RFC 1006)
TPKT_VERSION = 0x03

# COTP (ISO 8073) PDU types
COTP_PDU_CR = 0xE0  # Connection Request
COTP_PDU_CC = 0xD0  # Connection Confirm
COTP_PDU_DT = 0xF0  # Data Transfer

# S7comm PDU types
S7_PDU_JOB = 0x01
S7_PDU_ACK_DATA = 0x03
S7_PDU_USERDATA = 0x07

# ADD YOUR PROTOCOL CONSTANTS HERE:
# YOUR_PROTOCOL_PORT = 12345
# YOUR_PROTOCOL_MSG_TYPE_1 = 0x01
# YOUR_PROTOCOL_MSG_TYPE_2 = 0x02
```

### 4.2 DeviceContext Integration

The `DeviceContext` class provides `get_effective_identity()` for merging CVE overrides:

```python
@dataclass
class DeviceContext:
    device_id: str
    mac_address: str
    ip_address: str
    port: int
    vendor_fingerprint: dict[str, Any] = field(default_factory=dict)
    vulnerability_override: dict[str, Any] | None = None

    def get_effective_identity(self, identity_type: str) -> dict[str, Any]:
        """Get effective protocol identity with vulnerability overrides applied.

        Args:
            identity_type: Identity type key (e.g., "s7_identity", "your_protocol_identity")

        Returns:
            Merged identity dict with vulnerability overrides applied
        """
        base_identity = dict(self.vendor_fingerprint.get(identity_type, {}))

        if self.vulnerability_override:
            override_key = f"{identity_type}_override"
            override = self.vulnerability_override.get(override_key) or \
                       self.vulnerability_override.get(identity_type)
            if override:
                base_identity.update(override)

        return base_identity
```

**Usage in packet builders:**
```python
def _build_your_protocol_response(self, device: DeviceContext) -> bytes:
    # Get merged identity with CVE overrides applied
    identity = device.get_effective_identity("your_protocol_identity")

    vendor_id = identity.get("vendor_id", 0)
    firmware_version = identity.get("firmware_version", "1.0")
    # ... build response packet with these values
```

### 4.3 Packet Builder Methods

Create packet builder methods for your protocol:

```python
def _build_your_protocol_request(self) -> bytes:
    """Build YourProtocol discovery request."""
    # Build packet bytes
    header = struct.pack(">HH", YOUR_PROTOCOL_MSG_REQUEST, 0)
    return header

def _build_your_protocol_response(self, device: DeviceContext) -> bytes:
    """Build YourProtocol discovery response with device identity.

    CRITICAL: Use get_effective_identity() to include CVE overrides.
    """
    # Get identity with CVE overrides merged
    identity = device.get_effective_identity("your_protocol_identity")

    vendor_id = identity.get("vendor_id", 0)
    product_code = identity.get("product_code", "Unknown")
    firmware_version = identity.get("firmware_version", "1.0")

    # Build response with identity fields
    header = struct.pack(">HHI", YOUR_PROTOCOL_MSG_RESPONSE, len(product_code), vendor_id)
    payload = product_code.encode("ascii") + firmware_version.encode("ascii")

    logger.info(
        f"YourProtocol response: vendor_id={vendor_id}, "
        f"product={product_code}, firmware={firmware_version}"
    )

    return header + payload
```

**Common pitfalls with `struct.pack`:**
- Format string specifiers must match argument count exactly
- Use `>` prefix for network byte order (big-endian)
- Common specifiers: `B` (1 byte), `H` (2 bytes), `I` (4 bytes), `s` (string bytes)

### 4.4 Discovery Sequence

**CRITICAL**: Discovery is what makes devices visible to Cyber Vision. Without discovery packets, devices remain invisible.

The `_generate_discovery_sequences()` method handles per-protocol discovery:

```python
def _generate_discovery_sequences(self, time_ms: float) -> float:
    """Generate protocol-specific discovery sequences for all flows."""
    current_time = time_ms

    # CRITICAL: Track devices per protocol (not globally!)
    # This ensures a device can be discovered via multiple protocols
    discovered_enip: set[str] = set()
    discovered_profinet: set[str] = set()
    discovered_s7comm: set[str] = set()
    discovered_modbus: set[str] = set()
    discovered_snmp: set[str] = set()
    discovered_bacnet: set[str] = set()
    # ADD YOUR PROTOCOL TRACKING SET:
    # discovered_your_protocol: set[str] = set()

    for flow_state in self.flows:
        flow = flow_state.flow
        protocol = flow.protocol
        dst = flow.destination
        src = flow.source

        # ADD YOUR PROTOCOL DISCOVERY LOGIC:
        if protocol == "your_protocol":
            your_identity = dst.vendor_fingerprint.get("your_protocol_identity")
            if your_identity and dst.device_id not in discovered_your_protocol:
                discovered_your_protocol.add(dst.device_id)

                # Build and schedule discovery request
                request = self._build_your_protocol_request()
                request_pkt = self._build_udp_packet(src, dst, request)
                self._schedule_event(current_time, ("packet", request_pkt))

                # Build and schedule discovery response (contains identity)
                response = self._build_your_protocol_response(dst)
                response_pkt = self._build_udp_packet(dst, src, response)
                self._schedule_event(current_time + 20, ("packet", response_pkt))

                current_time += 100
                logger.info(
                    f"Scheduled YourProtocol discovery for {dst.ip_address} "
                    f"(vendor={your_identity.get('vendor_id')}, "
                    f"firmware={your_identity.get('firmware_version')})"
                )

    return current_time
```

**Key Points:**
1. **Use per-protocol tracking sets** - A single global set blocks discovery when multiple protocols target the same device
2. **Log discovery scheduling** - Essential for debugging why devices don't appear
3. **Include identity fields in logs** - Verify the correct values are being used

### 4.5 Poll Cycle

The `_generate_poll_cycle()` method handles ongoing protocol traffic:

```python
def _generate_poll_cycle(self, flow_state: FlowState, time_ms: float) -> None:
    """Generate a single poll cycle for the given flow."""
    flow = flow_state.flow
    protocol = flow.protocol

    # ADD YOUR PROTOCOL POLL CYCLE:
    if protocol == "your_protocol":
        self._generate_your_protocol_poll(flow_state, time_ms)

def _generate_your_protocol_poll(self, flow_state: FlowState, time_ms: float) -> None:
    """Generate a YourProtocol request/response cycle."""
    flow = flow_state.flow
    src = flow.source
    dst = flow.destination

    # Build request
    request = self._build_your_protocol_read_request()
    request_pkt = self._build_tcp_packet(
        src, dst, request, flow_state.seq_number, flow_state.ack_number
    )
    self._schedule_event(time_ms, ("packet", request_pkt))
    flow_state.seq_number += len(request)

    # Build response
    response = self._build_your_protocol_read_response(dst)
    response_pkt = self._build_tcp_packet(
        dst, src, response, flow_state.ack_number, flow_state.seq_number
    )
    self._schedule_event(time_ms + 10, ("packet", response_pkt))
    flow_state.ack_number += len(response)
```

---

## 5. Step-by-Step Implementation Checklist

### Phase 1: Define Identity Fields

- [ ] **Research protocol identity mechanism** - How does this protocol expose device identity?
- [ ] **Identify key fields** - What fields does Cyber Vision parse for detection?
- [ ] **Document firmware field format** - How should firmware version be formatted?
- [ ] **Define protocol constants** - Ports, message types, magic numbers

### Phase 2: Backend Data Layer

- [ ] **Add database model column** - Add `your_protocol_identity` to `VendorFingerprint`
- [ ] **Add override column** - Add `your_protocol_identity_override` to `VulnerableFingerprintVariant`
- [ ] **Run database migration** - `alembic revision --autogenerate && alembic upgrade head`
- [ ] **Add vendor fingerprint data** - Add protocol identity block to vendor fingerprint files
- [ ] **Add CVE data** - Add vulnerable variants with `firmware_version` field

### Phase 3: Firmware Derivation

- [ ] **Add derivation method** - Add `derive_your_protocol()` to `FirmwareVersionDeriver`
- [ ] **Update derive_all()** - Include new protocol in `derive_all()` return dict
- [ ] **Test derivation** - Verify correct firmware format for your protocol

### Phase 4: Traffic Generator

- [ ] **Add protocol constants** - Define at top of `live_orchestrator.py`
- [ ] **Implement packet builders** - `_build_your_protocol_request()` and `_build_your_protocol_response()`
- [ ] **Use get_effective_identity()** - Ensure CVE overrides are applied in responses
- [ ] **Add per-protocol tracking set** - Add `discovered_your_protocol: set[str] = set()`
- [ ] **Implement discovery sequence** - Add `elif protocol == "your_protocol":` block
- [ ] **Implement poll cycle** - Add poll cycle logic if needed
- [ ] **Add logging** - Log discovery scheduling with identity fields

### Phase 5: Integration

- [ ] **Add to ProtocolType enum** - `backend/app/protocol_engines/types.py`
- [ ] **Register in __init__.py** - `backend/app/protocol_engines/__init__.py`
- [ ] **Update scenario templates** - Add protocol to template flows

### Phase 6: Verify Fingerprinting Outcome

- [ ] **Check database** - Verify fingerprints and CVEs loaded correctly
- [ ] **Check traffic generator logs** - Verify discovery is scheduled with correct identity
- [ ] **Capture traffic with Wireshark** - Verify identity fields in packets
- [ ] **Check Cyber Vision** - Verify device detection with full identity

---

## 6. Protocol Reference Examples

### S7comm (Siemens)

**Identity Mechanism:** SZL (System Status List) Read Response

**Key Files:**
- Constants: `live_orchestrator.py` lines 243-272
- Packet Builders: `_build_s7_szl_request()`, `_build_s7_szl_response()`
- Discovery: `_generate_discovery_sequences()` S7comm section

**Key Fields:**
- `order_code`: Siemens part number (e.g., "6ES7 516-3AN01-0AB0")
- `module_type`: Device type (e.g., "CPU 1516-3 PN/DP")
- `firmware_version`: V-prefixed version (e.g., "V2.8.0")

**Discovery Sequence:**
1. COTP Connection Request/Confirm
2. S7 Setup Communication Request/Response
3. S7 SZL Read Request (SZL_ID_MODULE_ID)
4. S7 SZL Read Response (contains firmware version)

### EtherNet/IP (Rockwell)

**Identity Mechanism:** ListIdentity Response (UDP broadcast)

**Key Fields:**
- `vendor_id`: ODVA vendor ID (e.g., 1 = Rockwell)
- `product_name`: Device name (e.g., "1756-L85E/A LOGIX5585")
- `revision_major`, `revision_minor`: Firmware version as integers

**Discovery Sequence:**
1. ListIdentity Request (UDP broadcast)
2. ListIdentity Response (contains all identity fields)

### PROFINET (Siemens)

**Identity Mechanism:** DCP Identify Response (Layer 2 multicast)

**Key Fields:**
- `vendor_id`: PROFINET vendor ID (e.g., 0x002A = Siemens)
- `device_id`: Product identifier
- `station_name`: Device network name
- `sw_release`: V-prefixed firmware version

**Discovery Sequence:**
1. DCP Identify Request (multicast)
2. DCP Identify Response (contains station name, vendor, firmware)

### Rockwell EtherNet/IP (Reference Implementation)

The Rockwell implementation is the most complete reference for fingerprinting. Key patterns:

**1. Multi-Protocol Identity Blocks:**
Rockwell fingerprints include BOTH `modbus_identity` AND `ethernet_ip_identity` because devices support multiple protocols:

```python
{
    "vendor": "Rockwell",
    "model": "1756-L85E",
    "modbus_identity": {
        "vendor_name": "Rockwell Automation/Allen-Bradley",
        "product_code": "1756-L85E/B",
        "major_minor_revision": "33.011",  # Firmware
    },
    "ethernet_ip_identity": {
        "vendor_id": 1,
        "device_type": 14,
        "product_code": 85,
        "revision_major": 33,  # Firmware major
        "revision_minor": 11,  # Firmware minor
        "product_name": "1756-L85E/B LOGIX5585E",
    },
}
```

**2. Extended CIP Identity Object:**
For deep fingerprinting beyond ListIdentity, include `cip_identity_object`:

```python
"cip_identity_object": {
    "status": 0x0030,  # Owned + Configured
    "configuration_consistency_value": 0xA5B6C7D8,
    "heartbeat_interval": 250,  # ms
    "protection_mode": 0,  # 0 = no protection (vulnerable)
    "maximum_cip_connections": 64,
}
```

**3. Explicit CVE Overrides (vs Auto-Derivation):**
Rockwell CVEs use EXPLICIT overrides for full control:

```python
"vulnerable_variants": [
    {
        "firmware_version": "32.011",
        "display_name": "ControlLogix L85E (CVE-2022-1159)",
        # EXPLICIT overrides - full control over every field
        "modbus_identity_override": {
            "major_minor_revision": "32.011",
            "product_name": "1756-L85E/B LOGIX5585",
        },
        "ethernet_ip_identity_override": {
            "revision_major": 32,
            "revision_minor": 11,
            "product_name": "1756-L85E/B LOGIX5585",
        },
        "cip_identity_override": {
            "protection_mode": 0,  # Vulnerable config
        },
    },
]
```

**When to use Explicit vs Auto-Derivation:**
- **Auto-derivation** (`firmware_version` only): When firmware format is standard and you just need version detection
- **Explicit overrides**: When CVE requires specific non-firmware fields (like `protection_mode`) or when firmware format is non-standard

**4. Both Source AND Target Discovery:**
The working EtherNet/IP implementation discovers BOTH devices in a flow:

```python
# EtherNet/IP: generate for BOTH source and target devices
for device in [dst, src]:  # <-- BOTH devices
    eip_identity = device.vendor_fingerprint.get("ethernet_ip_identity")
    if eip_identity and device.device_id not in discovered_enip:
        discovered_enip.add(device.device_id)
        # Generate discovery for this device...
```

This ensures all devices on the network are visible, not just targets.

**5. Additional Object Types:**
For full EtherNet/IP fingerprinting, Rockwell includes:

```python
# Connection Manager Object (Class 0x06)
"connection_manager_object": {
    "max_connections": 64,
    "connection_timeout_multiplier": 32,
    "supported_connection_types": ["implicit", "explicit", "unconnected_send"],
},
# Assembly Objects (Class 0x04)
"assembly_objects": {
    "input": {"instance": 100, "size_bytes": 500},
    "output": {"instance": 101, "size_bytes": 500},
},
# ListServices Response
"list_services_response": {
    "communications": {
        "type_code": 0x0100,
        "capability_flags": 0x0120,  # TCP + UDP
    },
},
```

**6. Safety Extensions (GuardLogix):**
For safety PLCs, include CIP Safety configuration:

```python
"protocol_quirks": {
    "cip_safety_enabled": True,
},
"safety_config": {
    "sil_level": "SIL3",
    "category": "Cat4",
    "safety_watchdog_ms": 50,
},
"cip_safety": {
    "safety_network_number": 1,
    "safety_signature": 0x1A2B3C4D5E6F,
    "tunid": (1, 1, 0, 0),
},
```

---

## 7. Verification & Troubleshooting

### Pre-Deployment Verification

**Check database:**
```sql
-- Verify fingerprints loaded
SELECT vendor, model, your_protocol_identity
FROM vendor_fingerprints
WHERE your_protocol_identity IS NOT NULL;

-- Verify CVEs loaded
SELECT cv.cve_id, vfv.firmware_version, vfv.your_protocol_identity_override
FROM vulnerable_fingerprint_variants vfv
JOIN cve_vulnerabilities cv ON vfv.cve_vulnerability_id = cv.id;
```

**Check scenario export:**
```bash
# Verify fingerprint included in scenario JSON
curl http://localhost:8001/api/v1/scenarios/{id} | jq '.definition.devices[].vendorFingerprint.your_protocol_identity'
```

### Traffic Generator Verification

**Check logs for discovery scheduling:**
```
Scheduled YourProtocol discovery for 10.1.0.10 (vendor=42, firmware=V3.10)
```

If discovery is NOT scheduled, check:
1. Is `your_protocol_identity` present in vendor fingerprint?
2. Is device already in the per-protocol tracking set?
3. Is the protocol check correct in `_generate_discovery_sequences()`?

**Check logs for identity fields:**
```
YourProtocol response: vendor_id=42, product=DeviceModel, firmware=V3.10
```

If identity fields are wrong or missing, check:
1. Is `get_effective_identity()` being called?
2. Are CVE overrides being applied?
3. Is `FirmwareVersionDeriver` including your protocol?

### Wireshark Verification

Capture traffic and verify protocol-specific identity fields are populated:
- Filter by protocol
- Inspect identity response packets
- Verify firmware version field matches expected vulnerable version

### Cyber Vision Verification

**Ultimate Success Criteria:**
1. Device appears in inventory
2. Vendor name correctly identified
3. Model name correctly identified
4. Firmware version correctly parsed
5. CVE vulnerabilities flagged when present
6. Protocol activities visible

### Common Fingerprinting Failures

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Device not visible | Discovery not scheduled | Check per-protocol tracking set, add logging |
| Vendor/model wrong | Base fingerprint missing | Add vendor fingerprint data |
| Firmware version wrong | CVE override not applied | Use `get_effective_identity()` |
| CVE not detected | Firmware format incorrect | Check `FirmwareVersionDeriver` |
| Multiple protocols fail | Global tracking set | Use per-protocol tracking sets |

### Lessons Learned: S7comm Implementation

During the S7comm implementation, several issues were discovered that apply to any new protocol:

**1. struct.pack Format/Argument Mismatch:**
```python
# WRONG - format has 6 specifiers but only 5 arguments
struct.pack(">BBHHHH", func, reserved, max_amq_caller, max_amq_callee, pdu_length)

# CORRECT - format and argument count must match
struct.pack(">BBHHH", func, reserved, max_amq_calling, max_amq_called, pdu_length)
```

**2. Per-Protocol Discovery Tracking:**
```python
# WRONG - single global set blocks multi-protocol discovery
discovered_devices: set[str] = set()  # ALL protocols share this

# CORRECT - separate sets per protocol
discovered_enip: set[str] = set()
discovered_profinet: set[str] = set()
discovered_s7comm: set[str] = set()
```

Without per-protocol sets, if PROFINET discovers device X first, S7comm won't discover it.

**3. Discovery Logging is Critical:**
Always log when discovery is scheduled:
```python
logger.info(
    f"Scheduled S7comm SZL discovery for {dst.ip_address} "
    f"(order_code={s7_identity.get('order_code')}, "
    f"firmware={s7_identity.get('firmware_version')})"
)
```

If you don't see this log, discovery isn't happening.

**4. TCP vs UDP Packet Building:**
- S7comm uses TCP (port 102) with TPKT/COTP layers
- EtherNet/IP ListIdentity uses UDP (port 44818)
- PROFINET DCP uses Layer 2 (Ethernet frames, no IP)

Choose the correct packet builder:
```python
# TCP-based protocols
self._build_tcp_packet(src, dst, payload, seq, ack)

# UDP-based protocols
self._build_udp_packet(src, dst, payload)

# Layer 2 protocols
self._build_profinet_frame(src_mac, dst_mac, payload)
```

### Debugging Commands

```bash
# Check traffic generator logs
docker logs -f packetarch-generator-{deployment_id}

# Check if discovery is being scheduled
docker logs packetarch-generator-{id} 2>&1 | grep "Scheduled.*discovery"

# Check identity fields in packets
docker logs packetarch-generator-{id} 2>&1 | grep "response:"
```

---

## Protocols Without CVE Identity Detection

The following protocols do **NOT** support passive CVE detection because they lack
firmware version exposure in their discovery mechanisms:

| Protocol | Reason | Traffic Generation |
|----------|--------|-------------------|
| OPC UA | Session-based discovery, no passive fingerprinting | Works |
| DNP3 | No firmware version in protocol responses | Works |
| IEC 104 | No firmware version in protocol responses | Works |

These protocols still generate realistic OT traffic but cannot expose vulnerable
firmware versions for CVE detection by passive scanners like Cisco Cyber Vision.

### Why These Protocols Differ

**OPC UA:** Uses a session-based discovery model where identity is obtained via
`GetEndpoints` after establishing a TCP connection. The identity is within an
encrypted session, not visible to passive network monitors.

**DNP3:** A SCADA polling protocol designed for telemetry, not device identity.
While there are Data Link Layer frames, they contain addresses and data, not
firmware versions or model information.

**IEC 104:** Similar to DNP3, focused on real-time data transmission for power
grid SCADA. No passive identity mechanism exists in the protocol specification.

### Implications for New Protocol Development

When evaluating whether to implement CVE detection for a new protocol, consider:

1. **Does the protocol have a broadcast/multicast discovery mechanism?**
   - EtherNet/IP ListIdentity (UDP broadcast)
   - PROFINET DCP (Layer 2 multicast)
   - BACnet Who-Is (UDP broadcast)

2. **Does the discovery response include firmware/version information?**
   - Modbus FC 43 includes vendor name, product code, revision
   - PROFINET DCP includes device type, SW release
   - S7comm SZL includes order code, firmware version

3. **Can passive scanners extract this information?**
   - Cyber Vision parses specific protocol fields
   - Wireshark dissectors show the fields

If any answer is "no", CVE identity detection is not feasible for that protocol.

---

## SNMP Universal Discovery

SNMP discovery is applied to **ALL devices** regardless of their primary protocol.
This maximizes Cisco Cyber Vision detection because `sysDescr` parsing is a primary
method for device fingerprinting.

### How It Works

In `live_orchestrator.py`, SNMP discovery is scheduled for every device:

```python
# Every device gets SNMP discovery, not just SNMP-primary devices
for device in scenario_devices:
    if device.ip_address not in discovered_snmp:
        schedule_snmp_discovery(device)
```

### Why Universal SNMP Matters

1. **Cyber Vision Priority:** SNMP is often the first discovery method Cyber Vision
   uses to identify devices on the network.

2. **Cross-Protocol Coverage:** A Siemens PLC might be discovered via SNMP before
   S7comm SZL discovery completes.

3. **Fallback Identity:** If protocol-specific discovery fails, SNMP provides a
   fallback fingerprint.

### SNMP sys_descr_template

The `snmp_sys_descr_template` field allows CVE-specific sysDescr formatting:

```python
"snmp_sys_descr_template": "Siemens SIMATIC S7-1500 CPU {firmware_version}"
```

This generates: `"Siemens SIMATIC S7-1500 CPU V2.8.0"` when the vulnerable
firmware version is applied.

---

## Summary

Adding a new protocol requires changes across multiple layers:

| Layer | Files | Key Changes |
|-------|-------|-------------|
| **Database Models** | `models/vendor_fingerprint.py`, `models/vulnerable_fingerprint.py` | Add JSONB columns |
| **Fingerprint Data** | `services/vendor_fingerprints/*.py` | Add protocol identity block |
| **CVE Data** | `services/cve_data/*.py` | Add vulnerable variants with `firmware_version` |
| **Firmware Deriver** | `protocol_engines/firmware_version_deriver.py` | Add `derive_your_protocol()` |
| **Traffic Generator** | `live_orchestrator.py` | Constants, packet builders, discovery, polling |

**Key Success Factors:**
1. Discovery packets must be generated to make devices visible
2. Use `get_effective_identity()` to merge CVE overrides
3. Use per-protocol tracking sets to allow multi-protocol discovery
4. Log discovery scheduling for debugging
5. Verify end-to-end in Cyber Vision
