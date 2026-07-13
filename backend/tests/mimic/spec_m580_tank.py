# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Reference P0 persona spec: a Schneider Modicon M580 driving a tank loop.

Shared by the pytest gate and the manual/on-box demo so both exercise the same
device. Holding registers project the live tank variables; coil 0 is the pump —
writing it feeds back into the model and moves the level.
"""

from __future__ import annotations

from app.mimic.interfaces import PersonaSpec, PointBinding, ProtocolBinding

TEMPLATE_ID = "schneider/modicon-m580/bmep584040"


def build_spec(*, bind_ip: str = "127.0.0.1", port: int = 15020, unit_id: int = 1) -> PersonaSpec:
    points = [
        PointBinding(space="holding", address=0, source="variable", variable="level", scale=100.0),
        PointBinding(space="holding", address=1, source="variable", variable="temperature", scale=100.0),
        PointBinding(space="holding", address=2, source="variable", variable="inflow", scale=100.0),
        PointBinding(space="holding", address=3, source="variable", variable="outflow", scale=100.0),
        # Pump coil: write-back drives the tank inflow (on → fill, off → drain).
        PointBinding(
            space="coil",
            address=0,
            source="actuator",
            writable=True,
            write_target="inflow",
            write_true_value=8.0,
            write_false_value=0.0,
        ),
    ]
    return PersonaSpec(
        device_id="p0-m580-001",
        scenario_id="p0-mimic",
        name="Tank_Farm_PLC_01",
        template_id=TEMPLATE_ID,
        bind_ip=bind_ip,
        process_model_id="tank_level",
        protocols=[ProtocolBinding(protocol="modbus", port=port, unit_id=unit_id, points=points)],
        step_interval_ms=100.0,
    )
