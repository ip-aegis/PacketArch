"""Cloud traffic scheduler - separate thread for cloud service heartbeats.

Handles TLS heartbeat traffic to cloud services (Talk2M, TeamViewer, etc.)
independently from the OT poll loop. This ensures cloud connectivity traffic
doesn't interfere with deterministic OT polling and vice versa.
"""

import logging
import random
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether
from scapy.packet import Raw
from scapy.sendrecv import sendp

logger = logging.getLogger(__name__)

# TLS Record Types
TLS_HANDSHAKE = 0x16
TLS_APPLICATION_DATA = 0x17
TLS_ALERT = 0x15

# TLS Handshake Types
TLS_CLIENT_HELLO = 0x01
TLS_SERVER_HELLO = 0x02

# TLS Versions
TLS_VERSION_1_2 = (0x03, 0x03)
TLS_VERSION_1_3 = (0x03, 0x04)


@dataclass
class CloudHeartbeatTask:
    """A single cloud heartbeat task configuration."""

    link_id: str
    source_ip: str
    source_mac: str
    target_ip: str
    target_port: int
    hostname: str
    interval_ms: int
    tls_enabled: bool = True
    next_run: float = 0.0
    packets_sent: int = 0
    # TCP state tracking for realistic connection behavior
    src_port: int = field(default_factory=lambda: random.randint(49152, 65535))
    seq_num: int = field(default_factory=lambda: random.randint(1, 4294967295))


