# Firmware Fingerprint Testing Guide

This document provides a comprehensive guide for validating firmware fingerprinting across all supported OT protocols in PacketArch.

## Overview

PacketArch generates OT traffic that includes device identity/fingerprint information. Security tools like Cisco Cyber Vision parse this traffic to identify devices and their firmware versions, enabling CVE detection. This testing guide helps verify that the traffic generator is producing correct fingerprint data.

## Protocol Matrix

| Protocol | Firmware Field | Packet Location | Port/EtherType | Detection Method |
|----------|---------------|-----------------|----------------|------------------|
| **SNMP** | `sys_descr` | GetResponse OID 1.3.6.1.2.1.1.1.0 | UDP 161 | Firmware embedded in string |
| **Modbus** | `major_minor_revision` | FC43 Object ID 0x02 | TCP 502 | Device Identification response |
| **EtherNet/IP** | `revision_major/minor` | ListIdentity response bytes 40-41 | TCP 44818 | 2-byte revision field |
| **PROFINET DCP** | `sw_release` | OEM Device ID block (0x02/0x08) | EtherType 0x8892 | "SW:V{version}" in string |
| **S7comm SZL** | `firmware_version` | SZL 0x0011 bytes 32-39 | TCP 102 | 8-byte fixed-width field |
| **BACnet** | `firmware_revision` | ReadProperty response Property 44 | UDP 47808 | APDU service response |

---

## Prerequisites

### Required Software
- Python 3.11+
- Poetry (backend package manager)
- scapy (packet parsing library)
- tcpdump (packet capture)
- SSH access to traffic generator host

### Access Requirements
- PacketArch backend server
- Traffic generator host (10.10.20.113)
- Network interface for packet capture

### Install Dependencies
```bash
cd /home/rocsmith/PacketArch/backend
poetry install
```

---

## Quick Start (5 Minutes)

For a rapid validation cycle:

```bash
# 1. Create test scenario
cd /home/rocsmith/PacketArch/backend
poetry run python scripts/create_fingerprint_test_scenario.py

# 2. Note the scenario ID and deploy via UI or API

# 3. Capture packets on traffic generator
sshpass -p 'cisco' ssh cisco@10.10.20.113 \
  "sudo timeout 60 tcpdump -i ens3 -w /tmp/test.pcap -c 3000"

# 4. Copy PCAP back
sshpass -p 'cisco' scp cisco@10.10.20.113:/tmp/test.pcap /tmp/

# 5. Validate
poetry run python scripts/validate_fingerprint_packets.py --pcap /tmp/test.pcap
```

---

## Full Validation Procedure

### Step 1: Create Test Scenario

```bash
cd /home/rocsmith/PacketArch/backend
poetry run python scripts/create_fingerprint_test_scenario.py
```

This creates:
- A scenario with 4 test devices covering all vendors/protocols
- `/tmp/expected_fingerprints.json` with expected values

**Test Devices Created:**

| Device | IP | Vendor | Protocols | CVE | Firmware |
|--------|-----|--------|-----------|-----|----------|
| Siemens S7-1516 | 10.99.0.10 | Siemens | PROFINET, S7comm | CVE-2019-13945 | V2.8.0 |
| Rockwell ControlLogix | 10.99.0.20 | Rockwell | EtherNet/IP | CVE-2022-1159 | 32.011 |
| Schneider M340 | 10.99.0.30 | Schneider | Modbus TCP | CVE-2019-6857 | 2.80 |
| JCI NAE55 | 10.99.0.40 | Johnson Controls | BACnet | - | 12.0.3 |

### Step 2: Deploy Scenario

**Option A: Via API**
```bash
curl -X POST http://localhost:8001/api/v1/remote-deployments \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "<scenario-id>",
    "docker_host_id": "<docker-host-id>",
    "network_interface": "ens3",
    "run_mode": "perpetual"
  }'
```

**Option B: Via UI**
1. Open PacketArch UI
2. Navigate to Scenarios
3. Select the test scenario
4. Click Deploy
5. Select traffic generator host
6. Start deployment

### Step 3: Verify Deployment Running

```bash
# Check container status
sshpass -p 'cisco' ssh cisco@10.10.20.113 \
  "docker ps --filter name=packetarch"

# Check logs for packet generation
sshpass -p 'cisco' ssh cisco@10.10.20.113 \
  "docker logs --tail 20 packetarch-generator-*"
```

Look for log messages like:
```
Scheduled universal SNMP discovery for 10.99.0.10 (sysDescr=Siemens SIMATIC...)
Scheduled PROFINET DCP discovery for ...
Scheduled S7comm SZL discovery for 10.99.0.10 (order_code=6ES7..., firmware=V2.8.0)
```

