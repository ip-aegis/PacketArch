# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Agent configuration from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for the PacketArch agent."""

    server_url: str
    agent_token: str
    default_interface: str
    log_level: str
    ssl_verify: bool
    reconnect_delay_seconds: float
    heartbeat_interval_seconds: float
    status_report_interval_seconds: float

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create config from environment variables."""
        server_url = os.environ.get("PACKETARCH_SERVER", "")
        if not server_url:
            raise ValueError("PACKETARCH_SERVER environment variable is required")

        agent_token = os.environ.get("AGENT_TOKEN", "")
        if not agent_token:
            raise ValueError("AGENT_TOKEN environment variable is required")

        # Convert HTTP(S) URL to WebSocket URL
        ws_url = server_url.replace("https://", "wss://").replace("http://", "ws://")
        if not ws_url.endswith("/"):
            ws_url = ws_url.rstrip("/")

        # Parse SSL_VERIFY (default true, set false for self-signed certs)
        ssl_verify_str = os.environ.get("SSL_VERIFY", "true").lower()
        ssl_verify = ssl_verify_str not in ("false", "0", "no", "off")

        return cls(
            server_url=ws_url,
            agent_token=agent_token,
            default_interface=os.environ.get("DEFAULT_INTERFACE", "eth0"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            ssl_verify=ssl_verify,
            reconnect_delay_seconds=float(os.environ.get("RECONNECT_DELAY", "5")),
            heartbeat_interval_seconds=float(os.environ.get("HEARTBEAT_INTERVAL", "30")),
            status_report_interval_seconds=float(os.environ.get("STATUS_REPORT_INTERVAL", "5")),
        )

    @property
    def websocket_url(self) -> str:
        """Get the full WebSocket URL for agent connection (with token as query param)."""
        from urllib.parse import quote
        return f"{self.server_url}/ws/agent?token={quote(self.agent_token)}"
