#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""
Direct script to enrich Cyber Vision devices with PacketArch scenario data.
Bypasses the UI and preset issues - uses main device IDs directly.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.scenario import Scenario
from app.models.settings import SystemSetting
from app.core.encryption import decrypt_value


async def get_cv_settings(session: AsyncSession) -> dict:
    """Get CV connection settings from database."""
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key.in_([
            "cyber_vision_url",
            "cyber_vision_api_token",
            "cyber_vision_verify_ssl"
        ]))
    )
    settings = {}
    for s in result.scalars().all():
        if s.key == "cyber_vision_api_token" and s.value:
            # Token is stored encrypted
            settings[s.key] = decrypt_value(s.value)
        else:
            settings[s.key] = s.value
    return settings


async def get_all_scenarios(session: AsyncSession) -> list:
    """Get all scenarios from database."""
    result = await session.execute(select(Scenario))
    return list(result.scalars().all())


async def get_cv_devices(client: httpx.AsyncClient, base_url: str) -> list:
    """Fetch ALL devices from CV main endpoint (not preset)."""
    all_devices = []
    page = 1
    page_size = 100

    while True:
        response = await client.get(
            f"{base_url}/api/3.0/devices",
            params={"page": page, "size": page_size}
        )
        response.raise_for_status()
        data = response.json()

        devices = data if isinstance(data, list) else data.get("items", [])
        all_devices.extend(devices)

        print(f"  Fetched page {page}: {len(devices)} devices")

        if len(devices) < page_size:
            break
        page += 1

        if page > 100:  # Safety limit
            break

    return all_devices


async def add_device_property(
    client: httpx.AsyncClient,
    base_url: str,
    device_id: str,
    label: str,
    value: str,
    debug: bool = False
) -> tuple[bool, str]:
    """Add a property to a CV device. Returns (success, status)."""
    try:
        response = await client.post(
            f"{base_url}/api/3.0/devices/{device_id}/usersProperties",
            json={"label": label[:60], "value": value[:180]}
        )
        if debug:
            print(f"      DEBUG add_property: {response.status_code} {response.text[:100]}")
        # CV returns 200 or 201 on success
        if response.status_code in (200, 201):
            return True, "added"
        elif response.status_code == 409:
            # Property already exists
            return False, "exists"
        else:
            return False, f"error:{response.status_code}"
    except Exception as e:
        return False, f"exception:{e}"


async def get_device_existing_properties(
    client: httpx.AsyncClient,
    base_url: str,
    device_id: str
) -> set:
    """Get existing property labels for a device.
    Note: CV API GET /devices/{id}/usersProperties returns 404, so this is disabled.
    """
    # CV API doesn't support reading user properties via GET, so we skip this check
    # Properties will be added/updated regardless
    return set()


