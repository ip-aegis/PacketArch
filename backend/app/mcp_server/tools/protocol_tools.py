"""Protocol-specific configuration tools for MCP.

This module provides tools for configuring:
- Modbus TCP devices and flows
- EtherNet/IP devices and connections
- PROFINET devices and Application Relationships
- Siemens S7 devices and communication
"""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.scenario import Scenario


# =============================================================================
# Modbus Tools
# =============================================================================


async def configure_modbus_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    unit_id: int | None = None,
    register_map: dict[str, Any] | None = None,
    function_codes: list[int] | None = None,
    exception_responses: list[dict[str, Any]] | None = None,
) -> str:
    """Configure Modbus-specific parameters for a device.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        unit_id: Modbus unit/slave ID (1-247)
        register_map: Register map configuration
        function_codes: Supported function codes
        exception_responses: Configured exception responses

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize modbus_config if not present
    if "modbus_config" not in device:
        device["modbus_config"] = {}

    if unit_id is not None:
        device["modbus_config"]["unit_id"] = max(1, min(247, unit_id))

    if register_map is not None:
        device["modbus_config"]["register_map"] = register_map

    if function_codes is not None:
        # Validate function codes (1-127)
        device["modbus_config"]["function_codes"] = [
            fc for fc in function_codes if 1 <= fc <= 127
        ]

    if exception_responses is not None:
        device["modbus_config"]["exception_responses"] = exception_responses

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "modbus_config": device.get("modbus_config"),
    })


async def configure_modbus_flow(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    read_operations: list[dict[str, Any]] | None = None,
    write_operations: list[dict[str, Any]] | None = None,
    exception_rate: float | None = None,
) -> str:
    """Configure Modbus flow polling patterns.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        read_operations: Read operations [{function_code, start_address, count, interval_ms}]
        write_operations: Write operations [{function_code, start_address, values[]}]
        exception_rate: Probability of exception response (0.0-1.0)

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize modbus_config if not present
    if "modbus_config" not in flow:
        flow["modbus_config"] = {}

    if read_operations is not None:
        flow["modbus_config"]["read_operations"] = read_operations

    if write_operations is not None:
        flow["modbus_config"]["write_operations"] = write_operations

    if exception_rate is not None:
        flow["modbus_config"]["exception_rate"] = max(0.0, min(1.0, exception_rate))

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "modbus_config": flow.get("modbus_config"),
    })


# =============================================================================
# EtherNet/IP Tools
# =============================================================================


async def configure_ethernet_ip_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    vendor_id: int | None = None,
    device_type: int | None = None,
    product_code: int | None = None,
    serial_number: str | None = None,
    cip_classes: dict[str, Any] | None = None,
) -> str:
    """Configure EtherNet/IP specific parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        vendor_id: CIP vendor ID
        device_type: CIP device type
        product_code: Product code
        serial_number: Serial number
        cip_classes: CIP class configurations (identity, assembly, connection_manager)

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize ethernet_ip_config if not present
    if "ethernet_ip_config" not in device:
        device["ethernet_ip_config"] = {}

    if vendor_id is not None:
        device["ethernet_ip_config"]["vendor_id"] = vendor_id

    if device_type is not None:
        device["ethernet_ip_config"]["device_type"] = device_type

    if product_code is not None:
        device["ethernet_ip_config"]["product_code"] = product_code

    if serial_number is not None:
        device["ethernet_ip_config"]["serial_number"] = serial_number

    if cip_classes is not None:
        device["ethernet_ip_config"]["cip_classes"] = cip_classes

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "ethernet_ip_config": device.get("ethernet_ip_config"),
    })


async def configure_ethernet_ip_connection(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    connection_type: str | None = None,
    rpi_ms: int | None = None,
    input_size: int | None = None,
    output_size: int | None = None,
    transport_class: int | None = None,
) -> str:
    """Configure EtherNet/IP I/O connection parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        connection_type: Connection type ('explicit', 'class1', 'class3')
        rpi_ms: Requested Packet Interval in milliseconds
        input_size: Input data size in bytes
        output_size: Output data size in bytes
        transport_class: Transport class (0, 1, 2, 3)

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize ethernet_ip_config if not present
    if "ethernet_ip_config" not in flow:
        flow["ethernet_ip_config"] = {}

    if connection_type is not None:
        if connection_type not in ("explicit", "class1", "class3"):
            return json.dumps({"error": f"Invalid connection type: {connection_type}"})
        flow["ethernet_ip_config"]["connection_type"] = connection_type

    if rpi_ms is not None:
        flow["ethernet_ip_config"]["rpi_ms"] = max(1, rpi_ms)

    if input_size is not None:
        flow["ethernet_ip_config"]["input_size"] = max(0, input_size)

    if output_size is not None:
        flow["ethernet_ip_config"]["output_size"] = max(0, output_size)

    if transport_class is not None:
        flow["ethernet_ip_config"]["transport_class"] = max(0, min(3, transport_class))

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "ethernet_ip_config": flow.get("ethernet_ip_config"),
    })


