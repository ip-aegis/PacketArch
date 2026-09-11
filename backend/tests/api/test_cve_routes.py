# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""GET /cve/list and /cve/critical must serialize the whole curated catalog.

Four NVD-verified entries affect every firmware version, so they carry
``affected_firmware_max: None`` (curation rule: never invent a bound). The
response model required a string, so one such entry 422'd the entire list and
the CVE browser loaded nothing.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.cve_data import ALL_CVES


def test_catalog_still_has_unbounded_entries():
    """The case these guards exist for must still be in the data."""
    assert any(c.get("affected_firmware_max") is None for c in ALL_CVES)


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/v1/cve/list", "/api/v1/cve/critical"])
async def test_cve_listing_serializes_every_entry(
    client: AsyncClient, auth_headers: dict[str, str], path: str
):
    resp = await client.get(path, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    if path.endswith("/list"):
        body = resp.json()
        assert len(body) == len(ALL_CVES)
        assert any(c["affected_firmware_max"] is None for c in body)