### Step 4: Capture Packets

```bash
# SSH to traffic generator and capture
sshpass -p 'cisco' ssh cisco@10.10.20.113

# On traffic generator host:
sudo tcpdump -i ens3 -w /tmp/fingerprint_test.pcap -c 5000

# Wait 60-120 seconds for discovery cycles
# Press Ctrl+C when done

# Copy PCAP back to PacketArch server
exit
sshpass -p 'cisco' scp cisco@10.10.20.113:/tmp/fingerprint_test.pcap /tmp/
```

### Step 5: Validate Packets

```bash
cd /home/rocsmith/PacketArch/backend
poetry run python scripts/validate_fingerprint_packets.py \
  --pcap /tmp/fingerprint_test.pcap
```

### Step 6: Interpret Results

**Successful Output:**
```
=== FINGERPRINT VALIDATION REPORT ===

--- RAW FINDINGS ---
10.99.0.10:
  snmp (3 packets):
    sys_descr: Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP V2.8.0
    sys_object_id: 1.3.6.1.4.1.4329.2.51.1516
  s7comm (2 packets):
    firmware_version: V2.8.0
    order_code: 6ES7 516-3AN01-0AB0

--- VALIDATION RESULTS ---
Siemens S7-1516 Test (10.99.0.10):
  [+] SNMP - sysDescr (exact)
      Expected: Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP V2.8.0
      Found:    Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP V2.8.0
  [+] S7comm SZL - firmware_version
      Expected: V2.8.0
      Found:    V2.8.0

=== SUMMARY ===
Total Checks: 18
Passed:       18
Failed:       0

All fingerprint validations PASSED!
```

---

## Protocol Deep Dives

### SNMP (MIB-II System Group)

**Packet Structure:**
```
UDP Datagram (port 161)
└─ SNMP Message (BER-TLV encoded)
   ├─ Version: 0 (SNMPv1) or 1 (SNMPv2c)
   ├─ Community: "public"
   └─ PDU Type: GetResponse (0xA2)
      ├─ Request ID
      ├─ Error Status: 0
      ├─ Error Index: 0
      └─ VarBindList
         ├─ OID: 1.3.6.1.2.1.1.1.0 (sysDescr)
         │  └─ Value: "Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP V2.8.0"
         ├─ OID: 1.3.6.1.2.1.1.2.0 (sysObjectID)
         │  └─ Value: 1.3.6.1.4.1.4329.2.51.1516
         └─ OID: 1.3.6.1.2.1.1.5.0 (sysName)
            └─ Value: "S7-1516-3-PN-DP"
```

**Firmware Location:** Embedded in `sysDescr` string

**Scapy Filter:**
```python
pkt[UDP].sport == 161 and Raw in pkt
```

### Modbus FC43 (Read Device Identification)

**Packet Structure:**
```
TCP Segment (port 502)
└─ MBAP Header (7 bytes)
   ├─ Transaction ID (2)
   ├─ Protocol ID (2): 0x0000
   ├─ Length (2)
   └─ Unit ID (1)
└─ Modbus PDU
   ├─ Function Code: 0x2B (FC43)
   ├─ MEI Type: 0x0E
   ├─ Device ID Code: 0x01-0x04
   ├─ Conformity Level: 0x81-0x83
   ├─ More Follows: 0x00
   ├─ Next Object ID: 0x00
   ├─ Number of Objects: N
   └─ Objects:
      ├─ Object 0x00: VendorName
      ├─ Object 0x01: ProductCode
      └─ Object 0x02: MajorMinorRevision  ← FIRMWARE
```

**Firmware Location:** Object ID 0x02 (MajorMinorRevision)

**Scapy Filter:**
```python
pkt[TCP].sport == 502 and payload[7] == 0x2B
```

### EtherNet/IP (ListIdentity)

**Packet Structure:**
```
TCP Segment (port 44818)
└─ Encapsulation Header (24 bytes)
   ├─ Command: 0x0063 (ListIdentity)
   ├─ Length
   └─ Session Handle
└─ CPF Items
   └─ Item Type 0x000C (ListIdentity)
      └─ Identity Data
         ├─ Socket Info (18 bytes)
         ├─ Vendor ID (2 bytes)
         ├─ Device Type (2 bytes)
         ├─ Product Code (2 bytes)
         ├─ Revision Major (1 byte)  ← FIRMWARE MAJOR
         ├─ Revision Minor (1 byte)  ← FIRMWARE MINOR
         ├─ Status (2 bytes)
         ├─ Serial Number (4 bytes)
         └─ Product Name (variable)
```

