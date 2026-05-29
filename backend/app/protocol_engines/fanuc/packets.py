# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""FANUC FOCAS (FANUC Open CNC API Specification) packet building utilities.

FOCAS is FANUC's proprietary protocol for CNC machine communication.
Default port: TCP 8193

Note: The actual FOCAS protocol is proprietary. This implementation
creates realistic simulated traffic based on known function patterns
and publicly documented API structures.

Supported CNC models (simulated):
- Series 30i-B, 31i-B, 32i-B
- Series 0i-MODEL F
- Power Motion i-A
"""

import struct
from dataclasses import dataclass
from enum import IntEnum


# =============================================================================
# FOCAS Constants
# =============================================================================

# Default TCP port
FOCAS_DEFAULT_PORT = 8193

# Protocol version
FOCAS_VERSION = 2  # FOCAS2

# Message types (simulated based on known patterns)
class FOCASMessageType(IntEnum):
    """FOCAS message types (simulated)."""
    REQUEST = 0x01
    RESPONSE = 0x02
    NOTIFICATION = 0x03
    ERROR = 0xFF


# Function codes (based on known FOCAS API functions)
class FOCASFunction(IntEnum):
    """FOCAS function codes (based on API documentation)."""
    # Connection management
    ALLCLIBHNDL3 = 0x0001    # Connect to CNC
    FREELIBHNDL = 0x0002      # Disconnect from CNC

    # System information
    SYSINFO = 0x0010          # cnc_sysinfo - Get system info
    STATINFO = 0x0011         # cnc_statinfo - Get status info
    STATINFO2 = 0x0012        # cnc_statinfo2 - Extended status

    # Axis/Position data
    RDPOSITION = 0x0020       # cnc_rdposition - Read position
    RDAXISDATA = 0x0021       # cnc_rdaxisdata - Read axis data
    MACHINE = 0x0022          # cnc_machine - Machine position
    ABSOLUTE = 0x0023         # cnc_absolute - Absolute position
    RELATIVE = 0x0024         # cnc_relative - Relative position

    # Spindle data
    ACTS = 0x0030             # cnc_acts - Actual spindle speed
    ACTS2 = 0x0031            # cnc_acts2 - Extended spindle data
    RDSPLOAD = 0x0032         # cnc_rdspload - Spindle load

    # Speed/Feed data
    RDSPEED = 0x0040          # cnc_rdspeed - Read speed
    ACTF = 0x0041             # cnc_actf - Actual feedrate
    RDFEEDRATE = 0x0042       # cnc_rdfeedrate - Feed rate override

    # Tool data
    RDTOFSR = 0x0050          # cnc_rdtofsr - Read tool offset
    WRTOFSR = 0x0051          # cnc_wrtofsr - Write tool offset
    RDTOFSINFO = 0x0052       # cnc_rdtofsinfo - Tool offset info
    RDTOOL = 0x0053           # cnc_rdtool - Current tool

    # Program data
    RDPROGNUM = 0x0060        # cnc_rdprognum - Program number
    RDPROGDIR = 0x0061        # cnc_rdprogdir - Program directory
    RDBLKCOUNT = 0x0062       # cnc_rdblkcount - Block count
    UPLOAD = 0x0063           # cnc_upload - Upload program

    # Alarm data
    ALARM = 0x0070            # cnc_alarm - Read alarm status
    RDALMMSG = 0x0071         # cnc_rdalmmsg - Read alarm message
    RDALMINFO = 0x0072        # cnc_rdalminfo - Alarm info

    # Parameters
    RDPARAM = 0x0080          # cnc_rdparam - Read parameter
    WRPARAM = 0x0081          # cnc_wrparam - Write parameter

    # Dynamic data
    RDDYNAMIC = 0x0090        # cnc_rddynamic - Read dynamic data
    RDDYNAMIC2 = 0x0091       # cnc_rddynamic2 - Extended dynamic


# CNC types
class CNCType(IntEnum):
    """CNC machine types."""
    MACHINING_CENTER = 0      # M-series (milling)
    LATHE = 1                 # T-series (turning)
    PUNCH_PRESS = 2           # P-series
    LASER = 3                 # L-series
    WIRE_EDM = 4              # W-series
    GRINDER = 5               # G-series


# Axis types
class AxisType(IntEnum):
    """Axis data types."""
    ABSOLUTE = 0              # Absolute position
    MACHINE = 1               # Machine position
    RELATIVE = 2              # Relative position
    DISTANCE = 3              # Distance to go


# Status bits
class StatusBits(IntEnum):
    """CNC status bits."""
    HDCK = 0x0001      # Manual handle retrace mode
    MOTION = 0x0002    # Axis motion
    MSTB = 0x0004      # M/S/T/B command executing
    EMERGENCY = 0x0008 # Emergency stop
    ALARM = 0x0010     # Alarm state
    EDIT = 0x0020      # Edit mode
    RUN = 0x0040       # Automatic operation running
    RESET = 0x0080     # Reset state


# =============================================================================
# FANUC CNC Models
# =============================================================================

FANUC_MODELS = {
    "30i-B": {"series": "30i", "version": "B", "max_axes": 32, "max_spindles": 8},
    "31i-B": {"series": "31i", "version": "B", "max_axes": 20, "max_spindles": 4},
    "31i-B5": {"series": "31i", "version": "B5", "max_axes": 11, "max_spindles": 2},
    "32i-B": {"series": "32i", "version": "B", "max_axes": 8, "max_spindles": 2},
    "0i-F": {"series": "0i", "version": "F", "max_axes": 8, "max_spindles": 2},
    "0i-F Plus": {"series": "0i", "version": "F Plus", "max_axes": 11, "max_spindles": 2},
    "Power Motion i-A": {"series": "PMi", "version": "A", "max_axes": 32, "max_spindles": 0},
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class FOCASHeader:
    """FOCAS message header (simulated).

    Based on reverse-engineered patterns.
    """
    version: int = FOCAS_VERSION
    message_type: int = FOCASMessageType.REQUEST
    function_code: int = 0
    sequence: int = 0
    data_length: int = 0
    handle: int = 0

    def pack(self) -> bytes:
        """Pack header to bytes."""
        return struct.pack(
            "<BBHHIH",
            self.version,
            self.message_type,
            self.function_code,
            self.sequence,
            self.data_length,
            self.handle,
        )

    @classmethod
    def size(cls) -> int:
        """Return header size."""
        return 12


@dataclass
class CNCStatus:
    """CNC status information (ODBST structure)."""
    hdck: int = 0          # Manual handle retrace
    tmmode: int = 0        # T/M mode selection
    aut: int = 0           # AUTO/MANUAL mode
    run: int = 0           # Run status
    motion: int = 0        # Axis moving
    mstb: int = 0          # M/S/T/B status
    emergency: int = 0     # Emergency stop
    alarm: int = 0         # Alarm status
    edit: int = 0          # Edit mode

    def pack(self) -> bytes:
        """Pack status to bytes."""
        return struct.pack(
            "<9h",
            self.hdck, self.tmmode, self.aut, self.run,
            self.motion, self.mstb, self.emergency, self.alarm, self.edit
        )


@dataclass
class AxisPosition:
    """Axis position data."""
    axis_name: str = "X"
    absolute: float = 0.0
    machine: float = 0.0
    relative: float = 0.0
    distance_to_go: float = 0.0

    def pack(self) -> bytes:
        """Pack position data to bytes."""
        # Axis name (4 bytes, padded)
        name_bytes = self.axis_name.encode("ascii")[:4].ljust(4, b"\x00")
        # Positions as 32-bit integers (microns)
        return (
            name_bytes +
            struct.pack("<iiii",
                int(self.absolute * 1000),
                int(self.machine * 1000),
                int(self.relative * 1000),
                int(self.distance_to_go * 1000),
            )
        )


@dataclass
class SpindleData:
    """Spindle data."""
    spindle_num: int = 1
    actual_speed: int = 0      # RPM
    commanded_speed: int = 0   # RPM
    load: int = 0              # Percentage (0-100)
    motor_temp: int = 0        # Temperature

    def pack(self) -> bytes:
        """Pack spindle data to bytes."""
        return struct.pack(
            "<hHHBB",
            self.spindle_num,
            self.actual_speed,
            self.commanded_speed,
            self.load,
            self.motor_temp,
        )


@dataclass
class AlarmInfo:
    """Alarm information."""
    alarm_no: int = 0
    alarm_type: int = 0
    alarm_text: str = ""
    axis: int = -1

    def pack(self) -> bytes:
        """Pack alarm info to bytes."""
        text_bytes = self.alarm_text.encode("ascii")[:64].ljust(64, b"\x00")
        return struct.pack("<HBb", self.alarm_no, self.alarm_type, self.axis) + text_bytes


@dataclass
class SystemInfo:
    """CNC system information (ODBSYS structure)."""
    cnc_type: int = CNCType.MACHINING_CENTER
    series: str = "30i"
    version: str = "B"
    axes: int = 5
    spindles: int = 1
    max_axis: int = 8

    def pack(self) -> bytes:
        """Pack system info to bytes."""
        series_bytes = self.series.encode("ascii")[:4].ljust(4, b"\x00")
        version_bytes = self.version.encode("ascii")[:4].ljust(4, b"\x00")
        return struct.pack(
            "<B4s4sBBB",
            self.cnc_type,
            series_bytes,
            version_bytes,
            self.axes,
            self.spindles,
            self.max_axis,
        )


# =============================================================================
# Packet Builders
# =============================================================================

def build_focas_header(
    message_type: int,
    function_code: int,
    sequence: int,
    data_length: int,
    handle: int = 0,
) -> bytes:
    """Build FOCAS message header.

    Args:
        message_type: Request, response, or notification
        function_code: FOCAS function code
        sequence: Sequence number for matching
        data_length: Length of data payload
        handle: Connection handle

    Returns:
        Header bytes (12 bytes)
    """
    header = FOCASHeader(
        version=FOCAS_VERSION,
        message_type=message_type,
        function_code=function_code,
        sequence=sequence,
        data_length=data_length,
        handle=handle,
    )
    return header.pack()


def build_focas_request(
    function_code: int,
    sequence: int,
    data: bytes = b"",
    handle: int = 0,
) -> bytes:
    """Build FOCAS request message.

    Args:
        function_code: FOCAS function to call
        sequence: Sequence number
        data: Request parameters
        handle: Connection handle

    Returns:
        Complete request message
    """
    header = build_focas_header(
        message_type=FOCASMessageType.REQUEST,
        function_code=function_code,
        sequence=sequence,
        data_length=len(data),
        handle=handle,
    )
    return header + data


def build_focas_response(
    function_code: int,
    sequence: int,
    data: bytes = b"",
    handle: int = 0,
    error_code: int = 0,
) -> bytes:
    """Build FOCAS response message.

    Args:
        function_code: FOCAS function (echoed)
        sequence: Sequence number (echoed)
        data: Response data
        handle: Connection handle
        error_code: Error code (0 = success)

    Returns:
        Complete response message
    """
    # Prepend error code to data
    response_data = struct.pack("<h", error_code) + data

    header = build_focas_header(
        message_type=FOCASMessageType.RESPONSE,
        function_code=function_code,
        sequence=sequence,
        data_length=len(response_data),
        handle=handle,
    )
    return header + response_data


# =============================================================================
# Function-Specific Request/Response Builders
# =============================================================================

def build_connect_request(
    ip_address: str = "192.168.1.1",
    port: int = FOCAS_DEFAULT_PORT,
    timeout: int = 10,
) -> bytes:
    """Build connection request (cnc_allclibhndl3).

    Args:
        ip_address: Target CNC IP
        port: FOCAS port
        timeout: Connection timeout

    Returns:
        Request message
    """
    # IP as null-terminated string (max 64 bytes)
    ip_bytes = ip_address.encode("ascii")[:63] + b"\x00"
    ip_padded = ip_bytes.ljust(64, b"\x00")

    data = ip_padded + struct.pack("<HH", port, timeout)

    return build_focas_request(
        function_code=FOCASFunction.ALLCLIBHNDL3,
        sequence=0,
        data=data,
    )


def build_connect_response(handle: int = 1) -> bytes:
    """Build connection response.

    Args:
        handle: Assigned connection handle

    Returns:
        Response message with handle
    """
    return build_focas_response(
        function_code=FOCASFunction.ALLCLIBHNDL3,
        sequence=0,
        data=struct.pack("<H", handle),
        handle=handle,
    )


def build_sysinfo_request(sequence: int, handle: int) -> bytes:
    """Build system info request (cnc_sysinfo).

    Args:
        sequence: Sequence number
        handle: Connection handle

    Returns:
        Request message
    """
    return build_focas_request(
        function_code=FOCASFunction.SYSINFO,
        sequence=sequence,
        handle=handle,
    )


def build_sysinfo_response(
    sequence: int,
    handle: int,
    model: str = "30i-B",
    cnc_type: int = CNCType.MACHINING_CENTER,
    axes: int = 5,
) -> bytes:
    """Build system info response.

    Args:
        sequence: Sequence number
        handle: Connection handle
        model: CNC model name
        cnc_type: CNC type (machining center, lathe, etc.)
        axes: Number of axes

    Returns:
        Response message with system info
    """
    model_info = FANUC_MODELS.get(model, FANUC_MODELS["30i-B"])

    sysinfo = SystemInfo(
        cnc_type=cnc_type,
        series=model_info["series"],
        version=model_info["version"],
        axes=axes,
        spindles=min(2, model_info["max_spindles"]),
        max_axis=model_info["max_axes"],
    )

    return build_focas_response(
        function_code=FOCASFunction.SYSINFO,
        sequence=sequence,
        data=sysinfo.pack(),
        handle=handle,
    )


def build_statinfo_request(sequence: int, handle: int) -> bytes:
    """Build status info request (cnc_statinfo).

    Args:
        sequence: Sequence number
        handle: Connection handle

    Returns:
        Request message
    """
    return build_focas_request(
        function_code=FOCASFunction.STATINFO,
        sequence=sequence,
        handle=handle,
    )


def build_statinfo_response(
    sequence: int,
    handle: int,
    status: CNCStatus | None = None,
) -> bytes:
    """Build status info response.

    Args:
        sequence: Sequence number
        handle: Connection handle
        status: CNC status (generated if not provided)

    Returns:
        Response message with status
    """
    if status is None:
        status = CNCStatus(
            run=1,      # Running
            motion=1,   # Moving
            aut=1,      # Auto mode
        )

    return build_focas_response(
        function_code=FOCASFunction.STATINFO,
        sequence=sequence,
        data=status.pack(),
        handle=handle,
    )


def build_rdposition_request(
    sequence: int,
    handle: int,
    axis_type: int = AxisType.ABSOLUTE,
    axis_num: int = -1,  # -1 = all axes
) -> bytes:
    """Build position read request (cnc_rdposition).

    Args:
        sequence: Sequence number
        handle: Connection handle
        axis_type: Type of position data
        axis_num: Axis number (-1 for all)

    Returns:
        Request message
    """
    data = struct.pack("<bh", axis_type, axis_num)
    return build_focas_request(
        function_code=FOCASFunction.RDPOSITION,
        sequence=sequence,
        data=data,
        handle=handle,
    )


def build_rdposition_response(
    sequence: int,
    handle: int,
    positions: list[AxisPosition] | None = None,
) -> bytes:
    """Build position read response.

    Args:
        sequence: Sequence number
        handle: Connection handle
        positions: Axis positions (generated if not provided)

    Returns:
        Response message with positions
    """
    if positions is None:
        # Generate typical 5-axis positions
        positions = [
            AxisPosition("X", 150.000, 150.000, 0.0, 0.0),
            AxisPosition("Y", 75.500, 75.500, 0.0, 0.0),
            AxisPosition("Z", -50.250, 249.750, 0.0, 0.0),
            AxisPosition("A", 45.0, 45.0, 0.0, 0.0),
            AxisPosition("B", 0.0, 0.0, 0.0, 0.0),
        ]

    # Pack axis count + positions
    data = struct.pack("<B", len(positions))
    for pos in positions:
        data += pos.pack()

    return build_focas_response(
        function_code=FOCASFunction.RDPOSITION,
        sequence=sequence,
        data=data,
        handle=handle,
    )


def build_acts_request(sequence: int, handle: int, spindle: int = 1) -> bytes:
    """Build actual spindle speed request (cnc_acts2).

    Args:
        sequence: Sequence number
        handle: Connection handle
        spindle: Spindle number

    Returns:
        Request message
    """
    data = struct.pack("<h", spindle)
    return build_focas_request(
        function_code=FOCASFunction.ACTS2,
        sequence=sequence,
        data=data,
        handle=handle,
    )


def build_acts_response(
    sequence: int,
    handle: int,
    spindle_data: SpindleData | None = None,
) -> bytes:
    """Build actual spindle speed response.

    Args:
        sequence: Sequence number
        handle: Connection handle
        spindle_data: Spindle data (generated if not provided)

    Returns:
        Response message with spindle data
    """
    if spindle_data is None:
        spindle_data = SpindleData(
            spindle_num=1,
            actual_speed=8000,
            commanded_speed=8000,
            load=35,
            motor_temp=45,
        )

    return build_focas_response(
        function_code=FOCASFunction.ACTS2,
        sequence=sequence,
        data=spindle_data.pack(),
        handle=handle,
    )


def build_alarm_request(sequence: int, handle: int) -> bytes:
    """Build alarm status request (cnc_alarm).

    Args:
        sequence: Sequence number
        handle: Connection handle

    Returns:
        Request message
    """
    return build_focas_request(
        function_code=FOCASFunction.ALARM,
        sequence=sequence,
        handle=handle,
    )


def build_alarm_response(
    sequence: int,
    handle: int,
    alarms: list[AlarmInfo] | None = None,
) -> bytes:
    """Build alarm status response.

    Args:
        sequence: Sequence number
        handle: Connection handle
        alarms: Alarm info list (empty if no alarms)

    Returns:
        Response message with alarm data
    """
    if alarms is None:
        alarms = []  # No alarms

    # Pack alarm count + alarm data
    data = struct.pack("<B", len(alarms))
    for alarm in alarms:
        data += alarm.pack()

    return build_focas_response(
        function_code=FOCASFunction.ALARM,
        sequence=sequence,
        data=data,
        handle=handle,
    )


def build_rdprognum_request(sequence: int, handle: int) -> bytes:
    """Build program number request (cnc_rdprognum).

    Args:
        sequence: Sequence number
        handle: Connection handle

    Returns:
        Request message
    """
    return build_focas_request(
        function_code=FOCASFunction.RDPROGNUM,
        sequence=sequence,
        handle=handle,
    )


def build_rdprognum_response(
    sequence: int,
    handle: int,
    main_prog: int = 1000,
    running_prog: int = 1000,
    current_block: int = 150,
) -> bytes:
    """Build program number response.

    Args:
        sequence: Sequence number
        handle: Connection handle
        main_prog: Main program number
        running_prog: Currently running program
        current_block: Current block number

    Returns:
        Response message with program info
    """
    data = struct.pack("<HHI", main_prog, running_prog, current_block)

    return build_focas_response(
        function_code=FOCASFunction.RDPROGNUM,
        sequence=sequence,
        data=data,
        handle=handle,
    )


def build_actf_request(sequence: int, handle: int) -> bytes:
    """Build actual feedrate request (cnc_actf).

    Args:
        sequence: Sequence number
        handle: Connection handle

    Returns:
        Request message
    """
    return build_focas_request(
        function_code=FOCASFunction.ACTF,
        sequence=sequence,
        handle=handle,
    )


def build_actf_response(
    sequence: int,
    handle: int,
    feedrate: int = 5000,  # mm/min
    override: int = 100,   # percentage
) -> bytes:
    """Build actual feedrate response.

    Args:
        sequence: Sequence number
        handle: Connection handle
        feedrate: Actual feedrate in mm/min
        override: Feed override percentage

    Returns:
        Response message with feedrate data
    """
    data = struct.pack("<IB", feedrate, override)

    return build_focas_response(
        function_code=FOCASFunction.ACTF,
        sequence=sequence,
        data=data,
        handle=handle,
    )


def build_disconnect_request(sequence: int, handle: int) -> bytes:
    """Build disconnect request (cnc_freelibhndl).

    Args:
        sequence: Sequence number
        handle: Connection handle

    Returns:
        Request message
    """
    return build_focas_request(
        function_code=FOCASFunction.FREELIBHNDL,
        sequence=sequence,
        handle=handle,
    )


def build_disconnect_response(sequence: int, handle: int) -> bytes:
    """Build disconnect response.

    Args:
        sequence: Sequence number
        handle: Connection handle

    Returns:
        Response message
    """
    return build_focas_response(
        function_code=FOCASFunction.FREELIBHNDL,
        sequence=sequence,
        handle=handle,
    )
