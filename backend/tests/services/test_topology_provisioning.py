# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Unit tests for topology provisioning service + live conductor output."""

import pytest

from app.services import local_sensor_service, topology_provisioning_service as tps


def _def() -> dict:
    return {
        "zones": {
            "z-cell": {"id": "z-cell", "name": "Cell", "level": 1,
                       "network": {"subnet": "10.5.1.0/24", "gateway": "10.5.1.1", "vlan": 101}},
            "z-ops": {"id": "z-ops", "name": "Ops", "level": 3,
                      "network": {"subnet": "10.5.3.0/24", "gateway": "10.5.3.1", "vlan": 103}},
        },
        "devices": {
            "plc1": {"id": "plc1", "zoneId": "z-cell",
                     "network": {"ipAddress": "10.5.1.10", "macAddress": "00:0e:8c:11:11:11"}},
            "hmi1": {"id": "hmi1", "zoneId": "z-ops",
                     "network": {"ipAddress": "10.5.3.10", "macAddress": "00:0e:8c:33:33:33"}},
        },
        "flows": {"f1": {"id": "f1", "sourceDeviceId": "hmi1", "targetDeviceId": "plc1", "protocol": "s7comm"}},
    }


class _FakeScn:
    def __init__(self, sid, definition):
        self.id = sid
        self.definition = definition


@pytest.fixture
def patched(monkeypatch):
    sid = "abcdef12-0000-0000-0000-000000000000"
    scn = _FakeScn(sid, _def())

    async def fake_load(db, scenario_id):
        return scn

    built = []
    labs_store = []

    async def fake_build_lab(db, *, name, agent_name, created_by_id, sensor_label=None):
        slug = f"slug{len(built)}"
        rec = {
            "lab_id": f"lab-{len(built)}", "slug": slug,
            "agent_id": f"agent-{len(built)}", "agent_token": "tok",
            "sensor_serial": f"ser-{len(built)}", "state": "provisioning",
        }
        built.append((name, rec))
        labs_store.append({"lab_id": rec["lab_id"], "name": name, "slug": slug,
                           "gen_if": f"pa-gen-{slug}", "state": "running"})
        return rec

    async def fake_list_labs(db):
        return list(labs_store)

    torn = []

    async def fake_teardown_lab(db, lab_id):
        torn.append(lab_id)
        return {"success": True}

    # status() reads the conductor AgentDeployment state; teardown() stops the
    # conductor + removes the deployment row. Mock those infra deps out.
    state = {"deployment_state": None}

    async def fake_deployment_state(db, scenario_id):
        return state["deployment_state"]

    # Pending-intent persistence (system_settings rows) + task arming: an
    # in-memory stand-in so deploy()/status()/teardown() logic runs for real.
    pending: dict[str, dict] = {}
    armed: list[str] = []

    async def fake_get_pending(db, scenario_id):
        return pending.get(scenario_id)

    async def fake_set_pending(db, scenario_id, provision_cyber_vision):
        pending[scenario_id] = {"provision_cyber_vision": provision_cyber_vision}

    async def fake_clear_pending(db, scenario_id):
        pending.pop(scenario_id, None)

    def fake_arm_deploy(scenario_id, provision_cyber_vision):
        armed.append(scenario_id)

    monkeypatch.setattr(tps, "_load_scenario", fake_load)
    monkeypatch.setattr(tps, "_deployment_state", fake_deployment_state)
    monkeypatch.setattr(tps, "_get_pending", fake_get_pending)
    monkeypatch.setattr(tps, "_set_pending", fake_set_pending)
    monkeypatch.setattr(tps, "_clear_pending", fake_clear_pending)
    monkeypatch.setattr(tps, "_arm_deploy", fake_arm_deploy)
    monkeypatch.setattr(local_sensor_service, "build_lab", fake_build_lab)
    monkeypatch.setattr(local_sensor_service, "list_labs", fake_list_labs)
    monkeypatch.setattr(local_sensor_service, "teardown_lab", fake_teardown_lab)

    from types import SimpleNamespace

    return SimpleNamespace(
        sid=sid, built=built, torn=torn,
        pending=pending, armed=armed, state=state,
    )


class _FakeDB:
    """Minimal async db stub for teardown's stop + AgentDeployment delete."""

    async def execute(self, *_a, **_k):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


