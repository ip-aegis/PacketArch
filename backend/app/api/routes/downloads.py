# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Routes for serving downloadable resources."""

import os
from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/downloads", tags=["downloads"])

# Path to the downloads directory
DOWNLOADS_DIR = Path(__file__).parent.parent.parent / "static" / "downloads"


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
# Three categories surface in the Settings → Downloads UI:
#
#   presentations  — exec + technical decks (PPTX / PDF / HTML / Marp source)
#   documentation  — long-form developer / operator docs
#   authoring      — the Portable Scenario Authoring Kit
#
AVAILABLE_DOWNLOADS = {
    # ── Executive Briefing (v1.5, May 2026) ──────────────────────
    # Audience: C-suite / VP / head-of-OT. Business value, risk, ROI.
    "exec-briefing-pptx": {
        "name": "Executive Briefing — PowerPoint",
        "filename": "PacketArch-Executive-Briefing.pptx",
        "description": "Slide deck for C-suite and security-leadership audiences. Covers what PacketArch is, the problem it solves, capability matrix, deployment models, economics, and a 90-day engagement roadmap. Pure business framing — pair with the Technical Deep-Dive for the engineering side.",
        "category": "presentations",
    },
    "exec-briefing-pdf": {
        "name": "Executive Briefing — PDF",
        "filename": "PacketArch-Executive-Briefing.pdf",
        "description": "Print-ready PDF of the executive deck. Identical content to the PPTX, locked layout.",
        "category": "presentations",
    },
    "exec-briefing-html": {
        "name": "Executive Briefing — HTML",
        "filename": "PacketArch-Executive-Briefing.html",
        "description": "Self-contained HTML presentation. Opens in any browser; arrow keys advance slides. Best for hand-off via email or shared drive.",
        "category": "presentations",
    },
    "exec-briefing-md": {
        "name": "Executive Briefing — Marp Source",
        "filename": "PacketArch-Executive-Briefing.md",
        "description": "Marp markdown source of the executive deck. Edit and re-render with Marp CLI to customise for your audience or branding.",
        "category": "presentations",
    },

    # ── Technical Deep-Dive (v1.5, May 2026) ─────────────────────
    # Audience: security architects, OT network engineers, SOC leads.
    "tech-deep-dive-pptx": {
        "name": "Technical Deep-Dive — PowerPoint",
        "filename": "PacketArch-Technical-Deep-Dive.pptx",
        "description": "Engineering-grade deck covering the protocol engine pattern, the unified PCAP/live traffic model, fingerprint application, conduit compliance, adaptive traffic, process simulation, live attack playbooks, after-action reporting, Cyber Vision integration, the traffic agent, and the AI architecture.",
        "category": "presentations",
    },
    "tech-deep-dive-pdf": {
        "name": "Technical Deep-Dive — PDF",
        "filename": "PacketArch-Technical-Deep-Dive.pdf",
        "description": "Print-ready PDF of the technical deck.",
        "category": "presentations",
    },
    "tech-deep-dive-html": {
        "name": "Technical Deep-Dive — HTML",
        "filename": "PacketArch-Technical-Deep-Dive.html",
        "description": "Self-contained HTML technical presentation. Arrow keys advance slides.",
        "category": "presentations",
    },
    "tech-deep-dive-md": {
        "name": "Technical Deep-Dive — Marp Source",
        "filename": "PacketArch-Technical-Deep-Dive.md",
        "description": "Marp markdown source of the technical deck. Edit and re-render with Marp CLI.",
        "category": "presentations",
    },

    # ── Cisco Briefing (May 2026) ────────────────────────────────
    # Audience: Cisco field / CV product / Cisco customer audiences.
    # Five-slide overview: cover, the gap, the platform, the workflow
    # (with bakery-demo walkthrough), Cyber Vision value prop.
    "cisco-briefing-pptx": {
        "name": "Cisco Briefing — PowerPoint",
        "filename": "PacketArch-Cisco-Briefing.pptx",
        "description": "Fully editable PowerPoint of the Cisco Briefing — every shape is a native PPT object, ready to rebrand or extend. Five slides: cover, the gap, the platform, the workflow (with the bakery-demo walkthrough), and the Cyber Vision value prop.",
        "category": "presentations",
    },
    "cisco-briefing-html": {
        "name": "Cisco Briefing — HTML",
        "filename": "PacketArch-Cisco-Briefing.html",
        "description": "Browser-viewable version of the Cisco Briefing. Self-contained HTML, fixed 16:9 layout — open in any browser, print-to-PDF for handoff.",
        "category": "presentations",
    },

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

    return DownloadsListResponse(files=files)


@router.get("/{filename}")
async def download_file(filename: str):
    """Download a specific file by filename."""
    # Security: only allow files that are in our allowed list
    allowed_filenames = {meta["filename"] for meta in AVAILABLE_DOWNLOADS.values()}

    if filename not in allowed_filenames:
        return JSONResponse(
            status_code=404,
            content={"error": "NOT_FOUND", "message": f"File '{filename}' not found"},
        )

    file_path = DOWNLOADS_DIR / filename

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
    }

    suffix = "".join(file_path.suffixes) if file_path.suffixes else file_path.suffix
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
