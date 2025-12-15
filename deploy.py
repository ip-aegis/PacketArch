#!/usr/bin/env python3
"""
PacketArch Deployment Tool
Deploy with just IP, username, and password.
"""

import getpass
import os
import secrets
import stat
import sys
import time
from pathlib import Path

# Auto-install paramiko if needed
try:
    import paramiko
except ImportError:
    import subprocess
    print("Installing paramiko...")
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "-q"], check=True)
    import paramiko


# Files/directories to exclude from upload
EXCLUDE_PATTERNS = [
    "node_modules",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    ".env",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "*.egg-info",
    # Old deployment scripts (will be deleted)
    "deploy_prod.py",
    "reset_and_rebuild.py",
    "upload_and_rebuild.py",
    "check_status.py",
    "get_logs.py",
    "debug_build.py",
    "wait_and_check.py",
]


class DeploymentClient:
    """SSH/SFTP client for remote deployment."""

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
        self.remote_dir = f"/home/{username}/packetarch"

    def _get_client(self) -> paramiko.SSHClient:
        """Create and connect SSH client."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.host,
            username=self.username,
            password=self.password,
            timeout=30
        )
        return client

    def run(self, cmd: str, sudo: bool = False, timeout: int = 600) -> tuple[str, str, int]:
        """Run command via SSH. Returns (stdout, stderr, exit_code)."""
        client = self._get_client()
        try:
            if sudo:
                # Pipe password to sudo for non-interactive execution
                cmd = f"echo '{self.password}' | sudo -S bash -c '{cmd}'"

            stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            return out, err, exit_code
        finally:
            client.close()

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        """Upload single file via SFTP."""
        client = self._get_client()
        sftp = client.open_sftp()
        try:
            sftp.put(str(local_path), remote_path)
        finally:
            sftp.close()
            client.close()

    def mkdir_p(self, remote_path: str) -> None:
        """Create remote directory (mkdir -p equivalent)."""
        client = self._get_client()
        sftp = client.open_sftp()
        try:
            dirs = remote_path.split("/")
            current = ""
            for d in dirs:
                if not d:
                    continue
                current += f"/{d}"
                try:
                    sftp.stat(current)
                except FileNotFoundError:
                    sftp.mkdir(current)
        finally:
            sftp.close()
            client.close()

    def test_connection(self) -> bool:
        """Test SSH connection."""
        try:
            out, err, code = self.run("echo 'OK'")
            return "OK" in out
        except Exception:
            return False


class Deployer:
    """Main deployment orchestrator."""

    def __init__(self, client: DeploymentClient):
        self.client = client
        self.project_root = Path(__file__).parent.resolve()

    def fresh_install(self) -> None:
        """Full deployment: Docker install + files + build."""
        print("\n" + "=" * 60)
        print("FRESH INSTALL")
        print("=" * 60)

        self._install_docker()
        self._upload_files()
        self._create_env()
        self._build_and_start()
        self._show_status()
        self._show_completion()

    def update_rebuild(self) -> None:
        """Sync files and rebuild containers."""
        print("\n" + "=" * 60)
        print("UPDATE & REBUILD")
        print("=" * 60)

        self._upload_files()
        self._stop_containers()
        self._build_and_start()
        self._show_status()
        self._show_completion()

    def check_status(self) -> None:
        """Show container status."""
        print("\n" + "=" * 60)
        print("CONTAINER STATUS")
        print("=" * 60)

        out, err, _ = self.client.run(
            "/usr/bin/docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
            sudo=True
        )
        self._print_filtered(out)

    def view_logs(self, lines: int = 50) -> None:
        """Show backend logs."""
        print("\n" + "=" * 60)
        print(f"BACKEND LOGS (last {lines} lines)")
        print("=" * 60)

        out, err, _ = self.client.run(
            f"cd {self.client.remote_dir} && /usr/bin/docker compose logs backend --tail {lines}",
            sudo=True
        )
        self._print_filtered(out + err)

    def reset_database(self) -> None:
        """Wipe volumes and rebuild (fresh database)."""
        print("\n" + "=" * 60)
        print("RESET DATABASE")
        print("=" * 60)

        print("\n[1/3] Stopping containers and removing volumes...")
        out, err, _ = self.client.run(
            f"cd {self.client.remote_dir} && /usr/bin/docker compose down -v",
            sudo=True,
            timeout=120
        )
        self._print_filtered(out + err, keywords=["removed", "done", "error"])

        print("\n[2/3] Rebuilding and starting...")
        self._build_and_start()

        print("\n[3/3] Checking status...")
        time.sleep(10)
        self._show_status()
        self._show_completion()

    # -------------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------------

    def _install_docker(self) -> None:
        """Install Docker if not present."""
        print("\n[1/4] Checking Docker installation...")

        out, err, _ = self.client.run("/usr/bin/docker --version 2>/dev/null || echo 'NOT_INSTALLED'")

        if "NOT_INSTALLED" in out:
            print("  Docker not found. Installing...")

            print("  Installing dependencies...")
            self.client.run("apt-get update -qq", sudo=True)
            self.client.run(
                "apt-get install -y -qq ca-certificates curl gnupg lsb-release",
                sudo=True
            )

            print("  Adding Docker repository...")
            self.client.run("install -m 0755 -d /etc/apt/keyrings", sudo=True)
            self.client.run(
                "curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
                sudo=True
            )
            self.client.run("chmod a+r /etc/apt/keyrings/docker.asc", sudo=True)

            add_repo = '''echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list'''
            self.client.run(add_repo, sudo=True)

            print("  Installing Docker Engine (this may take a few minutes)...")
            self.client.run("apt-get update -qq", sudo=True)
            self.client.run(
                "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
                sudo=True,
                timeout=300
            )

            self.client.run(f"usermod -aG docker {self.client.username}", sudo=True)
            print("  Docker installed successfully!")
        else:
            version = self._extract_line(out, "Docker")
            print(f"  {version or 'Docker already installed'}")

        # Verify compose
        out, err, _ = self.client.run("/usr/bin/docker compose version", sudo=True)
        version = self._extract_line(out, "Docker Compose")
        print(f"  {version or 'Docker Compose available'}")

    def _upload_files(self) -> None:
        """Upload project files to remote server."""
        print("\n[2/4] Uploading project files...")

        files = self._get_files_to_upload()
        total = len(files)

        for i, local_file in enumerate(files, 1):
            rel_path = local_file.relative_to(self.project_root)
            remote_path = f"{self.client.remote_dir}/{rel_path.as_posix()}"

            # Create parent directory
            remote_dir = str(Path(remote_path).parent)
            self.client.mkdir_p(remote_dir)

            # Upload file
            self.client.upload_file(local_file, remote_path)

            # Progress indicator
            pct = int(i / total * 100)
            print(f"\r  Uploading [{i}/{total}] {pct}% - {rel_path.name[:30]:<30}", end="", flush=True)

        print(f"\r  Uploaded {total} files" + " " * 40)

    def _create_env(self) -> None:
        """Create production .env file."""
        print("\n[3/4] Creating production .env...")

        secret_key = secrets.token_hex(32)
        env_content = f"""POSTGRES_PASSWORD=PacketArch_Prod_2024!