class CloudTrafficScheduler:
    """Separate scheduler for cloud service heartbeats.

    Runs in its own thread, independent of the OT poll loop.
    Generates TLS Client Hello packets to simulate cloud service
    connectivity checks.
    """

    def __init__(self, interface: str, gateway_mac: str | None = None):
        """Initialize the cloud traffic scheduler.

        Args:
            interface: Network interface for packet injection
            gateway_mac: MAC address of the default gateway (for external routing)
        """
        self.interface = interface
        self.gateway_mac = gateway_mac or "ff:ff:ff:ff:ff:ff"  # Broadcast if unknown
        self.tasks: list[CloudHeartbeatTask] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.packets_sent = 0

    def add_link(self, link: dict[str, Any], device: dict[str, Any]) -> None:
        """Add a cloud service link.

        Args:
            link: Cloud service link configuration from scenario definition
            device: Device configuration from scenario definition
        """
        cloud_svc = link.get("cloud_service", {})

        # Get device network info
        network = device.get("network", {})
        source_ip = network.get("ipAddress", "10.0.0.1")
        source_mac = network.get("macAddress", "00:00:00:00:00:01")

        task = CloudHeartbeatTask(
            link_id=link.get("id", f"csl_{len(self.tasks)}"),
            source_ip=source_ip,
            source_mac=source_mac,
            target_ip=cloud_svc.get("primary_ip", "0.0.0.0"),
            target_port=cloud_svc.get("port", 443),
            hostname=cloud_svc.get("hostname", ""),
            interval_ms=link.get("heartbeat_interval_ms", 30000),
            tls_enabled=cloud_svc.get("tls_enabled", True),
            # Stagger start times to avoid burst at scheduler start
            next_run=time.time() + random.uniform(1, 5),
        )

        with self._lock:
            self.tasks.append(task)

        logger.info(
            f"Added cloud link: {task.source_ip} -> {task.target_ip}:{task.target_port} "
            f"(interval={task.interval_ms}ms)"
        )

    def start(self) -> None:
        """Start the scheduler thread."""
        if self._running:
            logger.warning("Cloud scheduler already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            name="cloud-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"Started cloud scheduler with {len(self.tasks)} tasks")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info(f"Cloud scheduler stopped. Total packets sent: {self.packets_sent}")

    def _run(self) -> None:
        """Main scheduler loop."""
        while self._running:
            now = time.time()

            with self._lock:
                for task in self.tasks:
                    if now >= task.next_run:
                        self._send_heartbeat(task)
                        # Add jitter (+/- 10% of interval)
                        jitter = random.uniform(-0.1, 0.1) * (task.interval_ms / 1000)
                        task.next_run = now + (task.interval_ms / 1000) + jitter

            # Sleep for 100ms before next check (responsive but not wasteful)
            time.sleep(0.1)

    def _send_heartbeat(self, task: CloudHeartbeatTask) -> None:
        """Generate and send TLS heartbeat packets to cloud service.

        Generates a realistic TCP SYN followed by TLS Client Hello,
        simulating a device establishing a secure connection to a cloud service.
        """
        try:
            # Generate TCP SYN packet
            syn_packet = self._build_tcp_syn(task)
            sendp(syn_packet, iface=self.interface, verbose=False)

            # Small delay between SYN and Client Hello (realistic)
            time.sleep(0.05)

            # Generate TLS Client Hello
            client_hello = self._build_tls_client_hello(task)
            sendp(client_hello, iface=self.interface, verbose=False)

            task.packets_sent += 2
            self.packets_sent += 2

            # Update sequence number for next heartbeat
            task.seq_num = (task.seq_num + 100) % 4294967296

            logger.debug(
                f"Sent cloud heartbeat: {task.source_ip} -> {task.target_ip}:{task.target_port}"
            )

        except Exception as e:
            logger.error(f"Error sending cloud heartbeat for {task.link_id}: {e}")

    def _build_tcp_syn(self, task: CloudHeartbeatTask) -> bytes:
        """Build a TCP SYN packet for initiating connection.

        Args:
            task: Cloud heartbeat task

        Returns:
            Scapy packet ready for injection
        """
        # Ethernet frame - use gateway MAC for external destinations
        eth = Ether(
            src=task.source_mac,
            dst=self.gateway_mac,
        )

        # IP header
        ip = IP(
            src=task.source_ip,
            dst=task.target_ip,
            ttl=64,
        )

        # TCP SYN header
        tcp = TCP(
            sport=task.src_port,
            dport=task.target_port,
            seq=task.seq_num,
            flags="S",
            window=65535,
            options=[
                ("MSS", 1460),
                ("NOP", None),
                ("WScale", 7),
                ("NOP", None),
                ("NOP", None),
                ("SAckOK", b""),
            ],
        )

        return eth / ip / tcp

    def _build_tls_client_hello(self, task: CloudHeartbeatTask) -> bytes:
        """Build a TLS 1.2 Client Hello packet.

        Args:
            task: Cloud heartbeat task

        Returns:
            Scapy packet ready for injection
        """
        # Build TLS Client Hello payload
        client_hello = self._build_tls_client_hello_payload(task.hostname)

        # Ethernet frame
        eth = Ether(
            src=task.source_mac,
            dst=self.gateway_mac,
        )

        # IP header
        ip = IP(
            src=task.source_ip,
            dst=task.target_ip,
            ttl=64,
        )

        # TCP header with PSH+ACK flags (data transfer)
        tcp = TCP(
            sport=task.src_port,
            dport=task.target_port,
            seq=task.seq_num + 1,  # After SYN
            ack=1,  # Simplified - real would track server's ISN
            flags="PA",
            window=65535,
        )

        return eth / ip / tcp / Raw(load=client_hello)

    def _build_tls_client_hello_payload(self, hostname: str) -> bytes:
        """Build TLS 1.2 Client Hello payload with SNI extension.

        Args:
            hostname: Server hostname for SNI

        Returns:
            TLS record bytes
        """
        # Random bytes (32 bytes: 4-byte timestamp + 28 random)
        random_bytes = struct.pack(">I", int(time.time())) + bytes(
            random.randint(0, 255) for _ in range(28)
        )

        # Session ID (empty for new connection)
        session_id = b""

        # Cipher suites (common TLS 1.2 suites)
        cipher_suites = bytes(
            [
                0x00,
                0x08,  # Length: 8 bytes = 4 suites
                0xC0,
                0x2B,  # TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
                0xC0,
                0x2F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
                0xC0,
                0x2C,  # TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
                0xC0,
                0x30,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
            ]
        )

        # Compression methods (null only)
        compression = bytes([0x01, 0x00])

        # Extensions
        extensions = b""

        # SNI extension (0x0000)
        if hostname:
            hostname_bytes = hostname.encode("utf-8")
            sni_data = struct.pack(">BH", 0x00, len(hostname_bytes)) + hostname_bytes
            sni_list = struct.pack(">H", len(sni_data)) + sni_data
            extensions += struct.pack(">HH", 0x0000, len(sni_list)) + sni_list

        # Supported versions extension (0x002B) - indicate TLS 1.2/1.3
        supported_versions = bytes([0x03, 0x03, 0x03, 0x03, 0x04])  # length + TLS 1.2 + TLS 1.3
        extensions += struct.pack(">HH", 0x002B, len(supported_versions)) + supported_versions

        # EC point formats extension (0x000B)
        ec_formats = bytes([0x01, 0x00])  # uncompressed
        extensions += struct.pack(">HH", 0x000B, len(ec_formats)) + ec_formats

        # Supported groups extension (0x000A)
        groups = bytes(
            [
                0x00,
                0x06,  # length
                0x00,
                0x1D,  # x25519
                0x00,
                0x17,  # secp256r1
                0x00,
                0x18,  # secp384r1
            ]
        )
        extensions += struct.pack(">HH", 0x000A, len(groups)) + groups

        # Build Client Hello message
        client_hello = (
            bytes([TLS_VERSION_1_2[0], TLS_VERSION_1_2[1]])  # Legacy version
            + random_bytes  # Random
            + bytes([len(session_id)])
            + session_id  # Session ID
            + cipher_suites  # Cipher suites
            + compression  # Compression
            + struct.pack(">H", len(extensions))
            + extensions  # Extensions
        )

        # Handshake header
        handshake = bytes([TLS_CLIENT_HELLO]) + struct.pack(">I", len(client_hello))[1:] + client_hello

        # TLS Record header
        tls_record = (
            bytes([TLS_HANDSHAKE])  # Content type
            + bytes([TLS_VERSION_1_2[0], TLS_VERSION_1_2[1]])  # Version
            + struct.pack(">H", len(handshake))  # Length
            + handshake
        )

        return tls_record
