#!/usr/bin/env python3
"""Run deployment to production server using GitHub."""

import secrets
import sys
sys.path.insert(0, '.')
from deploy import DeploymentClient

HOST = "10.10.20.231"
USER = "rocsmith"
PASS = r"C!sco123"
REPO = "https://github.com/kingsmanrocky-max/PacketArch.git"
REMOTE_DIR = f"/home/{USER}/packetarch"

def run_cmd(client, cmd, sudo=False, desc=None):
    """Run command and print output."""
    if desc:
        print(f"\n  {desc}...")
    out, err, code = client.run(cmd, sudo=sudo, timeout=600)
    # Filter password prompts
    for line in (out + err).split("\n"):
        if line.strip() and "password" not in line.lower():
            print(f"    {line.strip()}")
    return code == 0

def main():
    print("=" * 60)
    print("  PacketArch Production Deployment (GitHub)")
    print("=" * 60)

    client = DeploymentClient(HOST, USER, PASS)

    print(f"\nConnecting to {HOST}...")
    if not client.test_connection():
        print("ERROR: Connection failed!")
        return 1
    print("Connected!")

    # Step 1: Check/Clone repository
    print("\n[1/4] Setting up repository...")
    out, _, _ = client.run(f"ls {REMOTE_DIR}/.git 2>/dev/null && echo EXISTS || echo NOT_FOUND")

    if "EXISTS" in out:
        print("  Repository exists. Pulling latest...")
        run_cmd(client, f"cd {REMOTE_DIR} && git fetch origin && git reset --hard origin/master")
    else:
        print("  Cloning repository...")
        run_cmd(client, f"git clone {REPO} {REMOTE_DIR}")

    # Step 2: Create .env file
    print("\n[2/4] Creating .env file...")
    secret_key = secrets.token_hex(32)
    env_content = f'''POSTGRES_PASSWORD=PacketArch_Prod_2024!
SECRET_KEY={secret_key}
ENCRYPTION_KEY=
ADMIN_PASSWORD=PacketArch_Admin!
DEBUG=false'''

    run_cmd(client, f"cat > {REMOTE_DIR}/.env << 'ENVEOF'\n{env_content}\nENVEOF")
    print("  .env created")

    # Step 3: Build and start containers
    print("\n[3/4] Building and starting containers...")
    print("  This may take several minutes...")

    run_cmd(client,
        f"cd {REMOTE_DIR} && sudo /usr/bin/docker compose down 2>/dev/null || true",
        desc="Stopping existing containers"
    )

    success = run_cmd(client,
        f"cd {REMOTE_DIR} && sudo /usr/bin/docker compose up -d --build",
        desc="Building and starting services"
    )

    # Step 4: Show status
    print("\n[4/4] Checking status...")
    import time
    time.sleep(10)

    run_cmd(client, f"cd {REMOTE_DIR} && sudo /usr/bin/docker compose ps")

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