SECRET_KEY={secret_key}
ENCRYPTION_KEY=
ADMIN_PASSWORD=PacketArch_Admin!
DEBUG=false"""

        self.client.run(
            f"cat > {self.client.remote_dir}/.env << 'ENVEOF'\n{env_content}\nENVEOF"
        )
        print("  .env created with secure defaults")

    def _stop_containers(self) -> None:
        """Stop existing containers."""
        print("\n  Stopping existing containers...")
        self.client.run(
            f"cd {self.client.remote_dir} && /usr/bin/docker compose down 2>/dev/null || true",
            sudo=True,
            timeout=120
        )

    def _build_and_start(self) -> None:
        """Build and start Docker containers."""
        print("\n[4/4] Building and starting containers...")
        print("  This may take several minutes on first build...")

        out, err, code = self.client.run(
            f"cd {self.client.remote_dir} && /usr/bin/docker compose up -d --build 2>&1",
            sudo=True,
            timeout=900
        )

        # Show relevant output
        self._print_filtered(
            out + err,
            keywords=["error", "failed", "built", "created", "started", "pulling", "healthy"]
        )

        if code != 0:
            print("\n  WARNING: Build may have encountered issues. Check logs.")

    def _show_status(self) -> None:
        """Show container status."""
        print("\n" + "-" * 60)
        print("Container Status:")
        print("-" * 60)

        time.sleep(5)  # Wait for containers to stabilize

        out, err, _ = self.client.run(
            f"cd {self.client.remote_dir} && /usr/bin/docker compose ps --format 'table {{{{.Name}}}}\t{{{{.Status}}}}'",
            sudo=True
        )
        self._print_filtered(out)

    def _show_completion(self) -> None:
        """Show completion message with access URLs."""
        print("\n" + "=" * 60)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 60)

        print(f"""
