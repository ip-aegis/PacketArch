# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Traffic agent authentication token helpers.

Split out from api/routes/agents.py so services (local_sensor_service,
cml_service) can mint/hash agent tokens without importing a routes module —
that reverse dependency caused a circular import once routes/agents.py
itself needed to call into local_sensor_service.
"""

import hashlib
import secrets


def generate_agent_token() -> str:
    """Generate a secure random token for agent authentication."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()
