"""S7 Protocol packet builders for TPKT, COTP, and S7comm layers."""

import struct
from dataclasses import dataclass

from .config import (
    S7Area,
    S7ConnectionType,
    S7DataReturnCode,
    S7Function,
    S7ReadArea,
    S7TransportSize,
    S7WriteArea,
)


# =============================================================================
# TPKT Layer (RFC 1006) - ISO Transport over TCP
# =============================================================================


@dataclass
class TPKTPacket:
    """TPKT header for ISO-on-TCP transport.

    Structure:
        - Version: 1 byte (always 0x03)
        - Reserved: 1 byte (always 0x00)
        - Length: 2 bytes (total packet length including TPKT header)
    """

    payload: bytes

    def build(self) -> bytes:
        """Build TPKT packet with payload."""
        length = 4 + len(self.payload)  # TPKT header (4) + payload
        return struct.pack(">BBH", 0x03, 0x00, length) + self.payload

    @staticmethod
    def parse_header(data: bytes) -> tuple[int, int]:
        """Parse TPKT header, return (version, length)."""
        if len(data) < 4:
            raise ValueError("TPKT header too short")
        version, _, length = struct.unpack(">BBH", data[:4])
        return version, length


# =============================================================================
# COTP Layer (ISO 8073) - Connection-Oriented Transport Protocol
# =============================================================================


class COTPType:
    """COTP PDU types."""

    CR = 0xE0  # Connection Request
    CC = 0xD0  # Connection Confirm
    DR = 0x80  # Disconnect Request
    DC = 0xC0  # Disconnect Confirm
    DT = 0xF0  # Data Transfer
    ED = 0x10  # Expedited Data
    AK = 0x60  # Data Acknowledgment
    EA = 0x20  # Expedited Data Acknowledgment
    RJ = 0x50  # Reject
    ER = 0x70  # Error


@dataclass
class COTPConnectionRequest:
    """COTP Connection Request (CR) PDU.

    Used for initiating S7 connection with rack/slot destination.
    """

    dst_ref: int = 0x0000  # Destination reference (will be assigned by server)
    src_ref: int = 0x0001  # Source reference
    dst_tsap: bytes = b"\x01\x00"  # Destination TSAP (connection type + rack/slot)
    src_tsap: bytes = b"\x01\x00"  # Source TSAP

    @classmethod
    def for_s7(
        cls,
        rack: int = 0,
        slot: int = 1,
        connection_type: int = S7ConnectionType.PG,
    ) -> "COTPConnectionRequest":
        """Create CR for S7 connection with specific rack/slot."""
        # Destination TSAP: connection_type, rack*32 + slot
        dst_tsap = bytes([connection_type, rack * 32 + slot])
        # Source TSAP: typically 0x01 0x00 for PG connections
        src_tsap = bytes([0x01, 0x00])
        return cls(dst_tsap=dst_tsap, src_tsap=src_tsap)

    def build(self) -> bytes:
        """Build COTP CR PDU."""
        # Variable part: parameters
        params = b""
        # Parameter 0xC0: TPDU size (default 1024)
        params += bytes([0xC0, 0x01, 0x0A])  # TPDU size = 1024
        # Parameter 0xC1: Source TSAP
        params += bytes([0xC1, len(self.src_tsap)]) + self.src_tsap
        # Parameter 0xC2: Destination TSAP
        params += bytes([0xC2, len(self.dst_tsap)]) + self.dst_tsap

        # Fixed part
        fixed = struct.pack(
            ">BHBHB",
            6 + len(params),  # Length indicator (excludes LI itself)
            COTPType.CR,  # PDU type (actually only 4 bits, top nibble)
            0x00,  # CDT (credit)
            self.dst_ref,  # Destination reference
            self.src_ref & 0xFF,  # Source reference low byte
        )
        # Actually CR structure is slightly different, let me fix:
        # LI | CR/CDT | DST-REF | SRC-REF | CLASS | PARAMS
        header = bytes(
            [
                6 + len(params),  # Length indicator
                COTPType.CR,  # PDU type (CR = 0xE0)
                (self.dst_ref >> 8) & 0xFF,  # DST-REF high
                self.dst_ref & 0xFF,  # DST-REF low
                (self.src_ref >> 8) & 0xFF,  # SRC-REF high
                self.src_ref & 0xFF,  # SRC-REF low
                0x00,  # Class option (class 0)
            ]
        )
        return header + params


