#!/usr/bin/env python3
"""Comprehensive vendor/protocol/CVE test scenario.

Creates and runs a scenario hitting all major OT vendors and protocols
with CVE-vulnerable devices for Cisco Cyber Vision detection.
"""

import asyncio
import httpx
import json
import sys

# PacketArch API configuration
API_BASE = "https://10.10.20.231/api/v1"
ADMIN_CREDS = {"username": "admin", "password": "PacketArch_Admin!"}

# Docker host for traffic injection
DOCKER_HOST_ID = "a4b1edd7-c926-475d-b990-9656c6b91af0"
NETWORK_INTERFACE = "ens3"

# Comprehensive device list with FULL vendor fingerprints and CVEs
DEVICES = [
    # Rockwell Allen-Bradley ControlLogix (EtherNet/IP)
    {
        "name": "AB-ControlLogix-1756",
        "type": "plc",
        "vendor": "Rockwell",
        "fingerprint_model": "1756-L83E",
        "protocols": ["ethernet_ip"],
        "role": "controller",
        "cve_ids": ["CVE-2022-1159"],
        "vendor_fingerprint": {
            "ethernet_ip_identity": {
                "vendor_id": 1,  # Rockwell Automation
                "device_type": 14,  # Programmable Logic Controller
                "product_code": 55,
                "revision_major": 28,  # Vulnerable version for CVE-2022-1159
                "revision_minor": 11,
                "serial_number": 0x12345678,
                "product_name": "1756-L83E/B LOGIX5583E",
                "state": 3,
            },
            "modbus_identity": {
                "vendor_name": "Rockwell Automation/Allen-Bradley",
                "product_code": "1756-L83E/B",
                "major_minor_revision": "28.011",
                "product_name": "1756-L83E Logix5583E Controller",
            },
        },
    },
    # Rockwell CompactLogix (EtherNet/IP)
    {
        "name": "AB-CompactLogix-5380",
        "type": "plc",
        "vendor": "Rockwell",
        "fingerprint_model": "5069-L330ER",
        "protocols": ["ethernet_ip"],
        "role": "controller",
        "cve_ids": ["CVE-2022-1161"],
        "vendor_fingerprint": {
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 14,
                "product_code": 89,
                "revision_major": 30,
                "revision_minor": 14,
                "serial_number": 0x23456789,
                "product_name": "5069-L330ER CompactLogix 5380",
                "state": 3,
            },
        },
    },
    # Siemens S7-1500 (PROFINET, S7comm)
    {
        "name": "Siemens-S7-1500",
        "type": "plc",
        "vendor": "Siemens",
        "fingerprint_model": "6ES7 517-3AP00-0AB0",
        "protocols": ["profinet", "s7comm"],
        "role": "controller",
        "cve_ids": ["CVE-2019-13945"],
        "vendor_fingerprint": {
            "profinet_identity": {
                "vendor_id": 0x002A,  # Siemens AG
                "device_id": 0x0403,  # S7-1500
                "station_name": "siemens-s7-1500-cpu",
                "device_type": "S7-1500 CPU 1517-3 PN/DP",
                "order_id": "6ES7 517-3AP00-0AB0",
                "serial_number": "S Q-X8C912345678",
                "hw_revision": 1,
                "sw_revision_prefix": "V",
                "sw_revision_major": 2,
                "sw_revision_minor": 5,
                "sw_revision_patch": 0,
            },
            "s7_identity": {
                "module_type": "CPU 1517-3 PN/DP",
                "serial_number": "S Q-X8C912345678",
                "plant_id": "PLANT01",
                "copyright": "Original Siemens Equipment",
                "module_name": "PLC_1",
                "hw_version": "1",
                "fw_version": "V2.5.0",
                "order_number": "6ES7 517-3AP00-0AB0",
            },
        },
    },
    # Siemens S7-1200 (PROFINET, S7comm)
    {
        "name": "Siemens-S7-1200",
        "type": "plc",
        "vendor": "Siemens",
        "fingerprint_model": "6ES7 214-1AG40-0XB0",
        "protocols": ["profinet", "s7comm"],
        "role": "controller",
        "cve_ids": ["CVE-2019-10929"],
        "vendor_fingerprint": {
            "profinet_identity": {
                "vendor_id": 0x002A,
                "device_id": 0x0301,
                "station_name": "siemens-s7-1200-cpu",
                "device_type": "S7-1200 CPU 1214C DC/DC/DC",
                "order_id": "6ES7 214-1AG40-0XB0",
                "serial_number": "S C-K4U812345678",
                "sw_revision_major": 4,
                "sw_revision_minor": 2,
                "sw_revision_patch": 1,
            },
            "s7_identity": {
                "module_type": "CPU 1214C DC/DC/DC",
                "serial_number": "S C-K4U812345678",
                "fw_version": "V4.2.1",
                "order_number": "6ES7 214-1AG40-0XB0",
            },
        },
    },
    # Siemens ET 200SP (PROFINET)
    {
        "name": "Siemens-ET200SP",
        "type": "io",
        "vendor": "Siemens",
        "fingerprint_model": "6ES7 155-6AU01-0BN0",
        "protocols": ["profinet"],
        "role": "field_device",
        "vendor_fingerprint": {
            "profinet_identity": {
                "vendor_id": 0x002A,
                "device_id": 0x0B01,
                "station_name": "et200sp-io-device",
                "device_type": "ET 200SP Interface Module",
                "order_id": "6ES7 155-6AU01-0BN0",
                "serial_number": "S V-P5A612345678",
                "sw_revision_major": 2,
                "sw_revision_minor": 2,
            },
        },
    },
    # Schneider Electric Modicon M340 (Modbus TCP, EtherNet/IP)
    {
        "name": "Schneider-M340",
        "type": "plc",
        "vendor": "Schneider",
        "fingerprint_model": "BMXP342020",
        "protocols": ["modbus_tcp", "ethernet_ip"],
        "role": "controller",
        "cve_ids": ["CVE-2021-22779"],
        "vendor_fingerprint": {
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "BMXP342020",
                "major_minor_revision": "3.10",
                "vendor_url": "https://www.se.com",
                "product_name": "Modicon M340 CPU",
                "model_name": "BMXP342020",
            },
            "ethernet_ip_identity": {
                "vendor_id": 523,  # Schneider Electric
                "device_type": 14,
                "product_code": 342,
                "revision_major": 3,
                "revision_minor": 10,
                "serial_number": 0x34567890,
                "product_name": "Modicon M340 BMXP342020",
                "state": 3,
            },
        },
    },
    # Schneider Electric Modicon M580 (Modbus TCP, EtherNet/IP)
    {
        "name": "Schneider-M580",
        "type": "plc",
        "vendor": "Schneider",
        "fingerprint_model": "BMEP584040",
        "protocols": ["modbus_tcp", "ethernet_ip"],
        "role": "controller",
        "cve_ids": ["CVE-2022-45788"],
        "vendor_fingerprint": {
            "modbus_identity": {
                "vendor_name": "Schneider Electric",
                "product_code": "BMEP584040",
                "major_minor_revision": "3.20",
                "product_name": "Modicon M580 ePAC",
                "model_name": "BMEP584040",
            },
            "ethernet_ip_identity": {
                "vendor_id": 523,
                "device_type": 14,
                "product_code": 584,
                "revision_major": 3,
                "revision_minor": 20,
                "serial_number": 0x45678901,
                "product_name": "Modicon M580 BMEP584040",
                "state": 3,
            },
        },
    },
    # ABB AC500 (Modbus TCP, EtherNet/IP)
    {
        "name": "ABB-AC500",
        "type": "plc",
        "vendor": "ABB",
        "fingerprint_model": "PM5650-2ETH",
        "protocols": ["modbus_tcp", "ethernet_ip"],
        "role": "controller",
        "cve_ids": ["CVE-2020-8481"],
        "vendor_fingerprint": {
            "modbus_identity": {
                "vendor_name": "ABB",
                "product_code": "PM5650-2ETH",
                "major_minor_revision": "2.8.0",
                "product_name": "AC500 PM5650 PLC",
                "model_name": "PM5650-2ETH",
            },
            "ethernet_ip_identity": {
                "vendor_id": 292,  # ABB
                "device_type": 14,
                "product_code": 5650,
                "revision_major": 2,
                "revision_minor": 8,
                "serial_number": 0x56789012,
                "product_name": "ABB AC500 PM5650-2ETH",
                "state": 3,
            },
        },
    },
    # Honeywell Experion C300 (Modbus TCP)
    {
        "name": "Honeywell-C300",
        "type": "plc",
        "vendor": "Honeywell",
        "fingerprint_model": "C300",
        "protocols": ["modbus_tcp"],
        "role": "controller",
        "cve_ids": ["CVE-2020-10628"],
        "vendor_fingerprint": {
            "modbus_identity": {
                "vendor_name": "Honeywell Process Solutions",
                "product_code": "C300-CONTROLLER",
                "major_minor_revision": "310.2",
                "product_name": "Experion PKS C300 Controller",
                "model_name": "C300",
            },
        },
    },
    # GE/Emerson RX3i (Modbus TCP, EtherNet/IP)
    {
        "name": "GE-RX3i",
        "type": "plc",
        "vendor": "GE",
        "fingerprint_model": "IC695CPE330",
        "protocols": ["modbus_tcp", "ethernet_ip"],
        "role": "controller",
        "cve_ids": ["CVE-2018-10936"],
        "vendor_fingerprint": {
            "modbus_identity": {
                "vendor_name": "GE Intelligent Platforms",
                "product_code": "IC695CPE330",
                "major_minor_revision": "9.30",
                "product_name": "PACSystems RX3i CPE330",
                "model_name": "IC695CPE330",
            },
            "ethernet_ip_identity": {
                "vendor_id": 104,  # GE Fanuc
                "device_type": 14,
                "product_code": 330,
                "revision_major": 9,
                "revision_minor": 30,
                "serial_number": 0x67890123,
                "product_name": "PACSystems RX3i IC695CPE330",
                "state": 3,
            },
        },
    },
    # SCADA Server
    {
        "name": "SCADA-Server",
        "type": "scada",
        "vendor": "Generic",
        "protocols": ["modbus_tcp", "ethernet_ip"],
        "role": "scada",
        "vendor_fingerprint": {},
    },
    # Siemens HMI Panel
    {
        "name": "Siemens-HMI",
        "type": "hmi",
        "vendor": "Siemens",
        "fingerprint_model": "6AV2124-0GC01-0AX0",
        "protocols": ["profinet"],
        "role": "hmi",
        "vendor_fingerprint": {
            "profinet_identity": {
                "vendor_id": 0x002A,
                "device_id": 0x0501,
                "station_name": "siemens-tp1500-hmi",
                "device_type": "TP1500 Comfort Panel",
                "order_id": "6AV2124-0GC01-0AX0",
                "serial_number": "S V-HMI12345678",
                "sw_revision_major": 16,
                "sw_revision_minor": 0,
            },
        },
    },
    # Rockwell Remote I/O
    {
        "name": "AB-POINT-IO",
        "type": "io",
        "vendor": "Rockwell",
        "fingerprint_model": "1734-AENT",
        "protocols": ["ethernet_ip"],
        "role": "field_device",
        "vendor_fingerprint": {
            "ethernet_ip_identity": {
                "vendor_id": 1,
                "device_type": 12,  # Communications Adapter
                "product_code": 180,
                "revision_major": 6,
                "revision_minor": 1,
                "serial_number": 0x78901234,
                "product_name": "1734-AENT POINT I/O",
                "state": 3,
            },
        },
    },
]

