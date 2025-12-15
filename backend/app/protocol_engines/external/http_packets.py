"""HTTP packet builders for C2 beaconing and data exfiltration.

Generates HTTP/HTTPS traffic patterns that simulate:
- C2 beacon check-ins (GET/POST to command server)
- Data exfiltration (encoded uploads)
- Malware downloads
- Web shells and backdoors

Traffic patterns are designed to trigger common IDS signatures.
"""

import base64
import random
import struct
from dataclasses import dataclass
from typing import Iterator

from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
from scapy.layers.inet import IP, TCP
from scapy.packet import Packet, Raw


# Common C2 User-Agent strings (detected by many IDS rules)
C2_USER_AGENTS = [
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)",  # Ancient IE - suspicious
    "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko",  # Old IE11
    "python-requests/2.25.1",  # Python requests - common in malware
    "curl/7.68.0",  # curl - often used in attacks
    "Wget/1.20.3",  # wget - download tool
    "Java/1.8.0_151",  # Java - common in RATs
    "",  # Empty UA - very suspicious
]

# Suspicious URL paths commonly used by C2
C2_URL_PATHS = [
    "/admin/login.php",
    "/wp-admin/admin-ajax.php",
    "/wp-content/uploads/shell.php",
    "/images/pixel.gif",
    "/api/v1/check",
    "/gate.php",
    "/panel/index.php",
    "/c2/beacon",
    "/update/check",
    "/config.json",
]

# Suspicious POST data patterns
SUSPICIOUS_POST_PATTERNS = [
    "cmd=",  # Command injection indicator
    "exec=",
    "shell=",
    "eval(",
    "base64_decode(",
    "system(",
    "passthru(",
]

# Base64-encoded command patterns (for detection)
ENCODED_COMMANDS = [
    base64.b64encode(b"whoami").decode(),
    base64.b64encode(b"ipconfig /all").decode(),
    base64.b64encode(b"systeminfo").decode(),
    base64.b64encode(b"net user").decode(),
    base64.b64encode(b"tasklist").decode(),
]


@dataclass
class HTTPBeaconConfig:
    """Configuration for HTTP beacon generation."""

    method: str = "GET"  # GET or POST
    path: str = "/api/check"
    user_agent: str | None = None  # None = random suspicious UA
    interval_ms: int = 60000  # Beacon interval
    jitter_pct: float = 0.15  # Timing jitter percentage
    include_cookie: bool = True
    cookie_name: str = "session"
    include_host: bool = True
    custom_headers: dict | None = None
    post_data: str | None = None  # For POST requests


@dataclass
class HTTPExfilConfig:
    """Configuration for HTTP exfiltration generation."""

    method: str = "POST"
    path: str = "/upload"
    encoding: str = "base64"  # base64, hex, raw
    chunk_size: int = 4096  # Bytes per request
    content_type: str = "application/octet-stream"
    use_multipart: bool = False
    filename_param: str = "file"


def build_http_beacon_request(
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int = 80,
    config: HTTPBeaconConfig | None = None,
    seq_num: int = 1000,
) -> Packet:
    """Build an HTTP beacon request packet.

    Args:
        src_ip: Source IP (infected device)
        dst_ip: Destination IP (C2 server)
        src_port: Source port
        dst_port: Destination port (usually 80 or 443)
        config: Beacon configuration
        seq_num: TCP sequence number

    Returns:
        Scapy packet with HTTP beacon request
    """
    if config is None:
        config = HTTPBeaconConfig()

    # Select suspicious user agent if not specified
    user_agent = config.user_agent or random.choice(C2_USER_AGENTS)
    path = config.path or random.choice(C2_URL_PATHS)

    # Build HTTP headers
    http_headers = f"{config.method} {path} HTTP/1.1\r\n"
    http_headers += f"Host: {dst_ip}\r\n"
    http_headers += f"User-Agent: {user_agent}\r\n"
    http_headers += "Accept: */*\r\n"
    http_headers += "Connection: keep-alive\r\n"

    if config.include_cookie:
        # Generate suspicious-looking session cookie
        cookie_value = base64.b64encode(struct.pack(">I", random.randint(0, 0xFFFFFFFF))).decode()
        http_headers += f"Cookie: {config.cookie_name}={cookie_value}\r\n"

    if config.custom_headers:
        for key, value in config.custom_headers.items():
            http_headers += f"{key}: {value}\r\n"

    # POST data for POST requests
    body = ""
    if config.method == "POST":
        if config.post_data:
            body = config.post_data
        else:
            # Generate suspicious POST data
            cmd = random.choice(ENCODED_COMMANDS)
            body = f"data={cmd}&action=exec"

        http_headers += f"Content-Length: {len(body)}\r\n"
        http_headers += "Content-Type: application/x-www-form-urlencoded\r\n"

    http_headers += "\r\n"

    # Build packet
    ip = IP(src=src_ip, dst=dst_ip)
    tcp = TCP(
        sport=src_port,
        dport=dst_port,
        flags="PA",  # PSH+ACK
        seq=seq_num,
        ack=seq_num + 1,
    )

    payload = http_headers + body
    return ip / tcp / Raw(load=payload.encode())