@dataclass
class COTPConnectionConfirm:
    """COTP Connection Confirm (CC) PDU."""

    dst_ref: int = 0x0001
    src_ref: int = 0x0000
    tpdu_size: int = 1024

    def build(self) -> bytes:
        """Build COTP CC PDU."""
        # Parameters
        params = bytes([0xC0, 0x01, 0x0A])  # TPDU size

        header = bytes(
            [
                6 + len(params),  # Length indicator
                COTPType.CC,  # PDU type (CC = 0xD0)
                (self.dst_ref >> 8) & 0xFF,
                self.dst_ref & 0xFF,
                (self.src_ref >> 8) & 0xFF,
                self.src_ref & 0xFF,
                0x00,  # Class option
            ]
        )
        return header + params


@dataclass
class COTPData:
    """COTP Data Transfer (DT) PDU.

    Used for carrying S7 protocol data.
    """

    payload: bytes
    last: bool = True  # Last data unit flag
    tpdu_nr: int = 0  # TPDU number (0-127)

    def build(self) -> bytes:
        """Build COTP DT PDU."""
        # DT header: LI (2) | DT (0xF0) | EOT+TPDU_NR
        eot_nr = (0x80 if self.last else 0x00) | (self.tpdu_nr & 0x7F)
        header = bytes([0x02, COTPType.DT, eot_nr])
        return header + self.payload


@dataclass
class COTPDisconnectRequest:
    """COTP Disconnect Request (DR) PDU."""

    dst_ref: int = 0x0000
    src_ref: int = 0x0001
    reason: int = 0x00  # Normal disconnect

    def build(self) -> bytes:
        """Build COTP DR PDU."""
        return bytes(
            [
                0x06,  # Length indicator
                COTPType.DR,
                (self.dst_ref >> 8) & 0xFF,
                self.dst_ref & 0xFF,
                (self.src_ref >> 8) & 0xFF,
                self.src_ref & 0xFF,
                self.reason,
            ]
        )


# =============================================================================
# S7 Protocol Layer
# =============================================================================


class S7PDUType:
    """S7 PDU types."""

    JOB = 0x01  # Job request
    ACK = 0x02  # Acknowledge without data
    ACK_DATA = 0x03  # Acknowledge with data
    USERDATA = 0x07  # Original (userdata) equipment


@dataclass
class S7Header:
    """S7 protocol header.

    Structure:
        - Protocol ID: 1 byte (always 0x32)
        - ROSCTR (PDU type): 1 byte
        - Reserved: 2 bytes (always 0x0000)
        - PDU reference: 2 bytes (request ID)
        - Parameter length: 2 bytes
        - Data length: 2 bytes
        - Error class: 1 byte (only in ACK_DATA)
        - Error code: 1 byte (only in ACK_DATA)
    """

    pdu_type: int
    pdu_ref: int = 0x0000
    param_length: int = 0
    data_length: int = 0
    error_class: int = 0  # Only for ACK_DATA
    error_code: int = 0  # Only for ACK_DATA

    def build(self) -> bytes:
        """Build S7 header."""
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            self.pdu_type,
            0x0000,  # Reserved
            self.pdu_ref,
            self.param_length,
            self.data_length,
        )
        # Add error fields for ACK_DATA
        if self.pdu_type in (S7PDUType.ACK, S7PDUType.ACK_DATA):
            header += struct.pack(">BB", self.error_class, self.error_code)
        return header


# =============================================================================
# S7 Setup Communication
# =============================================================================


