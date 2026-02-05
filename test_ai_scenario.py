#!/usr/bin/env python3
"""Test AI scenario generation via API."""

import requests
import json
import sys

BASE_URL = "http://localhost:8001/api/v1"


def main():
    # Login
    print("Logging in...")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "C!sco123"}
    )
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        sys.exit(1)

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Login successful. Token: {token[:30]}...")

    # Generate scenario preview with AI
    print("\n" + "=" * 70)
    print("GENERATING AI SCENARIO PREVIEW")
    print("=" * 70)

    preview_request = {
        "name": "Automotive Assembly Line",
        "vertical": "manufacturing",
        "description": (
            "A modern automotive assembly line with robotic welding cells, "
            "paint booth controls, and quality inspection stations. The line includes "
            "Siemens S7-1500 PLCs controlling the robotic arms, Rockwell drives for "
            "conveyor systems, and operator HMIs at each station. Include network "
            "infrastructure for the OT network."
        ),
        "total_device_count": 15,
        "duration_ms": 300000,
        "include_vulnerable_devices": False
    }

    print(f"\nRequest:")
    print(json.dumps(preview_request, indent=2))
    print("\n" + "-" * 70)
    print("Calling AI scenario designer (this may take a moment)...")

    resp = requests.post(
        f"{BASE_URL}/ai/scenarios/generate-preview",
        headers=headers,
        json=preview_request,
        timeout=120
    )

    print(f"Response status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"ERROR: {resp.text}")
        sys.exit(1)

    preview = resp.json()

    print(f"\nPREVIEW GENERATED: {preview['preview_id']}")
    print(f"AI Enhanced: {preview['ai_enhanced']}")
    if preview.get('ai_features'):
        print(f"AI Features: {', '.join(preview['ai_features'])}")
    if preview.get('design_rationale'):
        print(f"Design Rationale: {preview['design_rationale'][:300]}...")

    print(f"\n{'='*70}")
    print(f"DEVICES ({preview['device_count']})")
    print("=" * 70)
    for d in preview["devices"]:
        protocols = ", ".join(d.get("protocols", []))
        vendor = d.get("vendor", "N/A") or "N/A"
        ip = d.get("ip_address", "N/A") or "N/A"
        print(f"  [{d['device_type']:10}] {d['name']:35} | {vendor:15} | {ip:15} | {protocols}")

    print(f"\n{'='*70}")
    print(f"FLOWS ({preview['flow_count']})")
    print("=" * 70)
    for i, f in enumerate(preview["flows"]):
        if i >= 15:
            print(f"  ... and {preview['flow_count'] - 15} more flows")
            break
        desc = f["description"][:50] if f.get("description") else ""
        print(f"  {f['source_device_id']:20} -> {f['destination_device_id']:20} | {f['protocol']:12} | {desc}")

    print(f"\n{'='*70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total Devices: {preview['device_count']}")
    print(f"  Total Flows: {preview['flow_count']}")
    print(f"  Protocols Used: {', '.join(preview['protocols_used'])}")
    print(f"  Vendors Used: {', '.join(preview['vendors_used'])}")
    if preview.get('zones'):
        print(f"  Zones: {len(preview['zones'])}")

    # Save preview_id for creating the scenario
    preview_id = preview["preview_id"]
    print(f"\n{'='*70}")
    print("CREATING SCENARIO FROM PREVIEW")
    print("=" * 70)

    create_resp = requests.post(
        f"{BASE_URL}/ai/scenarios/create-from-preview",
        headers=headers,
        json={"preview_id": preview_id},
        timeout=60
    )

    if create_resp.status_code != 200:
        print(f"Create failed: {create_resp.text}")
        sys.exit(1)

    scenario = create_resp.json()
    print(f"\nSCENARIO CREATED!")
    print(f"  ID: {scenario['scenario_id']}")
    print(f"  Name: {scenario['name']}")
    print(f"  Device Count: {scenario['device_count']}")
    print(f"  Flow Count: {scenario['flow_count']}")

    # Now fetch the full scenario to verify all data
    print(f"\n{'='*70}")
    print("VERIFYING SCENARIO DATA")
    print("=" * 70)

    scenario_resp = requests.get(
        f"{BASE_URL}/scenarios/{scenario['scenario_id']}",
        headers=headers
    )

    if scenario_resp.status_code != 200:
        print(f"Fetch failed: {scenario_resp.text}")
        sys.exit(1)

    full_scenario = scenario_resp.json()

    print(f"\nScenario: {full_scenario['name']}")
    print(f"Description: {full_scenario.get('description', 'N/A')[:100]}...")
    print(f"Duration: {full_scenario.get('duration_ms', 0)}ms")
    print(f"Vertical: {full_scenario.get('vertical', 'N/A')}")

    # Check devices have all expected fields
    print(f"\nDEVICE DETAILS:")
    devices = full_scenario.get("devices", [])
    for d in devices[:5]:  # Show first 5
        print(f"\n  Device: {d.get('name')}")
        print(f"    Type: {d.get('device_type')}")
        print(f"    Vendor: {d.get('vendor')}")
        print(f"    Model: {d.get('fingerprint_model')}")
        print(f"    Firmware: {d.get('firmware_version')}")
        print(f"    IP: {d.get('ip_address')}")
        print(f"    MAC: {d.get('mac_address')}")
        print(f"    Protocols: {d.get('protocols')}")
        print(f"    Template ID: {d.get('template_id')}")

    if len(devices) > 5:
        print(f"\n  ... and {len(devices) - 5} more devices")

    # Check flows
    print(f"\nFLOW DETAILS:")
    flows = full_scenario.get("flows", [])
    for f in flows[:5]:
        print(f"  {f.get('source_device_id')} -> {f.get('destination_device_id')} ({f.get('protocol')})")

    # Final verification summary
    print(f"\n{'='*70}")
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    issues = []

    # Check all devices have required fields
    for d in devices:
        if not d.get('vendor'):
            issues.append(f"Device {d.get('name')} missing vendor")
        if not d.get('ip_address'):
            issues.append(f"Device {d.get('name')} missing IP address")
        if not d.get('protocols'):
            issues.append(f"Device {d.get('name')} missing protocols")

    # Check flows reference valid devices
    device_ids = {d.get('device_id') for d in devices}
    for f in flows:
        if f.get('source_device_id') not in device_ids:
            issues.append(f"Flow references unknown source: {f.get('source_device_id')}")
        if f.get('destination_device_id') not in device_ids:
            issues.append(f"Flow references unknown dest: {f.get('destination_device_id')}")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues[:10]:
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more issues")
    else:
        print("ALL CHECKS PASSED!")
        print(f"  - {len(devices)} devices with complete data")
        print(f"  - {len(flows)} flows with valid references")
        print(f"  - Vendors represented: {', '.join(set(d.get('vendor') for d in devices if d.get('vendor')))}")
        print(f"  - Protocols used: {', '.join(set(p for d in devices for p in (d.get('protocols') or [])))}")


if __name__ == "__main__":
    main()
