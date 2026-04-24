# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Test all scenario templates for proper device-flow coverage."""
import requests
import sys

BASE_URL = "http://localhost:8001/api/v1"

# All template configurations to test
TEMPLATES = [
    # Manufacturing (Siemens)
    {"vertical": "manufacturing", "template_name": "discrete_manufacturing"},
    {"vertical": "manufacturing", "template_name": "automotive_assembly"},
    {"vertical": "manufacturing", "template_name": "packaging_line"},
    # Water/Wastewater (Schneider)
    {"vertical": "water_wastewater", "template_name": "water_treatment"},
    {"vertical": "water_wastewater", "template_name": "wastewater_collection"},
    {"vertical": "water_wastewater", "template_name": "distribution_network"},
    # Energy/Power (Rockwell)
    {"vertical": "energy_power", "template_name": "transmission_substation"},
    {"vertical": "energy_power", "template_name": "distribution_feeder"},
    {"vertical": "energy_power", "template_name": "generation_plant"},
    # Oil & Gas (Schneider)
    {"vertical": "oil_gas", "template_name": "pipeline_scada"},
    {"vertical": "oil_gas", "template_name": "offshore_platform"},
    {"vertical": "oil_gas", "template_name": "refinery_unit"},
    {"vertical": "oil_gas", "template_name": "gas_gathering"},
    # Distribution & Logistics (Mixed vendors)
    {"vertical": "distribution_logistics", "template_name": "fulfillment_center"},
    {"vertical": "distribution_logistics", "template_name": "distribution_center"},
    {"vertical": "distribution_logistics", "template_name": "cold_chain_warehouse"},
    {"vertical": "distribution_logistics", "template_name": "parcel_sorting_hub"},
]


def main():
    # Login
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "C!sco123"}
    )
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.json()}")
        sys.exit(1)

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    results = []
    created_scenarios = []

    for template in TEMPLATES:
        vertical = template["vertical"]
        name = template["template_name"]
        scenario_name = f"Test_{name}"

        print(f"\n{'='*60}")
        print(f"Testing: {vertical} / {name}")
        print(f"{'='*60}")

        # Create scenario from template
        create_resp = requests.post(
            f"{BASE_URL}/templates/create",
            headers=headers,
            json={
                "vertical": vertical,
                "template_name": name,
                "scenario_name": scenario_name,
                "description": f"Test scenario for {name}",
            }
        )

        if create_resp.status_code not in (200, 201):
            print(f"  FAILED to create: {create_resp.status_code}")
            print(f"  Error: {create_resp.text}")
            results.append({
                "template": name,
                "status": "CREATE_FAILED",
                "error": create_resp.text
            })
            continue

        create_data = create_resp.json()
        scenario_id = create_data["scenario_id"]
        created_scenarios.append(scenario_id)

        print(f"  Created: {scenario_id}")
        print(f"  Devices: {create_data['device_count']}, Flows: {create_data['flow_count']}")

        # Validate the scenario
        validate_resp = requests.get(
            f"{BASE_URL}/scenarios/{scenario_id}/validate",
            headers=headers
        )

        if validate_resp.status_code != 200:
            print(f"  FAILED to validate: {validate_resp.status_code}")
            results.append({
                "template": name,
                "status": "VALIDATE_FAILED",
                "error": validate_resp.text
            })
            continue

        val_data = validate_resp.json()
        warnings = val_data.get("warnings", [])

        # Count warnings by type
        by_code = {}
        for w in warnings:
            code = w["code"]
            by_code[code] = by_code.get(code, 0) + 1

        is_valid = val_data["is_valid"]
        orphan_count = by_code.get("orphan_device", 0)

        status = "PASS" if is_valid and orphan_count == 0 else "WARN" if is_valid else "FAIL"

        print(f"  Valid: {is_valid}")
        print(f"  Warnings: {len(warnings)}")
        if by_code:
            for code, count in sorted(by_code.items()):
                print(f"    - {code}: {count}")

        results.append({
            "template": name,
            "vertical": vertical,
            "status": status,
            "is_valid": is_valid,
            "device_count": create_data["device_count"],
            "flow_count": create_data["flow_count"],
            "warning_count": len(warnings),
            "orphan_count": orphan_count,
            "warnings_by_type": by_code,
        })

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    pass_count = sum(1 for r in results if r.get("status") == "PASS")
    warn_count = sum(1 for r in results if r.get("status") == "WARN")
    fail_count = sum(1 for r in results if r.get("status") in ("FAIL", "CREATE_FAILED", "VALIDATE_FAILED"))

    print(f"PASS: {pass_count}, WARN: {warn_count}, FAIL: {fail_count}")
    print()

    for r in results:
        status = r.get("status", "UNKNOWN")
        template = r.get("template", "?")
        if status == "PASS":
            print(f"  [PASS] {template}: {r.get('device_count', 0)} devices, {r.get('flow_count', 0)} flows")
        elif status == "WARN":
            print(f"  [WARN] {template}: {r.get('orphan_count', 0)} orphan devices")
        else:
            print(f"  [FAIL] {template}: {r.get('error', status)[:50]}")

    # Clean up test scenarios
    print(f"\nCleaning up {len(created_scenarios)} test scenarios...")
    for sid in created_scenarios:
        requests.delete(f"{BASE_URL}/scenarios/{sid}", headers=headers)

    print("Done!")

    # Exit with error if any failures
    if fail_count > 0 or warn_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