# Flow definitions
FLOWS = [
    # EtherNet/IP flows
    {"source": "SCADA-Server", "target": "AB-ControlLogix-1756", "protocol": "ethernet_ip"},
    {"source": "SCADA-Server", "target": "AB-CompactLogix-5380", "protocol": "ethernet_ip"},
    {"source": "AB-ControlLogix-1756", "target": "AB-POINT-IO", "protocol": "ethernet_ip"},
    {"source": "SCADA-Server", "target": "GE-RX3i", "protocol": "ethernet_ip"},
    {"source": "SCADA-Server", "target": "Schneider-M340", "protocol": "ethernet_ip"},
    {"source": "SCADA-Server", "target": "ABB-AC500", "protocol": "ethernet_ip"},
    # Modbus TCP flows
    {"source": "SCADA-Server", "target": "Schneider-M340", "protocol": "modbus_tcp"},
    {"source": "SCADA-Server", "target": "Schneider-M580", "protocol": "modbus_tcp"},
    {"source": "SCADA-Server", "target": "ABB-AC500", "protocol": "modbus_tcp"},
    {"source": "SCADA-Server", "target": "Honeywell-C300", "protocol": "modbus_tcp"},
    {"source": "SCADA-Server", "target": "GE-RX3i", "protocol": "modbus_tcp"},
    # PROFINET flows
    {"source": "Siemens-HMI", "target": "Siemens-S7-1500", "protocol": "profinet"},
    {"source": "Siemens-S7-1500", "target": "Siemens-ET200SP", "protocol": "profinet"},
    {"source": "Siemens-HMI", "target": "Siemens-S7-1200", "protocol": "profinet"},
    # S7comm flows
    {"source": "SCADA-Server", "target": "Siemens-S7-1500", "protocol": "s7comm"},
    {"source": "SCADA-Server", "target": "Siemens-S7-1200", "protocol": "s7comm"},
]