class TestProvisioning:
    async def test_preflight_counts(self, patched):
        sid = patched.sid
        pf = await tps.preflight(None, sid)
        assert pf["sensor_count"] == 3  # 2 zones + core
        assert pf["ram_estimate_gb"] == round(3 * 1.26, 2)
        assert set(pf["spans"]) == {"zone:z-cell", "zone:z-ops", "core"}
        assert pf["has_core"] is True

    async def test_provision_builds_one_lab_per_span(self, patched):
        sid, built = patched.sid, patched.built
        res = await tps.provision(None, sid)
        assert res["sensor_count"] == 3
        assert len(built) == 3
        # every span mapped to an injection interface
        assert set(res["span_interface_map"]) == {"zone:z-cell", "zone:z-ops", "core"}
        for span, iface in res["span_interface_map"].items():
            assert iface.startswith("pa-gen-")
        # core member flagged
        roles = {m["span_id"]: m["role"] for m in res["members"]}
        assert roles["core"] == "core"
        assert roles["zone:z-cell"] == "zone"
        # names grouped by prefix
        prefix = tps.group_prefix(sid)
        assert all(name.startswith(prefix) for name, _ in built)

    async def test_provision_refuses_duplicate(self, patched):
        sid = patched.sid
        await tps.provision(None, sid)
        with pytest.raises(Exception) as ei:
            await tps.provision(None, sid)
        assert "already exists" in str(ei.value)

    async def test_status_filters_by_prefix(self, patched):
        sid = patched.sid
        await tps.provision(None, sid)
        st = await tps.status(None, sid)
        assert st["sensor_count"] == 3

    async def test_teardown_tears_down_all_members(self, patched, monkeypatch):
        sid, torn = patched.sid, patched.torn
        from app.services.agent_manager import agent_manager

        async def fake_stop(scenario_id):
            return True

        monkeypatch.setattr(agent_manager, "stop_scenario", fake_stop)
        await tps.provision(None, sid)
        res = await tps.teardown(_FakeDB(), sid)
        assert len(res["torn_down"]) == 3
        assert all(r["ok"] for r in res["torn_down"])
        assert len(torn) == 3

    async def test_deploy_provisions_persists_intent_and_arms(self, patched):
        p = patched
        res = await tps.deploy(None, p.sid)
        assert res["deploy_pending"] is True
        assert res["sensor_count"] == 3
        assert len(p.built) == 3
        assert p.sid in p.pending
        assert p.armed == [p.sid]

    async def test_deploy_resumes_when_labs_exist_without_conductor(self, patched):
        """Labs provisioned but conductor never went live (old give-up timeout,
        or backend restart) — deploy() must resume, not refuse."""
        p = patched
        await tps.provision(None, p.sid)
        res = await tps.deploy(None, p.sid)
        assert res["deploy_pending"] is True
        assert res["sensor_count"] == 3
        assert len(p.built) == 3  # no second provisioning pass
        assert set(res["span_interface_map"]) == {"zone:z-cell", "zone:z-ops", "core"}
        assert p.sid in p.pending
        assert p.armed == [p.sid]

    async def test_deploy_refuses_when_conductor_live(self, patched):
        p = patched
        await tps.provision(None, p.sid)
        p.state["deployment_state"] = "running"
        with pytest.raises(Exception) as ei:
            await tps.deploy(None, p.sid)
        assert "already live" in str(ei.value)

    async def test_teardown_clears_pending_intent(self, patched, monkeypatch):
        p = patched
        from app.services.agent_manager import agent_manager

        async def fake_stop(scenario_id):
            return True

        monkeypatch.setattr(agent_manager, "stop_scenario", fake_stop)
        await tps.deploy(None, p.sid)
        assert p.sid in p.pending
        await tps.teardown(_FakeDB(), p.sid)
        assert p.sid not in p.pending


class TestLiveTopologyOutput:
    def test_injects_reframed_copies_per_span_socket(self, monkeypatch):
        from app.protocol_engines import output as out_mod
        from app.services.topology_planner import derive_topology, plan_segments
        from scapy.layers.inet import IP, TCP
        from scapy.layers.l2 import Ether

        plan = derive_topology(_def(), seed="s")
        plan = plan_segments(_def(), plan).as_dict()

        sent: dict[str, list[bytes]] = {}

        class FakeSock:
            def __init__(self, iface):
                self.iface = iface
                sent.setdefault(iface, [])
            def send(self, data):
                sent[self.iface].append(bytes(data))
            def close(self):
                pass

        monkeypatch.setattr("scapy.arch.L2Socket", FakeSock, raising=False)

        ifmap = {"zone:z-cell": "pa-gen-a", "zone:z-ops": "pa-gen-b", "core": "pa-gen-c"}
        sink = out_mod.LiveTopologyOutput(plan, ifmap)

        # a cross-zone frame (hmi1 -> plc1) should hit all three sockets
        frame = bytes(Ether(src="00:0e:8c:33:33:33", dst="00:0e:8c:11:11:11")
                      / IP(src="10.5.3.10", dst="10.5.1.10", ttl=64) / TCP(sport=5000, dport=102))
        sink.write_packet(frame, 0.0, flow_id="f1")
        sink.close()

        assert len(sent["pa-gen-b"]) == 1  # source zone (near side)
        assert len(sent["pa-gen-a"]) == 1  # target zone (far side)
        assert len(sent["pa-gen-c"]) == 2  # core carries both framings
        assert sink.packet_count == 4