@dataclass
class S7SetupCommunicationRequest:
    """S7 Setup Communication request.

    Negotiates PDU size and connection parameters.
    """

    pdu_ref: int = 0x0000
    max_amq_calling: int = 1  # Max outstanding jobs (calling)
    max_amq_called: int = 1  # Max outstanding jobs (called)
    pdu_size: int = 480  # Requested PDU size

    def build(self) -> bytes:
        """Build complete S7 Setup Communication packet."""
        # Parameter data
        param = struct.pack(
            ">BBHHH",
            S7Function.SETUP_COMM,  # Function code 0xF0
            0x00,  # Reserved
            self.max_amq_calling,
            self.max_amq_called,
            self.pdu_size,
        )

        # S7 header
        header = S7Header(
            pdu_type=S7PDUType.JOB,
            pdu_ref=self.pdu_ref,
            param_length=len(param),
            data_length=0,
        )

        return header.build() + param


@dataclass
class S7SetupCommunicationResponse:
    """S7 Setup Communication response."""

    pdu_ref: int = 0x0000
    max_amq_calling: int = 1
    max_amq_called: int = 1
    pdu_size: int = 480

    def build(self) -> bytes:
        """Build S7 Setup Communication response."""
        param = struct.pack(
            ">BBHHH",
            S7Function.SETUP_COMM,
            0x00,
            self.max_amq_calling,
            self.max_amq_called,
            self.pdu_size,
        )

        header = S7Header(
            pdu_type=S7PDUType.ACK_DATA,
            pdu_ref=self.pdu_ref,
            param_length=len(param),
            data_length=0,
            error_class=0,
            error_code=0,
        )

        return header.build() + param


# =============================================================================
# S7 Read Variable
# =============================================================================


@dataclass
class S7ReadVarRequest:
    """S7 Read Variable request.

    Reads data from PLC memory areas (DB, I, Q, M, etc.).
    """

    pdu_ref: int = 0x0000
    items: list[S7ReadArea] | None = None

    def __post_init__(self):
        if self.items is None:
            self.items = []

    def build(self) -> bytes:
        """Build S7 Read Variable request."""
        items = self.items or []

        # Build item specifications
        item_data = b""
        for item in items:
            # Any-type pointer format for S7-300/400
            # Specification type (0x12), length (10), syntax ID (0x10 = S7ANY)
            # Transport size, length, DB number, area, address (3 bytes)
            address = item.start  # Already in bits for S7-300/400

            item_spec = struct.pack(
                ">BBBBHHB",
                0x12,  # Specification type: variable specification
                0x0A,  # Length of remaining (10 bytes)
                0x10,  # Syntax ID: S7ANY
                item.transport_size,  # Transport size
                item.size,  # Length (number of items)
                item.db_number,  # DB number
                item.area,  # Area code
            )
            # Address: 3 bytes (24 bits) - byte address * 8 + bit
            item_spec += struct.pack(
                ">BBB",
                (address >> 16) & 0xFF,
                (address >> 8) & 0xFF,
                address & 0xFF,
            )
            item_data += item_spec

        # Parameter: function code + item count + items
        param = struct.pack(">BB", S7Function.READ_VAR, len(items)) + item_data

        header = S7Header(
            pdu_type=S7PDUType.JOB,
            pdu_ref=self.pdu_ref,
            param_length=len(param),
            data_length=0,
        )

        return header.build() + param


@dataclass
class S7ReadVarResponse:
    """S7 Read Variable response."""

    pdu_ref: int = 0x0000
    items: list[tuple[int, bytes]] | None = None  # List of (return_code, data)

    def __post_init__(self):
        if self.items is None:
            self.items = []

    def build(self) -> bytes:
        """Build S7 Read Variable response."""
        items = self.items or []

        # Parameter: function code + item count
        param = struct.pack(">BB", S7Function.READ_VAR, len(items))

        # Data: item responses
        data = b""
        for return_code, item_data in items:
            if return_code == S7DataReturnCode.SUCCESS:
                # Return code (1) + transport size (1) + length (2) + data
                # For byte data: transport size = 0x04 (BYTE), length in bits
                data_len_bits = len(item_data) * 8
                data += struct.pack(
                    ">BBH",
                    return_code,
                    0x04,  # Transport size: BYTE
                    data_len_bits,
                )
                data += item_data
                # Pad to even length if needed
                if len(item_data) % 2 != 0:
                    data += b"\x00"
            else:
                # Error response: just return code
                data += struct.pack(">B", return_code)

        header = S7Header(
            pdu_type=S7PDUType.ACK_DATA,
            pdu_ref=self.pdu_ref,
            param_length=len(param),
            data_length=len(data),
            error_class=0,
            error_code=0,
        )

        return header.build() + param + data


