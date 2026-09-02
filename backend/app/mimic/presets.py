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


# --------------------------------------------------------------------------- #
# Example scenarios — small, realistic multi-device cells across the verticals,
# each backed by a process model so the values are live + controllable. Servers
# use responder templates; the polling client is an HMI/SCADA (software) role.
# Point maps are scaffolded from the process model (same as the Studio canvas).
# --------------------------------------------------------------------------- #

from .scaffold import _PORTS, _scaffold_points  # noqa: E402


def _srv(device_id: str, name: str, template_id: str, model_id: str, protocol: str) -> PersonaSpec:
    return PersonaSpec(
        device_id=device_id, scenario_id="mimic", name=name,
        template_id=template_id, process_model_id=model_id,
        protocols=[ProtocolBinding(protocol=protocol, port=_PORTS[protocol],
                                   points=_scaffold_points(protocol, model_id))],
    )


def _cli(device_id: str, name: str, template_id: str, target_device_id: str,
         protocol: str = "modbus") -> PersonaSpec:
    # The supervisor (HMI/SCADA) actively polls a peer over that peer's NATIVE
    # protocol — Modbus reads, OPC UA browse/read, BACnet Who-Is+ReadProperty, or
    # IEC-104 interrogation — a live master<->outstation conversation CV can see.
    return PersonaSpec(
        device_id=device_id, scenario_id="mimic", name=name, template_id=template_id,
        clients=[ClientBinding(protocol=protocol, target_device=target_device_id,
                               port=_PORTS.get(protocol, 502), interval_s=2.0)],
    )


def _sc_water() -> list[PersonaSpec]:
    return [
        _srv("wp-plc", "Pump_Station_PLC", "schneider/modicon-m580/bmep584040", "pump_station", "modbus"),
        _cli("wp-hmi", "Pump_Operator_HMI", "schneider/magelis/hmigto5310", "wp-plc"),
    ]


def _sc_reactor() -> list[PersonaSpec]:
    return [
        _srv("rx-plc", "Reactor_Control_PLC", "siemens/s7-1500/cpu-1516-3", "chemical_reactor", "opcua"),
        _srv("rx-flow", "Reactor_Feed_FlowMeter", "emerson/micromotion/5700", "chemical_reactor", "modbus"),
        _cli("rx-hmi", "Reactor_HMI", "siemens/hmi/tp1200-comfort", "rx-plc", "opcua"),
    ]


def _sc_compressor() -> list[PersonaSpec]:
    return [
        _srv("cs-plc", "Compressor_Unit_PLC", "schneider/modicon-m580/bmep584040", "compressor_station", "modbus"),
        _cli("cs-scada", "Pipeline_SCADA", "siemens/wincc/professional", "cs-plc"),
    ]


def _sc_substation() -> list[PersonaSpec]:
    return [
        _srv("sub-bay", "Feeder_Bay_Controller", "schneider/micom/c264", "power_feeder", "iec104"),
        _srv("sub-relay", "Feeder_Protection_Relay", "siemens/siprotec/7sj85", "power_feeder", "modbus"),
        _cli("sub-scada", "Substation_SCADA", "siemens/wincc/professional", "sub-bay", "iec104"),
    ]


def _sc_building() -> list[PersonaSpec]:
    return [
        _srv("ahu-ctrl", "AHU_Room_Controller", "siemens/desigo/dxr2", "heat_exchanger", "bacnet"),
        _srv("ahu-meter", "AHU_Power_Meter", "schneider/power/pm8000", "heat_exchanger", "modbus"),
        _cli("ahu-hmi", "Building_HMI", "siemens/hmi/tp1200-comfort", "ahu-ctrl", "bacnet"),
    ]


def _sc_manufacturing() -> list[PersonaSpec]:
    return [
        _srv("mf-plc", "Assembly_Line_PLC", "siemens/s7-1500/cpu-1516-3", "tank_level_control", "opcua"),
        _srv("mf-drive", "Conveyor_VFD_Drive", "siemens/drives/g120c", "pump_station", "modbus"),
        _cli("mf-hmi", "Line_Operator_HMI", "schneider/magelis/hmigto5310", "mf-plc", "opcua"),
    ]


# key -> (name, description, personas)
_PRESETS: dict[str, tuple[str, str, list[PersonaSpec]]] = {
    "controlled-plc": ("Controlled PLC — Level Setpoint", "Schneider M580 running a PI level-control loop; write the setpoint register to move the process, which tracks it and rejects disturbances.", [_controlled_plc()]),
    "modbus-plc": ("Modbus PLC — Tank Loop", "Schneider Modicon M580 answering Modbus TCP, live tank process.", [_modbus_plc()]),
    "opcua-plc": ("OPC UA PLC — Tank Loop", "Siemens S7-1500 OPC UA server, live tank process.", [_opcua_plc()]),
    "bacnet-controller": ("BACnet Controller — Tank Loop", "Siemens Desigo DXR2 room controller on BACnet/IP.", [_bacnet_controller()]),
    "iec104-rtu": ("IEC-104 RTU — Tank Loop", "Substation RTU answering IEC 60870-5-104 telecontrol.", [_iec104_rtu()]),
    "hmi-plc-pair": ("HMI + PLC pair", "A Modbus PLC and a Magelis HMI that actively polls it — a live conversation.", _hmi_plc_pair()),
    # --- Example scenarios (multi-device cells) ---
    "scenario-water-pump": ("Scenario: Water Pump Station", "Water/wastewater — a Schneider M580 pump-station PLC running a PI discharge-pressure loop (VFD holds header pressure vs a diurnal demand), with a Magelis HMI polling it.", _sc_water()),
    "scenario-reactor": ("Scenario: Exothermic Reactor Unit", "Chemical/oil & gas — a Siemens S7-1500 OPC UA reactor controller (reverse-acting PI cools an exothermic reaction) plus an Emerson Modbus feed flow-meter, with a Siemens HMI polling the reactor over OPC UA.", _sc_reactor()),
    "scenario-compressor": ("Scenario: Gas Compressor Station", "Oil & gas pipeline — a Schneider M580 compressor PLC holding discharge pressure via speed, polled by a WinCC SCADA over Modbus.", _sc_compressor()),
    "scenario-substation": ("Scenario: Substation Feeder Bay", "Energy — a Schneider MiCOM bay controller on IEC-104 and a Siemens SIPROTEC protection relay on Modbus (PI voltage regulation via LTC tap), with a WinCC SCADA interrogating the bay controller over IEC-104.", _sc_substation()),
    "scenario-building": ("Scenario: Building AHU Zone", "Building automation — a Siemens Desigo BACnet AHU/room controller and a Schneider PM8000 Modbus power meter, with a Siemens HMI polling the AHU over BACnet (Who-Is + ReadProperty).", _sc_building()),
    "scenario-manufacturing": ("Scenario: Manufacturing Line Cell", "Manufacturing — a Siemens S7-1500 OPC UA line PLC and a Siemens G120C Modbus VFD drive, with a Magelis HMI polling the line PLC over OPC UA.", _sc_manufacturing()),
}


def list_presets() -> list[dict]:
    """Preset catalog for the UI (personas serialized to the deploy schema)."""
    return [
        {"key": key, "name": name, "description": desc,
         "personas": [p.to_dict() for p in personas]}
        for key, (name, desc, personas) in _PRESETS.items()
    ]