**Firmware Location:** Bytes 40-41 of ListIdentity response (revision_major, revision_minor)

**Scapy Filter:**
```python
pkt[TCP].sport == 44818 and payload[0:2] == b'\x63\x00'
```

### PROFINET DCP (Identify Response)

**Packet Structure:**
```
Ethernet Frame (EtherType 0x8892)
└─ DCP Header
   ├─ Frame ID: 0xFEFF (Identify Response)
   ├─ Service ID: 0x05 (Identify)
   ├─ Service Type: 0x01 (Success)
   ├─ XID (4 bytes)
   ├─ Response Delay (2 bytes)
   └─ Data Length (2 bytes)
└─ DCP Blocks
   ├─ Block: Device Name (0x02, 0x02)
   ├─ Block: Device ID (0x02, 0x03) - Vendor ID + Device ID
   └─ Block: OEM Device ID (0x02, 0x08)  ← FIRMWARE
      └─ Format: "OrderID:xxx;SN:xxx;Type:xxx;HW:x.x;SW:Vx.x.x"
```

**Firmware Location:** "SW:" field in OEM Device ID block

**Scapy Filter:**
```python
pkt[Ether].type == 0x8892 and payload[2:4] == b'\x05\x01'
```

### S7comm SZL 0x0011 (Module Identification)

**Packet Structure:**
```
TCP Segment (port 102)
└─ TPKT Header (4 bytes)
   ├─ Version: 0x03
   └─ Length
└─ COTP Header
   ├─ Length
   └─ PDU Type: 0x0F (Data)
└─ S7comm Header
   ├─ Protocol ID: 0x32
   ├─ Message Type: 0x07 (Userdata)
   └─ Parameters
└─ SZL Data (for ID 0x0011)
   ├─ SZL ID: 0x0011
   ├─ Index: 0x0000
   ├─ Data Length: 64
   ├─ Element Count: 1
   └─ Record:
      ├─ Order Code (20 bytes): "6ES7 516-3AN01-0AB0"
      ├─ Serial Number (12 bytes)
      ├─ Firmware Version (8 bytes): "V2.8.0\x00\x00"  ← FIRMWARE
      └─ Module Type (24 bytes): "CPU 1516-3 PN/DP"
```

**Firmware Location:** Bytes 32-39 of SZL 0x0011 record data

**Scapy Filter:**
```python
pkt[TCP].sport == 102 and b'\x00\x11\x00\x00' in payload
```

### BACnet (I-Am / ReadProperty)

**Packet Structure:**
```
UDP Datagram (port 47808)
└─ BVLC Header (4 bytes)
   ├─ Type: 0x81 (BACnet/IP)
   ├─ Function: 0x0B (Original Broadcast)
   └─ Length
└─ NPDU
└─ APDU
   ├─ PDU Type: Unconfirmed Request or Complex-ACK
   └─ Service: I-Am (0x00) or ReadProperty-ACK
      └─ Property 44 (firmware_revision): "12.0.3"  ← FIRMWARE
```

**Firmware Location:** Property 44 (firmware_revision) in ReadProperty response

**Scapy Filter:**
```python
pkt[UDP].sport == 47808 and payload[0] == 0x81
```

---

## Expected Values by Vendor

### Siemens (S7-1500 Series)

| Field | Example Value |
|-------|---------------|
| SNMP sysDescr | `Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP V2.8.0` |
| SNMP sysObjectID | `1.3.6.1.4.1.4329.2.51.1516` |
| PROFINET sw_release | `V2.8.0` |
| PROFINET vendor_id | `0x002A` (42) |
| S7 order_code | `6ES7 516-3AN01-0AB0` |
| S7 firmware_version | `V2.8.0` |

### Rockwell (ControlLogix)

| Field | Example Value |
|-------|---------------|
| SNMP sysDescr | `Rockwell Automation 1756-L85E/B ControlLogix v32.011` |
| EtherNet/IP vendor_id | `1` |
| EtherNet/IP revision_major | `32` |
| EtherNet/IP revision_minor | `11` |
| Modbus MajorMinorRevision | `32.011` |

### Schneider Electric (Modicon)

| Field | Example Value |
|-------|---------------|
| SNMP sysDescr | `Schneider Electric Modicon M340 v2.80` |
| Modbus VendorName | `Schneider Electric` |
| Modbus ProductCode | `Modicon M340` |
| Modbus MajorMinorRevision | `2.80` |

### Johnson Controls (Building Automation)