async def main():
    """Create and run comprehensive test scenario."""
    async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
        # 1. Authenticate
        print("Authenticating...")
        login_resp = await client.post(
            f"{API_BASE}/auth/login",
            json=ADMIN_CREDS,
        )
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.text}")
            sys.exit(1)

        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Authenticated successfully")

        # 2. Create scenario
        print("\nCreating comprehensive vendor test scenario...")
        scenario_data = {
            "name": "Comprehensive Vendor CVE Test v2",
            "description": "Tests all major vendors with full fingerprints for Cyber Vision detection",
            "vertical": "manufacturing",
            "total_duration_ms": 120000,  # 2 minutes
        }

        create_resp = await client.post(
            f"{API_BASE}/scenarios",
            json=scenario_data,
            headers=headers,
        )
        if create_resp.status_code != 200:
            print(f"Failed to create scenario: {create_resp.text}")
            sys.exit(1)

        scenario = create_resp.json()
        scenario_id = scenario["id"]
        print(f"Created scenario: {scenario_id}")

        # 3. Build definition with devices, flows, zones
        print("\nBuilding scenario definition with full fingerprints...")

        # Create zones
        zones = {
            "zone_scada": {
                "id": "zone_scada",
                "name": "SCADA Zone",
                "level": 3,
                "network": {"subnet": "10.100.0.0/24"},
            },
            "zone_control": {
                "id": "zone_control",
                "name": "Control Zone",
                "level": 2,
                "network": {"subnet": "10.100.1.0/24"},
            },
            "zone_field": {
                "id": "zone_field",
                "name": "Field Zone",
                "level": 1,
                "network": {"subnet": "10.100.2.0/24"},
            },
        }

        # Assign devices to zones and IPs
        devices = {}
        device_name_to_id = {}
        ip_offset = {"zone_scada": 10, "zone_control": 10, "zone_field": 10}
        mac_counter = 1

        for i, dev_spec in enumerate(DEVICES):
            device_id = f"device_{i+1:03d}"
            device_name_to_id[dev_spec["name"]] = device_id

            # Determine zone based on role
            role = dev_spec.get("role", "field_device")
            if role in ["scada", "hmi"]:
                zone_id = "zone_scada"
                subnet_base = "10.100.0"
            elif role in ["controller", "gateway"]:
                zone_id = "zone_control"
                subnet_base = "10.100.1"
            else:
                zone_id = "zone_field"
                subnet_base = "10.100.2"

            ip_addr = f"{subnet_base}.{ip_offset[zone_id]}"
            ip_offset[zone_id] += 1

            # Generate unique MAC addresses
            mac_addr = f"00:1A:2B:{mac_counter:02X}:{(mac_counter*3) % 256:02X}:{(mac_counter*7) % 256:02X}"
            mac_counter += 1

            device = {
                "id": device_id,
                "name": dev_spec["name"],
                "type": dev_spec["type"],
                "vendor": dev_spec.get("vendor"),
                "fingerprintModel": dev_spec.get("fingerprint_model"),
                "protocols": dev_spec.get("protocols", []),
                "role": role,
                "zoneId": zone_id,
                "network": {
                    "ipAddress": ip_addr,
                    "subnetMask": "255.255.255.0",
                    "gateway": f"{subnet_base}.1",
                    "macAddress": mac_addr,
                },
                # CRITICAL: Include the full vendor fingerprint!
                "vendorFingerprint": dev_spec.get("vendor_fingerprint", {}),
            }

            # Add CVE IDs if specified
            if dev_spec.get("cve_ids"):
                device["cveIds"] = dev_spec["cve_ids"]

            devices[device_id] = device

        # Build flows
        flows = {}
        for i, flow_spec in enumerate(FLOWS):
            flow_id = f"flow_{i+1:03d}"
            source_id = device_name_to_id.get(flow_spec["source"])
            target_id = device_name_to_id.get(flow_spec["target"])

            if not source_id or not target_id:
                print(f"Warning: Could not find device for flow {flow_spec}")
                continue

            flows[flow_id] = {
                "id": flow_id,
                "sourceDeviceId": source_id,
                "targetDeviceId": target_id,
                "protocol": flow_spec["protocol"],
                "timing": {
                    "intervalMs": 1000,
                },
                "protocolConfig": {
                    "function_code": 3 if flow_spec["protocol"] == "modbus_tcp" else None,
                    "start_address": 0,
                    "quantity": 10,
                    "send_device_id_request": True,  # Enable Modbus FC 43
                },
            }

        # Create phases
        phases = [
            {
                "id": "startup",
                "name": "Startup",
                "duration_pct": 10,
                "traffic_multiplier": 0.5,
            },
            {
                "id": "normal",
                "name": "Normal Operation",
                "duration_pct": 70,
                "traffic_multiplier": 1.0,
            },
            {
                "id": "discovery",
                "name": "Discovery Burst",
                "duration_pct": 10,
                "traffic_multiplier": 2.0,
            },
            {
                "id": "shutdown",
                "name": "Shutdown",
                "duration_pct": 10,
                "traffic_multiplier": 0.3,
            },
        ]

        definition = {
            "devices": devices,
            "flows": flows,
            "zones": zones,
            "phases": phases,
        }

        # 4. Update scenario with definition
        print("Updating scenario definition...")
        update_resp = await client.put(
            f"{API_BASE}/scenarios/{scenario_id}",
            json={
                "name": scenario_data["name"],
                "description": scenario_data["description"],
                "definition": definition,
                "total_duration_ms": scenario_data["total_duration_ms"],
            },
            headers=headers,
        )
        if update_resp.status_code != 200:
            print(f"Failed to update scenario: {update_resp.text}")
            sys.exit(1)

        print(f"Scenario updated with {len(devices)} devices and {len(flows)} flows")

        # 5. Print summary
        print("\n" + "="*60)
        print("SCENARIO SUMMARY")
        print("="*60)
        print(f"Scenario ID: {scenario_id}")
        print(f"Duration: 2 minutes")
        print(f"\nDevices ({len(devices)}):")

        vendors = {}
        protocols_used = set()
        cve_count = 0

        for dev in devices.values():
            vendor = dev.get("vendor", "Generic")
            if vendor not in vendors:
                vendors[vendor] = []
            vendors[vendor].append(dev["name"])
            protocols_used.update(dev.get("protocols", []))
            if dev.get("cveIds"):
                cve_count += len(dev["cveIds"])

        for vendor, devs in sorted(vendors.items()):
            print(f"  {vendor}: {', '.join(devs)}")

        print(f"\nProtocols: {', '.join(sorted(protocols_used))}")
        print(f"Total CVEs: {cve_count}")

        print(f"\nFlows ({len(flows)}):")
        protocol_flows = {}
        for flow in flows.values():
            proto = flow["protocol"]
            if proto not in protocol_flows:
                protocol_flows[proto] = 0
            protocol_flows[proto] += 1

        for proto, count in sorted(protocol_flows.items()):
            print(f"  {proto}: {count} flows")

        # 6. Deploy to Docker host
        print("\n" + "="*60)
        print("DEPLOYING TO TRAFFIC INJECTOR")
        print("="*60)

        deploy_resp = await client.post(
            f"{API_BASE}/deployments",
            json={
                "scenario_id": scenario_id,
                "docker_host_id": DOCKER_HOST_ID,
                "network_interface": NETWORK_INTERFACE,
            },
            headers=headers,
        )
        if deploy_resp.status_code != 200:
            print(f"Failed to deploy scenario: {deploy_resp.text}")
            sys.exit(1)

        deployment = deploy_resp.json()
        deployment_id = deployment["id"]
        print(f"Deployment started: {deployment_id}")
        print(f"Container: {deployment.get('container_name')}")
        print(f"Interface: {NETWORK_INTERFACE}")
        print(f"Status: {deployment.get('status')}")

        print(f"\n>>> Monitor in Cisco Cyber Vision at: https://10.10.20.115")
        print(f"\nThe scenario will run for 2 minutes generating traffic from:")
        print(f"  - {len(vendors)} vendors (Rockwell, Siemens, Schneider, ABB, Honeywell, GE)")
        print(f"  - {len(protocols_used)} protocols (EtherNet/IP, Modbus TCP, PROFINET, S7)")
        print(f"  - {cve_count} CVE-vulnerable device configurations")

        return scenario_id, deployment_id


if __name__ == "__main__":
    scenario_id, deployment_id = asyncio.run(main())
    print(f"\nTest scenario created and running")
    print(f"  Scenario ID: {scenario_id}")
    print(f"  Deployment ID: {deployment_id}")