async def main():
    print("=" * 60)
    print("CV Device Enrichment Script")
    print("=" * 60)

    # Connect to database (use 'postgres' hostname when running in Docker)
    import os
    import urllib.parse
    db_host = os.environ.get("DB_HOST", "postgres")
    db_password = urllib.parse.quote_plus(os.environ.get("POSTGRES_PASSWORD", "PacketArch_Prod_2024!"))
    db_url = f"postgresql+asyncpg://packetarch:{db_password}@{db_host}:5432/packetarch"
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get CV settings
        print("\n[1] Getting CV connection settings...")
        settings = await get_cv_settings(session)

        cv_url = settings.get("cyber_vision_url", "")
        cv_token = settings.get("cyber_vision_api_token", "")
        verify_ssl = settings.get("cyber_vision_verify_ssl", "false").lower() == "true"

        if not cv_url or not cv_token:
            print("ERROR: CV URL or token not configured in settings!")
            print(f"  cv_url: '{cv_url}'")
            print(f"  cv_token: '{cv_token[:20]}...' (length: {len(cv_token)})" if cv_token else "  cv_token: EMPTY")
            return

        print(f"  CV URL: {cv_url}")
        print(f"  Token length: {len(cv_token)}")
        print(f"  Verify SSL: {verify_ssl}")

        # Get all scenarios
        print("\n[2] Loading PacketArch scenarios...")
        scenarios = await get_all_scenarios(session)
        print(f"  Found {len(scenarios)} scenarios")

        # Build MAC/IP -> scenario device mapping
        scenario_devices_by_mac = {}
        scenario_devices_by_ip = {}

        for scenario in scenarios:
            definition = scenario.definition or {}
            devices = definition.get("devices", {})

            for dev_id, device in devices.items():
                network = device.get("network", {})
                mac = network.get("macAddress", "")
                ip = network.get("ipAddress", "")

                if mac:
                    norm_mac = mac.lower().replace("-", ":").replace(".", ":")
                    scenario_devices_by_mac[norm_mac] = device

                if ip:
                    scenario_devices_by_ip[ip] = device

        print(f"  Built lookup: {len(scenario_devices_by_mac)} MACs, {len(scenario_devices_by_ip)} IPs")

    # Connect to CV API
    print("\n[3] Connecting to Cyber Vision...")

    async with httpx.AsyncClient(
        verify=verify_ssl,
        headers={"x-token-id": cv_token},
        timeout=30.0
    ) as client:
        # Test connection - just try to get devices
        try:
            response = await client.get(f"{cv_url}/api/3.0/devices", params={"size": 1})
            response.raise_for_status()
            print("  Connected to CV successfully!")
        except Exception as e:
            print(f"  ERROR connecting to CV: {e}")
            return

        # Get all CV devices (main endpoint, not preset)
        print("\n[4] Fetching CV devices from main endpoint...")
        cv_devices = await get_cv_devices(client, cv_url)
        print(f"  Total CV devices: {len(cv_devices)}")

        # Match and enrich
        print("\n[5] Matching and enriching devices...")

        matched = 0
        enriched = 0
        properties_added = 0

        for cv_device in cv_devices:
            cv_id = cv_device.get("id", "")
            cv_name = cv_device.get("label", cv_device.get("name", "Unknown"))

            # Get CV device MAC/IP
            cv_macs = cv_device.get("mac", [])
            cv_ips = cv_device.get("ip", [])

            if isinstance(cv_macs, str):
                cv_macs = [cv_macs] if cv_macs else []
            if isinstance(cv_ips, str):
                cv_ips = [cv_ips] if cv_ips else []

            # Try to find matching scenario device
            scenario_device = None
            match_type = ""

            for mac in cv_macs:
                norm_mac = mac.lower().replace("-", ":").replace(".", ":")
                if norm_mac in scenario_devices_by_mac:
                    scenario_device = scenario_devices_by_mac[norm_mac]
                    match_type = f"MAC:{mac}"
                    break

            if not scenario_device:
                for ip in cv_ips:
                    if ip in scenario_devices_by_ip:
                        scenario_device = scenario_devices_by_ip[ip]
                        match_type = f"IP:{ip}"
                        break

            if not scenario_device:
                continue

            matched += 1

            # Build properties to push
            properties = {}

            # Vendor
            vendor = scenario_device.get("vendor")
            if vendor:
                properties["Vendor"] = vendor

            # Model
            model = scenario_device.get("fingerprintModel") or scenario_device.get("model")
            if model:
                properties["Model"] = model

            # Device Type
            dev_type = scenario_device.get("type")
            if dev_type:
                properties["Device Type"] = dev_type

            # Role
            role = scenario_device.get("role")
            if role:
                properties["Role"] = role

            # Protocols
            protocols = scenario_device.get("protocols", [])
            if protocols:
                properties["Protocols"] = ", ".join(protocols) if isinstance(protocols, list) else str(protocols)

            # Hostname
            network = scenario_device.get("network", {})
            hostname = network.get("hostname")
            if hostname:
                properties["Hostname"] = hostname

            if not properties:
                continue

            print(f"\n  [{matched}] {cv_name} (ID: {cv_id}) - matched by {match_type}")
            print(f"      Properties to add: {list(properties.keys())}")

            # Add properties (CV API doesn't support reading existing, so we just add)
            added_count = 0
            debug_first = (matched == 1)  # Debug first device
            for label, value in properties.items():
                success, status = await add_device_property(client, cv_url, cv_id, label, value, debug=debug_first)
                if success:
                    print(f"      + {label}: {value}")
                    added_count += 1
                    properties_added += 1
                elif status == "exists":
                    print(f"      = {label}: already exists")
                else:
                    print(f"      ! {label}: {status}")

            if added_count > 0:
                enriched += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  CV devices scanned: {len(cv_devices)}")
    print(f"  Matched to scenarios: {matched}")
    print(f"  Devices enriched: {enriched}")
    print(f"  Properties added: {properties_added}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
