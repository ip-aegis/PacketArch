"""Live traffic orchestrator - injects packets onto network interface."""

import heapq
import logging
import random
import struct
import time
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.packet import Raw
from scapy.sendrecv import sendp

# EtherNet/IP constants
ENIP_CMD_LIST_IDENTITY = 0x0063
ENIP_CMD_REGISTER_SESSION = 0x0065
ENIP_CMD_SEND_RR_DATA = 0x006F
CIP_SERVICE_GET_ATTRIBUTE_ALL = 0x01
CIP_CLASS_IDENTITY = 0x01

# PROFINET constants
PROFINET_ETHERTYPE = 0x8892
DCP_SERVICE_IDENTIFY = 0x05
DCP_SERVICE_TYPE_REQUEST = 0x00
DCP_SERVICE_TYPE_RESPONSE = 0x01
DCP_MULTICAST_MAC = "01:0E:CF:00:00:00"

logger = logging.getLogger(__name__)


@dataclass
class DeviceContext:
    """Context information for a device in a flow."""
    device_id: str
    mac_address: str
    ip_address: str
    port: int
    unit_id: int = 1
    vendor_fingerprint: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowContext:
    """Context for a communication flow between devices."""
    flow_id: str
    source: DeviceContext
    destination: DeviceContext
    protocol: str
    config: dict[str, Any] = field(default_factory=dict)
    timing_model: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowState:
    """State tracking for a flow during generation."""
    flow: FlowContext
    transaction_id: int = 0
    seq_number: int = 1000
    ack_number: int = 1000
    next_poll_time: float = 0.0
    is_started: bool = False
    poll_interval_ms: float = 1000.0


