# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for the local sensor lab routes.

The host-agent file-queue is patched so these tests never touch a real shared
volume or Docker — they exercise the route/service/DB layer only. Both the route
and the service do `from app.services import host_agent_client`, so patching the
attributes on that module covers both call sites. The Cyber Vision API is
likewise faked — `local_sensor_service` talks to it via `cv_service_from_settings`,
patched to return an in-memory fake instead of a real httpx-backed client.
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.local_lab import LocalLab
from app.models.traffic_agent import TrafficAgent

_HAC = "app.services.host_agent_client"
_LSS = "app.services.local_sensor_service"


class FakeCyberVisionService:
    """Minimal stand-in for CyberVisionService's auto-provisioning surface."""

    def __init__(self):
        self.deleted_sensor_ids: list[str] = []
        self.closed = False

    async def create_deployment_token(self, name: str) -> dict:
        return {"name": name, "usageCount": 1, "maxUsageCount": 100}

    async def mint_sensor_jwt(self, deployment_name: str, serial: str) -> str:
        return f"fake-jwt-for-{serial}"

    def sensor_image_ref(self) -> str:
        return "10.0.0.5:443/sensor"

    async def find_sensor_by_serial(self, serial: str) -> dict | None:
        return {"id": "sensor-uuid-1", "serialNumber": serial}

    async def delete_sensor(self, sensor_id: str) -> None:
        self.deleted_sensor_ids.append(sensor_id)

    async def close(self) -> None:
        self.closed = True


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


@contextmanager
def fake_cyber_vision(configured: bool = True):
    """Patch `cv_service_from_settings` to return a FakeCyberVisionService (or
    None, simulating "Cyber Vision isn't configured")."""
    fake = FakeCyberVisionService() if configured else None
    with patch(f"{_LSS}.cv_service_from_settings", AsyncMock(return_value=fake)):
        yield fake


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
    """Build auto-provisions via the (faked) CV API, mints an agent token, and
    persists LocalLab + agent."""
    with fake_host_agent() as hac, fake_cyber_vision():
        resp = await client.post(
            "/api/v1/local-sensor/build",
            headers=admin_auth_headers,
            json={"name": "Test Lab"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["agent_token"]  # shown once
    assert body["sensor_serial"]
    assert body["slug"]
    hac["build"].assert_called_once()

    lab = (
        await db_session.execute(select(LocalLab).where(LocalLab.name == "Test Lab"))
    ).scalar_one()
    assert lab.sensor_serial == body["sensor_serial"]
    assert "SERIAL_NUMBER=" in lab.sensor_compose
    assert "PROVISIONING_TOKEN=" in lab.sensor_compose
    agent = (
        await db_session.execute(
            select(TrafficAgent).where(TrafficAgent.local_lab_id == str(lab.id))
        )
    ).scalar_one()
    assert agent.default_interface == lab.gen_if


async def test_build_rejects_when_cv_not_configured(
    client: AsyncClient, admin_auth_headers: dict
):
    """No Cyber Vision connection configured -> 400 ValidationError."""
    with fake_host_agent(), fake_cyber_vision(configured=False):
        resp = await client.post(
            "/api/v1/local-sensor/build",
            headers=admin_auth_headers,
            json={"name": "Bad Lab"},
        )
    assert resp.status_code == 400


async def test_list_then_teardown(
    client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession
):
    """A built lab lists, then teardown full-deletes the lab + its agent (and
    best-effort deletes the CV sensor object)."""
    with fake_host_agent() as hac, fake_cyber_vision() as cv:
        build = await client.post(
            "/api/v1/local-sensor/build",
            headers=admin_auth_headers,
            json={"name": "Cycle Lab"},
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
    assert cv.deleted_sensor_ids == ["sensor-uuid-1"]

    remaining = (
        await db_session.execute(select(LocalLab).where(LocalLab.name == "Cycle Lab"))
    ).scalar_one_or_none()
    assert remaining is None