# =============================================================================
# PROFINET Tools
# =============================================================================


async def configure_profinet_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    station_name: str | None = None,
    vendor_id: int | None = None,
    device_id_value: int | None = None,
    gsd_info: dict[str, Any] | None = None,
) -> str:
    """Configure PROFINET device parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        station_name: PROFINET station name
        vendor_id: Vendor ID
        device_id_value: Device ID value
        gsd_info: GSD file information (device_access_point_id, module_slots)

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize profinet_config if not present
    if "profinet_config" not in device:
        device["profinet_config"] = {}

    if station_name is not None:
        # Validate station name (lowercase alphanumeric with hyphens)
        import re
        if re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", station_name):
            device["profinet_config"]["station_name"] = station_name
        else:
            return json.dumps({"error": "Invalid station name format"})

    if vendor_id is not None:
        device["profinet_config"]["vendor_id"] = vendor_id

    if device_id_value is not None:
        device["profinet_config"]["device_id"] = device_id_value

    if gsd_info is not None:
        device["profinet_config"]["gsd_info"] = gsd_info

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "profinet_config": device.get("profinet_config"),
    })


async def configure_profinet_ar(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    ar_type: str | None = None,
    cycle_time_us: int | None = None,
    io_data: dict[str, Any] | None = None,
) -> str:
    """Configure PROFINET Application Relationship.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        ar_type: AR type ('io_controller', 'io_device', 'io_supervisor')
        cycle_time_us: Cycle time in microseconds
        io_data: I/O data configuration (input_modules, output_modules)

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize profinet_config if not present
    if "profinet_config" not in flow:
        flow["profinet_config"] = {}

    if ar_type is not None:
        if ar_type not in ("io_controller", "io_device", "io_supervisor"):
            return json.dumps({"error": f"Invalid AR type: {ar_type}"})
        flow["profinet_config"]["ar_type"] = ar_type

    if cycle_time_us is not None:
        # Typical cycle times: 250, 500, 1000, 2000, 4000 us
        flow["profinet_config"]["cycle_time_us"] = max(250, cycle_time_us)

    if io_data is not None:
        flow["profinet_config"]["io_data"] = io_data

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "profinet_config": flow.get("profinet_config"),
    })


# =============================================================================
# Siemens S7 Tools
# =============================================================================


