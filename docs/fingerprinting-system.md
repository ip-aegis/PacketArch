# PacketArch Fingerprinting System - Comprehensive Documentation

## Overview

This document provides deep documentation of the fingerprinting process in PacketArch, covering the complete flow from scenario/template creation through traffic generation on remote agents.

---

## Table of Contents

1. [Fingerprinting Architecture](#1-fingerprinting-architecture)
2. [Data Models](#2-data-models)
3. [Unique vs Shared Elements](#3-unique-vs-shared-elements)
4. [Complete Data Flow](#4-complete-data-flow)
5. [Key Services & Components](#5-key-services--components)
6. [Protocol Identity System](#6-protocol-identity-system)
7. [Ambiguous/Duplicative/Unused Code](#7-ambiguousduplicativeunused-code)
8. [File Reference Map](#8-file-reference-map)

---

## 1. Fingerprinting Architecture

### 1.1 Purpose

Fingerprinting enables **hyper-realistic OT traffic generation** by providing:
- Protocol-specific device identity responses (Modbus FC 43, EtherNet/IP ListIdentity, etc.)
- TCP/IP stack characteristics (TTL, window size, MSS)
- Response timing distributions
- Vendor-specific error behaviors
- MAC address OUI patterns

### 1.2 Three-Source Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DeviceTemplate (Unified)                  │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │  VENDOR_BUILTIN  │  │   PCAP_LEARNED   │  │ USER_CREATED│ │
│  │  (from Python    │  │ (from PCAP       │  │ (custom     │ │
│  │   library)       │  │  analysis)       │  │  templates) │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Three-Layer Enrichment (at deployment time)

```
Layer 1: Base Fingerprint
├── Vendor/model identification
├── Protocol identities (vendor-specific)
├── TCP stack characteristics
└── Response timing model

Layer 2: CVE Vulnerability Overrides (optional)
├── Firmware version override
├── Protocol-specific field overrides
└── Preserves device-specific fields

Layer 3: Instance-Specific Identifiers (ALWAYS APPLIED)
├── Unique serial numbers (per protocol)
├── Unique network identifiers (station_name, sys_name, etc.)
└── Deterministic from (device_id + scenario_id)
```

---

## 2. Data Models

### 2.1 DeviceTemplate (AUTHORITATIVE - Current)

**File:** `backend/app/models/device_template.py`

The unified model consolidating all fingerprint sources:

| Category | Fields | Purpose |
|----------|--------|---------|
| **Source** | `source` (enum), `source_pcap_id` | Provenance tracking |
| **Identity** | `vendor`, `vendor_family`, `model`, `firmware_version`, `device_type` | Device identification |
| **Network** | `oui_patterns`, `tcp_signature` (JSONB) | Network-level fingerprinting |
| **Protocol (Unified)** | `protocol_identities` (JSONB) | Modern: `{modbus: {...}, s7: {...}}` |
| **Protocol (Legacy)** | `modbus_identity`, `ethernet_ip_identity`, `profinet_identity`, `s7_identity`, `snmp_identity`, `bacnet_identity`, `opc_ua_identity` | Per-protocol columns (backward compat) |
| **Timing** | `response_timings` (JSONB), `protocol_quirks`, `error_behavior` | Behavioral characteristics |
| **Behavioral** | `role`, `active_protocols`, `typical_ports` | Device behavior patterns |
| **Quality** | `confidence`, `sample_count`, `consistency_score` | Learning metrics |

**Key Methods:**
- `get_protocol_identity(protocol)` - Returns identity (checks unified then legacy)
- `get_timing_for_protocol(protocol)` - Returns timing distribution
- `from_vendor_fingerprint()` - Migration helper
- `from_learned_fingerprint()` - Migration helper

### 2.2 VendorFingerprint (DEPRECATED)

**File:** `backend/app/models/vendor_fingerprint.py`

**Status:** DEPRECATED - Data migrated to DeviceTemplate

Original model for built-in vendor fingerprints. Retained for rollback capability.

### 2.3 LearnedDeviceFingerprint (DEPRECATED BUT STILL QUERIED)

**File:** `backend/app/models/learned_device_fingerprint.py`

**Status:** DEPRECATED - Data migrated to DeviceTemplate, BUT still actively queried

Original model for PCAP-learned fingerprints. Retained for rollback capability.

**WARNING - Incomplete Migration:** The learning API routes (`/api/v1/learning/*`) still directly query `LearnedDeviceFingerprint` instead of using `DeviceTemplate` with `source=PCAP_LEARNED`. This creates parallel code paths that should be consolidated.

### 2.4 VulnerableFingerprintVariant (SPECIALIZED)

**File:** `backend/app/models/vulnerable_fingerprint.py`

Links CVE vulnerabilities to protocol identity overrides:
- `cve_vulnerability_id` - CVE foreign key
- `*_identity_override` columns for each protocol
- `firmware_version` for version-specific CVE simulation

### 2.5 Model Relationship Diagram

```
DeviceTemplate (unified)
  ├── source: 'vendor_builtin' <── migrated from VendorFingerprint
  ├── source: 'pcap_learned' <── migrated from LearnedDeviceFingerprint
  └── source: 'user_created' <── new user templates

VulnerableFingerprintVariant
  ├── base_fingerprint_id -> VendorFingerprint (DEPRECATED, should use DeviceTemplate)
  └── cve_vulnerability_id -> CVEVulnerability

PcapCapture
  └── learning_session_id -> LearningSession
      └── device_fingerprints -> LearnedDeviceFingerprint (DEPRECATED)
```

---

## 3. Unique vs Shared Elements

### 3.1 UNIQUE Per Device (Instance-Specific)

These MUST be different for each device in a scenario to prevent device merging in Cisco Cyber Vision:

| Element | Protocol | Format | Generation |
|---------|----------|--------|------------|
| **Serial Number** | EtherNet/IP | 32-bit uint | `SerialNumberGenerator` |
| **Serial Number** | S7comm | 12-char string ("S V-XXXXXXXX") | `SerialNumberGenerator` |
| **Serial Number** | PROFINET | 16-char hex (IM0 serial) | `SerialNumberGenerator` |
| **Device Instance** | BACnet | 1-4194302 | `UniqueIdentifierGenerator` |
| **Object Name** | BACnet | "{BASE}-{4HEX}" | `UniqueIdentifierGenerator` |
| **Station Name** | PROFINET | lowercase-hyphen | `UniqueIdentifierGenerator` |
| **sys_name** | SNMP | "{UPPERCASE}-{4HEX}" | `UniqueIdentifierGenerator` |
| **PLC Name** | S7comm | "{UPPERCASE}-{4HEX}" | `UniqueIdentifierGenerator` |
| **Product Name** | EtherNet/IP | "MODEL DEVICE_NAME" | `UniqueIdentifierGenerator` |
| **Product Name** | Modbus | From FC 43 MEI | `UniqueIdentifierGenerator` |
| **MAC Address** | All | Vendor OUI + random suffix | `generate_mac()` |

**Generation Method:** Deterministic hash of `(device_id + scenario_id)` ensures reproducibility.

### 3.2 SHARED Across Devices (Fingerprint-Specific)

These CAN be identical for devices with the same fingerprint:

| Element | Protocol(s) | Purpose |
|---------|-------------|---------|
| **vendor_id** | EtherNet/IP, PROFINET, BACnet | Vendor identification |
| **device_type** | EtherNet/IP | Device category code |
| **product_code** | EtherNet/IP, Modbus | Product model code |
| **revision_major/minor** | EtherNet/IP | Firmware version |
| **sw_release** | PROFINET | Software version string |
| **firmware_version** | S7comm, BACnet | Firmware string |
| **order_code** | S7comm | Siemens order number |
| **module_type** | S7comm | Module category |
| **sys_object_id** | SNMP | SNMP OID |
| **sys_descr** | SNMP | System description |
| **sys_location/contact** | SNMP | Location/contact info |
| **vendor_name** | BACnet, Modbus | Vendor string |
| **model_name** | BACnet | Model string |
| **TTL, window_size, MSS** | TCP/IP stack | Network characteristics |
| **Response timing distribution** | All | Delay parameters |
| **Error behavior** | All | Exception/timeout rates |

---

## 4. Complete Data Flow

### 4.1 Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  1. SCENARIO TEMPLATE DEFINITION                            │
│  Location: backend/app/scenario_templates/*.py              │
│                                                             │
│  Device specs include fingerprint_model:                    │
│  {"type": "plc", "vendor": "siemens",                      │
│   "fingerprint_model": "6ES7 516-3AN02", ...}              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. SCENARIO CREATION (API)                                 │
│  Location: backend/app/api/routes/templates.py              │
│            create_scenario_from_template()                  │
│                                                             │
│  Steps:                                                     │
│  a) Look up fingerprint: get_fingerprint_by_vendor_model()  │
│  b) Assign to device: device["vendorFingerprint"] = {...}   │
│  c) Enrich with serials: _enrich_device_with_serial_numbers()
│  d) Enrich with IDs: _enrich_device_with_unique_identifiers()
│  e) Optional AI naming: device_namer.name_devices()         │
│  f) Apply learned patterns: enhance_scenario_from_learned() │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. SCENARIO PERSISTENCE (DB)                               │
│  Location: backend/app/api/routes/scenarios.py              │
│                                                             │
│  Scenario.definition stores:                                │
│  - devices[].vendorFingerprint (full fingerprint)           │
│  - devices[].protocols[] (enabled protocols)                │
│  - flows[], zones[], phases[]                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. DEPLOYMENT ENRICHMENT                                   │
│  Location: backend/app/services/scenario_enricher.py        │
│            ScenarioDefinitionEnricher.enrich_for_deployment()
│                                                             │
│  Three-layer enrichment:                                    │
│  Layer 1: Base fingerprint (from DB)                        │
│  Layer 2: CVE overrides (if applicable)                     │
│  Layer 3: Unique serials/identifiers (ALWAYS)               │
│                                                             │
│  Critical: Only enriches EXISTING protocol identities       │
│  (prevents creating wrong vendor identities)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. AGENT DEPLOYMENT (WebSocket)                            │
│  Location: backend/app/api/websocket/agent_hub.py           │
│                                                             │
│  START_SCENARIO command includes:                           │
│  - Enriched scenario definition                             │
│  - All fingerprints with unique serials/identifiers         │
│  - Timing models, phases, flow configs                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  6. TRAFFIC GENERATION (Agent)                              │
│  Location: docker/packetarch-agent/app/                     │
│            live_orchestrator.py                             │
│                                                             │
│  Uses fingerprints for:                                     │
│  - Protocol identity responses (Modbus FC 43, etc.)         │
│  - TCP/IP stack characteristics                             │
│  - Response timing (sampled from distribution)              │
│  - Error injection rates                                    │
│                                                             │
│  Agent uses fingerprints AS-IS (no modification)            │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Critical Integration Points

| Step | File | Function | Purpose |
|------|------|----------|---------|
| Template Definition | `scenario_templates/*.py` | N/A | Define `fingerprint_model` per device |
| Fingerprint Lookup | `services/device_templates.py` | `get_fingerprint_by_vendor_model()` | Load full fingerprint |
| Serial Generation | `services/serial_number_generator.py` | `SerialNumberGenerator.generate()` | Unique serials |
| Unique ID Generation | `services/unique_identifier_generator.py` | `UniqueIdentifierGenerator.*()` | Unique network names |
| Deployment Enrichment | `services/scenario_enricher.py` | `enrich_for_deployment()` | Three-layer composition |
| DeviceContext | `protocol_engines/types.py` | `DeviceContext` | Carries fingerprint to engines |
| Fingerprint Application | `protocol_engines/fingerprint_applicator.py` | `FingerprintApplicator` | Applies to packets |
| Protocol Engines | `protocol_engines/*/engine.py` | Various | Use fingerprints for responses |

---

## 5. Key Services & Components

### 5.1 FingerprintCache

**File:** `backend/app/services/fingerprint_cache.py`

O(1) fingerprint lookups with thread-safe caching:
- Singleton pattern with lazy initialization
- Indexes by `(vendor, model)`, by `vendor`, and by alternate model names
- Loads from DeviceTemplate DB, falls back to Python library
- Vendor name normalization ("Johnson Controls" -> "johnson_controls")

### 5.2 FingerprintApplicator

**File:** `backend/app/protocol_engines/fingerprint_applicator.py`

Central integration point for fingerprint application:
- Extracts protocol-specific identities from fingerprint dict
- Applies CVE vulnerability overrides (respecting preserved fields)
- Generates unique serial numbers via `SerialNumberGenerator`
- Generates unique identifiers via `UniqueIdentifierGenerator`
- Provides methods for TCP options, response delays, identity responses

**Preserved Fields (not overwritten by CVE):**
- `serial_number`, `product_name`, `object_name`, `station_name`, `sys_name`, `plc_name`

### 5.3 SerialNumberGenerator

**File:** `backend/app/services/serial_number_generator.py`

Generates deterministic, unique serial numbers:

| Protocol | Format | Example |
|----------|--------|---------|
| EtherNet/IP | 32-bit uint | 2847593612 |
| S7comm | 12-char string | "S V-P12AB34CD" |
| PROFINET | 16-char hex | "12AB34CD56EF7890" |

**Method:** `hashlib.sha256(f"{device_id}:{scenario_id}".encode())`

### 5.4 UniqueIdentifierGenerator

**File:** `backend/app/services/unique_identifier_generator.py`

Generates deterministic, network-unique identifiers:

| Protocol | Identifier | Format |
|----------|------------|--------|
| BACnet | device_instance | 1-4194302 |
| BACnet | object_name | "{BASE}-{4HEX}" |
| PROFINET | station_name | lowercase-hyphen (max 240 chars) |
| SNMP | sys_name | "{UPPERCASE}-{4HEX}" |
| S7 | plc_name | "{UPPERCASE}-{4HEX}" (max ~24 chars) |
| EtherNet/IP | product_name | "MODEL DEVICE_NAME" (max 32 chars) |

**Fallback Chain:** device_name -> model -> vendor_family -> vendor -> "device"

### 5.5 Learned Pattern Service (SEPARATE SYSTEM)

**File:** `backend/app/services/learned_pattern_service.py`

**Important:** This is a **separate system** for PCAP-derived analysis, NOT an alternative fingerprint access path.

- Queries database tables: `LearnedDeviceFingerprint`, `LearnedProtocolPattern`, `LearnedSequence`
- Returns confidence scores and observation counts
- Provides statistical aggregation across learned samples
- Use ONLY for analyzing learned patterns, not for accessing vendor fingerprints

**Canonical Access for Vendor Fingerprints:**
```python
# CORRECT - Use device_templates for fingerprint access
from app.services.device_templates import get_fingerprint_by_vendor_model
fp = get_fingerprint_by_vendor_model("Siemens", "6ES7 516-3AN02-0AB0")

# WRONG - learned_pattern_service is for PCAP analysis only
from app.services.learned_pattern_service import ...  # Don't use for vendor fingerprints
```

### 5.6 Vendor Fingerprint Libraries

**Location:** `backend/app/services/vendor_fingerprints/`

Pre-built fingerprints organized by vendor:

| File | Coverage |
|------|----------|
| `rockwell.py` (85KB) | Allen-Bradley ControlLogix/CompactLogix |
| `siemens.py` (38KB) | S7-1200, S7-1500, PROFINET devices |
| `schneider.py` (39KB) | Modicon, Lexium, PowerLogic |
| `specialty.py` (85KB) | Niche vendors |
| `ge.py` (11KB) | GE Automation |
| `building_automation.py` (38KB) | Johnson Controls, Delta, Distech |
| `energy.py` (24KB) | Substation RTUs, protective relays |
| `transportation.py` (42KB) | ITS traffic controllers |
| `microsoft.py` (13KB) | Windows/cloud services |

---

## 6. Protocol Identity System

### 6.1 Identity Builder Architecture

**Location:** `backend/app/protocol_engines/identity/`

Registry pattern with protocol-specific builders:

```
ProtocolIdentityBuilder (base.py)
    ├── ModbusIdentityBuilder
    ├── EtherNetIPIdentityBuilder
    ├── ProfinetIdentityBuilder
    ├── S7IdentityBuilder
    ├── SNMPIdentityBuilder
    ├── BACnetIdentityBuilder
    └── OPCUAIdentityBuilder (future)
```

**Base Class Methods:**
- `build_identity_response()` - Builds complete identity with overrides
- `derive_firmware_fields()` - Protocol-specific firmware derivation
- `build_raw_response()` - Binary protocol bytes (optional)

### 6.2 Firmware Derivation Per Protocol

| Protocol | Input | Output |
|----------|-------|--------|
| Modbus | "3.10" | `major_minor_revision: "3.10"` |
| EtherNet/IP | "3.10" | `revision_major: 3, revision_minor: 10` |
| PROFINET | "3.10" | `sw_release: "V3.10"` |
| S7comm | "3.0.0" | `firmware_version: "V3.0.0"` |
| SNMP | "2.1.4" | Embedded in `sys_descr` |
| BACnet | "12.0.3" | `firmware_revision: "12.0.3"` |

### 6.3 MAC Address Generation

**File:** `backend/app/protocol_engines/identity/__init__.py`

```python
generate_mac(vendor, device_type, oui_patterns) -> "XX:XX:XX:XX:XX:XX"
generate_mac_from_fingerprint(fingerprint, fallback_vendor) -> "XX:XX:XX:XX:XX:XX"
```

**OUI Database:** `backend/app/protocol_engines/vendor_oui.py`

Contains IEEE-registered OUI prefixes for major OT vendors.

---

## 7. Ambiguous/Duplicative/Unused Code

### 7.1 DEPRECATED Models (Keep for Rollback)

| Model | File | Status | Active Queries? |
|-------|------|--------|-----------------|
| `VendorFingerprint` | `models/vendor_fingerprint.py` | DEPRECATED | No (seed_data.py only) |
| `LearnedDeviceFingerprint` | `models/learned_device_fingerprint.py` | DEPRECATED | **YES** - learning routes still query directly |

**Migration:** `alembic/versions/20260122_consolidate_fingerprints.py`

**Issue:** LearnedDeviceFingerprint migration is incomplete. The following files still query it directly:
- `backend/app/api/routes/learning.py` - List/get learned fingerprints
- `backend/app/api/routes/scenarios.py` - Apply fingerprints to devices
- `backend/app/mcp_server/tools/learning_tools.py` - MCP tool access
- `backend/app/services/learned_pattern_service.py` - Pattern queries

**Impact:** Two parallel query paths for learned data - one via deprecated model, one via DeviceTemplate. Changes must be made in both places.

### 7.2 Dual Protocol Identity Storage

DeviceTemplate has BOTH:
- `protocol_identities` (JSONB) - Modern unified format
- Individual columns (`modbus_identity`, `s7_identity`, etc.) - Legacy format

**Issue:** `get_protocol_identity()` checks both, creating ambiguity about authoritative source.

**Recommendation:** Document that `protocol_identities` is preferred; legacy columns for backward compatibility only.

### 7.3 Multiple Enrichment Points

Serial numbers and unique identifiers are enriched at multiple points:

1. `templates.py:_enrich_device_with_serial_numbers()` - During template creation (PRIMARY)
2. `templates.py:_enrich_device_with_unique_identifiers()` - During template creation (PRIMARY)
3. `scenarios.py:ensure_device_serial_numbers()` - During scenario updates
4. `scenario_enricher.py:enrich_for_deployment()` - During deployment (FALLBACK)

**Potential Issue:** Same device could be enriched multiple times if flow isn't carefully controlled.

**Observation:** The code has guards (only enriches existing protocol identities), but the multi-point enrichment adds complexity.

**Design Principle:** Scenario creation time should be the **authoritative enrichment point** because:
- **Reproducibility**: Same scenario deployed multiple times gets identical identifiers
- **Transparency**: Users can inspect identifiers in scenario definition before deployment
- **Debuggability**: Earlier source of truth makes tracing issues straightforward
- **Self-contained**: Scenario DB record is complete with no hidden transformations

**Recommendation:** Keep scenario creation as the primary enrichment point. Deployment-time enrichment should serve as a **validation/fallback layer** that:
- Verifies required identifiers exist
- Only fills gaps for legacy scenarios created before enrichment code existed
- Logs warnings if it has to fill gaps (indicating upstream issue that should be investigated)

### 7.4 Enrichment Gaps Between Code Paths

**Critical Finding:** Different scenario creation and deployment paths have different enrichment coverage:

| Enrichment Type | Template Creation | Manual Scenario | Docker Deployment | Agent Deployment |
|-----------------|-------------------|-----------------|-------------------|------------------|
| **Serial Numbers** | YES | YES (guardrail) | YES (re-gen if missing) | YES (guardrail) |
| **Unique Identifiers** | YES (after AI naming) | **NO** | YES | **NO** |
| **CVE Overrides** | YES (stored) | YES (stored) | YES (merged) | **NO** |
| **AI Naming** | YES (optional) | **NO** | N/A | N/A |

**Gaps to Address:**
1. **Manual scenarios miss unique identifiers** - `create_scenario()` only calls `ensure_device_serial_numbers()`, not unique identifier enrichment
2. **Agent deployments miss unique identifiers** - `validate_and_enrich_serial_numbers()` only generates serials
3. **Agent deployments miss CVE overrides** - CVE merging only happens in `ScenarioDefinitionEnricher` for Docker deployments

**Risk:** Agent-deployed scenarios may have protocol identifier conflicts (duplicate PROFINET station_name, SNMP sys_name, etc.) and won't simulate vulnerable firmware versions.

### 7.5 VulnerableFingerprintVariant.base_fingerprint_id

**Issue:** References `VendorFingerprint` (deprecated model) instead of `DeviceTemplate`.

**Location:** `models/vulnerable_fingerprint.py`

**Recommendation:** Update foreign key to reference DeviceTemplate.

### 7.6 Inconsistent Fingerprint Access Patterns

Code accesses fingerprints via multiple paths:
1. `FingerprintCache.get_by_vendor_model()` - Cached lookup
2. `device_templates.get_fingerprint_by_vendor_model()` - Service function
3. Direct DB query on `DeviceTemplate`
4. Python library functions in `vendor_fingerprints/`

**Recommendation:** Consolidate to use `FingerprintCache` as single source of truth.

### 7.7 Timing Model Inconsistencies

Two timing model systems exist:
1. `response_timing` (single dict) in `VendorFingerprint`
2. `response_timings` (JSONB, per-protocol) in `DeviceTemplate`

**Files:**
- `protocol_engines/timing/` - Timing model system
- Fingerprint models with different timing field structures

### 7.8 Learned Pattern Service Protocol Aliases

**File:** `services/learned_pattern_service.py`

Has protocol alias mapping but may not align with identity builder protocol names:
- Service: `s7` -> `[s7comm, s7]`
- Builder: `protocol_name = "s7"`

### 7.9 Device Template Service Duplication

Two overlapping services:
1. `services/device_templates.py` - Template library with firmware variants
2. `services/fingerprint_cache.py` - Cached fingerprint lookups

Both load fingerprints but with different features (firmware variants vs caching).

---

## 8. File Reference Map

### 8.1 Models
| Purpose | File |
|---------|------|
| Unified template | `backend/app/models/device_template.py` |
| Vendor fingerprint (deprecated) | `backend/app/models/vendor_fingerprint.py` |
| Learned fingerprint (deprecated) | `backend/app/models/learned_device_fingerprint.py` |
| CVE variants | `backend/app/models/vulnerable_fingerprint.py` |
| PCAP capture | `backend/app/models/pcap_capture.py` |
| Learning session | `backend/app/models/learning_session.py` |
| Learned patterns | `backend/app/models/learned_pattern.py` |

### 8.2 Services
| Purpose | File |
|---------|------|
| Fingerprint cache | `backend/app/services/fingerprint_cache.py` |
| Device templates | `backend/app/services/device_templates.py` |
| Learned patterns | `backend/app/services/learned_pattern_service.py` |
| Serial generation | `backend/app/services/serial_number_generator.py` |
| Unique ID generation | `backend/app/services/unique_identifier_generator.py` |
| Scenario enrichment | `backend/app/services/scenario_enricher.py` |
| Vendor fingerprint data | `backend/app/services/vendor_fingerprint_data.py` |

### 8.3 Vendor Fingerprint Libraries
| Purpose | File |
|---------|------|
| Rockwell | `backend/app/services/vendor_fingerprints/rockwell.py` |
| Siemens | `backend/app/services/vendor_fingerprints/siemens.py` |
| Schneider | `backend/app/services/vendor_fingerprints/schneider.py` |
| Specialty vendors | `backend/app/services/vendor_fingerprints/specialty.py` |
| Building automation | `backend/app/services/vendor_fingerprints/building_automation.py` |
| Energy | `backend/app/services/vendor_fingerprints/energy.py` |
| Transportation | `backend/app/services/vendor_fingerprints/transportation.py` |

### 8.4 Protocol Identity System
| Purpose | File |
|---------|------|
| Identity registry | `backend/app/protocol_engines/identity/__init__.py` |
| Base builder | `backend/app/protocol_engines/identity/base.py` |
| Modbus builder | `backend/app/protocol_engines/identity/modbus_builder.py` |
| EtherNet/IP builder | `backend/app/protocol_engines/identity/ethernet_ip_builder.py` |
| PROFINET builder | `backend/app/protocol_engines/identity/profinet_builder.py` |
| S7 builder | `backend/app/protocol_engines/identity/s7_builder.py` |
| SNMP builder | `backend/app/protocol_engines/identity/snmp_builder.py` |
| BACnet builder | `backend/app/protocol_engines/identity/bacnet_builder.py` |
| OPC UA builder | `backend/app/protocol_engines/identity/opc_ua_builder.py` |

### 8.5 Core Integration
| Purpose | File |
|---------|------|
| Fingerprint applicator | `backend/app/protocol_engines/fingerprint_applicator.py` |
| Device context | `backend/app/protocol_engines/types.py` |
| Vendor OUI | `backend/app/protocol_engines/vendor_oui.py` |

### 8.6 API Routes
| Purpose | File |
|---------|------|
| Fingerprints API | `backend/app/api/routes/fingerprints.py` |
| Templates API | `backend/app/api/routes/templates.py` |
| Scenarios API | `backend/app/api/routes/scenarios.py` |
| Deployments API | `backend/app/api/routes/deployments.py` |
| Learning API | `backend/app/api/routes/learning.py` |

### 8.7 Scenario Templates
| Purpose | File |
|---------|------|
| Base types | `backend/app/scenario_templates/base.py` |
| Manufacturing | `backend/app/scenario_templates/manufacturing.py` |
| Water | `backend/app/scenario_templates/water.py` |
| Energy | `backend/app/scenario_templates/energy.py` |
| Oil & Gas | `backend/app/scenario_templates/oil_gas.py` |
| Building automation | `backend/app/scenario_templates/building_automation.py` |
| Transportation | `backend/app/scenario_templates/transportation.py` |

### 8.8 Traffic Generation
| Purpose | File |
|---------|------|
| Flow generator | `backend/app/traffic_generator/flow_generator.py` |
| Tasks (Celery) | `backend/app/traffic_generator/tasks.py` |
| Agent orchestrator | `docker/packetarch-agent/app/live_orchestrator.py` |
| Agent pool | `docker/packetarch-agent/app/orchestrator_pool.py` |

### 8.9 AI Services
| Purpose | File |
|---------|------|
| Scenario generator | `backend/app/ai_services/scenario_generator.py` |
| AI scenario designer | `backend/app/ai_services/ai_scenario_designer.py` |
| Device namer | `backend/app/ai_services/device_namer.py` |
| Base extractor | `backend/app/ai_services/extractors/base.py` |
| Fingerprint extractor | `backend/app/ai_services/extractors/fingerprint_extractor.py` |

### 8.10 Database Migrations
| Purpose | File |
|---------|------|
| Consolidate fingerprints | `backend/alembic/versions/20260122_consolidate_fingerprints.py` |
| Refactor fingerprints | `backend/alembic/versions/20260122_refactor_fingerprints_to_templates.py` |

---

## Summary of Findings

### Strengths
1. Well-designed three-source architecture (vendor, learned, user)
2. Clear separation of unique vs shared elements
3. Deterministic generation ensures reproducibility across deployments
4. Protocol-specific identity builders provide extensibility
5. Multi-layer enrichment architecture supports CVE simulation
6. Intentionally layered service architecture (DB -> Cache -> Access functions -> Applicator)
7. Guard patterns prevent duplicate enrichment (checks before writing)
8. Template creation path is fully functional and authoritative

### Areas for Improvement

**Critical (Functionality Gaps):**
1. LearnedDeviceFingerprint still actively queried - migration incomplete
2. Agent deployments miss unique identifiers (PROFINET station_name, SNMP sys_name, etc.)
3. Agent deployments miss CVE override merging
4. Manual scenarios miss unique identifier enrichment

**Important (Code Quality):**
5. Deprecated models still present (VendorFingerprint, LearnedDeviceFingerprint)
6. Dual protocol identity storage (unified JSONB + legacy columns)
7. VulnerableFingerprintVariant references deprecated VendorFingerprint model
8. Inconsistent fingerprint access patterns across codebase
9. Two overlapping services for template/fingerprint loading (device_templates.py vs fingerprint_cache.py)

### Recommended Cleanup Tasks

**Priority 1 - Fix Functionality Gaps:**
1. Add unique identifier enrichment to agent deployment path (`validate_and_enrich_serial_numbers()`)
2. Add CVE override merging to agent deployment path
3. Add unique identifier enrichment to manual scenario creation (`create_scenario()`)
4. Complete LearnedDeviceFingerprint -> DeviceTemplate migration in learning routes

**Priority 2 - Code Consolidation:**
5. Standardize on `protocol_identities` JSONB, deprecate individual columns
6. Update VulnerableFingerprintVariant to reference DeviceTemplate
7. Consolidate fingerprint access through single canonical path (`device_templates.get_fingerprint_by_vendor_model()`)
8. Merge device_templates.py and fingerprint_cache.py functionality

**Priority 3 - Cleanup (After Rollback Period):**
9. Remove deprecated VendorFingerprint model
10. Remove deprecated LearnedDeviceFingerprint model (after learning routes migrated)
