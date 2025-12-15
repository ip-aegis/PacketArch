#!/usr/bin/env python3
"""Automated deployment to production server."""

import secrets
import sys
import time

try:
    import paramiko
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "-q"], check=True)
    import paramiko

# Server credentials
HOST = "10.10.20.231"
USER = "rocsmith"
PASS = "C" + "!" + "sco123"  # Avoid escape issues
REMOTE_DIR = f"/home/{USER}/packetarch"
REPO = "https://github.com/kingsmanrocky-max/PacketArch.git"


def get_client():
    """Create SSH client connection."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)
    return client


def run_cmd(cmd, sudo=False, timeout=600):
    """Run command on server."""
    client = get_client()
    try:
        if sudo:
            cmd = f"echo '{PASS}' | sudo -S bash -c '{cmd}'"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
        code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")

        # Print filtered output (handle encoding)
        for line in (out + err).split("\n"):
            line = line.strip()
            if line and "password" not in line.lower():
                # Replace non-ASCII chars to avoid encoding errors
                safe_line = line.encode('ascii', 'replace').decode('ascii')
                print(f"    {safe_line}")

        return code == 0, out
    finally:
        client.close()


def main():
    print("=" * 60)
    print("  PacketArch Production Deployment")
    print("=" * 60)

    # Step 1: Test connection
    print(f"\n[1/5] Connecting to {HOST}...")
    try:
        client = get_client()
        client.close()
        print("    Connected!")
    except Exception as e:
        print(f"    ERROR: {e}")
        return 1

    # Step 2: Check/clone repository
    print("\n[2/5] Setting up repository...")
    success, out = run_cmd(f"ls {REMOTE_DIR}/.git 2>/dev/null && echo EXISTS || echo NOT_FOUND")

    if "EXISTS" in out:
        print("    Repository exists. Pulling latest...")
        run_cmd(f"cd {REMOTE_DIR} && git fetch origin && git reset --hard origin/master", timeout=120)
    else:
        print("    Cloning repository (shallow clone)...")
        # Remove any partial directory first
        run_cmd(f"rm -rf {REMOTE_DIR}")
        success, _ = run_cmd(f"git clone --depth 1 {REPO} {REMOTE_DIR}", timeout=300)
        if not success:
            print("    ERROR: Clone failed")
            return 1

    # Step 3: Create .env file
    print("\n[3/5] Creating .env file...")
    secret_key = secrets.token_hex(32)
    env_content = f"""POSTGRES_PASSWORD=PacketArch_Prod_2024!
SECRET_KEY={secret_key}
ENCRYPTION_KEY=
ADMIN_PASSWORD=PacketArch_Admin!
DEBUG=false"""

    run_cmd(f"cat > {REMOTE_DIR}/.env << 'ENVEOF'\n{env_content}\nENVEOF")
    print("    .env created")

    # Step 4: Build and start containers
    print("\n[4/5] Building and starting containers...")
    print("    Stopping existing containers...")
    run_cmd(f"cd {REMOTE_DIR} && /usr/bin/docker compose down 2>/dev/null || true", sudo=True, timeout=120)

    print("    Building and starting (this takes several minutes)...")
    success, _ = run_cmd(f"cd {REMOTE_DIR} && /usr/bin/docker compose up -d --build", sudo=True, timeout=900)

    # Step 5: Verify deployment
    print("\n[5/5] Verifying deployment...")
    time.sleep(15)

    print("\n    Container Status:")
    run_cmd(f"cd {REMOTE_DIR} && /usr/bin/docker compose ps", sudo=True)

    # Done
    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print(f"""
Access URLs:
  Frontend:  http://{HOST}:3001
  API Docs:  http://{HOST}:8001/api/docs

Credentials:
  Username:  admin
  Password:  PacketArch_Admin!
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
