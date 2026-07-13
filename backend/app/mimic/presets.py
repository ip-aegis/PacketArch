# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Ready-to-deploy persona presets.

Each preset is a validated device (or small cell) the Mimic UI can deploy onto a
lab with one click — a Schneider Modbus PLC, a Siemens OPC UA PLC, a BACnet
building controller, an IEC-104 RTU, or an HMI↔PLC pair. Full per-device authoring
(custom point maps, process bindings) is the Mimic Studio canvas; presets make the
proven configurations one-click while that's built.

Presets carry placeholder ``device_id``/``scenario_id`` — the caller uniquifies
them per deployment so multiple cells can run the same preset.
"""

from __future__ import annotations

from .interfaces import ClientBinding, PersonaSpec, PointBinding, ProtocolBinding


def _tank_modbus_points() -> list[PointBinding]:
    return [
        PointBinding(space="holding", address=0, source="variable", variable="level", scale=100.0),
        PointBinding(space="holding", address=1, source="variable", variable="temperature", scale=100.0),
        PointBinding(space="holding", address=2, source="variable", variable="inflow", scale=100.0),
        PointBinding(space="coil", address=0, source="actuator", writable=True,
                     write_target="inflow", write_true_value=8.0, write_false_value=0.0),
    ]


def _tank_named_points() -> list[PointBinding]:
    return [
        PointBinding(space="", address=0, source="variable", variable="level", name="Level"),
        PointBinding(space="", address=1, source="variable", variable="temperature", name="Temperature"),
        PointBinding(space="", address=2, source="variable", variable="inflow", name="Inflow"),
        PointBinding(space="", address=3, source="actuator", name="PumpCommand", writable=True,
                     write_target="inflow", write_true_value=8.0, write_false_value=0.0),
    ]


def _tank_iec104_points() -> list[PointBinding]:
    return [
        PointBinding(space="", address=11, source="variable", variable="level"),
        PointBinding(space="", address=12, source="variable", variable="temperature"),
        PointBinding(space="", address=21, source="actuator", writable=True,
                     write_target="inflow", write_true_value=8.0, write_false_value=0.0),
    ]


def _tank_control_points() -> list[PointBinding]:
    # Holding register 3 is the writable LEVEL SETPOINT — writing it moves the
    # PI-controlled process, as an operator would (not a raw pump toggle).
    return [
        PointBinding(space="holding", address=0, source="variable", variable="level", scale=100.0),
        PointBinding(space="holding", address=1, source="variable", variable="temperature", scale=100.0),
        PointBinding(space="holding", address=2, source="variable", variable="inflow", scale=100.0),
        PointBinding(space="holding", address=3, source="variable", variable="setpoint", scale=100.0,
                     writable=True, write_target="setpoint"),
    ]


def _controlled_plc() -> PersonaSpec:
    return PersonaSpec(
        device_id="ctrl-plc", scenario_id="mimic", name="Level_Control_PLC",
        template_id="schneider/modicon-m580/bmep584040", process_model_id="tank_level_control",
        protocols=[ProtocolBinding(protocol="modbus", port=502, points=_tank_control_points())],
    )


def _modbus_plc() -> PersonaSpec:
    return PersonaSpec(
        device_id="modbus-plc", scenario_id="mimic", name="Tank_Farm_PLC",
        template_id="schneider/modicon-m580/bmep584040", process_model_id="tank_level",
        protocols=[ProtocolBinding(protocol="modbus", port=502, points=_tank_modbus_points())],
    )


def _opcua_plc() -> PersonaSpec:
    return PersonaSpec(
        device_id="opcua-plc", scenario_id="mimic", name="Reactor_PLC",
        template_id="siemens/s7-1500/cpu-1516-3", process_model_id="tank_level",
        protocols=[ProtocolBinding(protocol="opcua", port=4840, points=_tank_named_points())],
    )


def _bacnet_controller() -> PersonaSpec:
    return PersonaSpec(
        device_id="bacnet-ctrl", scenario_id="mimic", name="Zone_Room_Controller",
        template_id="siemens/desigo/dxr2", process_model_id="tank_level",
        protocols=[ProtocolBinding(protocol="bacnet", port=47808, points=_tank_named_points())],
    )


def _iec104_rtu() -> PersonaSpec:
    return PersonaSpec(
        device_id="iec104-rtu", scenario_id="mimic", name="Substation_RTU",
        template_id="schneider/modicon-m580/bmep584040", process_model_id="tank_level",
        protocols=[ProtocolBinding(protocol="iec104", port=2404, unit_id=1, points=_tank_iec104_points())],
    )


def _hmi_plc_pair() -> list[PersonaSpec]:
    plc = _modbus_plc()
    plc.device_id, plc.name = "pair-plc", "Line1_PLC"
    hmi = PersonaSpec(
        device_id="pair-hmi", scenario_id="mimic", name="Line1_Operator_HMI",
        template_id="schneider/magelis/hmigto5310",
        clients=[ClientBinding(protocol="modbus", target_device="pair-plc", port=502, interval_s=2.0)],
    )
    return [plc, hmi]


# key -> (name, description, personas)
_PRESETS: dict[str, tuple[str, str, list[PersonaSpec]]] = {
    "controlled-plc": ("Controlled PLC — Level Setpoint", "Schneider M580 running a PI level-control loop; write the setpoint register to move the process, which tracks it and rejects disturbances.", [_controlled_plc()]),
    "modbus-plc": ("Modbus PLC — Tank Loop", "Schneider Modicon M580 answering Modbus TCP, live tank process.", [_modbus_plc()]),
    "opcua-plc": ("OPC UA PLC — Tank Loop", "Siemens S7-1500 OPC UA server, live tank process.", [_opcua_plc()]),
    "bacnet-controller": ("BACnet Controller — Tank Loop", "Siemens Desigo DXR2 room controller on BACnet/IP.", [_bacnet_controller()]),
    "iec104-rtu": ("IEC-104 RTU — Tank Loop", "Substation RTU answering IEC 60870-5-104 telecontrol.", [_iec104_rtu()]),
    "hmi-plc-pair": ("HMI + PLC pair", "A Modbus PLC and a Magelis HMI that actively polls it — a live conversation.", _hmi_plc_pair()),
}


def list_presets() -> list[dict]:
    """Preset catalog for the UI (personas serialized to the deploy schema)."""
    return [
        {"key": key, "name": name, "description": desc,
         "personas": [p.to_dict() for p in personas]}
        for key, (name, desc, personas) in _PRESETS.items()
    ]
