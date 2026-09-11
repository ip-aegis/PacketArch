# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""GET /admin/site-config (Settings > Overview).

v1.19.0 put the list of Cyber Vision centers into the CV card's ``detail``,
which is a flat key -> scalar map. The response model rejected it, so the
whole endpoint returned 422 and the Overview tab showed "Could not load site
configuration" as soon as one center existed. Nothing called this route in
tests, so these do, with one center and with two.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import cv_centers


async def _site_config(client: AsyncClient, headers: dict[str, str]) -> dict:
    resp = await client.get("/api/v1/admin/site-config", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for sub in body["subsystems"]:
        for key, value in sub["detail"].items():
            assert value is None or isinstance(value, (str, int, bool)), (
                f"{sub['key']}.detail[{key!r}] is {type(value).__name__}; the "
                f"Overview card renders scalars only"
            )
    return body


def _cv(body: dict) -> dict:
    return next(s for s in body["subsystems"] if s["key"] == "cyber_vision")


@pytest.mark.asyncio
async def test_site_config_loads_with_one_center(
    client: AsyncClient, admin_auth_headers: dict[str, str], cv_center
):
    cv = _cv(await _site_config(client, admin_auth_headers))
    assert cv["status"] == "ok"
    assert cv["detail"]["centers"] == 1
    assert cv["detail"]["default_center"] == cv_center.name
    assert cv["detail"]["api_token_set"] is True


@pytest.mark.asyncio
async def test_site_config_loads_with_two_centers(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_auth_headers: dict[str, str],
    cv_center,
):
    await cv_centers.create_center(
        db_session, name="Plant B", url="https://10.0.0.99", api_token="tok-b"
    )
    await db_session.commit()
    cv = _cv(await _site_config(client, admin_auth_headers))
    assert cv["detail"]["centers"] == 2
    assert "Plant B" in cv["summary"] and cv_center.name in cv["summary"]


@pytest.mark.asyncio
async def test_site_config_loads_with_no_center(
    client: AsyncClient, admin_auth_headers: dict[str, str]
):
    cv = _cv(await _site_config(client, admin_auth_headers))
    assert cv["status"] == "needs_attention"
    assert cv["detail"] == {"centers": 0}
