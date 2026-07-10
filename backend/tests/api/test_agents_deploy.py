# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for deploying a scenario to a brand-new, dedicated Local Sensor Lab.

Covers the new `POST /agents/deploy-new-lab` route (auto-provisions via the
faked CV API + host-agent, same fakes as test_local_sensor.py) and the
`agent_manager.resolve_pending_deploy` auto-fire-on-connect path, tested
directly rather than through a real websocket connection.
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.local_lab import LocalLab
from app.models.scenario import Scenario
from app.models.traffic_agent import AgentDeployment, TrafficAgent
from app.services.agent_manager import agent_manager

_HAC = "app.services.host_agent_client"
_LSS = "app.services.local_sensor_service"
_AM = "app.services.agent_manager"


class FakeCyberVisionService:
    """Minimal stand-in for CyberVisionService's auto-provisioning surface
    (mirrors test_local_sensor.py's fake — this flow calls the same methods)."""

    def __init__(self):
        self.deleted_sensor_ids: list[str] = []

    async def create_deployment_token(self, name: str) -> dict:
        return {"name": name, "usageCount": 1, "maxUsageCount": 100}

    async def mint_sensor_jwt(self, deployment_name: str, serial: str) -> str:
        return f"fake-jwt-for-{serial}"

    def sensor_image_ref(self) -> str:
        return "10.0.0.5:443/sensor"

    async def find_sensor_by_serial(self, serial: str) -> dict | None:
        return None

    async def delete_sensor(self, sensor_id: str) -> None:
        self.deleted_sensor_ids.append(sensor_id)

    async def close(self) -> None:
        pass


@contextmanager
def fake_host_agent():
    with (
        patch(f"{_HAC}.is_available", return_value=True),
        patch(f"{_HAC}.submit_build", return_value="req-build"),
        patch(f"{_HAC}.submit_teardown", return_value="req-teardown"),
        patch(f"{_HAC}.read_status", return_value=None),
    ):
        yield


@contextmanager
def fake_cyber_vision():
    with patch(f"{_LSS}.cv_service_from_settings", AsyncMock(return_value=FakeCyberVisionService())):
        yield


async def _make_scenario(db_session: AsyncSession, test_user) -> Scenario:
    scenario = Scenario(
        user_id=test_user.id,
        name="Test Deploy Scenario",
        vertical="manufacturing",
        total_duration_ms=60000,
        definition={"devices": {}, "flows": {}},
    )
    db_session.add(scenario)
    await db_session.commit()
    await db_session.refresh(scenario)
    return scenario


async def test_deploy_new_lab_creates_pending_deploy(
    client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, test_user,
):
    """POST /agents/deploy-new-lab auto-provisions a lab and stores a pending
    deploy on the new agent — it does NOT deploy immediately."""
    scenario = await _make_scenario(db_session, test_user)

    with fake_host_agent(), fake_cyber_vision():
        resp = await client.post(
            "/api/v1/agents/deploy-new-lab",
            headers=admin_auth_headers,
            json={"scenario_id": str(scenario.id), "lab_name": "Deploy Test Lab"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["agent_id"]
    assert "automatically" in body["message"]

    lab = (
        await db_session.execute(select(LocalLab).where(LocalLab.name == "Deploy Test Lab"))
    ).scalar_one()
    agent = (
        await db_session.execute(select(TrafficAgent).where(TrafficAgent.id == lab.agent_id))
    ).scalar_one()
    assert str(agent.pending_deploy_scenario_id) == str(scenario.id)
    assert agent.pending_deploy_config is not None

    # No deployment has been created/fired yet.
    deployments = (
        await db_session.execute(
            select(AgentDeployment).where(AgentDeployment.agent_id == agent.id)
        )
    ).scalars().all()
    assert deployments == []


async def test_deploy_new_lab_requires_cv_configured(
    client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, test_user,
):
    scenario = await _make_scenario(db_session, test_user)
    with fake_host_agent(), patch(f"{_LSS}.cv_service_from_settings", AsyncMock(return_value=None)):
        resp = await client.post(
            "/api/v1/agents/deploy-new-lab",
            headers=admin_auth_headers,
            json={"scenario_id": str(scenario.id), "lab_name": "No CV Lab"},
        )
    assert resp.status_code == 400


async def test_resolve_pending_deploy_fires_and_clears(
    db_engine, db_session: AsyncSession, test_user,
):
    """Simulates the moment a lab-created agent's websocket connects: a
    pending deploy fires (AgentDeployment created, agent_manager.deploy_scenario
    called) and the pending fields are cleared so it can never re-fire."""
    scenario = await _make_scenario(db_session, test_user)

    agent = TrafficAgent(
        name="pending-deploy-agent",
        token_hash="x" * 64,
        default_interface="pa-gen-test",
        pending_deploy_scenario_id=scenario.id,
        pending_deploy_config={
            "interface": None,
            "adaptive_config": None,
            "attack_playbook": None,
            "cell_isolation_override": None,
            "provision_cyber_vision": False,
        },
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    # resolve_pending_deploy opens its OWN session via async_session_maker —
    # point that at a sibling session on the same (in-memory, single-connection)
    # test engine so it sees the same data, and stub the actual websocket send.
    test_session_maker = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    with (
        patch(f"{_AM}.async_session_maker", test_session_maker),
        patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=True)) as deploy_mock,
    ):
        await agent_manager.resolve_pending_deploy(agent.id)

    deploy_mock.assert_called_once()
    call_kwargs = deploy_mock.call_args.kwargs
    assert call_kwargs["agent_id"] == agent.id
    assert call_kwargs["scenario_id"] == str(scenario.id)

    await db_session.refresh(agent)
    assert agent.pending_deploy_scenario_id is None
    assert agent.pending_deploy_config is None

    deployment = (
        await db_session.execute(
            select(AgentDeployment).where(AgentDeployment.agent_id == agent.id)
        )
    ).scalar_one()
    assert deployment.scenario_id == scenario.id


async def test_resolve_pending_deploy_noop_when_nothing_pending(
    db_engine, db_session: AsyncSession,
):
    agent = TrafficAgent(
        name="no-pending-agent",
        token_hash="y" * 64,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    test_session_maker = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    with (
        patch(f"{_AM}.async_session_maker", test_session_maker),
        patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=True)) as deploy_mock,
    ):
        await agent_manager.resolve_pending_deploy(agent.id)

    deploy_mock.assert_not_called()