Access URLs:
  Frontend:  http://{self.client.host}:3001
  API Docs:  http://{self.client.host}:8001/api/docs

Credentials:
  Username:  admin
  Password:  PacketArch_Admin!
""")

    def _get_files_to_upload(self) -> list[Path]:
        """Get list of files to upload, respecting exclusions."""
        files = []

        for item in self.project_root.rglob("*"):
            if not item.is_file():
                continue

            # Check against exclusion patterns
            rel_path = item.relative_to(self.project_root)
            parts = rel_path.parts

            skip = False
            for pattern in EXCLUDE_PATTERNS:
                if pattern.startswith("*"):
                    # Suffix match (e.g., *.pyc)
                    if item.name.endswith(pattern[1:]):
                        skip = True
                        break
                else:
                    # Directory or exact file match
                    if pattern in parts or item.name == pattern:
                        skip = True
                        break

            if not skip:
                files.append(item)

        return sorted(files)

    def _print_filtered(self, output: str, keywords: list[str] = None) -> None:
        """Print output, filtering password prompts and optionally by keywords."""
        for line in output.split("\n"):
            # Skip password prompts
            if "password" in line.lower():
                continue

            # Clean ANSI codes
            clean = "".join(c if ord(c) < 128 else "." for c in line)
            clean = clean.strip()

            if not clean:
                continue

            # Filter by keywords if provided
            if keywords:
                if any(kw in clean.lower() for kw in keywords):
                    print(f"  {clean}")
            else:
                print(f"  {clean}")

    def _extract_line(self, output: str, contains: str) -> str | None:
        """Extract first line containing a substring."""
        for line in output.split("\n"):
            if contains in line and "password" not in line.lower():
                return line.strip()
        return None


def print_banner():
    """Print application banner."""
    print("""
+------------------------------------------+
|       PacketArch Deployment Tool         |
+------------------------------------------+
""")


def show_menu() -> str:
    """Show operation menu and get user choice."""
    print("""
Select operation:
  [1] Fresh Install  - Docker + files + build (new server)
  [2] Update/Rebuild - Sync files + rebuild containers
  [3] Check Status   - Show container status
  [4] View Logs      - Show backend logs
  [5] Reset Database - Wipe data + rebuild
  [q] Quit
""")
    return input("Choice: ").strip().lower()


def main() -> int:
    """Main entry point."""
    print_banner()

    # Get credentials interactively
    print("Enter target server details:")
    host = input("  Host: ").strip()
    if not host:
        print("ERROR: Host is required")
        return 1

    username = input("  Username: ").strip()
    if not username:
        print("ERROR: Username is required")
        return 1

    password = getpass.getpass("  Password: ")
    if not password:
        print("ERROR: Password is required")
        return 1

    # Test connection
    print("\nTesting connection...", end=" ", flush=True)
    client = DeploymentClient(host, username, password)

    if not client.test_connection():
        print("FAILED")
        print("ERROR: Could not connect to server. Check credentials and network.")
        return 1

    print("OK")

    # Create deployer and show menu
    deployer = Deployer(client)

    while True:
        choice = show_menu()

        if choice == "1":
            deployer.fresh_install()
            break
        elif choice == "2":
            deployer.update_rebuild()
            break
        elif choice == "3":
            deployer.check_status()
        elif choice == "4":
            deployer.view_logs()
        elif choice == "5":
            confirm = input("  This will DELETE all data. Type 'yes' to confirm: ")
            if confirm.lower() == "yes":
                deployer.reset_database()
                break
            else:
                print("  Cancelled.")
        elif choice == "q":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