class LiveTrafficOrchestrator:
    """Orchestrates live traffic injection across multiple flows."""

    def __init__(self, interface: str, duration_ms: int | None):
        """Initialize orchestrator.

        Args:
            interface: Network interface for packet injection
            duration_ms: Total duration in milliseconds, or None for perpetual mode
        """
        self.interface = interface
        self.duration_ms = duration_ms
        self.perpetual = duration_ms is None
        self.flows: list[FlowState] = []
        self.event_queue: list[tuple[float, int, Any]] = []  # (time_ms, counter, event)
        self.event_counter = 0
        self.packets_sent = 0
        self.start_time: float = 0
        self._running = True  # Flag for graceful shutdown

    def add_flow(self, flow_context: FlowContext) -> None:
        """Add a flow to be generated."""
        poll_interval = flow_context.timing_model.get("poll_interval_ms", 1000.0)

        flow_state = FlowState(
            flow=flow_context,
            poll_interval_ms=poll_interval,
            seq_number=random.randint(1000, 50000),
            ack_number=random.randint(1000, 50000),
        )

        self.flows.append(flow_state)
        logger.info(f"Added flow {flow_context.flow_id} ({flow_context.protocol})")

    def _schedule_event(self, time_ms: float, event: Any) -> None:
        """Schedule an event at a specific time."""
        heapq.heappush(self.event_queue, (time_ms, self.event_counter, event))
        self.event_counter += 1

    def _apply_jitter(self, interval_ms: float, timing_model: dict) -> float:
        """Apply jitter to an interval."""
        jitter_min = timing_model.get("jitter_min_ms", 0)
        jitter_max = timing_model.get("jitter_max_ms", 50)
        jitter = random.uniform(jitter_min, jitter_max)
        return interval_ms + jitter

    def _send_packet(self, packet_bytes: bytes) -> None:
        """Send a packet on the interface."""
        try:
            # packet_bytes is already a complete Ethernet frame from _build_tcp_packet
            # Use Raw to send the bytes directly without additional parsing
            sendp(Raw(packet_bytes), iface=self.interface, verbose=False)
            self.packets_sent += 1

            if self.packets_sent % 100 == 0:
                logger.info(f"Sent {self.packets_sent} packets")
        except Exception as e:
            logger.error(f"Failed to send packet: {e}")

    def _build_tcp_packet(
        self,
        src: DeviceContext,
        dst: DeviceContext,
        payload: bytes,
        seq: int,
        ack: int,
        flags: str = "PA",
    ) -> bytes:
        """Build a TCP packet with full headers."""
        packet = (
            Ether(src=src.mac_address, dst=dst.mac_address)
            / IP(src=src.ip_address, dst=dst.ip_address)
            / TCP(sport=src.port, dport=dst.port, seq=seq, ack=ack, flags=flags)
        )
        if payload:
            packet = packet / Raw(load=payload)
        return bytes(packet)

    def _build_modbus_request(
        self, transaction_id: int, unit_id: int, function_code: int,
        start_addr: int, quantity: int
    ) -> bytes:
        """Build a Modbus TCP request."""
        pdu = struct.pack(">BHH", function_code, start_addr, quantity)
        length = len(pdu) + 1
        mbap = struct.pack(">HHHB", transaction_id, 0, length, unit_id)
        return mbap + pdu

    def _build_modbus_response(
        self, transaction_id: int, unit_id: int, function_code: int,
        register_values: list[int]
    ) -> bytes:
        """Build a Modbus TCP response."""
        byte_count = len(register_values) * 2
        data = struct.pack(">" + "H" * len(register_values), *register_values)
        pdu = struct.pack(">BB", function_code, byte_count) + data
        length = len(pdu) + 1
        mbap = struct.pack(">HHHB", transaction_id, 0, length, unit_id)
        return mbap + pdu

    def _build_modbus_device_id_response(
        self, transaction_id: int, unit_id: int, fingerprint: dict
    ) -> bytes:
        """Build Modbus FC 43 (Read Device Identification) response.

        This response identifies the device with vendor/model/firmware info
        that security scanners like Cisco Cyber Vision use for device detection.
        """
        modbus_identity = fingerprint.get("modbus_identity", {})

        # Object IDs for device identification
        objects = []
        object_data = {
            0x00: modbus_identity.get("vendor_name", "Unknown Vendor"),
            0x01: modbus_identity.get("product_code", "Unknown"),
            0x02: modbus_identity.get("major_minor_revision", "1.0"),
            0x03: modbus_identity.get("vendor_url", ""),
            0x04: modbus_identity.get("product_name", ""),
            0x05: modbus_identity.get("model_name", ""),
        }

        for obj_id, value in object_data.items():
            if value:
                value_bytes = value.encode("ascii")[:255]
                objects.append(struct.pack("BB", obj_id, len(value_bytes)) + value_bytes)

        # Build MEI response
        # FC 43 (0x2B), MEI type 0x0E, Read Device ID code, Conformity level, More follows, Next obj ID, Number of objects
        object_bytes = b"".join(objects)
        mei_response = struct.pack(
            ">BBBBBBB",
            0x2B,  # Function code 43
            0x0E,  # MEI type (Read Device Identification)
            0x01,  # Read Device ID code (basic)
            0x01,  # Conformity level (basic)
            0x00,  # More follows (no)
            0x00,  # Next object ID
            len(objects),  # Number of objects
        ) + object_bytes

        # MBAP header
        length = len(mei_response) + 1
        mbap = struct.pack(">HHHB", transaction_id, 0, length, unit_id)
        return mbap + mei_response

    def _build_udp_packet(
        self,
        src: DeviceContext,
        dst: DeviceContext,
        payload: bytes,
    ) -> bytes:
        """Build a UDP packet with full headers."""
        packet = (
            Ether(src=src.mac_address, dst=dst.mac_address)
            / IP(src=src.ip_address, dst=dst.ip_address)
            / UDP(sport=src.port, dport=dst.port)
            / Raw(load=payload)
        )
        return bytes(packet)

    def _build_enip_list_identity_request(self) -> bytes:
        """Build EtherNet/IP ListIdentity request."""
        # Encapsulation header (24 bytes) - no data for ListIdentity request
        # Command(2) + Length(2) + Session(4) + Status(4) + Context(8) + Options(4)
        return struct.pack(
            "<HHIIQI",
            ENIP_CMD_LIST_IDENTITY,  # Command
            0,                        # Length (no data)
            0,                        # Session handle
            0,                        # Status
            0,                        # Sender context (8 bytes)
            0,                        # Options (4 bytes)
        )

    def _build_enip_list_identity_response(
        self, src: DeviceContext, fingerprint: dict
    ) -> bytes:
        """Build EtherNet/IP ListIdentity response with device fingerprint."""
        eip_identity = fingerprint.get("ethernet_ip_identity", {})

        vendor_id = eip_identity.get("vendor_id", 1)
        device_type = eip_identity.get("device_type", 14)
        product_code = eip_identity.get("product_code", 1)
        revision_major = eip_identity.get("revision_major", 1)
        revision_minor = eip_identity.get("revision_minor", 0)
        serial_number = eip_identity.get("serial_number", 0x12345678)
        product_name = eip_identity.get("product_name", "Unknown Device")[:32]
        state = eip_identity.get("state", 3)

        # Socket address info (16 bytes)
        ip_parts = [int(x) for x in src.ip_address.split(".")]
        socket_addr = struct.pack(
            ">HHBBBB8s",
            2,  # sin_family (AF_INET)
            src.port,
            ip_parts[0], ip_parts[1], ip_parts[2], ip_parts[3],
            b"\x00" * 8,  # sin_zero
        )

        # Identity item data (inside the CIP Identity item)
        # Format: Protocol Version + Socket Address + Identity attributes
        product_name_bytes = product_name.encode("utf-8")

        # Identity attributes after socket address
        # Vendor(2) + DevType(2) + ProdCode(2) + RevMajor(1) + RevMinor(1) + Status(2) + Serial(4) + NameLen(1)
        identity_attrs = struct.pack(
            "<HHHBBHIB",
            vendor_id,
            device_type,
            product_code,
            revision_major,
            revision_minor,
            0x0030,        # Status (owned)
            serial_number,
            len(product_name_bytes),
        ) + product_name_bytes + struct.pack("<B", state)

        # CIP Identity item data: protocol version (2) + socket addr (16) + identity attrs
        identity_item_data = struct.pack("<H", 0x0001) + socket_addr + identity_attrs

        # CPF structure: 1 item of type 0x000C (CIP Identity)
        cpf_data = struct.pack(
            "<HHH",
            1,              # Item count = 1
            0x000C,         # Item type = CIP Identity
            len(identity_item_data),  # Item length
        ) + identity_item_data

        # Encapsulation header (24 bytes)
        # Command(2) + Length(2) + Session(4) + Status(4) + Context(8) + Options(4)
        header = struct.pack(
            "<HHIIQI",
            ENIP_CMD_LIST_IDENTITY,
            len(cpf_data),
            0,  # Session handle
            0,  # Status
            0,  # Sender context (8 bytes)
            0,  # Options (4 bytes)
        )

        return header + cpf_data

    def _build_cip_identity_response(self, fingerprint: dict) -> bytes:
        """Build CIP GetAttributeAll response for Identity Object."""
        eip_identity = fingerprint.get("ethernet_ip_identity", {})
        cip_identity = fingerprint.get("cip_identity_object", {})

        vendor_id = eip_identity.get("vendor_id", 1)
        device_type = eip_identity.get("device_type", 14)
        product_code = eip_identity.get("product_code", 1)
        revision_major = eip_identity.get("revision_major", 1)
        revision_minor = eip_identity.get("revision_minor", 0)
        serial_number = eip_identity.get("serial_number", 0x12345678)
        product_name = eip_identity.get("product_name", "Unknown")[:32]
        state = eip_identity.get("state", 3)

        # Build Identity Object attributes
        product_name_bytes = product_name.encode("utf-8")
        attr_data = struct.pack(
            "<HHHBBHI",
            vendor_id,
            device_type,
            product_code,
            revision_major,
            revision_minor,
            0x0030,  # Status
            serial_number,
        ) + struct.pack("<B", len(product_name_bytes)) + product_name_bytes
        attr_data += struct.pack("<B", state)

        # Add extended attributes (9-20) from cip_identity_object
        config_consistency = cip_identity.get("configuration_consistency_value", 0)
        heartbeat = cip_identity.get("heartbeat_interval", 250)
        protection_mode = cip_identity.get("protection_mode", 0)
        max_connections = cip_identity.get("maximum_cip_connections", 32)

        attr_data += struct.pack("<IBHH", config_consistency, heartbeat, protection_mode, max_connections)

        # CIP response header (service | 0x80, reserved, status, additional_status_size)
        response = struct.pack("<BBBB", CIP_SERVICE_GET_ATTRIBUTE_ALL | 0x80, 0, 0, 0) + attr_data
        return response

    def _build_profinet_dcp_identify_request(self, src: DeviceContext, xid: int) -> bytes:
        """Build PROFINET DCP Identify Request.

        Args:
            src: Source device context
            xid: Transaction ID (must match corresponding response)
        """
        # DCP header
        dcp_header = struct.pack(
            ">BBIHH",
            DCP_SERVICE_IDENTIFY,  # Service ID
            DCP_SERVICE_TYPE_REQUEST,  # Service type
            xid,  # Transaction ID
            0,    # Response delay
            0,    # Data length (no filter blocks)
        )

        # Build Ethernet frame with PROFINET EtherType
        frame = (
            Ether(src=src.mac_address, dst=DCP_MULTICAST_MAC, type=PROFINET_ETHERTYPE)
            / Raw(load=struct.pack(">H", 0xFEFE) + dcp_header)  # 0xFEFE = DCP frame ID
        )
        return bytes(frame)

    def _build_profinet_dcp_identify_response(
        self, src: DeviceContext, dst: DeviceContext, xid: int
    ) -> bytes:
        """Build PROFINET DCP Identify Response with device fingerprint."""
        fingerprint = src.vendor_fingerprint
        pn_identity = fingerprint.get("profinet_identity", {})

        # Get identity values (support multiple key formats)
        # Ensure integer types for struct packing
        station_name = pn_identity.get("station_name", f"device-{src.device_id[:8]}")
        vendor_id = int(pn_identity.get("vendor_id", 0x002A))
        device_id = int(pn_identity.get("device_id", 0x0001))

        # Handle device_role - can be int or string like "controller", "device"
        raw_role = pn_identity.get("device_role", 0x01)
        if isinstance(raw_role, str):
            role_map = {"device": 1, "controller": 2, "multidevice": 4, "supervisor": 8}
            device_role = role_map.get(raw_role.lower(), 1)
        else:
            device_role = int(raw_role)
        order_id = pn_identity.get("order_id") or pn_identity.get("im0_order_id", "")
        sw_revision = (
            pn_identity.get("software_revision") or
            pn_identity.get("sw_release") or
            pn_identity.get("im0_sw_revision") or
            "V1.0"
        )
        hw_revision = pn_identity.get("hardware_revision") or pn_identity.get("im0_hw_revision", "1.0")
        if isinstance(hw_revision, int):
            hw_revision = str(hw_revision)
        serial_number = pn_identity.get("serial_number") or pn_identity.get("im0_serial_number", "")
        device_type = pn_identity.get("device_type", "")

        # Build DCP blocks
        blocks = b""

        # Station name block (Option 0x02, Suboption 0x02)
        name_bytes = station_name.encode("ascii")
        blocks += struct.pack(">BBHH", 0x02, 0x02, len(name_bytes) + 2, 0x0000) + name_bytes
        if len(name_bytes) % 2:
            blocks += b"\x00"  # Padding

        # Device ID block (Option 0x02, Suboption 0x01)
        blocks += struct.pack(">BBHHH", 0x02, 0x01, 6, 0x0000, vendor_id) + struct.pack(">H", device_id)

        # Device Role block (Option 0x02, Suboption 0x04)
        # Format: Option(1) + Suboption(1) + Length(2) + BlockInfo(2) + DeviceRole(1) + Reserved(1)
        # Length = 4: BlockInfo(2) + DeviceRole(1) + Reserved(1)
        blocks += struct.pack(">BBHHBB", 0x02, 0x04, 4, 0x0000, device_role, 0x00)

        # IP Address block (Option 0x01, Suboption 0x02)
        ip_parts = [int(x) for x in src.ip_address.split(".")]
        ip_block = struct.pack(">H", 0x0001)  # IP set flag
        ip_block += bytes(ip_parts)  # IP address
        ip_block += bytes([255, 255, 255, 0])  # Subnet mask
        ip_block += bytes([0, 0, 0, 0])  # Gateway
        blocks += struct.pack(">BBH", 0x01, 0x02, len(ip_block)) + ip_block

        # OEM Device ID block (Option 0x02, Suboption 0x08) - Contains firmware version!
        oem_parts = []
        if order_id:
            oem_parts.append(f"OrderID:{order_id}")
        if serial_number:
            oem_parts.append(f"SN:{serial_number}")
        if device_type:
            oem_parts.append(f"Type:{device_type}")
        if hw_revision:
            oem_parts.append(f"HW:{hw_revision}")
        if sw_revision:
            oem_parts.append(f"SW:{sw_revision}")  # KEY for CVE detection

        if oem_parts:
            oem_data = ";".join(oem_parts).encode("ascii")
            oem_len = len(oem_data) + 2
            blocks += struct.pack(">BBH", 0x02, 0x08, oem_len) + struct.pack(">H", 0x0000) + oem_data
            if len(oem_data) % 2:
                blocks += b"\x00"  # Padding

        # DCP header
        dcp_header = struct.pack(
            ">BBIHH",
            DCP_SERVICE_IDENTIFY,
            DCP_SERVICE_TYPE_RESPONSE,
            xid,
            0,  # Response delay
            len(blocks),
        )

        # Build Ethernet frame
        frame = (
            Ether(src=src.mac_address, dst=dst.mac_address, type=PROFINET_ETHERTYPE)
            / Raw(load=struct.pack(">H", 0xFEFF) + dcp_header + blocks)  # 0xFEFF = DCP response frame ID
        )
        return bytes(frame)

    def _generate_discovery_sequences(self, time_ms: float) -> float:
        """Generate protocol-specific discovery sequences for all flows.

        Returns the timestamp after all discovery packets are scheduled.
        """
        current_time = time_ms

        # Track devices we've already generated discovery for (avoid duplicates)
        discovered_devices: set[str] = set()

        for flow_state in self.flows:
            flow = flow_state.flow
            protocol = flow.protocol
            dst = flow.destination
            src = flow.source

            if protocol == "ethernet_ip":
                # EtherNet/IP ListIdentity - generate for BOTH source and target devices
                for device in [dst, src]:
                    eip_identity = device.vendor_fingerprint.get("ethernet_ip_identity")
                    if eip_identity and device.device_id not in discovered_devices:
                        discovered_devices.add(device.device_id)

                        # ListIdentity request (broadcast discovery)
                        request = self._build_enip_list_identity_request()
                        # Use a scanner context for the request
                        scanner = DeviceContext(
                            device_id="scanner",
                            mac_address=src.mac_address if device == dst else dst.mac_address,
                            ip_address=src.ip_address if device == dst else dst.ip_address,
                            port=50000,
                        )
                        request_pkt = self._build_udp_packet(scanner, device, request)
                        self._schedule_event(current_time, ("packet", request_pkt))

                        # ListIdentity response (device -> scanner)
                        response = self._build_enip_list_identity_response(device, device.vendor_fingerprint)
                        device_response = DeviceContext(
                            device_id=device.device_id,
                            mac_address=device.mac_address,
                            ip_address=device.ip_address,
                            port=44818,
                            vendor_fingerprint=device.vendor_fingerprint,
                        )
                        response_pkt = self._build_udp_packet(device_response, scanner, response)
                        self._schedule_event(current_time + 20, ("packet", response_pkt))

                        current_time += 100
                        logger.info(
                            f"Scheduled EtherNet/IP discovery for {device.ip_address} "
                            f"(vendor={eip_identity.get('vendor_id')}, product={eip_identity.get('product_name', '')[:20]})"
                        )

            elif protocol in ("profinet", "profisafe"):
                # PROFINET DCP Identify - generate for BOTH source and target devices
                for device in [dst, src]:
                    pn_identity = device.vendor_fingerprint.get("profinet_identity")
                    if pn_identity and device.device_id not in discovered_devices:
                        discovered_devices.add(device.device_id)
                        xid = random.randint(1, 0xFFFFFFFF)

                        # DCP Identify request (multicast)
                        other = src if device == dst else dst
                        request = self._build_profinet_dcp_identify_request(other, xid)
                        self._schedule_event(current_time, ("packet", request))

                        # DCP Identify response (device -> controller)
                        response = self._build_profinet_dcp_identify_response(device, other, xid)
                        self._schedule_event(current_time + 30, ("packet", response))

                        current_time += 100
                        logger.info(
                            f"Scheduled PROFINET DCP discovery for {device.mac_address} "
                            f"(vendor_id=0x{pn_identity.get('vendor_id', 0):04X}, "
                            f"station={pn_identity.get('station_name', 'unknown')}, "
                            f"order_id={pn_identity.get('order_id', 'none')})"
                        )

            elif protocol == "modbus_tcp":
                # Modbus FC 43 Read Device Identification
                if dst.vendor_fingerprint.get("modbus_identity"):
                    # This will be sent as part of the first poll cycle
                    # Mark that we should send FC 43 request
                    flow_state.flow.config["send_device_id_request"] = True
                    logger.info(f"Will send Modbus FC 43 for {dst.ip_address}")

        return current_time

    def _generate_startup(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate TCP handshake for a flow."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        # SYN from client
        syn = self._build_tcp_packet(src, dst, b"", flow_state.seq_number, 0, "S")
        self._schedule_event(time_ms, ("packet", syn))

        # SYN-ACK from server
        syn_ack = self._build_tcp_packet(
            dst, src, b"", flow_state.ack_number, flow_state.seq_number + 1, "SA"
        )
        self._schedule_event(time_ms + 5, ("packet", syn_ack))

        # ACK from client
        ack = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number + 1, flow_state.ack_number + 1, "A"
        )
        self._schedule_event(time_ms + 10, ("packet", ack))

        flow_state.seq_number += 1
        flow_state.ack_number += 1
        flow_state.is_started = True

    def _generate_poll_cycle(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate a request/response cycle."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        flow_state.transaction_id += 1

        if flow.protocol == "modbus_tcp":
            # Modbus request
            config = flow.config
            unit_id = dst.unit_id or 1

            # Check if we should send FC 43 (Read Device Identification) first
            if config.get("send_device_id_request") and dst.vendor_fingerprint.get("modbus_identity"):
                # Send FC 43 request/response for device identification
                config["send_device_id_request"] = False  # Only send once

                # FC 43 Request (MEI type 0x0E, device ID code 0x01)
                fc43_request = struct.pack(
                    ">HHHBBBB",
                    flow_state.transaction_id,  # Transaction ID
                    0,  # Protocol ID
                    5,  # Length
                    unit_id,
                    0x2B,  # Function code 43
                    0x0E,  # MEI type
                    0x01,  # Read Device ID code (basic)
                )
                fc43_request_pkt = self._build_tcp_packet(
                    src, dst, fc43_request, flow_state.seq_number, flow_state.ack_number
                )
                self._schedule_event(time_ms, ("packet", fc43_request_pkt))

                # FC 43 Response with device identification
                fc43_response = self._build_modbus_device_id_response(
                    flow_state.transaction_id, unit_id, dst.vendor_fingerprint
                )
                fc43_response_pkt = self._build_tcp_packet(
                    dst, src, fc43_response,
                    flow_state.ack_number, flow_state.seq_number + len(fc43_request)
                )
                self._schedule_event(time_ms + 25, ("packet", fc43_response_pkt))

                flow_state.seq_number += len(fc43_request)
                flow_state.ack_number += len(fc43_response)
                flow_state.transaction_id += 1
                time_ms += 100  # Add delay before normal poll

                logger.info(f"Sent Modbus FC 43 device identification for {dst.ip_address}")

            function_code = config.get("function_code", 3)
            start_addr = config.get("start_address", 0)
            quantity = config.get("quantity", 10)

            request_payload = self._build_modbus_request(
                flow_state.transaction_id, unit_id, function_code, start_addr, quantity
            )
            request_pkt = self._build_tcp_packet(
                src, dst, request_payload, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms, ("packet", request_pkt))

            # Response with random values
            response_values = [random.randint(0, 65535) for _ in range(quantity)]
            response_payload = self._build_modbus_response(
                flow_state.transaction_id, unit_id, function_code, response_values
            )

            # Response timing with jitter
            response_delay = random.uniform(5, 50)
            response_pkt = self._build_tcp_packet(
                dst, src, response_payload,
                flow_state.ack_number, flow_state.seq_number + len(request_payload)
            )
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

            # Update sequence numbers
            flow_state.seq_number += len(request_payload)
            flow_state.ack_number += len(response_payload)

        else:
            # Generic TCP traffic for other protocols (profinet, ethernet_ip, etc.)
            # Generate a simple request/response with random payload data
            request_payload = struct.pack(
                ">HHI",
                flow_state.transaction_id,  # Transaction ID
                random.randint(1, 100),     # Function/command code
                random.randint(0, 1000),    # Data value
            ) + bytes(random.randint(0, 255) for _ in range(random.randint(4, 20)))

            request_pkt = self._build_tcp_packet(
                src, dst, request_payload, flow_state.seq_number, flow_state.ack_number
            )
            self._schedule_event(time_ms, ("packet", request_pkt))

            # Generate response
            response_payload = struct.pack(
                ">HHI",
                flow_state.transaction_id,
                0,  # Success status
                random.randint(0, 65535),
            ) + bytes(random.randint(0, 255) for _ in range(random.randint(8, 32)))

            response_delay = random.uniform(5, 50)
            response_pkt = self._build_tcp_packet(
                dst, src, response_payload,
                flow_state.ack_number, flow_state.seq_number + len(request_payload)
            )
            self._schedule_event(time_ms + response_delay, ("packet", response_pkt))

            # Update sequence numbers
            flow_state.seq_number += len(request_payload)
            flow_state.ack_number += len(response_payload)

    def _generate_shutdown(self, flow_state: FlowState, time_ms: float) -> None:
        """Generate TCP connection teardown."""
        flow = flow_state.flow
        src = flow.source
        dst = flow.destination

        # FIN from client
        fin = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number, flow_state.ack_number, "FA"
        )
        self._schedule_event(time_ms, ("packet", fin))

        # FIN-ACK from server
        fin_ack = self._build_tcp_packet(
            dst, src, b"", flow_state.ack_number, flow_state.seq_number + 1, "FA"
        )
        self._schedule_event(time_ms + 5, ("packet", fin_ack))

        # ACK from client
        ack = self._build_tcp_packet(
            src, dst, b"", flow_state.seq_number + 1, flow_state.ack_number + 1, "A"
        )
        self._schedule_event(time_ms + 10, ("packet", ack))

    def stop(self) -> None:
        """Signal the orchestrator to stop (for graceful shutdown)."""
        self._running = False

    def run(self) -> int:
        """Run the traffic generation.

        Returns:
            Number of packets sent
        """
        logger.info(f"Starting live traffic generation on interface {self.interface}")
        if self.perpetual:
            logger.info(f"Mode: PERPETUAL (runs until stopped), Flows: {len(self.flows)}")
        else:
            logger.info(f"Duration: {self.duration_ms}ms, Flows: {len(self.flows)}")

        self.start_time = time.time() * 1000

        # Schedule discovery sequences first (device fingerprinting)
        discovery_end_time = self._generate_discovery_sequences(0)
        logger.info(f"Discovery sequences scheduled up to {discovery_end_time}ms")

        # Track last discovery time for periodic re-discovery in perpetual mode
        last_discovery_real_time = time.time()
        DISCOVERY_INTERVAL = 30.0  # Re-broadcast discovery every 30 seconds

        # Schedule startup for all flows (after discovery)
        startup_base_time = discovery_end_time + 50
        for i, flow_state in enumerate(self.flows):
            startup_offset = startup_base_time + (i * 100)  # Stagger startups
            self._generate_startup(flow_state, startup_offset)

            # Schedule first poll
            first_poll = startup_offset + 50 + self._apply_jitter(
                flow_state.poll_interval_ms, flow_state.flow.timing_model
            )
            self._schedule_event(first_poll, ("poll", flow_state.flow.flow_id))

        # Main event loop
        while self.event_queue and self._running:
            event_time, _, event = heapq.heappop(self.event_queue)

            # Check if we've exceeded duration (only for timed mode)
            if not self.perpetual and event_time > self.duration_ms:
                break

            # Wait until event time
            current_time = (time.time() * 1000) - self.start_time
            if event_time > current_time:
                sleep_time = (event_time - current_time) / 1000
                time.sleep(sleep_time)

            # Handle event
            if event[0] == "packet":
                self._send_packet(event[1])
            elif event[0] == "poll":
                flow_id = event[1]
                for flow_state in self.flows:
                    if flow_state.flow.flow_id == flow_id:
                        self._generate_poll_cycle(flow_state, event_time)
                        # Schedule next poll
                        next_poll = event_time + self._apply_jitter(
                            flow_state.poll_interval_ms, flow_state.flow.timing_model
                        )
                        # In perpetual mode, always schedule next poll
                        # In timed mode, only if within duration
                        if self.perpetual or next_poll < self.duration_ms:
                            self._schedule_event(next_poll, ("poll", flow_id))
                        break

            # Periodic re-discovery for perpetual mode (ensures Cyber Vision catches fingerprints)
            if self.perpetual:
                current_real_time = time.time()
                if current_real_time - last_discovery_real_time >= DISCOVERY_INTERVAL:
                    logger.info("Re-broadcasting discovery sequences for device fingerprinting")
                    # Use current event time for scheduling
                    self._generate_discovery_sequences(event_time)
                    last_discovery_real_time = current_real_time

        # Generate shutdown sequences (only for timed mode or when stopped)
        if not self.perpetual or not self._running:
            current_time = (time.time() * 1000) - self.start_time
            shutdown_time = self.duration_ms if not self.perpetual else current_time
            for flow_state in self.flows:
                self._generate_shutdown(flow_state, shutdown_time)
                shutdown_time += 20

            # Process remaining shutdown events
            while self.event_queue:
                event_time, _, event = heapq.heappop(self.event_queue)
                current_time = (time.time() * 1000) - self.start_time
                if event_time > current_time:
                    sleep_time = (event_time - current_time) / 1000
                    time.sleep(sleep_time)

                if event[0] == "packet":
                    self._send_packet(event[1])

        logger.info(f"Generation complete: {self.packets_sent} packets sent")
        return self.packets_sent
