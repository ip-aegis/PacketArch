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


# Define available downloads with metadata
AVAILABLE_DOWNLOADS = {
    "packetarch-briefing-pptx": {
        "name": "PacketArch Briefing Deck (PowerPoint)",
        "filename": "PacketArch-Briefing.pptx",
        "description": "Comprehensive PowerPoint slide deck covering PacketArch architecture, features, and capabilities (~40 slides)",
        "category": "documentation",
    },
    "packetarch-briefing-pdf": {
        "name": "PacketArch Briefing Deck (PDF)",
        "filename": "PacketArch-Briefing.pdf",
        "description": "PDF version of the briefing deck for viewing and printing",
        "category": "documentation",
    },
    "packetarch-briefing-html": {
        "name": "PacketArch Briefing (HTML)",
        "filename": "PacketArch-Briefing.html",
        "description": "Interactive HTML presentation - view in browser with arrow key navigation",
        "category": "documentation",
    },
    "packetarch-briefing-md": {
        "name": "PacketArch Briefing (Marp Source)",
        "filename": "PacketArch-Briefing.md",
        "description": "Marp markdown source for the briefing deck - can be edited and re-exported using Marp CLI",
        "category": "documentation",
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
