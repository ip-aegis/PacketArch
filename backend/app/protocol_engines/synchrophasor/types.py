# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""IEEE C37.118.2-2011 synchrophasor protocol types.

C37.118 frames a Phasor Measurement Unit (PMU) reporting to a
Phasor Data Concentrator (PDC) in wide-area measurement systems
(WAMS) for the electric power grid.
"""

from dataclasses import dataclass, field
from enum import IntEnum


class FrameType(IntEnum):
    """C37.118.2 frame types (3-bit field in SYNC byte 2 bits 6:4)."""

    DATA = 0
    HEADER = 1
    CONFIG_1 = 2
    CONFIG_2 = 3
    COMMAND = 4
    CONFIG_3 = 5


# SYNC field high byte is always 0xAA. Low byte encodes:
#   bits 7    = reserved 0
#   bits 6:4  = frame type
#   bits 3:0  = version (current spec = 1)
SYNC_HIGH = 0xAA
SYNC_VERSION = 0x01

FRAME_SYNC = {
    FrameType.DATA:     (SYNC_HIGH << 8) | (FrameType.DATA     << 4) | SYNC_VERSION,
    FrameType.HEADER:   (SYNC_HIGH << 8) | (FrameType.HEADER   << 4) | SYNC_VERSION,
    FrameType.CONFIG_1: (SYNC_HIGH << 8) | (FrameType.CONFIG_1 << 4) | SYNC_VERSION,
    FrameType.CONFIG_2: (SYNC_HIGH << 8) | (FrameType.CONFIG_2 << 4) | SYNC_VERSION,
    FrameType.COMMAND:  (SYNC_HIGH << 8) | (FrameType.COMMAND  << 4) | SYNC_VERSION,
    FrameType.CONFIG_3: (SYNC_HIGH << 8) | (FrameType.CONFIG_3 << 4) | SYNC_VERSION,
}


# Command codes (CMD field in command frame body)
CMD_TURN_OFF_TX     = 0x0001  # Turn off transmission of data frames
CMD_TURN_ON_TX      = 0x0002  # Turn on transmission of data frames
CMD_SEND_HEADER     = 0x0003  # Send HDR frame
CMD_SEND_CFG_1      = 0x0004  # Send CFG-1 frame
CMD_SEND_CFG_2      = 0x0005  # Send CFG-2 frame
CMD_SEND_CFG_3      = 0x0006  # Send CFG-3 frame (extended config)


# Default TIME_BASE — divisor for FRACSEC field. Common value 1_000_000
# gives microsecond resolution.
DEFAULT_TIME_BASE = 1_000_000

# Default ports per spec / common practice
C37118_PORT_TCP = 4712
C37118_PORT_UDP = 4713


@dataclass
class C37118Identity:
    """Realistic identity for a C37.118 PMU.

    All fields default to values typical of a single-phasor PMU
    at 60 Hz, 30 frames/sec — i.e. the cheapest valid PMU.
    """

    station_name: str = "PMU01"          # 16-char ASCII (padded)
    idcode: int = 1                       # uint16, 1..65534
    data_rate: int = 30                   # frames/sec (positive = fps)
    fnom: int = 60                        # 60Hz=0, 50Hz=1 in wire encoding
    config_count: int = 1                 # CFGCNT revision counter
    time_base: int = DEFAULT_TIME_BASE    # FRACSEC divisor

    # PMU phasor / analog / digital channel counts
    num_phasors: int = 1
    num_analog: int = 0
    num_digital: int = 0

    # Channel names (PHNMR + ANNMR + 16*DGNMR names, each 16 bytes).
    # If empty, names are auto-generated.
    channel_names: list[str] = field(default_factory=list)

    # FORMAT word bit flags:
    #   bit 0: 0 = phasors in rect (int16+int16), 1 = polar (float32+float32)
    #   bit 1: 0 = phasors int16, 1 = phasors float32
    #   bit 2: 0 = analogs int16, 1 = analogs float32
    #   bit 3: 0 = freq int16, 1 = freq float32
    # Default: integer rectangular phasors, int16 freq/dfreq, int16 analogs.
    format_flags: int = 0x0000

    def fnom_code(self) -> int:
        """Encode nominal line frequency for FNOM wire field."""
        return 0 if self.fnom == 60 else 1
