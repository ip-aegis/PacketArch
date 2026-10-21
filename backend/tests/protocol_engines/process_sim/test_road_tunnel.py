# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Road tunnel process model: control behaviour and fault persistence."""

from __future__ import annotations

import random

import pytest

from app.protocol_engines.process_sim.templates import build_from_vertical
from app.protocol_engines.process_sim.templates import road_tunnel as rt


def _run(seconds: int, fault: str | None = None, at: int = 0):
    random.seed(7)
    model = rt.build_model()
    faults = {f.name: f for f in rt.build_faults()}
    models = {"t": model}
    switches, prev = 0, 0.0
    for t in range(1, seconds + 1):
        model.step(1.0)
        if fault and t == at:
            faults[fault].activate(t * 1000.0)
        for f in faults.values():
            f.step(models, t * 1000.0)
        running = model.get_value("pump_running")
        if running != prev:
            switches, prev = switches + 1, running
    return model, switches


def test_registered_as_a_scenario_process_model():
    models, faults = build_from_vertical("road_tunnel")
    assert models and {f.name for f in faults} == {
        "jet_fan_trip", "drainage_pump_failure", "incident_congestion",
    }


def test_steady_state_ventilation_holds_co_below_the_control_level():
    model, _ = _run(1800)
    assert 10.0 < model.get_value("co_ppm") < rt.CO_CONTROL_PPM
    assert 20.0 < model.get_value("jet_fan_speed") < 90.0


def test_sump_pump_cycles_on_its_level_band_without_chatter():
    # About one start/stop pair every few minutes; a stateless threshold
    # would toggle on almost every tick near the start level.
    _, switches = _run(3600)
    assert 6 <= switches <= 60


@pytest.mark.parametrize("fault,variable,check", [
    ("jet_fan_trip", "co_ppm", lambda v: v > 100.0),
    ("drainage_pump_failure", "sump_level", lambda v: v > 90.0),
])
def test_faults_persist_past_the_next_tick(fault, variable, check):
    # Faults trip model inputs; one that set a computed variable would be
    # recomputed away on the following tick.
    model, _ = _run(1800 + 900, fault=fault, at=1800)
    assert check(model.get_value(variable))


def test_incident_congestion_raises_fan_demand():
    base, _ = _run(2400)
    incident, _ = _run(2400, fault="incident_congestion", at=1200)
    assert incident.get_value("jet_fan_speed") > base.get_value("jet_fan_speed") + 5.0


@pytest.mark.parametrize("protocol", ["MODBUS_TCP", "S7COMM", "ETHERNET_IP"])
def test_tunnel_values_reach_protocol_slots_by_name(protocol):
    """Each slot carries the variable its profile was cloned from, in the
    slot's encoding, instead of whichever variable came first positionally."""
    from app.protocol_engines.payload_defaults import create_default_payload_generator
    from app.protocol_engines.process_sim.binder import VariableBinder
    from app.protocol_engines.types import ProtocolType

    gen = create_default_payload_generator(ProtocolType[protocol], {}, vertical="road_tunnel")
    model = rt.build_model()
    for _ in range(600):
        model.step(1.0)
    binder = VariableBinder.auto_bind({"t": model}, {"f": gen})
    binder.push_values({"t": model}, {"f": gen})

    checked = 0
    for name, profile in gen.profiles.items():
        assert profile.source in model.variables, name
        expected = model.get_value(profile.source) * profile.source_scale
        assert gen.states[name].current_value == pytest.approx(
            max(profile.min_value, min(profile.max_value, expected)))
        checked += 1
    assert checked