async def configure_s7_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    rack: int | None = None,
    slot: int | None = None,
    pdu_size: int | None = None,
    cpu_type: str | None = None,
    data_blocks: list[dict[str, Any]] | None = None,
) -> str:
    """Configure Siemens S7 protocol parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        rack: Rack number (typically 0)
        slot: Slot number (typically 1 or 2)
        pdu_size: Maximum PDU size
        cpu_type: CPU type ('S7-300', 'S7-400', 'S7-1200', 'S7-1500')
        data_blocks: Data block configurations

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize s7_config if not present
    if "s7_config" not in device:
        device["s7_config"] = {}

    if rack is not None:
        device["s7_config"]["rack"] = max(0, min(7, rack))

    if slot is not None:
        device["s7_config"]["slot"] = max(1, min(31, slot))

    if pdu_size is not None:
        # Common PDU sizes: 240 (S7-300), 480 (S7-400), 960 (S7-1500)
        device["s7_config"]["pdu_size"] = max(240, min(65535, pdu_size))

    if cpu_type is not None:
        valid_cpu_types = ("S7-300", "S7-400", "S7-1200", "S7-1500")
        if cpu_type in valid_cpu_types:
            device["s7_config"]["cpu_type"] = cpu_type
        else:
            return json.dumps({"error": f"Invalid CPU type: {cpu_type}. Valid: {valid_cpu_types}"})

    if data_blocks is not None:
        device["s7_config"]["data_blocks"] = data_blocks

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "s7_config": device.get("s7_config"),
    })


async def configure_s7_communication(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    read_areas: list[dict[str, Any]] | None = None,
    write_areas: list[dict[str, Any]] | None = None,
) -> str:
    """Configure S7 read/write operations.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        read_areas: Read operations [{area, db_number, start, length, interval_ms}]
        write_areas: Write operations [{area, db_number, start, values[]}]

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize s7_config if not present
    if "s7_config" not in flow:
        flow["s7_config"] = {}

    valid_areas = ("DB", "M", "I", "Q", "C", "T")

    if read_areas is not None:
        # Validate areas
        for op in read_areas:
            if op.get("area") and op["area"] not in valid_areas:
                return json.dumps({"error": f"Invalid area: {op['area']}. Valid: {valid_areas}"})
        flow["s7_config"]["read_areas"] = read_areas

    if write_areas is not None:
        for op in write_areas:
            if op.get("area") and op["area"] not in valid_areas:
                return json.dumps({"error": f"Invalid area: {op['area']}. Valid: {valid_areas}"})
        flow["s7_config"]["write_areas"] = write_areas

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "s7_config": flow.get("s7_config"),
    })


# =============================================================================
# DNP3 Tools
# =============================================================================


async def configure_dnp3_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    master_address: int | None = None,
    outstation_address: int | None = None,
    data_link_config: dict[str, Any] | None = None,
    application_config: dict[str, Any] | None = None,
) -> str:
    """Configure DNP3 device parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        master_address: DNP3 master address (0-65519)
        outstation_address: DNP3 outstation address (0-65519)
        data_link_config: Data link layer config {confirm_timeout_ms, max_retries}
        application_config: Application layer config {response_timeout_ms, event_buffer_size}

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize dnp3_config if not present
    if "dnp3_config" not in device:
        device["dnp3_config"] = {}

    if master_address is not None:
        device["dnp3_config"]["master_address"] = max(0, min(65519, master_address))

    if outstation_address is not None:
        device["dnp3_config"]["outstation_address"] = max(0, min(65519, outstation_address))

    if data_link_config is not None:
        device["dnp3_config"]["data_link_config"] = data_link_config

    if application_config is not None:
        device["dnp3_config"]["application_config"] = application_config

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "dnp3_config": device.get("dnp3_config"),
    })


async def configure_dnp3_flow(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    polling_classes: list[int] | None = None,
    integrity_poll_interval_ms: int | None = None,
    unsolicited_responses: bool | None = None,
    event_config: dict[str, Any] | None = None,
) -> str:
    """Configure DNP3 flow polling patterns.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        polling_classes: Classes to poll (0=static, 1/2/3=events)
        integrity_poll_interval_ms: Interval for integrity polls
        unsolicited_responses: Enable unsolicited response mode
        event_config: Event configuration {class1_buffer, class2_buffer, class3_buffer}

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize dnp3_config if not present
    if "dnp3_config" not in flow:
        flow["dnp3_config"] = {}

    if polling_classes is not None:
        # Validate classes (0, 1, 2, 3)
        flow["dnp3_config"]["polling_classes"] = [c for c in polling_classes if 0 <= c <= 3]

    if integrity_poll_interval_ms is not None:
        flow["dnp3_config"]["integrity_poll_interval_ms"] = max(1000, integrity_poll_interval_ms)

    if unsolicited_responses is not None:
        flow["dnp3_config"]["unsolicited_responses"] = unsolicited_responses

    if event_config is not None:
        flow["dnp3_config"]["event_config"] = event_config

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "dnp3_config": flow.get("dnp3_config"),
    })


