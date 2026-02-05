#!/bin/bash
# Comprehensive Vendor/Protocol/CVE Test
# Creates and runs a test scenario for Cyber Vision detection

set -e

API_BASE="https://10.10.20.231/api/v1"
CURL_OPTS="-sk"  # silent, insecure (self-signed cert)

echo "=============================================="
echo "PacketArch Comprehensive Vendor/CVE Test"
echo "=============================================="

# 1. Authenticate
echo "Authenticating..."
LOGIN_RESP=$(curl $CURL_OPTS -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"C!sco123"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Login failed: $LOGIN_RESP"
  exit 1
fi
echo "Authenticated successfully"

AUTH="Authorization: Bearer $TOKEN"

# 2. Create scenario  
echo ""
echo "Creating test scenario..."

SCENARIO_RESP=$(curl $CURL_OPTS -X POST "$API_BASE/scenarios" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Comprehensive Vendor CVE Test",
    "description": "All major OT vendors, protocols, and CVEs",
    "vertical": "manufacturing",
    "total_duration_ms": 300000
  }')

SCENARIO_ID=$(echo "$SCENARIO_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

if [ -z "$SCENARIO_ID" ]; then
  echo "Failed to create scenario: $SCENARIO_RESP"
  exit 1
fi
echo "Created scenario: $SCENARIO_ID"

# 3. Build and update definition with all vendors/protocols/CVEs
echo ""
echo "Building scenario definition..."

# Create the full definition JSON
DEFINITION=$(cat << 'JSONDEF'
{
  "devices": {
    "dev_001": {
      "id": "dev_001",
      "name": "SCADA-Server",
      "type": "scada",
      "vendor": "Generic",
      "role": "scada",
      "protocols": ["modbus_tcp", "ethernet_ip"],
      "zoneId": "zone_scada",
      "network": {"ipAddress": "10.100.0.10", "subnetMask": "255.255.255.0", "gateway": "10.100.0.1"}
    },
    "dev_002": {
      "id": "dev_002",
      "name": "HMI-Panel-Siemens",
      "type": "hmi",
      "vendor": "Siemens",
      "role": "hmi",
      "fingerprintModel": "6AV2124-0GC01-0AX0",
      "protocols": ["profinet", "s7comm"],
      "zoneId": "zone_scada",
      "network": {"ipAddress": "10.100.0.11", "subnetMask": "255.255.255.0", "gateway": "10.100.0.1"}
    },
    "dev_003": {
      "id": "dev_003",
      "name": "AB-ControlLogix-1756",
      "type": "plc",
      "vendor": "Rockwell",
      "role": "controller",
      "fingerprintModel": "1756-L85E/B",
      "protocols": ["ethernet_ip"],
      "cveIds": ["CVE-2022-1159"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.10", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_004": {
      "id": "dev_004",
      "name": "AB-CompactLogix-1769",
      "type": "plc",
      "vendor": "Rockwell",
      "role": "controller",
      "fingerprintModel": "1769-L33ER",
      "protocols": ["ethernet_ip"],
      "cveIds": ["CVE-2022-1161"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.11", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_005": {
      "id": "dev_005",
      "name": "Siemens-S7-1500",
      "type": "plc",
      "vendor": "Siemens",
      "role": "controller",
      "fingerprintModel": "6ES7 517-3AP00-0AB0",
      "protocols": ["profinet", "s7comm"],
      "cveIds": ["CVE-2019-13945"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.12", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_006": {
      "id": "dev_006",
      "name": "Siemens-S7-1200",
      "type": "plc",
      "vendor": "Siemens",
      "role": "controller",
      "fingerprintModel": "6ES7 214-1AG40-0XB0",
      "protocols": ["profinet", "s7comm"],
      "cveIds": ["CVE-2019-10929"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.13", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_007": {
      "id": "dev_007",
      "name": "Schneider-Modicon-M340",
      "type": "plc",
      "vendor": "Schneider",
      "role": "controller",
      "fingerprintModel": "BMXP342020",
      "protocols": ["modbus_tcp", "ethernet_ip"],
      "cveIds": ["CVE-2021-22779"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.14", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_008": {
      "id": "dev_008",
      "name": "Schneider-Modicon-M580",
      "type": "plc",
      "vendor": "Schneider",
      "role": "controller",
      "fingerprintModel": "BMEP584040",
      "protocols": ["modbus_tcp", "ethernet_ip"],
      "cveIds": ["CVE-2022-45788"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.15", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_009": {
      "id": "dev_009",
      "name": "Schneider-TM221",
      "type": "plc",
      "vendor": "Schneider",
      "role": "controller",
      "fingerprintModel": "TM221CE40R",
      "protocols": ["modbus_tcp"],
      "cveIds": ["CVE-2020-7537"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.16", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_010": {
      "id": "dev_010",
      "name": "ABB-AC500",
      "type": "plc",
      "vendor": "ABB",
      "role": "controller",
      "fingerprintModel": "PM5650-2ETH",
      "protocols": ["modbus_tcp", "ethernet_ip"],
      "cveIds": ["CVE-2020-8481"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.17", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_011": {
      "id": "dev_011",
      "name": "Honeywell-Experion-C300",
      "type": "plc",
      "vendor": "Honeywell",
      "role": "controller",
      "fingerprintModel": "C300",
      "protocols": ["modbus_tcp"],
      "cveIds": ["CVE-2020-10628"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.18", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_012": {
      "id": "dev_012",
      "name": "GE-PACSystems-RX3i",
      "type": "plc",
      "vendor": "GE",
      "role": "controller",
      "fingerprintModel": "IC695CPE330",
      "protocols": ["modbus_tcp", "ethernet_ip"],
      "cveIds": ["CVE-2018-10936"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.19", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    },
    "dev_013": {
      "id": "dev_013",
      "name": "Siemens-ET200SP",
      "type": "io",
      "vendor": "Siemens",
      "role": "field_device",
      "fingerprintModel": "6ES7 155-6AU01-0BN0",
      "protocols": ["profinet"],
      "zoneId": "zone_field",
      "network": {"ipAddress": "10.100.2.10", "subnetMask": "255.255.255.0", "gateway": "10.100.2.1"}
    },
    "dev_014": {
      "id": "dev_014",
      "name": "Rockwell-POINT-IO",
      "type": "io",
      "vendor": "Rockwell",
      "role": "field_device",
      "fingerprintModel": "1734-AENT",
      "protocols": ["ethernet_ip"],
      "zoneId": "zone_field",
      "network": {"ipAddress": "10.100.2.11", "subnetMask": "255.255.255.0", "gateway": "10.100.2.1"}
    },
    "dev_015": {
      "id": "dev_015",
      "name": "Schneider-TM3-IO",
      "type": "io",
      "vendor": "Schneider",
      "role": "field_device",
      "fingerprintModel": "TM3DI16",
      "protocols": ["modbus_tcp"],
      "zoneId": "zone_field",
      "network": {"ipAddress": "10.100.2.12", "subnetMask": "255.255.255.0", "gateway": "10.100.2.1"}
    },
    "dev_016": {
      "id": "dev_016",
      "name": "Modbus-Gateway",
      "type": "gateway",
      "vendor": "Generic",
      "role": "gateway",
      "protocols": ["modbus_tcp"],
      "zoneId": "zone_control",
      "network": {"ipAddress": "10.100.1.20", "subnetMask": "255.255.255.0", "gateway": "10.100.1.1"}
    }
  },
  "flows": {
    "flow_001": {"id": "flow_001", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_003", "protocol": "ethernet_ip", "timing": {"intervalMs": 1000}},
    "flow_002": {"id": "flow_002", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_004", "protocol": "ethernet_ip", "timing": {"intervalMs": 1000}},
    "flow_003": {"id": "flow_003", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_007", "protocol": "modbus_tcp", "timing": {"intervalMs": 1000}, "config": {"function_code": 3, "start_address": 0, "quantity": 10}},
    "flow_004": {"id": "flow_004", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_008", "protocol": "modbus_tcp", "timing": {"intervalMs": 1000}, "config": {"function_code": 3, "start_address": 0, "quantity": 10}},
    "flow_005": {"id": "flow_005", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_009", "protocol": "modbus_tcp", "timing": {"intervalMs": 1000}, "config": {"function_code": 3, "start_address": 0, "quantity": 10}},
    "flow_006": {"id": "flow_006", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_010", "protocol": "modbus_tcp", "timing": {"intervalMs": 1000}, "config": {"function_code": 3, "start_address": 0, "quantity": 10}},
    "flow_007": {"id": "flow_007", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_011", "protocol": "modbus_tcp", "timing": {"intervalMs": 1000}, "config": {"function_code": 3, "start_address": 0, "quantity": 10}},
    "flow_008": {"id": "flow_008", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_012", "protocol": "ethernet_ip", "timing": {"intervalMs": 1000}},
    "flow_009": {"id": "flow_009", "sourceDeviceId": "dev_002", "targetDeviceId": "dev_005", "protocol": "profinet", "timing": {"intervalMs": 500}},
    "flow_010": {"id": "flow_010", "sourceDeviceId": "dev_002", "targetDeviceId": "dev_006", "protocol": "profinet", "timing": {"intervalMs": 500}},
    "flow_011": {"id": "flow_011", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_005", "protocol": "s7comm", "timing": {"intervalMs": 1000}},
    "flow_012": {"id": "flow_012", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_006", "protocol": "s7comm", "timing": {"intervalMs": 1000}},
    "flow_013": {"id": "flow_013", "sourceDeviceId": "dev_003", "targetDeviceId": "dev_014", "protocol": "ethernet_ip", "timing": {"intervalMs": 500}},
    "flow_014": {"id": "flow_014", "sourceDeviceId": "dev_005", "targetDeviceId": "dev_013", "protocol": "profinet", "timing": {"intervalMs": 250}},
    "flow_015": {"id": "flow_015", "sourceDeviceId": "dev_016", "targetDeviceId": "dev_015", "protocol": "modbus_tcp", "timing": {"intervalMs": 1000}, "config": {"function_code": 3, "start_address": 0, "quantity": 8}},
    "flow_016": {"id": "flow_016", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_007", "protocol": "ethernet_ip", "timing": {"intervalMs": 2000}},
    "flow_017": {"id": "flow_017", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_010", "protocol": "ethernet_ip", "timing": {"intervalMs": 2000}},
    "flow_018": {"id": "flow_018", "sourceDeviceId": "dev_001", "targetDeviceId": "dev_012", "protocol": "modbus_tcp", "timing": {"intervalMs": 1000}, "config": {"function_code": 3, "start_address": 0, "quantity": 10}}
  },
  "zones": {
    "zone_scada": {"id": "zone_scada", "name": "SCADA Zone (L3)", "level": 3, "network": {"subnet": "10.100.0.0/24"}},
    "zone_control": {"id": "zone_control", "name": "Control Zone (L2)", "level": 2, "network": {"subnet": "10.100.1.0/24"}},
    "zone_field": {"id": "zone_field", "name": "Field Zone (L1)", "level": 1, "network": {"subnet": "10.100.2.0/24"}}
  },
  "phases": [
    {"id": "startup", "name": "Startup", "duration_pct": 10, "traffic_multiplier": 0.5},
    {"id": "normal", "name": "Normal Operation", "duration_pct": 60, "traffic_multiplier": 1.0},
    {"id": "discovery", "name": "Discovery Burst", "duration_pct": 15, "traffic_multiplier": 2.0, "behaviors": ["discovery_scan"]},
    {"id": "shutdown", "name": "Shutdown", "duration_pct": 15, "traffic_multiplier": 0.3}
  ]
}
JSONDEF
)

# 4. Update scenario with definition
echo "Updating scenario with device/flow definition..."

UPDATE_RESP=$(curl $CURL_OPTS -X PUT "$API_BASE/scenarios/$SCENARIO_ID" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Comprehensive Vendor CVE Test\",
    \"description\": \"All major OT vendors, protocols, and CVEs\",
    \"definition\": $DEFINITION,
    \"total_duration_ms\": 300000
  }")

echo "Scenario updated"

# 5. Print summary
echo ""
echo "=============================================="
echo "SCENARIO SUMMARY"
echo "=============================================="
echo "Scenario ID: $SCENARIO_ID"
echo "Duration: 5 minutes"
echo ""
echo "VENDORS (6):"
echo "  - Rockwell Allen-Bradley (ControlLogix, CompactLogix)"
echo "  - Siemens (S7-1500, S7-1200, ET200SP, HMI)"  
echo "  - Schneider Electric (Modicon M340, M580, TM221)"
echo "  - ABB (AC500)"
echo "  - Honeywell (Experion C300)"
echo "  - GE (PACSystems RX3i)"
echo ""
echo "PROTOCOLS (4):"
echo "  - EtherNet/IP (CIP)"
echo "  - Modbus TCP"
echo "  - PROFINET"
echo "  - S7comm"
echo ""
echo "CVEs (10):"
echo "  - CVE-2022-1159 (Rockwell ControlLogix)"
echo "  - CVE-2022-1161 (Rockwell CompactLogix)"
echo "  - CVE-2019-13945 (Siemens S7-1500)"
echo "  - CVE-2019-10929 (Siemens S7-1200)"
echo "  - CVE-2021-22779 (Schneider M340)"
echo "  - CVE-2022-45788 (Schneider M580)"
echo "  - CVE-2020-7537 (Schneider TM221)"
echo "  - CVE-2020-8481 (ABB AC500)"
echo "  - CVE-2020-10628 (Honeywell C300)"
echo "  - CVE-2018-10936 (GE RX3i)"
echo ""
echo "DEVICES: 16 total (2 SCADA/HMI, 10 PLCs, 3 I/O, 1 Gateway)"
echo "FLOWS: 18 total"
echo ""

# 6. Start traffic generation
echo "=============================================="
echo "STARTING TRAFFIC GENERATION"
echo "=============================================="

START_RESP=$(curl $CURL_OPTS -X POST "$API_BASE/scenarios/$SCENARIO_ID/start" \
  -H "$AUTH" \
  -H "Content-Type: application/json")

echo "Start response: $START_RESP"
echo ""
echo "=============================================="
echo "Traffic generation initiated!"
echo ""
echo "View in Cisco Cyber Vision to see:"
echo "  - Device discovery (16 OT devices)"
echo "  - Protocol identification (EtherNet/IP, Modbus, PROFINET, S7)"
echo "  - Vulnerability detection (10 CVEs)"
echo ""
echo "Scenario ID: $SCENARIO_ID"
echo "=============================================="
