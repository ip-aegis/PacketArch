# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Flagship roadway templates: what is authored is what gets created."""

from __future__ import annotations

from collections import Counter

import pytest

from app.api.routes.scenarios import compute_scenario_readiness
from app.scenario_templates.transportation_flagships import FLAGSHIP_TEMPLATES
from app.services.template_audit import audit_irrational_flows
from app.services.template_definition_builder import populate_definition_from_template

FLAGSHIPS = sorted(FLAGSHIP_TEMPLATES)


def _values(collection):
    return list(collection.values()) if isinstance(collection, dict) else list(collection)


@pytest.fixture(scope="module", params=FLAGSHIPS)
def built(request):
    return request.param, populate_definition_from_template("transportation", request.param)


def test_every_authored_device_is_created(built):
    name, definition = built
    authored = sum(d.get("count", 1) for d in FLAGSHIP_TEMPLATES[name]["devices"])
    assert len(_values(definition["devices"])) == authored


def test_repair_passes_rewrite_no_flow(built):
    # A rewritten flow means the template says one thing and the scenario does
    # another (e.g. an NTCIP poll silently turned into an HTTPS session).
    _, definition = built
    repaired = [f for f in _values(definition["flows"]) if f.get("auto_protocol_repaired")]
    assert not repaired, [(f["original_protocol"], f["protocol"]) for f in repaired[:5]]


def test_curated_names_survive_and_are_unique(built):
    name, definition = built
    created = [d["name"] for d in _values(definition["devices"])]
    assert len(set(created)) == len(created)
    authored = {d["name"] for d in FLAGSHIP_TEMPLATES[name]["devices"]}
    # Site code prefix + the authored name, never a regenerated one.
    assert all(any(n.endswith("-" + a) for a in authored) for n in created)


def test_readiness_has_no_errors_and_every_flow_is_rational(built):
    _, definition = built
    readiness = compute_scenario_readiness(definition)
    assert readiness.error_count == 0
    assert not [f for f in audit_irrational_flows(definition) if f.severity == "warning"]


def test_ntcip_pollers_speak_snmp_to_signals_and_signs(built):
    _, definition = built
    devices = {d["id"]: d for d in _values(definition["devices"])}
    to_ntcip = Counter(
        f["protocol"]
        for f in _values(definition["flows"])
        if devices[f["targetDeviceId"]]["type"] in {"traffic_controller", "dms", "weather_station"}
    )
    assert to_ntcip and set(to_ntcip) == {"snmp"}


def test_tunnel_runs_its_own_process_model():
    definition = populate_definition_from_template("transportation", "twin_bore_road_tunnel")
    assert definition["process_sim"] == {"enabled": True, "vertical": "road_tunnel"}


def test_firmware_pins_carry_their_cves():
    definition = populate_definition_from_template("transportation", "metro_arterial_signal_system")
    cves = Counter(c for d in _values(definition["devices"]) for c in d.get("cveIds", []))
    assert cves["CVE-2023-0451"] == 3       # three Cobalt cabinets on EOS 3.2.20
    assert cves["CVE-2021-31986"] == 2      # two cameras on AXIS OS 10.6.0
    assert cves["CVE-2025-1100"] == 6       # every MAXTIME controller (<= 2.11.0, no fix)
