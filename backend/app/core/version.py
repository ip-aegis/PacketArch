# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Product version, ownership, and license metadata.

Single source of truth for strings surfaced in the /about endpoint, startup
logs, acknowledgment modal, and About dialog. If you change OWNER_* or
LICENSE_* here, also update NOTICE and LICENSE at the repo root.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from app.core.config import settings


# Owner / maintainer attribution. Shown in About modal, /about endpoint,
# startup logs, and source-file copyright headers.
OWNER_NAME = "Rocky Smith"
OWNER_EMAIL = "rocky.d.smith@proton.me"
OWNER_COPYRIGHT = "© 2026 Rocky Smith"

# License. PacketArch is distributed under GPL-3.0 because it depends on
# Scapy (GPLv2). Any redistribution must preserve copyright notices.
LICENSE_ID = "GPL-3.0"
LICENSE_NAME = "GNU General Public License v3.0"
LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"

# Acknowledgment document version. Bump this when you materially change
# the acknowledgment text; users will be re-prompted on next login.
ACK_DOCUMENT = "eula"
ACK_VERSION = "1.0"
ACK_TITLE = "Welcome to PacketArch"
ACK_BODY = (
    "PacketArch is free and open-source software, developed and maintained "
    f"by {OWNER_NAME} ({OWNER_EMAIL}), and licensed under {LICENSE_ID}.\n\n"
    "By continuing, you acknowledge that this software is provided AS-IS "
    "with no warranty, and that any redistribution must preserve the "
    "copyright notices and license text, as required by the license."
)


def get_build_commit() -> str:
    """Git commit SHA at build time. Set BUILD_COMMIT in the Docker build."""
    return os.environ.get("BUILD_COMMIT", "dev")


def get_build_date() -> str:
    """Build timestamp (ISO-8601 UTC). Set BUILD_DATE in the Docker build."""
    return os.environ.get("BUILD_DATE", datetime.now(timezone.utc).isoformat())


def get_startup_banner() -> str:
    """Single-line attribution printed at backend startup."""
    return (
        f"{settings.app_name} v{settings.app_version} · "
        f"{OWNER_COPYRIGHT} <{OWNER_EMAIL}> · "
        f"Licensed under {LICENSE_ID}"
    )
