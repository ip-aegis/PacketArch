# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Routes for serving agent installation resources."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, PlainTextResponse

router = APIRouter(prefix="/agent", tags=["agent-install"])

# Path to the install script (in backend/app/static/agent/)
STATIC_DIR = Path(__file__).parent.parent.parent / "static" / "agent"
INSTALL_SCRIPT_PATH = STATIC_DIR / "install.sh"
# Built image lives in the volume-backed dist/ subdir (see agents.py).
AGENT_IMAGE_PATH = STATIC_DIR / "dist" / "packetarch-agent.tar.gz"
# Content checksum written alongside the tarball by the image builder. Served as
# the X-Checksum-SHA256 header so clients (install.sh, the host-agent reconcile
# loop) can detect a new build without downloading the whole image.
AGENT_CHECKSUM_PATH = STATIC_DIR / "dist" / "checksum.txt"


@router.get("/install.sh", response_class=PlainTextResponse)
async def get_install_script():
    """Serve the agent installation script.

    This script can be piped to bash to install the PacketArch agent:

        curl -fsSLk https://server/agent/install.sh | sudo bash -s -- \\
            --server https://server --token "TOKEN" --insecure
    """
    if INSTALL_SCRIPT_PATH.exists():
        return PlainTextResponse(
            content=INSTALL_SCRIPT_PATH.read_text(),
            media_type="text/x-shellscript",
        )
    else:
        # Return a minimal script with an error message if file not found
        return PlainTextResponse(
            content='#!/bin/bash\necho "ERROR: Install script not found on server"\nexit 1\n',
            media_type="text/x-shellscript",
            status_code=404,
        )


@router.get("/docker-compose.yml", response_class=PlainTextResponse)
async def get_docker_compose():
    """Serve the agent docker-compose file."""
    compose_path = STATIC_DIR / "docker-compose.agent.yml"

    if compose_path.exists():
        return PlainTextResponse(
            content=compose_path.read_text(),
            media_type="text/yaml",
        )
    else:
        return PlainTextResponse(
            content="# ERROR: docker-compose file not found\n",
            media_type="text/yaml",
            status_code=404,
        )


MIMIC_IMAGE_PATH = STATIC_DIR / "dist" / "mimic-persona.tar.gz"

# In-memory persona check-in registry (off-box CML nodes report their own IP on
# startup, since CML doesn't surface a stock-Ubuntu node's DHCP address — this is
# the persona analogue of the agent's WebSocket phone-home).
_MIMIC_CHECKINS: dict[str, dict] = {}


@router.api_route("/mimic-checkin", methods=["GET", "POST"])
async def mimic_checkin(request: Request):
    """A CML persona node reports its name + management IP + liveness once it's up.

    GET *and* POST — a node self-reports via busybox ``wget`` (a GET), so the
    endpoint must accept GET. Arbitrary query fields (ip, modbus_listening,
    running, fc43, …) let a node report that the persona bound its protocol port,
    without the backend needing inbound reachability to a NAT'd node.
    """
    from datetime import datetime, timezone
    params = dict(request.query_params)
    name = params.pop("name", "?")
    params["at"] = datetime.now(timezone.utc).isoformat()
    _MIMIC_CHECKINS[name] = params
    return {"ok": True, "name": name, **params}


@router.get("/mimic-checkins")
async def mimic_checkins():
    """List persona check-ins (for the backend to discover node IPs)."""
    return _MIMIC_CHECKINS


@router.api_route("/mimic-image.tar.gz", methods=["GET", "HEAD"])
async def get_mimic_image():
    """Serve the Mimic persona-runtime Docker image (unauthenticated, like the
    agent image) so a CML persona node can ``docker load`` it via cloud-init."""
    if MIMIC_IMAGE_PATH.exists():
        return FileResponse(
            path=MIMIC_IMAGE_PATH,
            media_type="application/gzip",
            filename="mimic-persona.tar.gz",
        )
    return PlainTextResponse(content="ERROR: Mimic image not found on server\n", status_code=404)


@router.api_route("/image.tar.gz", methods=["GET", "HEAD"])
async def get_agent_image():
    """Serve the agent Docker image as a tar.gz file.

    This allows the install script to download and load the image
    directly from the PacketArch server without needing a registry.

    Exposes the build's content checksum as ``X-Checksum-SHA256`` and accepts
    HEAD so the host-agent reconcile loop can cheaply detect a new build (via
    the header) and reload the image only when it changed — the no-CLI
    version-bump path for local-sensor agents. FileResponse omits the body on
    HEAD, so the check stays lightweight.
    """
    if AGENT_IMAGE_PATH.exists():
        headers = {}
        if AGENT_CHECKSUM_PATH.exists():
            checksum = AGENT_CHECKSUM_PATH.read_text().strip()
            if checksum:
                headers["X-Checksum-SHA256"] = checksum
        return FileResponse(
            path=AGENT_IMAGE_PATH,
            media_type="application/gzip",
            filename="packetarch-agent.tar.gz",
            headers=headers,
        )
    else:
        return PlainTextResponse(
            content="ERROR: Agent image not found on server\n",
            status_code=404,
        )
