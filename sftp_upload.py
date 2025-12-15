#!/usr/bin/env python3
"""Upload essential files via SFTP (excluding large folders)."""

import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "-q"], check=True)
    import paramiko

# Server credentials
HOST = "10.10.20.231"
USER = "rocsmith"
PASS = "C" + "!" + "sco123"
REMOTE_DIR = f"/home/{USER}/packetarch"
PROJECT_ROOT = Path(__file__).parent

# Exclude these from upload
EXCLUDE = {
    "node_modules",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    ".env",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    "training_pcaps",  # Large folder
    ".next",
    "coverage",
}

EXCLUDE_FILES = {
    ".pyc",
    ".pyo",
    ".egg-info",
}


def get_files():
    """Get list of files to upload."""
    files = []
    for item in PROJECT_ROOT.rglob("*"):
        if not item.is_file():
            continue

        # Check exclusions
        parts = item.relative_to(PROJECT_ROOT).parts
        skip = False
        for part in parts:
            if part in EXCLUDE:
                skip = True
                break

        if not skip:
            for ext in EXCLUDE_FILES:
                if item.name.endswith(ext):
                    skip = True
                    break

        if not skip:
            files.append(item)

    return sorted(files)


def upload_files():
    """Upload files via SFTP."""
    print(f"Connecting to {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)
    sftp = client.open_sftp()

    files = get_files()
    total = len(files)
    print(f"Uploading {total} files (excluding training_pcaps)...")

    created_dirs = set()

    for i, local_file in enumerate(files, 1):
        rel_path = local_file.relative_to(PROJECT_ROOT)
        remote_path = f"{REMOTE_DIR}/{rel_path.as_posix()}"
        remote_dir = str(Path(remote_path).parent.as_posix())

        # Create directories
        if remote_dir not in created_dirs:
            parts = remote_dir.split("/")
            current = ""
            for part in parts:
                if not part:
                    continue
                current += f"/{part}"
                if current not in created_dirs:
                    try:
                        sftp.stat(current)
                    except FileNotFoundError:
                        sftp.mkdir(current)
                    created_dirs.add(current)

        # Upload file
        sftp.put(str(local_file), remote_path)

        # Progress
        pct = int(i / total * 100)
        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] {pct}%")

    sftp.close()
    client.close()
    print("Upload complete!")


if __name__ == "__main__":
    upload_files()
