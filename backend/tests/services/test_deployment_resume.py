# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Tests for replaying deployments an agent lost while it was away.

`AgentManager.resume_disconnected_deployments` is the DB-backed successor of
the health monitor's in-memory redeploy list. It must survive a backend
restart / host reboot (the row IS the intent), must not touch rows the agent
still reports running (that is the sync path's job), must never replay the
same row twice, and must carry the original deploy options back.
"""

from datetime import datetime, timedelta, timezone
from itertools import count
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.scenario import Scenario
from app.models.traffic_agent import AgentDeployment, TrafficAgent
from app.services.agent_manager import agent_manager
from app.services.health_monitor import health_monitor

_AM = "app.services.agent_manager"
_TPS = "app.services.topology_provisioning_service"


async def _scenario(db: AsyncSession, user, name: str) -> Scenario:
    s = Scenario(
        user_id=user.id,
        name=name,
        vertical="manufacturing",
        total_duration_ms=60000,
        definition={"devices": {}, "flows": {}},
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _agent(db: AsyncSession, name: str) -> TrafficAgent:
    a = TrafficAgent(name=name, token_hash=name.ljust(64, "x"), default_interface="eth0")
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


_tick = count()


async def _row(db: AsyncSession, agent, scenario, state="disconnected", **kw) -> AgentDeployment:
    # Explicit, strictly increasing started_at: sqlite's CURRENT_TIMESTAMP has
    # one-second resolution, so rows created back-to-back would otherwise tie
    # on the "most recent row per scenario" ordering the resume path relies on.
    started = datetime(2026, 9, 11, tzinfo=timezone.utc) + timedelta(seconds=next(_tick))
    r = AgentDeployment(
        agent_id=agent.id, scenario_id=scenario.id, state=state, started_at=started, **kw
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def _rows(db: AsyncSession, agent_id, scenario_id) -> list[AgentDeployment]:
    db.expire_all()
    res = await db.execute(
        select(AgentDeployment)
        .where(AgentDeployment.agent_id == agent_id, AgentDeployment.scenario_id == scenario_id)
        .order_by(AgentDeployment.started_at)
    )
    return list(res.scalars())


@pytest.fixture
def sibling_session_maker(db_engine):
    # The resume path opens its OWN session — point it at the in-memory test engine.
    return sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


async def test_lost_row_is_replayed_with_its_deploy_options(
    db_engine, db_session, test_user, sibling_session_maker
):
    scenario = await _scenario(db_session, test_user, "Lost")
    agent = await _agent(db_session, "agent-a")
    lost = await _row(
        db_session, agent, scenario,
        interface="pa-gen-a",
        deploy_config={"adaptive_config": {"phase": "steady"}, "attack_playbook": {"id": "pb1"}},
    )
    agent_id, scenario_id, lost_id = agent.id, scenario.id, lost.id

    with (
        patch(f"{_AM}.async_session_maker", sibling_session_maker),
        patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=True)) as deploy,
        patch(f"{_AM}.asyncio.sleep", AsyncMock()),
    ):
        n = await agent_manager.resume_disconnected_deployments(agent_id, [])

    assert n == 1
    deploy.assert_called_once()
    kw = deploy.call_args.kwargs
    assert kw["agent_id"] == agent_id
    assert kw["scenario_id"] == str(scenario_id)
    assert kw["interface"] == "pa-gen-a"
    # The original options rode along into the injected definition.
    assert kw["definition"]["adaptive_config"] == {"phase": "steady"}
    assert kw["definition"]["attack_playbook"] == {"id": "pb1"}

    rows = await _rows(db_session, agent_id, scenario_id)
    assert len(rows) == 2
    old, new = rows[0], rows[1]
    assert old.id == lost_id and old.state == "stopped" and old.stopped_at is not None
    assert new.state == "starting" and new.interface == "pa-gen-a"
    # The fresh row carries the options forward, so a second loss replays them too.
    assert new.deploy_config["adaptive_config"] == {"phase": "steady"}

    # Recorded as a health event.
    kinds = [e.event_type.value for e in health_monitor.get_events()]
    assert "recovery_succeeded" in kinds


async def test_scenario_the_agent_still_runs_is_left_alone(
    db_engine, db_session, test_user, sibling_session_maker
):
    scenario = await _scenario(db_session, test_user, "Still running")
    agent = await _agent(db_session, "agent-b")
    await _row(db_session, agent, scenario)
    agent_id, scenario_id = agent.id, scenario.id

    with (
        patch(f"{_AM}.async_session_maker", sibling_session_maker),
        patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=True)) as deploy,
    ):
        n = await agent_manager.resume_disconnected_deployments(agent_id, [str(scenario_id)])

    assert n == 0
    deploy.assert_not_called()
    rows = await _rows(db_session, agent_id, scenario_id)
    assert len(rows) == 1 and rows[0].state == "disconnected"


async def test_second_heartbeat_does_not_replay_twice(
    db_engine, db_session, test_user, sibling_session_maker
):
    scenario = await _scenario(db_session, test_user, "Once")
    agent = await _agent(db_session, "agent-c")
    await _row(db_session, agent, scenario)

    with (
        patch(f"{_AM}.async_session_maker", sibling_session_maker),
        patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=True)) as deploy,
        patch(f"{_AM}.asyncio.sleep", AsyncMock()),
    ):
        assert await agent_manager.resume_disconnected_deployments(agent.id, []) == 1
        # Agent hasn't reported the new one running yet — still nothing to replay:
        # the newest row is 'starting', not 'disconnected'.
        assert await agent_manager.resume_disconnected_deployments(agent.id, []) == 0

    assert deploy.call_count == 1


async def test_only_the_newest_row_per_scenario_counts(
    db_engine, db_session, test_user, sibling_session_maker
):
    """An older disconnected row under a newer stopped one is history, not intent."""
    scenario = await _scenario(db_session, test_user, "Superseded")
    agent = await _agent(db_session, "agent-d")
    await _row(db_session, agent, scenario, state="disconnected")
    await _row(db_session, agent, scenario, state="stopped")

    with (
        patch(f"{_AM}.async_session_maker", sibling_session_maker),
        patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=True)) as deploy,
    ):
        assert await agent_manager.resume_disconnected_deployments(agent.id, []) == 0
    deploy.assert_not_called()


async def test_flag_off_disables_resume(db_engine, db_session, test_user, sibling_session_maker):
    scenario = await _scenario(db_session, test_user, "Flag off")
    agent = await _agent(db_session, "agent-e")
    await _row(db_session, agent, scenario)

    health_monitor.config.auto_redeploy_on_reconnect = False
    try:
        with (
            patch(f"{_AM}.async_session_maker", sibling_session_maker),
            patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=True)) as deploy,
        ):
            assert await agent_manager.resume_disconnected_deployments(agent.id, []) == 0
    finally:
        health_monitor.config.auto_redeploy_on_reconnect = True
    deploy.assert_not_called()


async def test_topology_conductor_goes_back_through_topology_service(
    db_engine, db_session, test_user, sibling_session_maker
):
    scenario = await _scenario(db_session, test_user, "Topology")
    agent = await _agent(db_session, "agent-f")
    await _row(db_session, agent, scenario, deploy_config={"topology": True})
    agent_id, scenario_id = agent.id, scenario.id

    with (
        patch(f"{_AM}.async_session_maker", sibling_session_maker),
        patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=True)) as deploy,
        patch(f"{_TPS}.deploy", AsyncMock(return_value={"deploy_pending": True})) as topo,
        patch(f"{_AM}.asyncio.sleep", AsyncMock()),
    ):
        assert await agent_manager.resume_disconnected_deployments(agent_id, []) == 1

    deploy.assert_not_called()
    topo.assert_called_once()
    assert topo.call_args.args[1] == str(scenario_id)
    assert topo.call_args.kwargs == {"provision_cyber_vision": False}
    rows = await _rows(db_session, agent_id, scenario_id)
    assert rows[0].state == "stopped"


async def test_failed_replay_is_recorded_not_raised(
    db_engine, db_session, test_user, sibling_session_maker
):
    scenario = await _scenario(db_session, test_user, "Fails")
    agent = await _agent(db_session, "agent-g")
    await _row(db_session, agent, scenario)
    agent_id, scenario_id = agent.id, scenario.id

    with (
        patch(f"{_AM}.async_session_maker", sibling_session_maker),
        patch.object(agent_manager, "deploy_scenario", AsyncMock(return_value=False)),
        patch(f"{_AM}.asyncio.sleep", AsyncMock()),
    ):
        assert await agent_manager.resume_disconnected_deployments(agent_id, []) == 0

    rows = await _rows(db_session, agent_id, scenario_id)
    assert [r.state for r in rows] == ["stopped", "error"]
    kinds = [e.event_type.value for e in health_monitor.get_events()]
    assert "recovery_failed" in kinds
