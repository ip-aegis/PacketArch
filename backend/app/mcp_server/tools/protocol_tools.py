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
