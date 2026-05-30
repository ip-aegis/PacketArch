# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for the local sensor lab routes.

The host-agent file-queue is patched so these tests never touch a real shared
volume or Docker — they exercise the route/service/DB layer only. Both the route
and the service do `from app.services import host_agent_client`, so patching the
attributes on that module covers both call sites.
"""

from contextlib import contextmanager
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.local_lab import LocalLab
from app.models.traffic_agent import TrafficAgent

# A minimal but valid CV docker-sensor compose: parse_sensor_compose needs
# image:, SERIAL_NUMBER=, and PROVISIONING_TOKEN= to succeed.
SAMPLE_COMPOSE = """\
services:
  ccv-sensor-1:
    image: 10.0.0.5:443/sensor
    container_name: ccv-sensor-1
    environment:
      - SERIAL_NUMBER=TST01
      - PROVISIONING_TOKEN=eyJhbGciOiJIUzI1NiJ9.eyJzZXJpYWxOdW1iZXIiOiJUU1QwMSJ9.sig
    networks:
      ccv-network-0-collection: {}
      ccv-network-capture-1: {}
networks:
  ccv-network-0-collection:
    driver: bridge
  ccv-network-capture-1:
    driver: macvlan
    driver_opts:
      parent: ens3
"""

_HAC = "app.services.host_agent_client"


@contextmanager
def fake_host_agent(available: bool = True):
    """Patch every host-agent client function the route/service touch."""
    with (
        patch(f"{_HAC}.is_available", return_value=available),
        patch(f"{_HAC}.host_agent_seen", return_value=available),
        patch(f"{_HAC}.read_status", return_value=None),
        patch(f"{_HAC}.submit_build", return_value="req-build") as build,
        patch(f"{_HAC}.submit_teardown", return_value="req-teardown") as teardown,
    ):
        yield {"build": build, "teardown": teardown}


async def test_host_status_unavailable(
    client: AsyncClient, admin_auth_headers: dict
):
    """host-status reflects an unmounted shared volume."""
    with fake_host_agent(available=False):
        resp = await client.get(
            "/api/v1/local-sensor/host-status", headers=admin_auth_headers
        )
    assert resp.status_code == 200
    assert resp.json()["available"] is False


async def test_build_creates_lab_and_agent(
    client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession
):
    """Build parses the compose, mints a token, and persists LocalLab + agent."""
    with fake_host_agent() as hac:
        resp = await client.post(
            "/api/v1/local-sensor/build",
            headers=admin_auth_headers,
            json={"name": "Test Lab", "sensor_compose": SAMPLE_COMPOSE},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["agent_token"]  # shown once
    assert body["sensor_serial"] == "TST01"
    assert body["slug"]
    hac["build"].assert_called_once()

    lab = (
        await db_session.execute(select(LocalLab).where(LocalLab.name == "Test Lab"))
    ).scalar_one()
    assert lab.sensor_serial == "TST01"
    agent = (
        await db_session.execute(
            select(TrafficAgent).where(TrafficAgent.local_lab_id == str(lab.id))
        )
    ).scalar_one()
    assert agent.default_interface == lab.gen_if


async def test_build_rejects_bad_compose(
    client: AsyncClient, admin_auth_headers: dict
):
    """A compose missing the token/serial is a 400 ValidationError."""
    with fake_host_agent():
        resp = await client.post(
            "/api/v1/local-sensor/build",
            headers=admin_auth_headers,
            json={"name": "Bad Lab", "sensor_compose": "services: {}"},
        )
    assert resp.status_code == 400


async def test_list_then_teardown(
    client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession
):
    """A built lab lists, then teardown full-deletes the lab + its agent."""
    with fake_host_agent() as hac:
        build = await client.post(
            "/api/v1/local-sensor/build",
            headers=admin_auth_headers,
            json={"name": "Cycle Lab", "sensor_compose": SAMPLE_COMPOSE},
        )
        lab_id = build.json()["lab_id"]

        listed = await client.get(
            "/api/v1/local-sensor/labs", headers=admin_auth_headers
        )
        assert listed.status_code == 200
        assert any(item["lab_id"] == lab_id for item in listed.json()["items"])

        teardown = await client.post(
            f"/api/v1/local-sensor/{lab_id}/teardown", headers=admin_auth_headers
        )
    assert teardown.status_code == 200
    assert teardown.json()["success"] is True
    hac["teardown"].assert_called_once()

    remaining = (
        await db_session.execute(select(LocalLab).where(LocalLab.name == "Cycle Lab"))
    ).scalar_one_or_none()
    assert remaining is None