# =============================================================================
# IEC 104 Tools
# =============================================================================


async def configure_iec104_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    originator_address: int | None = None,
    common_address: int | None = None,
    k_value: int | None = None,
    w_value: int | None = None,
    t1_timeout_ms: int | None = None,
    t2_timeout_ms: int | None = None,
    t3_timeout_ms: int | None = None,
) -> str:
    """Configure IEC 60870-5-104 device parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        originator_address: Originator address (OA)
        common_address: Common Address of ASDU (CA)
        k_value: Max unconfirmed I-format APDUs (1-32767)
        w_value: Latest ack threshold (1-32767)
        t1_timeout_ms: Send/receive timeout
        t2_timeout_ms: Ack timeout
        t3_timeout_ms: Test frame timeout

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize iec104_config if not present
    if "iec104_config" not in device:
        device["iec104_config"] = {}

    if originator_address is not None:
        device["iec104_config"]["originator_address"] = max(0, min(255, originator_address))

    if common_address is not None:
        device["iec104_config"]["common_address"] = max(1, min(65534, common_address))

    if k_value is not None:
        device["iec104_config"]["k_value"] = max(1, min(32767, k_value))

    if w_value is not None:
        device["iec104_config"]["w_value"] = max(1, min(32767, w_value))

    if t1_timeout_ms is not None:
        device["iec104_config"]["t1_timeout_ms"] = max(1000, t1_timeout_ms)

    if t2_timeout_ms is not None:
        device["iec104_config"]["t2_timeout_ms"] = max(1000, t2_timeout_ms)

    if t3_timeout_ms is not None:
        device["iec104_config"]["t3_timeout_ms"] = max(1000, t3_timeout_ms)

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "iec104_config": device.get("iec104_config"),
    })


async def configure_iec104_flow(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    general_interrogation: bool | None = None,
    interrogation_interval_ms: int | None = None,
    spontaneous_events: list[dict[str, Any]] | None = None,
    time_sync: bool | None = None,
) -> str:
    """Configure IEC 104 flow polling patterns.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        general_interrogation: Enable general interrogation
        interrogation_interval_ms: Interval between interrogation requests
        spontaneous_events: Spontaneous event config [{type_id, ioa_range, interval_ms}]
        time_sync: Enable time synchronization

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize iec104_config if not present
    if "iec104_config" not in flow:
        flow["iec104_config"] = {}

    if general_interrogation is not None:
        flow["iec104_config"]["general_interrogation"] = general_interrogation

    if interrogation_interval_ms is not None:
        flow["iec104_config"]["interrogation_interval_ms"] = max(1000, interrogation_interval_ms)

    if spontaneous_events is not None:
        flow["iec104_config"]["spontaneous_events"] = spontaneous_events

    if time_sync is not None:
        flow["iec104_config"]["time_sync"] = time_sync

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "iec104_config": flow.get("iec104_config"),
    })


# =============================================================================
# BACnet Tools
# =============================================================================


