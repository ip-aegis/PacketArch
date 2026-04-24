# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Routes for serving agent installation resources."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse

router = APIRouter(prefix="/agent", tags=["agent-install"])

# Path to the install script (in backend/app/static/agent/)
STATIC_DIR = Path(__file__).parent.parent.parent / "static" / "agent"
INSTALL_SCRIPT_PATH = STATIC_DIR / "install.sh"
AGENT_IMAGE_PATH = STATIC_DIR / "packetarch-agent.tar.gz"


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


@router.get("/image.tar.gz")
async def get_agent_image():
    """Serve the agent Docker image as a tar.gz file.

    This allows the install script to download and load the image
    directly from the PacketArch server without needing a registry.
    """
    if AGENT_IMAGE_PATH.exists():
        return FileResponse(
            path=AGENT_IMAGE_PATH,
            media_type="application/gzip",
            filename="packetarch-agent.tar.gz",
        )
    else:
        return PlainTextResponse(
            content="ERROR: Agent image not found on server\n",
            status_code=404,
        )
