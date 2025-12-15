"""Debug which devices are orphaned in templates."""
import requests

BASE_URL = "http://localhost:8001/api/v1"

def main():
    # Login
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "changeme123"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test one template
    template = {"vertical": "manufacturing", "template_name": "packaging_line"}

    # Create scenario
    create_resp = requests.post(
        f"{BASE_URL}/templates/create",
        headers=headers,
        json={
            "vertical": template["vertical"],
            "template_name": template["template_name"],
            "scenario_name": "Debug_orphans",
        }
    )

    data = create_resp.json()
    scenario_id = data["scenario_id"]
    print(f"Created scenario: {scenario_id}")

    # Get full scenario
    scenario_resp = requests.get(f"{BASE_URL}/scenarios/{scenario_id}", headers=headers)
    scenario = scenario_resp.json()

    definition = scenario.get("definition", {})
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    # Find which devices have flows
    devices_with_flows = set()
    for flow_id, flow in flows.items():
        source = flow.get("sourceDeviceId")
        target = flow.get("targetDeviceId")
        if source:
            devices_with_flows.add(source)
        if target:
            devices_with_flows.add(target)

    # Find orphans
    print(f"\nTotal devices: {len(devices)}")
    print(f"Devices with flows: {len(devices_with_flows)}")
    print(f"\nOrphaned devices:")

    orphans_by_type = {}
    for device_id, device in devices.items():
        if device_id not in devices_with_flows:
            dtype = device.get("type", "unknown")
            if dtype not in orphans_by_type:
                orphans_by_type[dtype] = []
            orphans_by_type[dtype].append(device.get("name", device_id))

    for dtype, names in sorted(orphans_by_type.items()):
        print(f"  {dtype}: {names}")

    # Check which device types exist and which are in flows
    device_types = set(d.get("type") for d in devices.values())
    flow_source_types = set()
    flow_target_types = set()

    # Read template directly to see flow specs
    print(f"\nDevice types in scenario: {sorted(device_types)}")

    # Clean up
    requests.delete(f"{BASE_URL}/scenarios/{scenario_id}", headers=headers)


if __name__ == "__main__":
    main()
