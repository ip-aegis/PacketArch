"""Docker service for remote container deployment."""

import json
import logging
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import docker
from docker.errors import APIError, DockerException, NotFound
from docker.tls import TLSConfig

from app.models.docker_host import DockerHost

logger = logging.getLogger(__name__)

# Traffic generator image name
TRAFFIC_GENERATOR_IMAGE = "packetarch/traffic-generator:latest"


@dataclass
class ConnectionTestResult:
    """Result of a Docker connection test."""

    success: bool
    message: str
    docker_version: str | None = None
    api_version: str | None = None
    latency_ms: float | None = None


@dataclass
class NetworkInterface:
    """Network interface information."""

    name: str
    mac_address: str | None = None
    ip_addresses: list[str] = None
    is_up: bool = True

    def __post_init__(self):
        if self.ip_addresses is None:
            self.ip_addresses = []


@dataclass
class ContainerStatus:
    """Container status information."""

    container_id: str
    name: str
    status: str  # running, exited, paused, etc.
    exit_code: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DockerService:
    """Service for interacting with remote Docker hosts."""

    def __init__(self):
        self._temp_dirs: dict[str, Path] = {}

    def _create_tls_config(self, host: DockerHost) -> TLSConfig | None:
        """Create TLS configuration from host certificates.

        Args:
            host: Docker host with TLS certificates

        Returns:
            TLS configuration or None if TLS is disabled
        """
        if not host.tls_enabled:
            return None

        if not (host.ca_cert and host.client_cert and host.client_key):
            logger.warning(f"TLS enabled for {host.name} but certificates missing")
            return None

        # Create temporary directory for certificates
        temp_dir = tempfile.mkdtemp(prefix=f"docker_tls_{host.id}_")
        temp_path = Path(temp_dir)
        self._temp_dirs[str(host.id)] = temp_path

        # Write certificates to temp files
        ca_path = temp_path / "ca.pem"
        cert_path = temp_path / "cert.pem"
        key_path = temp_path / "key.pem"

        ca_path.write_text(host.ca_cert)
        cert_path.write_text(host.client_cert)
        key_path.write_text(host.client_key)

        return TLSConfig(
            client_cert=(str(cert_path), str(key_path)),
            ca_cert=str(ca_path),
            verify=True,
        )

    def _cleanup_tls_files(self, host_id: str) -> None:
        """Clean up temporary TLS files.

        Args:
            host_id: Host ID to clean up
        """
        temp_path = self._temp_dirs.pop(host_id, None)
        if temp_path and temp_path.exists():
            import shutil

            shutil.rmtree(temp_path, ignore_errors=True)

    def connect(self, host: DockerHost) -> docker.DockerClient:
        """Connect to a remote Docker host.

        Args:
            host: Docker host to connect to

        Returns:
            Docker client instance

        Raises:
            DockerException: If connection fails
        """
        tls_config = self._create_tls_config(host)

        try:
            client = docker.DockerClient(
                base_url=host.docker_api_url,
                tls=tls_config,
                timeout=30,
            )
            # Test the connection
            client.ping()
            return client
        except Exception as e:
            self._cleanup_tls_files(str(host.id))
            raise DockerException(f"Failed to connect to {host.name}: {e}") from e

    def test_connection(self, host: DockerHost) -> ConnectionTestResult:
        """Test connection to a Docker host.

        Args:
            host: Docker host to test

        Returns:
            Connection test result
        """
        start_time = time.time()

        try:
            client = self.connect(host)
            latency_ms = (time.time() - start_time) * 1000

            # Get version info
            version_info = client.version()

            client.close()
            self._cleanup_tls_files(str(host.id))

            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                docker_version=version_info.get("Version"),
                api_version=version_info.get("ApiVersion"),
                latency_ms=round(latency_ms, 2),
            )

        except DockerException as e:
            return ConnectionTestResult(
                success=False,
                message=str(e),
            )
        except Exception as e:
            logger.exception(f"Unexpected error testing connection to {host.name}")
            return ConnectionTestResult(
                success=False,
                message=f"Unexpected error: {e}",
            )

    def list_interfaces(self, host: DockerHost) -> list[NetworkInterface]:
        """List network interfaces on a Docker host.

        This runs a helper container to list interfaces on the host.

        Args:
            host: Docker host to query

        Returns:
            List of network interfaces
        """
        try:
            client = self.connect(host)

            # Run a container to list interfaces using ip command
            # Use plain text output since BusyBox ip doesn't support -j flag
            result = client.containers.run(
                "alpine:latest",
                command="ip link show",
                network_mode="host",
                remove=True,
                stdout=True,
                stderr=True,
            )

            client.close()
            self._cleanup_tls_files(str(host.id))

            # Parse text output from ip link show
            # Format is like:
            # 1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
            #     link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
            # 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP
            #     link/ether 52:54:00:12:34:56 brd ff:ff:ff:ff:ff:ff
            interfaces = []
            lines = result.decode("utf-8").split("\n")
            current_iface = None

            for line in lines:
                # Interface line starts with number
                if line and line[0].isdigit() and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        iface_name = parts[1].strip().split("@")[0]
                        if iface_name != "lo":  # Skip loopback
                            is_up = "UP" in line
                            current_iface = NetworkInterface(
                                name=iface_name,
                                is_up=is_up,
                            )
                            interfaces.append(current_iface)
                        else:
                            current_iface = None
                # MAC address line
                elif current_iface and "link/ether" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "link/ether" and i + 1 < len(parts):
                            current_iface.mac_address = parts[i + 1]
                            break

            return interfaces

        except Exception as e:
            logger.exception(f"Error listing interfaces on {host.name}")
            self._cleanup_tls_files(str(host.id))
            raise DockerException(f"Failed to list interfaces: {e}") from e

    def _write_scenario_to_volume(
        self, client: docker.DockerClient, volume_name: str, scenario_json: str
    ) -> None:
        """Write scenario JSON to a Docker volume using a helper container.

        Args:
            client: Docker client
            volume_name: Name of the volume to write to
            scenario_json: Scenario JSON string
        """
        import base64
        import gzip

        # Compress and encode the scenario JSON to pass safely
        compressed = gzip.compress(scenario_json.encode("utf-8"))
        encoded = base64.b64encode(compressed).decode("ascii")

        # Use alpine to write the file - decode, decompress, and write
        helper_container = client.containers.run(
            "alpine:latest",
            command=[
                "sh",
                "-c",
                f'echo "{encoded}" | base64 -d | gunzip > /data/scenario.json',
            ],
            volumes={volume_name: {"bind": "/data", "mode": "rw"}},
            remove=True,
            detach=False,
        )

    def deploy_container(
        self,
        host: DockerHost,
        scenario_json: str,
        interface: str,
        duration_ms: int | None,
        run_mode: str,
        deployment_id: UUID,
    ) -> str:
        """Deploy a traffic generator container.

        Args:
            host: Docker host to deploy to
            scenario_json: Scenario configuration as JSON string
            interface: Network interface for packet injection
            duration_ms: Duration in milliseconds (None for perpetual mode)
            run_mode: Run mode - "timed" or "perpetual"
            deployment_id: Unique deployment ID for container naming

        Returns:
            Container ID

        Raises:
            DockerException: If deployment fails
        """
        try:
            client = self.connect(host)

            container_name = f"packetarch-generator-{str(deployment_id)[:8]}"
            volume_name = f"packetarch-scenario-{str(deployment_id)[:8]}"

            # Check if image exists, pull if not
            try:
                client.images.get(TRAFFIC_GENERATOR_IMAGE)
            except NotFound:
                logger.info(f"Pulling image {TRAFFIC_GENERATOR_IMAGE}")
                client.images.pull(TRAFFIC_GENERATOR_IMAGE)

            # For large scenarios, use volume mount instead of env var
            # Linux ARG_MAX is ~2MB, so use file-based approach for safety
            use_volume = len(scenario_json) > 100000  # 100KB threshold

            if use_volume:
                logger.info(
                    f"Scenario size ({len(scenario_json)} bytes) exceeds threshold, using volume mount"
                )
                # Create volume and write scenario file
                try:
                    client.volumes.get(volume_name)
                    client.volumes.get(volume_name).remove()
                except NotFound:
                    pass
                client.volumes.create(volume_name)
                self._write_scenario_to_volume(client, volume_name, scenario_json)

                # Build environment variables (without scenario JSON)
                env = {
                    "SCENARIO_FILE": "/scenario/scenario.json",
                    "NETWORK_INTERFACE": interface,
                    "RUN_MODE": run_mode,
                    "DEPLOYMENT_ID": str(deployment_id),
                }

                volumes = {volume_name: {"bind": "/scenario", "mode": "ro"}}
            else:
                # Small scenario - use env var (faster)
                env = {
                    "SCENARIO_JSON": scenario_json,
                    "NETWORK_INTERFACE": interface,
                    "RUN_MODE": run_mode,
                    "DEPLOYMENT_ID": str(deployment_id),
                }
                volumes = None

            # Only include duration for timed mode
            if run_mode == "timed" and duration_ms is not None:
                env["DURATION_MS"] = str(duration_ms)

            # Create and start container
            container = client.containers.run(
                TRAFFIC_GENERATOR_IMAGE,
                name=container_name,
                environment=env,
                volumes=volumes,
                network_mode="host",  # Required for interface access
                cap_add=["NET_ADMIN", "NET_RAW"],  # Required for raw sockets
                detach=True,
                remove=False,  # Keep container for logs inspection
            )

            container_id = container.id
            logger.info(
                f"Deployed container {container_name} ({container_id[:12]}) to {host.name}"
            )

            # Don't close connection here - caller may need it
            # Cleanup will happen on stop/remove

            return container_id

        except Exception as e:
            logger.exception(f"Error deploying container to {host.name}")
            self._cleanup_tls_files(str(host.id))
            raise DockerException(f"Failed to deploy container: {e}") from e

    def get_container_status(
        self, host: DockerHost, container_id: str
    ) -> ContainerStatus | None:
        """Get status of a container.

        Args:
            host: Docker host
            container_id: Container ID

        Returns:
            Container status or None if not found
        """
        try:
            client = self.connect(host)
            container = client.containers.get(container_id)
            container.reload()

            attrs = container.attrs
            state = attrs.get("State", {})

            status = ContainerStatus(
                container_id=container_id,
                name=attrs.get("Name", "").lstrip("/"),
                status=state.get("Status", "unknown"),
                exit_code=state.get("ExitCode"),
            )

            # Parse timestamps
            if state.get("StartedAt") and state["StartedAt"] != "0001-01-01T00:00:00Z":
                status.started_at = datetime.fromisoformat(
                    state["StartedAt"].replace("Z", "+00:00")
                )
            if state.get("FinishedAt") and state["FinishedAt"] != "0001-01-01T00:00:00Z":
                status.finished_at = datetime.fromisoformat(
                    state["FinishedAt"].replace("Z", "+00:00")
                )

            client.close()
            self._cleanup_tls_files(str(host.id))

            return status

        except NotFound:
            self._cleanup_tls_files(str(host.id))
            return None
        except Exception as e:
            logger.exception(f"Error getting container status from {host.name}")
            self._cleanup_tls_files(str(host.id))
            raise DockerException(f"Failed to get container status: {e}") from e

    def get_container_logs(
        self, host: DockerHost, container_id: str, tail: int = 100
    ) -> str:
        """Get container logs.

        Args:
            host: Docker host
            container_id: Container ID
            tail: Number of lines to return

        Returns:
            Container logs as string
        """
        try:
            client = self.connect(host)
            container = client.containers.get(container_id)

            logs = container.logs(tail=tail, timestamps=True)

            client.close()
            self._cleanup_tls_files(str(host.id))

            return logs.decode("utf-8") if isinstance(logs, bytes) else logs

        except NotFound:
            self._cleanup_tls_files(str(host.id))
            return "Container not found"
        except Exception as e:
            logger.exception(f"Error getting container logs from {host.name}")
            self._cleanup_tls_files(str(host.id))
            raise DockerException(f"Failed to get container logs: {e}") from e

    def stop_container(self, host: DockerHost, container_id: str) -> bool:
        """Stop a running container.

        Args:
            host: Docker host
            container_id: Container ID

        Returns:
            True if stopped successfully
        """
        try:
            client = self.connect(host)
            container = client.containers.get(container_id)
            container.stop(timeout=10)

            client.close()
            self._cleanup_tls_files(str(host.id))

            logger.info(f"Stopped container {container_id[:12]} on {host.name}")
            return True

        except NotFound:
            self._cleanup_tls_files(str(host.id))
            logger.warning(f"Container {container_id} not found on {host.name}")
            return True  # Already stopped/removed
        except Exception as e:
            logger.exception(f"Error stopping container on {host.name}")
            self._cleanup_tls_files(str(host.id))
            raise DockerException(f"Failed to stop container: {e}") from e

    def remove_container(
        self, host: DockerHost, container_id: str, deployment_id: str | None = None
    ) -> bool:
        """Remove a container and associated resources.

        Args:
            host: Docker host
            container_id: Container ID
            deployment_id: Optional deployment ID for volume cleanup

        Returns:
            True if removed successfully
        """
        try:
            client = self.connect(host)
            container = client.containers.get(container_id)

            # Get deployment ID from container name if not provided
            container_name = container.name
            if deployment_id is None and container_name.startswith("packetarch-generator-"):
                deployment_id = container_name.replace("packetarch-generator-", "")

            container.remove(force=True)
            logger.info(f"Removed container {container_id[:12]} from {host.name}")

            # Clean up associated scenario volume if it exists
            if deployment_id:
                volume_name = f"packetarch-scenario-{deployment_id}"
                try:
                    volume = client.volumes.get(volume_name)
                    volume.remove()
                    logger.info(f"Removed scenario volume {volume_name}")
                except NotFound:
                    pass  # Volume doesn't exist, that's fine

            client.close()
            self._cleanup_tls_files(str(host.id))

            return True

        except NotFound:
            self._cleanup_tls_files(str(host.id))
            logger.warning(f"Container {container_id} not found on {host.name}")
            return True  # Already removed
        except Exception as e:
            logger.exception(f"Error removing container from {host.name}")
            self._cleanup_tls_files(str(host.id))
            raise DockerException(f"Failed to remove container: {e}") from e

    def get_file_from_container(
        self, host: DockerHost, container_id: str, path: str
    ) -> bytes | None:
        """Get a file from a container.

        Args:
            host: Docker host
            container_id: Container ID
            path: Path to the file inside the container

        Returns:
            File contents as bytes, or None if not found
        """
        import tarfile
        import io

        try:
            client = self.connect(host)
            container = client.containers.get(container_id)

            # Get the archive from the container
            bits, stat = container.get_archive(path)

            # Extract the file from the tar archive
            tar_stream = io.BytesIO()
            for chunk in bits:
                tar_stream.write(chunk)
            tar_stream.seek(0)

            with tarfile.open(fileobj=tar_stream, mode='r') as tar:
                # Get the first (and should be only) file from the archive
                for member in tar.getmembers():
                    if member.isfile():
                        extracted = tar.extractfile(member)
                        if extracted:
                            content = extracted.read()
                            client.close()
                            self._cleanup_tls_files(str(host.id))
                            return content

            client.close()
            self._cleanup_tls_files(str(host.id))
            return None

        except NotFound:
            self._cleanup_tls_files(str(host.id))
            return None
        except Exception as e:
            logger.exception(f"Error getting file from container on {host.name}")
            self._cleanup_tls_files(str(host.id))
            raise DockerException(f"Failed to get file from container: {e}") from e

    def list_files_in_container(
        self, host: DockerHost, container_id: str, path: str
    ) -> list[str]:
        """List files in a container directory.

        Args:
            host: Docker host
            container_id: Container ID
            path: Directory path inside the container

        Returns:
            List of file names
        """
        try:
            client = self.connect(host)
            container = client.containers.get(container_id)

            # Run ls command to list files
            exit_code, output = container.exec_run(f"ls -1 {path}")

            client.close()
            self._cleanup_tls_files(str(host.id))

            if exit_code == 0:
                files = output.decode("utf-8").strip().split("\n")
                return [f for f in files if f]
            return []

        except NotFound:
            self._cleanup_tls_files(str(host.id))
            return []
        except Exception as e:
            logger.exception(f"Error listing files in container on {host.name}")
            self._cleanup_tls_files(str(host.id))
            return []


# Singleton instance
docker_service = DockerService()
