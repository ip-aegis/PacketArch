# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""OPC UA projection — a named-point projection (see ``named_point``).

OPC UA addresses by node browse-name, so it uses the shared
:class:`NamedPointProjection` directly. Kept as a named alias so the OPC UA
server reads intent-revealingly.
"""

from __future__ import annotations

from .named_point import NamedPointProjection

OpcUaProjection = NamedPointProjection

__all__ = ["OpcUaProjection"]