# =============================================================================
# S7 Write Variable
# =============================================================================


@dataclass
class S7WriteVarRequest:
    """S7 Write Variable request."""

    pdu_ref: int = 0x0000
    items: list[S7WriteArea] | None = None

    def __post_init__(self):
        if self.items is None:
            self.items = []

    def build(self) -> bytes:
        """Build S7 Write Variable request."""
        items = self.items or []

        # Build item specifications (same as read)
        item_specs = b""
        item_data = b""

        for item in items:
            address = item.start

            spec = struct.pack(
                ">BBBBHHB",
                0x12,
                0x0A,
                0x10,
                item.transport_size,
                len(item.data),
                item.db_number,
                item.area,
            )
            spec += struct.pack(
                ">BBB",
                (address >> 16) & 0xFF,
                (address >> 8) & 0xFF,
                address & 0xFF,
            )
            item_specs += spec

            # Data item
            data_len_bits = len(item.data) * 8
            item_data += struct.pack(
                ">BBH",
                S7DataReturnCode.RESERVED,  # Return code placeholder
                0x04,  # Transport size: BYTE
                data_len_bits,
            )
            item_data += item.data
            if len(item.data) % 2 != 0:
                item_data += b"\x00"

        # Parameter
        param = struct.pack(">BB", S7Function.WRITE_VAR, len(items)) + item_specs

        header = S7Header(
            pdu_type=S7PDUType.JOB,
            pdu_ref=self.pdu_ref,
            param_length=len(param),
            data_length=len(item_data),
        )

        return header.build() + param + item_data


@dataclass
class S7WriteVarResponse:
    """S7 Write Variable response."""

    pdu_ref: int = 0x0000
    return_codes: list[int] | None = None  # Return code per item

    def __post_init__(self):
        if self.return_codes is None:
            self.return_codes = []

    def build(self) -> bytes:
        """Build S7 Write Variable response."""
        codes = self.return_codes or []

        # Parameter
        param = struct.pack(">BB", S7Function.WRITE_VAR, len(codes))

        # Data: return codes only
        data = bytes(codes)

        header = S7Header(
            pdu_type=S7PDUType.ACK_DATA,
            pdu_ref=self.pdu_ref,
            param_length=len(param),
            data_length=len(data),
            error_class=0,
            error_code=0,
        )

        return header.build() + param + data


# =============================================================================
# S7 USERDATA (SZL Queries)
# =============================================================================


class S7UserdataType:
    """S7 Userdata subfunction types."""

    CPU_FUNCTIONS = 0x04  # CPU functions (including SZL read)


class S7UserdataSubfunction:
    """S7 Userdata subfunctions for CPU functions."""

    SZL_READ = 0x01  # Read SZL (System Status List)


