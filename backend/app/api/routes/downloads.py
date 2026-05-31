# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Routes for serving downloadable resources."""

import os
import re
from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/downloads", tags=["downloads"])

# Path to the downloads directory (small artifacts baked into the image).
DOWNLOADS_DIR = Path(__file__).parent.parent.parent / "static" / "downloads"

# Path to built virtual-appliance OVAs. These are large (~2 GB) so they are
# NOT baked into the image — instead the host's build output dir (where
# scripts/ova/build-ova.sh writes) is bind-mounted here read-only. Absent on
# installs that never built an appliance, in which case no OVA is listed.
APPLIANCE_DIR = Path(os.environ.get("APPLIANCE_DIR", "/app/appliance"))

_OVA_VERSION_RE = re.compile(r"^packetarch-(?P<version>.+)-appliance\.ova$")


class DownloadableFile(BaseModel):
    """Schema for a downloadable file."""

    name: str
    filename: str
    description: str
    size_bytes: int
    size_human: str
    category: str


class DownloadsListResponse(BaseModel):
    """Schema for list of downloadable files."""

    files: List[DownloadableFile]


def get_human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# Define available downloads with metadata.
#
# Two categories surface in the Settings → Downloads UI:
#
#   authoring      — the Portable Scenario Authoring Kit
#   appliance      — the built virtual appliance OVA (scanned from disk)
#
AVAILABLE_DOWNLOADS = {
    # ── Portable Scenario Authoring Kit ──────────────────────────
    # These four files together let any external program (or AI)
    # generate a .pascenario.json that this PacketArch install can
    # import. Designed for airgapped authors — no network access to
    # the server is required.
    "portable-scenario-llm-prompt": {
        "name": "LLM Authoring Prompt (start here)",
        "filename": "LLM_PROMPT.md",
        "description": "Ready-to-paste prompt for Claude / GPT / Gemini that encodes every authoring rule, vendor-protocol affinity, realistic timing, and a self-check. Attach this plus the schema (and optionally the fingerprint registry) to a chat, swap the bracketed scenario sentence at the bottom, and you'll get an importable JSON back.",
        "category": "authoring",
    },
    "portable-scenario-spec": {
        "name": "Portable Scenario Authoring Guide",
        "filename": "SCENARIO_SPEC.md",
        "description": "Long-form authoring guide. Covers the five realism dimensions, the three authoring modes (capability / vendor-pinned / fully-specified), the complete schema reference, vendor-protocol affinity, IEC 62443 conduit compliance, two worked examples, a validation checklist, and the airgap workflow.",
        "category": "authoring",
    },
    "portable-scenario-schema": {
        "name": "Portable Scenario JSON Schema (v1)",
        "filename": "packetarch-scenario.v1.json",
        "description": "The format contract. Drop this into any JSON Schema validator (ajv, check-jsonschema, VS Code) to verify a scenario file before transfer across an air gap. Equivalent to GET /api/v1/scenarios/schema/portable.json against this install.",
        "category": "authoring",
    },
    "fingerprint-registry": {
        "name": "Fingerprint Registry Snapshot (v1)",
        "filename": "fingerprint-registry.v1.json",
        "description": "Static snapshot of the device template catalog (~300 entries, 18 vendors). Use only when you want to pin specific `fingerprint_model` values. Capability-mode authoring doesn't need this file — the importer resolves vendor and model from the live catalog.",
        "category": "authoring",
    },
}


def scan_appliance_ovas() -> List[Path]:
    """Return built appliance OVAs (newest first), or [] if none/absent."""
    if not APPLIANCE_DIR.is_dir():
        return []
    ovas = [p for p in APPLIANCE_DIR.glob("*.ova") if p.is_file()]
    return sorted(ovas, key=lambda p: p.stat().st_mtime, reverse=True)


def _appliance_download(ova: Path) -> DownloadableFile:
    """Build the DownloadableFile entry for an appliance OVA."""
    match = _OVA_VERSION_RE.match(ova.name)
    version = match.group("version") if match else None
    name = (
        f"PacketArch Virtual Appliance {version} (OVA)"
        if version
        else "PacketArch Virtual Appliance (OVA)"
    )
    size_bytes = ova.stat().st_size
    return DownloadableFile(
        name=name,
        filename=ova.name,
        description=(
            "Self-contained virtual appliance. Import into VirtualBox, VMware "
            "Workstation/Player, or ESXi/vSphere and power on — it self-configures "
            "on first boot (loads images, mints fresh secrets + a self-signed TLS "
            "cert) and lands on the setup wizard at https://<appliance-ip>/. "
            "Console login ubuntu / packetarch (change after first login). "
            "Large file — the download streams directly from the server."
        ),
        size_bytes=size_bytes,
        size_human=get_human_size(size_bytes),
        category="appliance",
    )


@router.get("", response_model=DownloadsListResponse)
async def list_downloads():
    """List all available downloadable files."""
    files = []

    # Ensure downloads directory exists
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    for key, meta in AVAILABLE_DOWNLOADS.items():
        file_path = DOWNLOADS_DIR / meta["filename"]
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            files.append(
                DownloadableFile(
                    name=meta["name"],
                    filename=meta["filename"],
                    description=meta["description"],
                    size_bytes=size_bytes,
                    size_human=get_human_size(size_bytes),
                    category=meta["category"],
                )
            )

    # Appliance OVAs (bind-mounted from the host build dir; usually 0 or 1).
    for ova in scan_appliance_ovas():
        files.append(_appliance_download(ova))

    return DownloadsListResponse(files=files)


@router.get("/{filename}")
async def download_file(filename: str):
    """Download a specific file by filename."""
    # Security: only allow files that are in our allowed list. The allowed set
    # is the static catalog plus any built appliance OVAs (resolved from a
    # separate, bind-mounted dir — never inside DOWNLOADS_DIR).
    static_allowed = {meta["filename"] for meta in AVAILABLE_DOWNLOADS.values()}
    appliance_paths = {p.name: p for p in scan_appliance_ovas()}

    if filename in static_allowed:
        file_path = DOWNLOADS_DIR / filename
    elif filename in appliance_paths:
        file_path = appliance_paths[filename]
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "NOT_FOUND", "message": f"File '{filename}' not found"},
        )

    if not file_path.exists():
        return JSONResponse(
            status_code=404,
            content={
                "error": "NOT_FOUND",
                "message": f"File '{filename}' is not available for download",
            },
        )

    # Determine media type based on extension
    media_types = {
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".html": "text/html",
        ".md": "text/markdown",
        ".json": "application/json",
        ".zip": "application/zip",
        ".tar.gz": "application/gzip",
        ".ova": "application/octet-stream",
    }

    # Prefer a multi-suffix match (e.g. .tar.gz), else the final suffix. Using
    # the final suffix avoids version dots in OVA names (1.6.0) confusing the
    # multi-suffix join.
    media_type = media_types.get(
        "".join(file_path.suffixes),
        media_types.get(file_path.suffix, "application/octet-stream"),
    )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