async def configure_bacnet_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    device_instance: int | None = None,
    vendor_id: int | None = None,
    max_apdu_length: int | None = None,
    segmentation_support: str | None = None,
    object_list: list[dict[str, Any]] | None = None,
) -> str:
    """Configure BACnet device parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        device_instance: BACnet device instance (0-4194302)
        vendor_id: BACnet vendor ID
        max_apdu_length: Maximum APDU length (50-1476)
        segmentation_support: Segmentation ('both', 'transmit', 'receive', 'none')
        object_list: List of BACnet objects [{type, instance, name}]

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize bacnet_config if not present
    if "bacnet_config" not in device:
        device["bacnet_config"] = {}

    if device_instance is not None:
        device["bacnet_config"]["device_instance"] = max(0, min(4194302, device_instance))

    if vendor_id is not None:
        device["bacnet_config"]["vendor_id"] = vendor_id

    if max_apdu_length is not None:
        device["bacnet_config"]["max_apdu_length"] = max(50, min(1476, max_apdu_length))

    if segmentation_support is not None:
        valid_segmentation = ("both", "transmit", "receive", "none")
        if segmentation_support in valid_segmentation:
            device["bacnet_config"]["segmentation_support"] = segmentation_support
        else:
            return json.dumps({
                "error": f"Invalid segmentation support: {segmentation_support}. Valid: {valid_segmentation}"
            })

    if object_list is not None:
        device["bacnet_config"]["object_list"] = object_list

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "bacnet_config": device.get("bacnet_config"),
    })


async def configure_bacnet_polling(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    read_property_multiple: list[dict[str, Any]] | None = None,
    cov_subscriptions: list[dict[str, Any]] | None = None,
    poll_interval_ms: int | None = None,
) -> str:
    """Configure BACnet flow polling patterns.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        read_property_multiple: RPM config [{object_type, object_instance, properties[]}]
        cov_subscriptions: COV subscription config [{object_type, object_instance, lifetime}]
        poll_interval_ms: Polling interval for ReadProperty operations

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize bacnet_config if not present
    if "bacnet_config" not in flow:
        flow["bacnet_config"] = {}

    if read_property_multiple is not None:
        flow["bacnet_config"]["read_property_multiple"] = read_property_multiple

    if cov_subscriptions is not None:
        flow["bacnet_config"]["cov_subscriptions"] = cov_subscriptions

    if poll_interval_ms is not None:
        flow["bacnet_config"]["poll_interval_ms"] = max(100, poll_interval_ms)

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "bacnet_config": flow.get("bacnet_config"),
    })


# =============================================================================
# SNMP Tools
# =============================================================================


async def configure_snmp_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    snmp_version: str | None = None,
    community_read: str | None = None,
    community_write: str | None = None,
    sys_descr: str | None = None,
    sys_object_id: str | None = None,
    sys_name: str | None = None,
    sys_location: str | None = None,
    supported_mibs: list[str] | None = None,
) -> str:
    """Configure SNMP device parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        snmp_version: SNMP version ('v1', 'v2c', 'v3')
        community_read: Read community string
        community_write: Write community string
        sys_descr: System description
        sys_object_id: System OID
        sys_name: System name
        sys_location: System location
        supported_mibs: List of supported MIBs

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize snmp_config if not present
    if "snmp_config" not in device:
        device["snmp_config"] = {}

    if snmp_version is not None:
        valid_versions = ("v1", "v2c", "v3")
        if snmp_version in valid_versions:
            device["snmp_config"]["snmp_version"] = snmp_version
        else:
            return json.dumps({
                "error": f"Invalid SNMP version: {snmp_version}. Valid: {valid_versions}"
            })

    if community_read is not None:
        device["snmp_config"]["community_read"] = community_read

    if community_write is not None:
        device["snmp_config"]["community_write"] = community_write

    if sys_descr is not None:
        device["snmp_config"]["sys_descr"] = sys_descr

    if sys_object_id is not None:
        device["snmp_config"]["sys_object_id"] = sys_object_id

    if sys_name is not None:
        device["snmp_config"]["sys_name"] = sys_name

    if sys_location is not None:
        device["snmp_config"]["sys_location"] = sys_location

    if supported_mibs is not None:
        device["snmp_config"]["supported_mibs"] = supported_mibs

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "snmp_config": device.get("snmp_config"),
    })


async def configure_snmp_polling(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    oid_list: list[str] | None = None,
    poll_interval_ms: int | None = None,
    use_get_bulk: bool | None = None,
    max_repetitions: int | None = None,
    trap_config: dict[str, Any] | None = None,
) -> str:
    """Configure SNMP flow polling patterns.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        oid_list: List of OIDs to poll
        poll_interval_ms: Polling interval
        use_get_bulk: Use GetBulk requests (SNMPv2c/v3)
        max_repetitions: Max repetitions for GetBulk
        trap_config: Trap configuration {enabled, trap_oids[], interval_ms}

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize snmp_config if not present
    if "snmp_config" not in flow:
        flow["snmp_config"] = {}

    if oid_list is not None:
        flow["snmp_config"]["oid_list"] = oid_list

    if poll_interval_ms is not None:
        flow["snmp_config"]["poll_interval_ms"] = max(100, poll_interval_ms)

    if use_get_bulk is not None:
        flow["snmp_config"]["use_get_bulk"] = use_get_bulk

    if max_repetitions is not None:
        flow["snmp_config"]["max_repetitions"] = max(1, min(100, max_repetitions))

    if trap_config is not None:
        flow["snmp_config"]["trap_config"] = trap_config

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "snmp_config": flow.get("snmp_config"),
    })