def build_http_beacon_response(
    src_ip: str,  # C2 server
    dst_ip: str,  # Infected device
    src_port: int = 80,
    dst_port: int = 12345,
    response_code: int = 200,
    body: str = "",
    seq_num: int = 2000,
) -> Packet:
    """Build an HTTP beacon response packet.

    Args:
        src_ip: Source IP (C2 server)
        dst_ip: Destination IP (infected device)
        src_port: Source port (usually 80)
        dst_port: Destination port
        response_code: HTTP response code
        body: Response body (commands, etc.)
        seq_num: TCP sequence number

    Returns:
        Scapy packet with HTTP response
    """
    # Status text based on code
    status_texts = {
        200: "OK",
        204: "No Content",
        302: "Found",
        404: "Not Found",
        500: "Internal Server Error",
    }
    status_text = status_texts.get(response_code, "OK")

    # Build response
    http_response = f"HTTP/1.1 {response_code} {status_text}\r\n"
    http_response += "Server: Apache/2.4.41\r\n"
    http_response += "Content-Type: text/html; charset=UTF-8\r\n"
    http_response += f"Content-Length: {len(body)}\r\n"
    http_response += "Connection: keep-alive\r\n"
    http_response += "\r\n"
    http_response += body

    ip = IP(src=src_ip, dst=dst_ip)
    tcp = TCP(
        sport=src_port,
        dport=dst_port,
        flags="PA",
        seq=seq_num,
        ack=seq_num + 1,
    )

    return ip / tcp / Raw(load=http_response.encode())


def build_http_exfil_request(
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int = 80,
    data: bytes = b"",
    config: HTTPExfilConfig | None = None,
    seq_num: int = 1000,
) -> Packet:
    """Build an HTTP data exfiltration request.

    Args:
        src_ip: Source IP (exfiltrating device)
        dst_ip: Destination IP (exfil server)
        src_port: Source port
        dst_port: Destination port
        data: Data to exfiltrate
        config: Exfil configuration
        seq_num: TCP sequence number

    Returns:
        Scapy packet with exfil request
    """
    if config is None:
        config = HTTPExfilConfig()

    # Encode data based on config
    if config.encoding == "base64":
        encoded_data = base64.b64encode(data).decode()
    elif config.encoding == "hex":
        encoded_data = data.hex()
    else:
        encoded_data = data.decode("utf-8", errors="replace")

    # Build POST body
    if config.use_multipart:
        boundary = "----WebKitFormBoundary" + "".join(random.choices("0123456789abcdef", k=16))
        body = f"--{boundary}\r\n"
        body += f'Content-Disposition: form-data; name="{config.filename_param}"; filename="data.bin"\r\n'
        body += f"Content-Type: {config.content_type}\r\n\r\n"
        body += encoded_data
        body += f"\r\n--{boundary}--\r\n"
        content_type = f"multipart/form-data; boundary={boundary}"
    else:
        body = f"data={encoded_data}"
        content_type = "application/x-www-form-urlencoded"

    # Build HTTP request
    http_request = f"POST {config.path} HTTP/1.1\r\n"
    http_request += f"Host: {dst_ip}\r\n"
    http_request += f"User-Agent: {random.choice(C2_USER_AGENTS)}\r\n"
    http_request += f"Content-Type: {content_type}\r\n"
    http_request += f"Content-Length: {len(body)}\r\n"
    http_request += "Connection: close\r\n"
    http_request += "\r\n"
    http_request += body

    ip = IP(src=src_ip, dst=dst_ip)
    tcp = TCP(
        sport=src_port,
        dport=dst_port,
        flags="PA",
        seq=seq_num,
        ack=seq_num + 1,
    )

    return ip / tcp / Raw(load=http_request.encode())


def generate_beacon_sequence(
    src_ip: str,
    dst_ip: str,
    c2_port: int = 80,
    config: HTTPBeaconConfig | None = None,
    count: int = 5,
    start_time_ms: int = 0,
) -> Iterator[tuple[int, Packet]]:
    """Generate a sequence of beacon packets with timing.

    Args:
        src_ip: Source IP (infected device)
        dst_ip: Destination IP (C2 server)
        c2_port: C2 server port
        config: Beacon configuration
        count: Number of beacon exchanges
        start_time_ms: Starting timestamp

    Yields:
        Tuple of (timestamp_ms, packet)
    """
    if config is None:
        config = HTTPBeaconConfig()

    current_time = start_time_ms
    src_port = random.randint(49152, 65535)
    seq = random.randint(1000, 0xFFFFFF)

    for i in range(count):
        # Request
        request = build_http_beacon_request(
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=c2_port,
            config=config,
            seq_num=seq,
        )
        yield (current_time, request)

        # Small delay for response (50-200ms)
        current_time += random.randint(50, 200)
        seq += len(request[Raw].load) if Raw in request else 100

        # Response
        response = build_http_beacon_response(
            src_ip=dst_ip,
            dst_ip=src_ip,
            src_port=c2_port,
            dst_port=src_port,
            response_code=200,
            body="OK",
            seq_num=seq,
        )
        yield (current_time, response)

        # Calculate next beacon time with jitter
        base_interval = config.interval_ms
        jitter = int(base_interval * config.jitter_pct)
        interval = base_interval + random.randint(-jitter, jitter)
        current_time += interval

        # Occasionally change source port
        if random.random() < 0.3:
            src_port = random.randint(49152, 65535)