@dataclass
class S7UserdataRequest:
    """S7 Userdata request for SZL queries.

    Used to read System Status Lists (SZL) containing device identification,
    firmware version, order code, and other diagnostic information.

    Key SZL IDs:
        - 0x0011: Module identification (order code, serial number, version)
        - 0x001C: Component identification
        - 0x0111: Module identification (all modules)
    """

    pdu_ref: int = 0x0000
    szl_id: int = 0x0011  # Default: Module identification
    szl_index: int = 0x0000  # Index within SZL

    def build(self) -> bytes:
        """Build S7 Userdata SZL read request."""
        # Parameter structure for USERDATA:
        # - Parameter header: 3 bytes (header type, param length, unknown)
        # - Method/Type: 1 byte (0x11 = request, 0x12 = response)
        # - Type/Function group: 1 byte (0x44 = CPU functions)
        # - Subfunction: 1 byte (0x01 = SZL read)
        # - Sequence number: 1 byte
        # Data structure for SZL read request:
        # - Return code: 1 byte (0x0A for request)
        # - Transport size: 1 byte (0x00)
        # - Length: 2 bytes (4)
        # - SZL ID: 2 bytes
        # - SZL Index: 2 bytes

        # Parameter header
        param = struct.pack(
            ">BBBBBBB",
            0x00,  # Parameter header
            0x01,  # Param length (additional)
            0x12,  # Unknown
            0x04,  # Type: 0x04 = CPU functions
            0x11,  # Type/function: 0x11 = Request
            0x44,  # Function group: CPU
            S7UserdataSubfunction.SZL_READ,  # Subfunction: SZL read
        )
        param += struct.pack(">B", 0x00)  # Sequence number

        # Data: SZL read parameters
        data = struct.pack(
            ">BBHHH",
            0xFF,  # Return code placeholder (success for request)
            0x09,  # Transport size (octet string)
            0x0004,  # Length of following data (4 bytes)
            self.szl_id,  # SZL ID
            self.szl_index,  # SZL Index
        )

        header = S7Header(
            pdu_type=S7PDUType.USERDATA,
            pdu_ref=self.pdu_ref,
            param_length=len(param),
            data_length=len(data),
        )

        return header.build() + param + data


@dataclass
class S7UserdataResponse:
    """S7 Userdata response for SZL queries.

    Contains the SZL data with device identification information.
    """

    pdu_ref: int = 0x0000
    szl_id: int = 0x0011
    szl_index: int = 0x0000
    szl_data: bytes = b""  # SZL payload data

    def build(self) -> bytes:
        """Build S7 Userdata SZL response."""
        # Parameter header for response
        param = struct.pack(
            ">BBBBBBB",
            0x00,  # Parameter header
            0x01,  # Param length
            0x12,  # Unknown
            0x08,  # Type: 0x08 = CPU functions response
            0x12,  # Type/function: 0x12 = Response
            0x44,  # Function group: CPU
            S7UserdataSubfunction.SZL_READ,  # Subfunction: SZL read
        )
        param += struct.pack(">B", 0x00)  # Sequence number
        param += struct.pack(">BB", 0x00, 0x00)  # Data unit ref, last data unit

        # Data: SZL response
        # Header + actual SZL data
        szl_header = struct.pack(
            ">BBHHH",
            0xFF,  # Return code: success
            0x09,  # Transport size: octet string
            len(self.szl_data) + 4,  # Length including SZL ID and index
            self.szl_id,
            self.szl_index,
        )
        data = szl_header + self.szl_data

        header = S7Header(
            pdu_type=S7PDUType.USERDATA,
            pdu_ref=self.pdu_ref,
            param_length=len(param),
            data_length=len(data),
        )

        return header.build() + param + data


# =============================================================================
# Helper Functions
# =============================================================================


def build_s7_packet(
    cotp_payload: bytes,
) -> bytes:
    """Wrap S7 data in COTP DT and TPKT layers."""
    cotp = COTPData(payload=cotp_payload)
    tpkt = TPKTPacket(payload=cotp.build())
    return tpkt.build()


def build_cotp_cr_packet(
    rack: int = 0,
    slot: int = 1,
    connection_type: int = S7ConnectionType.PG,
) -> bytes:
    """Build COTP Connection Request packet."""
    cr = COTPConnectionRequest.for_s7(rack, slot, connection_type)
    tpkt = TPKTPacket(payload=cr.build())
    return tpkt.build()


def build_cotp_cc_packet(
    dst_ref: int = 0x0001,
    src_ref: int = 0x0000,
) -> bytes:
    """Build COTP Connection Confirm packet."""
    cc = COTPConnectionConfirm(dst_ref=dst_ref, src_ref=src_ref)
    tpkt = TPKTPacket(payload=cc.build())
    return tpkt.build()