# =============================================================================
# OPC UA Tools
# =============================================================================


async def configure_opcua_device(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    application_uri: str | None = None,
    product_uri: str | None = None,
    application_name: str | None = None,
    security_mode: str | None = None,
    security_policy: str | None = None,
    namespace_uris: list[str] | None = None,
) -> str:
    """Configure OPC UA device parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        application_uri: Application URI
        product_uri: Product URI
        application_name: Application name
        security_mode: Security mode ('None', 'Sign', 'SignAndEncrypt')
        security_policy: Security policy ('None', 'Basic128Rsa15', 'Basic256', 'Basic256Sha256')
        namespace_uris: List of namespace URIs

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize opcua_config if not present
    if "opcua_config" not in device:
        device["opcua_config"] = {}

    if application_uri is not None:
        device["opcua_config"]["application_uri"] = application_uri

    if product_uri is not None:
        device["opcua_config"]["product_uri"] = product_uri

    if application_name is not None:
        device["opcua_config"]["application_name"] = application_name

    if security_mode is not None:
        valid_modes = ("None", "Sign", "SignAndEncrypt")
        if security_mode in valid_modes:
            device["opcua_config"]["security_mode"] = security_mode
        else:
            return json.dumps({
                "error": f"Invalid security mode: {security_mode}. Valid: {valid_modes}"
            })

    if security_policy is not None:
        valid_policies = ("None", "Basic128Rsa15", "Basic256", "Basic256Sha256", "Aes128_Sha256_RsaOaep", "Aes256_Sha256_RsaPss")
        if security_policy in valid_policies:
            device["opcua_config"]["security_policy"] = security_policy
        else:
            return json.dumps({
                "error": f"Invalid security policy: {security_policy}. Valid: {valid_policies}"
            })

    if namespace_uris is not None:
        device["opcua_config"]["namespace_uris"] = namespace_uris

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "opcua_config": device.get("opcua_config"),
    })


async def configure_opcua_subscription(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    node_ids: list[str] | None = None,
    publishing_interval_ms: int | None = None,
    lifetime_count: int | None = None,
    max_keepalive_count: int | None = None,
    sampling_interval_ms: int | None = None,
) -> str:
    """Configure OPC UA subscription parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        node_ids: List of node IDs to subscribe to
        publishing_interval_ms: Publishing interval
        lifetime_count: Subscription lifetime count
        max_keepalive_count: Max keepalive count
        sampling_interval_ms: Sampling interval for monitored items

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize opcua_config if not present
    if "opcua_config" not in flow:
        flow["opcua_config"] = {}

    if node_ids is not None:
        flow["opcua_config"]["node_ids"] = node_ids

    if publishing_interval_ms is not None:
        flow["opcua_config"]["publishing_interval_ms"] = max(100, publishing_interval_ms)

    if lifetime_count is not None:
        flow["opcua_config"]["lifetime_count"] = max(3, lifetime_count)

    if max_keepalive_count is not None:
        flow["opcua_config"]["max_keepalive_count"] = max(1, max_keepalive_count)

    if sampling_interval_ms is not None:
        flow["opcua_config"]["sampling_interval_ms"] = max(0, sampling_interval_ms)

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "opcua_config": flow.get("opcua_config"),
    })


