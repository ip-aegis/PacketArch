# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Batch process all training PCAP files through the learning pipeline."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import httpx


API_BASE = "http://localhost:8001"
TRAINING_DIR = Path(__file__).parent / "training_pcaps"

# Map directories to industry verticals
VERTICAL_MAP = {
    "dnp3": "energy",
    "s7comm": "manufacturing",
    "modbus": "manufacturing",
    "ethernetip": "manufacturing",
    "profinet": "manufacturing",
    "mixed": None,
}


async def get_auth_token() -> str:
    """Get authentication token."""
    async with httpx.AsyncClient() as client:
        # Try to login with pcap processor credentials
        response = await client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"username": "pcap_processor", "password": "pcapprocess123"},
        )
        if response.status_code == 200:
            return response.json()["access_token"]

        # Try registering if login fails
        response = await client.post(
            f"{API_BASE}/api/v1/auth/register",
            json={
                "username": "pcap_processor",
                "email": "pcap@processor.net",
                "password": "pcapprocess123",
            },
        )
        if response.status_code in (200, 201):
            # Login after register
            response = await client.post(
                f"{API_BASE}/api/v1/auth/login",
                json={"username": "pcap_processor", "password": "pcapprocess123"},
            )
            return response.json()["access_token"]

        raise Exception(f"Could not authenticate: {response.text}")


async def upload_pcap(
    client: httpx.AsyncClient,
    file_path: Path,
    token: str,
    vertical: str | None,
) -> dict:
    """Upload a single PCAP file."""
    headers = {"Authorization": f"Bearer {token}"}

    # Build query params
    params = {}
    if vertical:
        params["industry_vertical"] = vertical
    params["description"] = f"Training PCAP: {file_path.name}"
    params["source_environment"] = "training_data"

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/octet-stream")}
        response = await client.post(
            f"{API_BASE}/api/v1/learning/pcap/upload",
            files=files,
            params=params,
            headers=headers,
            timeout=300.0,  # 5 minute timeout for large files
        )

    return response.status_code, response.json() if response.status_code < 500 else {"error": response.text}


async def process_all_pcaps():
    """Process all training PCAPs."""
    print("=" * 60)
    print("PacketArch Training PCAP Processor")
    print("=" * 60)

    # Get auth token
    print("\nAuthenticating...")
    try:
        token = await get_auth_token()
        print("  Authentication successful")
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    # Find all PCAP files
    pcap_files = []
    for ext in ["*.pcap", "*.pcapng", "*.cap"]:
        pcap_files.extend(TRAINING_DIR.rglob(ext))

    print(f"\nFound {len(pcap_files)} PCAP files to process")

    # Group by protocol
    by_protocol = {}
    for pcap in pcap_files:
        # Get protocol from first directory level
        rel_path = pcap.relative_to(TRAINING_DIR)
        protocol = rel_path.parts[0] if rel_path.parts else "unknown"
        by_protocol.setdefault(protocol, []).append(pcap)

    print("\nBreakdown by protocol:")
    for proto, files in sorted(by_protocol.items()):
        print(f"  {proto}: {len(files)} files")

    # Process each protocol
    results = {"success": 0, "failed": 0, "skipped": 0}

    async with httpx.AsyncClient() as client:
        for protocol, files in sorted(by_protocol.items()):
            print(f"\n{'=' * 40}")
            print(f"Processing {protocol.upper()} ({len(files)} files)")
            print("=" * 40)

            vertical = VERTICAL_MAP.get(protocol)

            for i, pcap_file in enumerate(files, 1):
                print(f"\n[{i}/{len(files)}] {pcap_file.name}")

                # Check file size
                size_mb = pcap_file.stat().st_size / (1024 * 1024)
                if size_mb > 100:
                    print(f"  SKIPPED: File too large ({size_mb:.1f} MB)")
                    results["skipped"] += 1
                    continue

                try:
                    status, response = await upload_pcap(client, pcap_file, token, vertical)

                    if status in (200, 201):
                        capture_id = response.get("id", "unknown")
                        print(f"  SUCCESS: Uploaded (ID: {capture_id[:8]}...)")
                        results["success"] += 1
                    elif status == 409:
                        print("  SKIPPED: Already exists")
                        results["skipped"] += 1
                    else:
                        print(f"  FAILED: {status} - {response.get('detail', response)}")
                        results["failed"] += 1

                except Exception as e:
                    print(f"  ERROR: {e}")
                    results["failed"] += 1

                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.5)

    # Summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"  Successful: {results['success']}")
    print(f"  Failed:     {results['failed']}")
    print(f"  Skipped:    {results['skipped']}")
    print(f"  Total:      {sum(results.values())}")


if __name__ == "__main__":
    asyncio.run(process_all_pcaps())
