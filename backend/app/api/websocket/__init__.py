# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""WebSocket endpoints for real-time communication."""

from app.api.websocket.agent_hub import router

__all__ = ["router"]