# =============================================================================
# IEC 61850 Tools
# =============================================================================


async def configure_iec61850_ied(
    db: AsyncSession,
    scenario_id: str,
    device_id: str,
    ied_name: str | None = None,
    manufacturer: str | None = None,
    model: str | None = None,
    logical_devices: list[dict[str, Any]] | None = None,
    goose_config: dict[str, Any] | None = None,
) -> str:
    """Configure IEC 61850 IED parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        device_id: Device ID
        ied_name: IED name (used in SCL)
        manufacturer: Manufacturer name
        model: Model number
        logical_devices: List of logical devices [{name, logical_nodes[]}]
        goose_config: GOOSE configuration {enabled, gocb_ref, dataset, app_id}

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    devices = definition.get("devices", {})

    if device_id not in devices:
        return json.dumps({"error": f"Device {device_id} not found"})

    device = devices[device_id].copy()

    # Initialize iec61850_config if not present
    if "iec61850_config" not in device:
        device["iec61850_config"] = {}

    if ied_name is not None:
        device["iec61850_config"]["ied_name"] = ied_name

    if manufacturer is not None:
        device["iec61850_config"]["manufacturer"] = manufacturer

    if model is not None:
        device["iec61850_config"]["model"] = model

    if logical_devices is not None:
        device["iec61850_config"]["logical_devices"] = logical_devices

    if goose_config is not None:
        device["iec61850_config"]["goose_config"] = goose_config

    devices[device_id] = device
    definition["devices"] = devices

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "device_id": device_id,
        "iec61850_config": device.get("iec61850_config"),
    })


async def configure_goose_publisher(
    db: AsyncSession,
    scenario_id: str,
    flow_id: str,
    gocb_ref: str | None = None,
    dataset: str | None = None,
    app_id: int | None = None,
    conf_rev: int | None = None,
    min_time_ms: int | None = None,
    max_time_ms: int | None = None,
) -> str:
    """Configure GOOSE publishing parameters.

    Args:
        db: Database session
        scenario_id: Scenario UUID
        flow_id: Flow ID
        gocb_ref: GOOSE control block reference
        dataset: Dataset reference
        app_id: Application ID
        conf_rev: Configuration revision
        min_time_ms: Minimum time between GOOSE frames
        max_time_ms: Maximum time between GOOSE frames

    Returns:
        JSON string with result
    """
    result = await db.execute(select(Scenario).where(Scenario.id == uuid.UUID(scenario_id)))
    scenario = result.scalar_one_or_none()

    if not scenario:
        return json.dumps({"error": "Scenario not found"})

    definition = scenario.definition.copy()
    flows = definition.get("flows", {})

    if flow_id not in flows:
        return json.dumps({"error": f"Flow {flow_id} not found"})

    flow = flows[flow_id].copy()

    # Initialize iec61850_config if not present
    if "iec61850_config" not in flow:
        flow["iec61850_config"] = {}

    if gocb_ref is not None:
        flow["iec61850_config"]["gocb_ref"] = gocb_ref

    if dataset is not None:
        flow["iec61850_config"]["dataset"] = dataset

    if app_id is not None:
        flow["iec61850_config"]["app_id"] = max(0, min(65535, app_id))

    if conf_rev is not None:
        flow["iec61850_config"]["conf_rev"] = max(1, conf_rev)

    if min_time_ms is not None:
        flow["iec61850_config"]["min_time_ms"] = max(1, min_time_ms)

    if max_time_ms is not None:
        flow["iec61850_config"]["max_time_ms"] = max(1, max_time_ms)

    flows[flow_id] = flow
    definition["flows"] = flows

    scenario.definition = definition
    flag_modified(scenario, "definition")
    scenario.version += 1

    await db.commit()
    await db.refresh(scenario)

    return json.dumps({
        "success": True,
        "flow_id": flow_id,
        "iec61850_config": flow.get("iec61850_config"),
    })