def build_cotp_dr_packet(
    dst_ref: int = 0x0000,
    src_ref: int = 0x0001,
) -> bytes:
    """Build COTP Disconnect Request packet."""
    dr = COTPDisconnectRequest(dst_ref=dst_ref, src_ref=src_ref)
    tpkt = TPKTPacket(payload=dr.build())
    return tpkt.build()


def build_s7_setup_request(
    pdu_ref: int = 0x0000,
    pdu_size: int = 480,
) -> bytes:
    """Build complete S7 Setup Communication request packet."""
    s7_req = S7SetupCommunicationRequest(pdu_ref=pdu_ref, pdu_size=pdu_size)
    return build_s7_packet(s7_req.build())


def build_s7_setup_response(
    pdu_ref: int = 0x0000,
    pdu_size: int = 480,
) -> bytes:
    """Build complete S7 Setup Communication response packet."""
    s7_resp = S7SetupCommunicationResponse(pdu_ref=pdu_ref, pdu_size=pdu_size)
    return build_s7_packet(s7_resp.build())


def build_s7_read_request(
    pdu_ref: int = 0x0000,
    read_areas: list[S7ReadArea] | None = None,
) -> bytes:
    """Build complete S7 Read Variable request packet."""
    s7_req = S7ReadVarRequest(pdu_ref=pdu_ref, items=read_areas)
    return build_s7_packet(s7_req.build())


def build_s7_read_response(
    pdu_ref: int = 0x0000,
    items: list[tuple[int, bytes]] | None = None,
) -> bytes:
    """Build complete S7 Read Variable response packet."""
    s7_resp = S7ReadVarResponse(pdu_ref=pdu_ref, items=items)
    return build_s7_packet(s7_resp.build())


def build_s7_write_request(
    pdu_ref: int = 0x0000,
    write_areas: list[S7WriteArea] | None = None,
) -> bytes:
    """Build complete S7 Write Variable request packet."""
    s7_req = S7WriteVarRequest(pdu_ref=pdu_ref, items=write_areas)
    return build_s7_packet(s7_req.build())


def build_s7_write_response(
    pdu_ref: int = 0x0000,
    return_codes: list[int] | None = None,
) -> bytes:
    """Build complete S7 Write Variable response packet."""
    s7_resp = S7WriteVarResponse(pdu_ref=pdu_ref, return_codes=return_codes)
    return build_s7_packet(s7_resp.build())


def build_s7_szl_request(
    pdu_ref: int = 0x0000,
    szl_id: int = 0x0011,
    szl_index: int = 0x0000,
) -> bytes:
    """Build complete S7 SZL read request packet.

    Args:
        pdu_ref: PDU reference number
        szl_id: SZL ID to request (0x0011 = Module ID, 0x001C = Component ID)
        szl_index: Index within the SZL

    Returns:
        Complete S7 packet with TPKT/COTP/S7 headers
    """
    s7_req = S7UserdataRequest(pdu_ref=pdu_ref, szl_id=szl_id, szl_index=szl_index)
    return build_s7_packet(s7_req.build())


def build_s7_szl_response(
    pdu_ref: int = 0x0000,
    szl_id: int = 0x0011,
    szl_index: int = 0x0000,
    szl_data: bytes = b"",
) -> bytes:
    """Build complete S7 SZL read response packet.

    Args:
        pdu_ref: PDU reference number (should match request)
        szl_id: SZL ID being responded to
        szl_index: Index within the SZL
        szl_data: The actual SZL payload data (from FingerprintApplicator)

    Returns:
        Complete S7 packet with TPKT/COTP/S7 headers
    """
    s7_resp = S7UserdataResponse(
        pdu_ref=pdu_ref,
        szl_id=szl_id,
        szl_index=szl_index,
        szl_data=szl_data,
    )
    return build_s7_packet(s7_resp.build())
