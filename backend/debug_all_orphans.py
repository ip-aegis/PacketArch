"""Debug all orphaned device types across all templates."""
import requests

BASE_URL = "http://localhost:8001/api/v1"

TEMPLATES = [
    {"vertical": "water_wastewater", "template_name": "water_treatment"},
    {"vertical": "water_wastewater", "template_name": "wastewater_collection"},
    {"vertical": "water_wastewater", "template_name": "distribution_network"},
    {"vertical": "energy_power", "template_name": "transmission_substation"},
    {"vertical": "energy_power", "template_name": "distribution_feeder"},
    {"vertical": "energy_power", "template_name": "generation_plant"},
    {"vertical": "oil_gas", "template_name": "pipeline_scada"},
    {"vertical": "oil_gas", "template_name": "offshore_platform"},
    {"vertical": "oil_gas", "template_name": "refinery_unit"},
    {"vertical": "oil_gas", "template_name": "gas_gathering"},
]


def main():
    # Login
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "changeme123"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for template in TEMPLATES:
        vertical = template["vertical"]
        name = template["template_name"]

        # Create scenario
        create_resp = requests.post(
            f"{BASE_URL}/templates/create",
            headers=headers,
            json={
                "vertical": vertical,
                "template_name": name,
                "scenario_name": f"Debug_{name}",
            }
        )

        if create_resp.status_code not in (200, 201):
            print(f"\n{name}: FAILED TO CREATE")
            continue

        data = create_resp.json()
        scenario_id = data["scenario_id"]

        # Get full scenario
        scenario_resp = requests.get(f"{BASE_URL}/scenarios/{scenario_id}", headers=headers)
        scenario = scenario_resp.json()

        definition = scenario.get("definition", {})
        devices = definition.get("devices", {})
        flows = definition.get("flows", {})

        # Find which devices have flows
        devices_with_flows = set()
        for flow in flows.values():
            source = flow.get("sourceDeviceId")
            target = flow.get("targetDeviceId")
            if source:
                devices_with_flows.add(source)
            if target:
                devices_with_flows.add(target)

        # Find orphans by type
        orphans_by_type = {}
        for device_id, device in devices.items():
            if device_id not in devices_with_flows:
                dtype = device.get("type", "unknown")
                orphans_by_type[dtype] = orphans_by_type.get(dtype, 0) + 1

        # Get all device types
        device_types = set(d.get("type") for d in devices.values())

        print(f"\n{'='*60}")
        print(f"{name}")
        print(f"{'='*60}")
        print(f"Device types: {sorted(device_types)}")
        if orphans_by_type:
            print(f"Orphans: {orphans_by_type}")
        else:
            print("No orphans!")

        # Clean up
        requests.delete(f"{BASE_URL}/scenarios/{scenario_id}", headers=headers)


if __name__ == "__main__":
    main()
