# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""System self-upgrade endpoints (admin-only, git-clone installs).

Mirrors the remote-agent update flow: a trigger endpoint launches the upgrade
and a status endpoint is polled for progress. Because the backend restarts
mid-upgrade, the work runs in a detached updater container and status lives on
a shared volume — see services/system_upgrade.py.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.api.deps import AdminUser
from app.core.config import settings
from app.services import system_upgrade

router = APIRouter(prefix="/system", tags=["System"])


class SystemVersion(BaseModel):
    current: str
    latest: str | None
    update_available: bool
    checked: bool  # False when the release source (GitHub) was unreachable


class UpgradeRequest(BaseModel):
    target: str | None = None  # vX.Y.Z; defaults to the latest release


def _semver(v: str) -> tuple[int, int, int]:
    """Parse 'v1.2.3' / '1.2.3' (tolerating describe suffixes) to a tuple."""
    core = v.lstrip("v").split("-")[0].split(".")
    nums = [int(p) for p in core[:3]] + [0, 0, 0]
    return nums[0], nums[1], nums[2]


@router.get("/version", response_model=SystemVersion)
async def get_system_version(_admin: AdminUser) -> SystemVersion:
    """Current product version vs the latest available release tag."""
    current = settings.app_version
    latest = await system_upgrade.get_latest_tag()
    update_available = False
    if latest:
        try:
            update_available = _semver(latest) > _semver(current)
        except Exception:
            update_available = False
    return SystemVersion(
        current=current,
        latest=latest,
        update_available=update_available,
        checked=latest is not None,
    )


@router.post("/upgrade")
async def start_system_upgrade(
    _admin: AdminUser, body: UpgradeRequest | None = None
) -> dict[str, Any]:
    """Launch a self-upgrade to a target release (defaults to the latest)."""
    if system_upgrade.is_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An upgrade is already in progress.",
        )

    target = body.target if body else None
    if not target:
        target = await system_upgrade.get_latest_tag()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No target version supplied and the latest release could not "
                    "be determined (offline?). Pass an explicit version."
                ),
            )
    if not system_upgrade.TAG_RE.match(target):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid version '{target}'. Expected vX.Y.Z.",
        )

    try:
        return await system_upgrade.start_upgrade(target, settings.app_version)
    except RuntimeError as exc:  # misconfiguration (HOST_INSTALL_DIR unset)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:  # docker launch failure
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to launch the updater: {exc}",
        )


@router.get("/upgrade-status")
async def get_upgrade_status(_admin: AdminUser) -> dict[str, Any]:
    """Current upgrade progress (idle when nothing is tracked)."""
    s = system_upgrade.read_status()
    if s is None:
        return {"status": "idle", "phase": "idle", "message": "No upgrade in progress"}
    return s


@router.delete("/upgrade-status", status_code=status.HTTP_204_NO_CONTENT)
async def clear_upgrade_status(_admin: AdminUser) -> Response:
    """Clear a terminal upgrade status (acknowledged by the operator)."""
    if system_upgrade.is_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot clear status while an upgrade is running.",
        )
    system_upgrade.clear_status()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