| Field | Example Value |
|-------|---------------|
| BACnet vendor_id | `5` |
| BACnet vendor_name | `Johnson Controls` |
| BACnet firmware_revision | `12.0.3` |
| SNMP sysDescr | `Johnson Controls NAE55` |

---

## Troubleshooting

### No Packets Captured

**Symptoms:** tcpdump captures 0 packets or validation finds no data

**Causes & Solutions:**
1. **Wrong interface**: Verify interface name
   ```bash
   ip addr show  # Find correct interface (e.g., ens3, eth0)
   ```

2. **Container not running**: Check deployment status
   ```bash
   docker ps --filter name=packetarch
   docker logs packetarch-generator-*
   ```

3. **Scenario not started**: Verify deployment is in "running" state

4. **Network isolation**: Ensure capture interface sees generated traffic

### Wrong Firmware in Packets

**Symptoms:** Firmware version doesn't match expected CVE-vulnerable version

**Causes & Solutions:**
1. **Stale scenario**: Recreate scenario after CVE data updates
   ```bash
   # Re-seed database
   docker compose exec backend python -c "
   from app.services.seed_data import seed_vulnerable_fingerprints
   import asyncio
   asyncio.run(seed_vulnerable_fingerprints())
   "

   # Create new scenario
   poetry run python scripts/create_fingerprint_test_scenario.py
   ```

2. **CVE data missing templates**: Verify CVE data files have `snmp_sys_descr_template`
   ```bash
   grep -r "snmp_sys_descr_template" backend/app/services/cve_data/
   ```

3. **Identity override not applied**: Check scenario definition includes `cveIdentityOverrides`

### Missing Protocol Packets

**Symptoms:** Some protocols show no packets (e.g., PROFINET but not S7comm)

**Causes & Solutions:**
1. **Device doesn't have protocol**: Check device's protocols array
   ```bash
   # In scenario definition:
   "protocols": ["profinet", "s7comm_plus"]
   ```

2. **Discovery not scheduled**: Check orchestrator logs
   ```bash
   docker logs packetarch-generator-* | grep -i "scheduled.*discovery"
   ```

3. **Protocol engine error**: Look for errors in logs
   ```bash
   docker logs packetarch-generator-* | grep -i error
   ```

### Cyber Vision Not Detecting

**Symptoms:** Packets validate correctly but Cyber Vision doesn't show device/CVE

**Causes & Solutions:**
1. **Verify traffic arrives at CV**: Use CV's packet capture or SPAN port monitoring

2. **Check CV has CVE data**: Cyber Vision needs matching CVE definitions

3. **Protocol not supported by CV**: Some protocols may not be parsed by CV version

4. **Firmware format mismatch**: CV may expect specific format (e.g., "V2.8" vs "2.8.0")

---

## Maintenance

### Adding New Protocol Support

1. Update `validate_fingerprint_packets.py` with new protocol parser
2. Add expected values to `TEST_DEVICES` in scenario creation script
3. Update protocol matrix table in this document
4. Add protocol deep dive section

### Adding New Vendors

1. Add new CVE data file in `backend/app/services/cve_data/`
2. Ensure `snmp_sys_descr_template` is populated
3. Add vendor fingerprint in `backend/app/services/vendor_fingerprints/`
4. Add test device in `create_fingerprint_test_scenario.py`
5. Update expected values table in this document

### Updating CVE Data

After modifying CVE data files:
```bash
# Re-seed database
docker compose exec backend python -c "
from app.services.seed_data import seed_vulnerable_fingerprints
import asyncio
asyncio.run(seed_vulnerable_fingerprints())
"

# Rebuild traffic generator
sshpass -p 'cisco' ssh cisco@10.10.20.113 \
  "cd /opt/packetarch-agent && docker compose pull && docker compose up -d"

# Recreate and redeploy test scenario
```

---

## Reference

### Files

| File | Purpose |
|------|---------|
| `backend/scripts/create_fingerprint_test_scenario.py` | Creates test scenario |
| `backend/scripts/validate_fingerprint_packets.py` | Validates captured packets |
| `docs/FIRMWARE_FINGERPRINT_TESTING.md` | This document |
| `backend/app/services/cve_data/*.py` | CVE definitions with vulnerable variants |
| `backend/app/protocol_engines/firmware_version_deriver.py` | Auto-derives firmware fields |
| `backend/app/protocol_engines/unified_orchestrator.py` | Packet generation logic |

### Related Documentation

- `docs/ADDING_NEW_PROTOCOLS.md` - Protocol implementation guide
- `docs/PROTOCOL_AUDIT_REPORT.md` - Protocol support matrix
- `CLAUDE.md` - Development guidelines
