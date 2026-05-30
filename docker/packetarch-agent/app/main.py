# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""PacketArch Remote Traffic Agent - Main Entry Point."""

import asyncio
import hashlib
import logging
import os
import signal
import socket
import subprocess
import sys
import tempfile
from typing import Any

import docker
import httpx
import psutil

from app.config import AgentConfig
from app.orchestrator_pool import OrchestratorPool, ScenarioState
from app.websocket_client import AgentWebSocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def find_agent_install_path() -> str | None:
    """Find the agent installation directory.

    Checks multiple common locations for the docker-compose.yml file.
    Returns the directory path or None if not found.
    """
    # Check environment variable first
    env_path = os.environ.get("AGENT_INSTALL_PATH")
    if env_path and os.path.isfile(os.path.join(env_path, "docker-compose.yml")):
        return env_path

    # Check common installation paths
    common_paths = [
        "/opt/packetarch-agent",
        "/opt/PacketArch-Agent",
        "/home/cisco/packetarch-agent",
        "/root/packetarch-agent",
        os.path.expanduser("~/packetarch-agent"),
    ]

    for path in common_paths:
        compose_file = os.path.join(path, "docker-compose.yml")
        if os.path.isfile(compose_file):
            return path

    return None


class PacketArchAgent:
    """Main agent class that coordinates WebSocket and orchestrator pool."""

    def __init__(self, config: AgentConfig):
        """Initialize the agent.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.pool = OrchestratorPool(on_status_change=self._on_status_change)
        self.ws = AgentWebSocket(config, on_command=self._handle_command)
        self.ws.get_running_scenarios = lambda: self.pool.running_scenarios
        self._status_queue: asyncio.Queue[tuple[str, ScenarioState, int, str | None]] = asyncio.Queue()
        self._running = False

    async def run(self) -> None:
        """Run the agent."""
        self._running = True
        logger.info("Starting PacketArch Agent...")
        logger.info(f"Server: {self.config.server_url}")
        logger.info(f"Default interface: {self.config.default_interface}")

        # Start status reporter and self-health check tasks
        status_task = asyncio.create_task(self._status_reporter())
        health_task = asyncio.create_task(self._self_health_check())

        try:
            # Connect to server (auto-reconnect loop)
            await self.ws.connect()
        except asyncio.CancelledError:
            logger.info("Agent cancelled")
        finally:
            self._running = False
            self.pool.stop_all()
            status_task.cancel()
            health_task.cancel()
            try:
                await status_task
            except asyncio.CancelledError:
                pass
            try:
                await health_task
            except asyncio.CancelledError:
                pass

    async def _status_reporter(self) -> None:
        """Report scenario status changes to server."""
        while self._running:
            try:
                # Wait for status updates with timeout
                scenario_id, state, packets_sent, error = await asyncio.wait_for(
                    self._status_queue.get(),
                    timeout=self.config.status_report_interval_seconds,
                )
                # For event-driven updates, get fresh rich stats
                fresh = self.pool.get_status(scenario_id)
                if fresh:
                    adaptation = self.pool.get_adaptation_state(scenario_id)
                    attack = self.pool.get_attack_state(scenario_id)
                    await self.ws.send_status(
                        scenario_id, state.value, fresh.packets_sent, error,
                        bytes_sent=fresh.bytes_sent,
                        protocol_breakdown=fresh.protocol_breakdown,
                        flow_count=fresh.flow_count,
                        packets_per_second=fresh.packets_per_second,
                        bytes_per_second=fresh.bytes_per_second,
                        adaptation=adaptation,
                        attack=attack,
                    )
                else:
                    await self.ws.send_status(scenario_id, state.value, packets_sent, error)

            except asyncio.TimeoutError:
                # Send periodic status for all running scenarios
                for status in self.pool.get_all_statuses():
                    if status.state in (ScenarioState.STARTING, ScenarioState.RUNNING):
                        # Include adaptation and attack state if available
                        adaptation = self.pool.get_adaptation_state(status.scenario_id)
                        attack = self.pool.get_attack_state(status.scenario_id)
                        await self.ws.send_status(
                            status.scenario_id,
                            status.state.value,
                            status.packets_sent,
                            bytes_sent=status.bytes_sent,
                            protocol_breakdown=status.protocol_breakdown,
                            flow_count=status.flow_count,
                            packets_per_second=status.packets_per_second,
                            bytes_per_second=status.bytes_per_second,
                            adaptation=adaptation,
                            attack=attack,
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Status reporter error: {e}")

    def _on_status_change(
        self,
        scenario_id: str,
        state: ScenarioState,
        packets_sent: int,
        error_message: str | None,
    ) -> None:
        """Callback from orchestrator pool when scenario status changes."""
        try:
            self._status_queue.put_nowait((scenario_id, state, packets_sent, error_message))
        except Exception:
            pass  # Queue might be full, ignore

    async def _self_health_check(self) -> None:
        """Periodically check scenario thread health."""
        while self._running:
            try:
                await asyncio.sleep(15)
                unhealthy = self.pool.check_thread_health()
                for scenario in unhealthy:
                    logger.error(
                        f"Unhealthy scenario detected: {scenario['scenario_id']} "
                        f"(thread_alive={scenario['thread_alive']})"
                    )
                    # The status change callback will notify the server
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Self-health check error: {e}")

    async def _handle_command(self, command: dict[str, Any]) -> None:
        """Handle a command from the server.

        Args:
            command: Command dict with 'type' and payload
        """
        cmd_type = command.get("type", "")
        logger.debug(f"Received command: {cmd_type}")

        try:
            if cmd_type == "START_SCENARIO":
                await self._handle_start_scenario(command)

            elif cmd_type == "STOP_SCENARIO":
                await self._handle_stop_scenario(command)

            elif cmd_type == "UPDATE_SCENARIO":
                await self._handle_update_scenario(command)

            elif cmd_type == "LIST_INTERFACES":
                await self._handle_list_interfaces(command)

            elif cmd_type == "GET_STATUS":
                await self._handle_get_status(command)

            elif cmd_type == "UPDATE_AGENT":
                await self._handle_update_agent(command)

            elif cmd_type == "GET_LOGS":
                await self._handle_get_logs(command)

            elif cmd_type == "PING_TEST":
                await self._handle_ping_test(command)

            elif cmd_type == "ADAPT_TRAFFIC":
                await self._handle_adapt_traffic(command)

            elif cmd_type == "START_ATTACK":
                await self._handle_attack_command(command, "start")

            elif cmd_type == "STOP_ATTACK":
                await self._handle_attack_command(command, "stop")

            elif cmd_type == "ADVANCE_STAGE":
                await self._handle_attack_command(command, "advance_stage")

            elif cmd_type == "PAUSE_ATTACK":
                await self._handle_attack_command(command, "pause")

            elif cmd_type == "INJECT_ATTACK":
                await self._handle_inject_attack(command)

            else:
                logger.warning(f"Unknown command type: {cmd_type}")
                await self.ws.send_error(
                    None,
                    f"Unknown command type: {cmd_type}",
                    "UNKNOWN_COMMAND",
                )

        except Exception as e:
            logger.error(f"Error handling command {cmd_type}: {e}")
            scenario_id = command.get("scenario_id")
            await self.ws.send_error(scenario_id, str(e), "COMMAND_ERROR")

    async def _handle_start_scenario(self, command: dict[str, Any]) -> None:
        """Handle START_SCENARIO command."""
        scenario_id = command.get("scenario_id")
        definition = command.get("definition", {})
        interface = command.get("interface") or self.config.default_interface

        if not scenario_id:
            await self.ws.send_error(None, "Missing scenario_id", "INVALID_COMMAND")
            return

        if not definition:
            await self.ws.send_error(scenario_id, "Missing definition", "INVALID_COMMAND")
            return

        # Validate interface exists
        available = list(psutil.net_if_addrs().keys())
        if interface not in available:
            await self.ws.send_error(
                scenario_id,
                f"Interface '{interface}' not found. Available: {available}",
                "INTERFACE_NOT_FOUND",
            )
            return

        logger.info(f"Starting scenario {scenario_id} on interface {interface}")
        success = self.pool.start(scenario_id, definition, interface)

        if not success:
            await self.ws.send_status(
                scenario_id,
                "error",
                0,
                "Scenario already running",
            )

    async def _handle_stop_scenario(self, command: dict[str, Any]) -> None:
        """Handle STOP_SCENARIO command."""
        scenario_id = command.get("scenario_id")

        if not scenario_id:
            await self.ws.send_error(None, "Missing scenario_id", "INVALID_COMMAND")
            return

        logger.info(f"Stopping scenario {scenario_id}")
        success = self.pool.stop(scenario_id)

        if not success:
            await self.ws.send_error(
                scenario_id,
                "Scenario not found or not running",
                "SCENARIO_NOT_FOUND",
            )

    async def _handle_update_scenario(self, command: dict[str, Any]) -> None:
        """Handle UPDATE_SCENARIO command (stop and restart with new definition)."""
        scenario_id = command.get("scenario_id")
        definition = command.get("definition", {})
        interface = command.get("interface") or self.config.default_interface

        if not scenario_id or not definition:
            await self.ws.send_error(
                scenario_id,
                "Missing scenario_id or definition",
                "INVALID_COMMAND",
            )
            return

        logger.info(f"Updating scenario {scenario_id}")

        # Stop existing
        self.pool.stop(scenario_id)

        # Brief delay to allow cleanup
        await asyncio.sleep(0.5)

        # Start with new definition
        self.pool.start(scenario_id, definition, interface)

    async def _handle_list_interfaces(self, command: dict[str, Any]) -> None:
        """Handle LIST_INTERFACES command."""
        request_id = command.get("request_id", "")

        interfaces = []
        net_if_addrs = psutil.net_if_addrs()

        for iface, addrs in net_if_addrs.items():
            try:
                info: dict[str, Any] = {"name": iface, "addresses": []}

                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        info["addresses"].append({
                            "type": "ipv4",
                            "address": addr.address,
                            "netmask": addr.netmask,
                        })
                    elif addr.family == socket.AF_INET6:
                        info["addresses"].append({
                            "type": "ipv6",
                            "address": addr.address,
                            "netmask": addr.netmask,
                        })
                    elif addr.family == psutil.AF_LINK:
                        info["mac"] = addr.address

                interfaces.append(info)
            except Exception as e:
                logger.debug(f"Error getting info for {iface}: {e}")
                interfaces.append({"name": iface, "error": str(e)})

        await self.ws.send_interfaces(request_id, interfaces)

    async def _handle_get_status(self, command: dict[str, Any]) -> None:
        """Handle GET_STATUS command."""
        scenario_id = command.get("scenario_id")

        if scenario_id:
            status = self.pool.get_status(scenario_id)
            if status:
                await self.ws.send_status(
                    scenario_id,
                    status.state.value,
                    status.packets_sent,
                    status.error_message,
                )
            else:
                await self.ws.send_error(
                    scenario_id,
                    "Scenario not found",
                    "SCENARIO_NOT_FOUND",
                )
        else:
            # Send status for all scenarios
            for status in self.pool.get_all_statuses():
                await self.ws.send_status(
                    status.scenario_id,
                    status.state.value,
                    status.packets_sent,
                    status.error_message,
                )

    async def _handle_get_logs(self, command: dict[str, Any]) -> None:
        """Handle GET_LOGS command - return recent agent logs."""
        request_id = command.get("request_id", "")
        lines = command.get("lines", 100)

        # Cap at 1000 lines to prevent memory issues
        lines = min(lines, 1000)

        logs = []
        try:
            # Try to read from Docker logs first (more reliable)
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), "packetarch-agent"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Combine stdout and stderr
                all_output = result.stdout + result.stderr
                logs = all_output.strip().split("\n") if all_output.strip() else []
            else:
                # Fallback: try reading from any available log file
                log_paths = [
                    "/var/log/packetarch-agent.log",
                    "/opt/packetarch-agent/agent.log",
                ]
                for log_path in log_paths:
                    if os.path.exists(log_path):
                        with open(log_path, "r") as f:
                            all_lines = f.readlines()
                            logs = [line.strip() for line in all_lines[-lines:]]
                            break

                if not logs:
                    logs = ["No logs available - container logs not accessible"]
        except subprocess.TimeoutExpired:
            logs = ["Log retrieval timed out"]
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            logs = [f"Error retrieving logs: {e}"]

        await self.ws.send({
            "type": "LOGS",
            "request_id": request_id,
            "logs": logs,
            "count": len(logs),
        })

    async def _handle_ping_test(self, command: dict[str, Any]) -> None:
        """Handle PING_TEST command - measure round-trip latency."""
        import time

        request_id = command.get("request_id", "")
        sent_at = command.get("sent_at", 0)

        # Calculate one-way latency if sent_at was provided
        receive_time = time.time() * 1000  # ms

        await self.ws.send({
            "type": "PING_RESPONSE",
            "request_id": request_id,
            "server_sent_at": sent_at,
            "agent_received_at": receive_time,
            "agent_sent_at": time.time() * 1000,
        })

    async def _handle_adapt_traffic(self, command: dict[str, Any]) -> None:
        """Handle ADAPT_TRAFFIC command - apply adaptive traffic directives.

        Directives adjust traffic behavior mid-deployment without restarting.
        """
        scenario_id = command.get("scenario_id")
        directives = command.get("directives", [])

        if not scenario_id:
            await self.ws.send_error(None, "Missing scenario_id", "INVALID_COMMAND")
            return

        if not directives:
            await self.ws.send_error(scenario_id, "Missing directives", "INVALID_COMMAND")
            return

        success = self.pool.apply_directives(scenario_id, directives)
        if success:
            logger.info(f"Applied {len(directives)} adaptive directives to scenario {scenario_id}")
        else:
            logger.warning(f"Failed to apply directives: scenario {scenario_id} not found or no adaptive controller")
            await self.ws.send_error(
                scenario_id,
                "Scenario not found or adaptive traffic not enabled",
                "ADAPT_FAILED",
            )

    async def _handle_inject_attack(self, command: dict[str, Any]) -> None:
        """Handle INJECT_ATTACK — hot-attach a playbook to a running scenario."""
        scenario_id = command.get("scenario_id")
        attack_playbook = command.get("attack_playbook", {})

        if not scenario_id:
            await self.ws.send_error(None, "Missing scenario_id", "INVALID_COMMAND")
            return

        playbook_id = attack_playbook.get("playbook_id")
        if not playbook_id:
            await self.ws.send_error(
                scenario_id,
                "Missing playbook_id in attack_playbook",
                "INVALID_COMMAND",
            )
            return

        success = self.pool.inject_attack(scenario_id, {
            "playbook_id": playbook_id,
            "config": attack_playbook,
        })

        if success:
            logger.info(
                f"Attack playbook '{playbook_id}' injection queued "
                f"for scenario {scenario_id}"
            )
            # Trigger an immediate status report so attack state
            # reaches the server faster (instead of waiting 5s).
            status = self.pool.get_status(scenario_id)
            if status:
                self._on_status_change(
                    scenario_id, status.state, status.packets_sent, None,
                )
        else:
            await self.ws.send_error(
                scenario_id,
                "Scenario not found, not running, or already has an attack configured",
                "INJECT_ATTACK_FAILED",
            )

    async def _handle_attack_command(self, command: dict[str, Any], cmd_type: str) -> None:
        """Handle attack control commands (START_ATTACK, STOP_ATTACK, ADVANCE_STAGE, PAUSE_ATTACK)."""
        scenario_id = command.get("scenario_id")

        if not scenario_id:
            await self.ws.send_error(None, "Missing scenario_id", "INVALID_COMMAND")
            return

        attack_cmd: dict[str, Any] = {"type": cmd_type}
        if cmd_type == "pause":
            attack_cmd["paused"] = command.get("paused", True)

        success = self.pool.send_attack_command(scenario_id, attack_cmd)
        if success:
            logger.info(f"Attack command '{cmd_type}' sent to scenario {scenario_id}")
        else:
            logger.warning(f"Failed to send attack command: scenario {scenario_id} not found or no attack orchestrator")
            await self.ws.send_error(
                scenario_id,
                "Scenario not found or no attack playbook configured",
                "ATTACK_COMMAND_FAILED",
            )

    async def _handle_update_agent(self, command: dict[str, Any]) -> None:
        """Handle UPDATE_AGENT command - download new image and restart.

        The agent will:
        1. Save the current image for rollback
        2. Download the latest image tarball from the PacketArch server
        3. Verify checksum integrity
        4. Load it with docker load
        5. Restart this container to use the new image
        6. Rollback to old image if restart fails
        """
        logger.info("Received UPDATE_AGENT command")

        # Get server URL for downloading image (convert ws:// back to http://)
        server_url = self.config.server_url.replace("wss://", "https://").replace("ws://", "http://")
        image_url = f"{server_url}/api/v1/agents/image"

        # Send acknowledgment
        await self.ws.send({
            "type": "UPDATE_STATUS",
            "status": "downloading",
            "message": "Preparing update...",
        })

        tarball_path = None
        old_image_id = None
        docker_client = None

        try:
            # Initialize Docker client early for rollback support
            try:
                docker_client = docker.from_env()
            except docker.errors.DockerException as e:
                logger.error(f"Docker not available: {e}")
                await self.ws.send({
                    "type": "UPDATE_STATUS",
                    "status": "failed",
                    "error": "Docker not available",
                    "message": "Docker is not available. Ensure Docker socket is mounted.",
                })
                return

            # Save current image ID for rollback. We capture TWO ids:
            #   - `old_image_id` — the SHA the `packetarch-agent:latest`
            #     tag currently points to. Used as the rollback target.
            #   - `running_image_id` — the SHA of the image the running
            #     container is ACTUALLY on. The freshness check below
            #     uses this one, because the tag and the container can
            #     diverge: when the agent shares a Docker daemon with
            #     the PacketArch backend (the typical local-host
            #     `LocalDiag` setup), the backend rebuilds the image
            #     in-place and the tag is bumped to the new SHA before
            #     UPDATE_AGENT ever reaches us. Comparing the load
            #     against the tag would then say "already up to date"
            #     even though our container is still on the old layers.
            running_image_id = None
            try:
                current_image = docker_client.images.get("packetarch-agent:latest")
                old_image_id = current_image.id
                logger.info(f"Tag 'packetarch-agent:latest' points at: {old_image_id[:12]}")
            except docker.errors.ImageNotFound:
                logger.warning("Current image not found - no rollback available")
            except Exception as e:
                logger.warning(f"Could not get current image for rollback: {e}")

            try:
                own_id = os.environ.get("HOSTNAME") or socket.gethostname()
                if own_id:
                    own_container = docker_client.containers.get(own_id)
                    running_image_id = own_container.image.id
                    logger.info(
                        f"Running container ({own_id[:12]}) image: {running_image_id[:12]}"
                    )
            except Exception as e:
                logger.warning(f"Could not inspect own container image: {e}")

            await self.ws.send({
                "type": "UPDATE_STATUS",
                "status": "downloading",
                "progress": 0,
                "message": "Downloading new agent image...",
            })

            # Download the image tarball with progress reporting
            ssl_verify = self.config.ssl_verify
            expected_checksum = None
            file_hasher = hashlib.sha256()

            async with httpx.AsyncClient(verify=ssl_verify, timeout=300.0) as client:
                logger.info(f"Downloading agent image from {image_url}")

                # Use streaming for progress updates
                async with client.stream(
                    "GET",
                    image_url,
                    headers={"Authorization": f"Bearer {self.config.agent_token}"},
                ) as response:
                    if response.status_code == 404:
                        await self.ws.send({
                            "type": "UPDATE_STATUS",
                            "status": "failed",
                            "error": "Image not available on server",
                            "message": "Agent image not available on server. Run 'Build Agent Image' first.",
                        })
                        return

                    response.raise_for_status()

                    # Get checksum from header for verification
                    expected_checksum = response.headers.get("x-checksum-sha256")
                    if expected_checksum:
                        logger.info(f"Expected checksum: {expected_checksum[:16]}...")

                    # Get total size for progress calculation
                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    last_progress = -1

                    # Save to temp file with progress updates
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as f:
                        tarball_path = f.name
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                            file_hasher.update(chunk)
                            downloaded += len(chunk)

                            # Report progress every 5%
                            if total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                if progress >= last_progress + 5:
                                    last_progress = progress
                                    await self.ws.send({
                                        "type": "UPDATE_STATUS",
                                        "status": "downloading",
                                        "progress": progress,
                                        "message": f"Downloading: {downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB ({progress}%)",
                                    })

            logger.info(f"Downloaded image to {tarball_path}")

            # Verify checksum
            if expected_checksum:
                actual_checksum = file_hasher.hexdigest()
                if actual_checksum.lower() != expected_checksum.lower():
                    logger.error(f"Checksum mismatch! Expected: {expected_checksum}, Got: {actual_checksum}")
                    await self.ws.send({
                        "type": "UPDATE_STATUS",
                        "status": "failed",
                        "error": "Checksum verification failed",
                        "message": "Downloaded image is corrupted. Please try again.",
                    })
                    return
                logger.info("Checksum verification passed")
            else:
                logger.warning("No checksum provided by server, skipping verification")

            await self.ws.send({
                "type": "UPDATE_STATUS",
                "status": "loading",
                "message": "Verifying and loading new image into Docker...",
            })

            # Load the image using Docker SDK
            loaded_image = None
            try:
                with open(tarball_path, "rb") as f:
                    images = docker_client.images.load(f)
                    if images:
                        loaded_image = images[0]
                        logger.info(f"Loaded image: {loaded_image.tags}, ID: {loaded_image.id[:12]}")
            except docker.errors.DockerException as e:
                logger.error(f"Docker error loading image: {e}")
                await self.ws.send({
                    "type": "UPDATE_STATUS",
                    "status": "failed",
                    "error": str(e),
                    "message": f"Failed to load image: {e}",
                })
                return
            finally:
                # Cleanup temp file
                if tarball_path:
                    try:
                        os.unlink(tarball_path)
                        tarball_path = None
                    except Exception:
                        pass

            # Verify the loaded image differs from the IMAGE THE
            # CONTAINER IS RUNNING (not just from the tag). Comparing
            # against the tag's SHA is wrong when the builder shares
            # our Docker daemon — the tag may already reflect the new
            # build while our container still runs the older layers
            # underneath. See the rationale comment near `old_image_id`.
            compare_id = running_image_id or old_image_id
            if compare_id and loaded_image and loaded_image.id == compare_id:
                logger.info(
                    "Loaded image matches the running container's image — "
                    "no recreate needed."
                )
                await self.ws.send({
                    "type": "UPDATE_STATUS",
                    "status": "complete",
                    "message": "Agent is already up to date.",
                })
                return

            await self.ws.send({
                "type": "UPDATE_STATUS",
                "status": "restarting",
                "message": "Restarting agent container...",
            })

            # Brief delay to allow status message to be sent
            await asyncio.sleep(1)

            # Recreate this container with the new image
            # Dynamically find the install path
            install_path = find_agent_install_path()
            compose_file = os.path.join(install_path, "docker-compose.yml") if install_path else None

            try:
                if install_path and compose_file and os.path.isfile(compose_file):
                    logger.info(f"Recreating container with docker compose from {install_path}...")
                    # Run the updater from the agent's OWN image: it already
                    # bundles docker + the compose plugin (see Dockerfile), is
                    # guaranteed present locally (we're running it + just loaded
                    # the new one), so it needs NO package install and NO image
                    # pull. The previous approach ran a minimal base image and
                    # fetched the docker CLI over the internet AT UPDATE TIME —
                    # after `down` had already removed the agent — which stranded
                    # connectivity-constrained agents (e.g. CML-lab VMs): the
                    # fetch failed/hung and nothing brought the agent back.
                    # (agent v1.48.0)
                    update_cmd = (
                        f"sleep 3 && "
                        f"docker compose -f {compose_file} down --remove-orphans 2>/dev/null || true && "
                        f"docker compose -f {compose_file} up -d"
                    )

                    # Use Docker SDK to run updater in a detached container
                    # This container will survive our shutdown
                    logger.info("Launching updater container (from agent image)...")

                    def launch_updater():
                        try:
                            docker_client.containers.run(
                                "packetarch-agent:latest",
                                entrypoint=["/bin/sh", "-c"],
                                command=update_cmd,
                                detach=True,
                                remove=True,
                                name="packetarch-updater",
                                volumes={
                                    "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
                                    install_path: {"bind": install_path, "mode": "rw"},
                                },
                            )
                            return True
                        except docker.errors.ImageNotFound:
                            return False

                    if not launch_updater():
                        logger.error(
                            "packetarch-agent:latest not found for updater — this "
                            "should never happen (the agent is running it). Aborting."
                        )
                        raise RuntimeError("agent image missing for updater container")

                    logger.info("Updater container launched, agent will restart shortly")
                else:
                    # Fallback: use Docker API with container recreation
                    logger.warning("Install path not found, using Docker API fallback")
                    try:
                        # Updater runs from the agent image itself (bundles
                        # docker; no apk / no internet) to stop+rm+recreate.
                        logger.info("Launching updater container (fallback mode)...")
                        docker_client.containers.run(
                            "packetarch-agent:latest",
                            entrypoint=["/bin/sh", "-c"],
                            command=(
                                "sleep 3 && "
                                "docker stop packetarch-agent 2>/dev/null || true && "
                                "docker rm packetarch-agent 2>/dev/null || true && "
                                "docker run -d --name packetarch-agent --restart unless-stopped "
                                "--network host --cap-add NET_ADMIN --cap-add NET_RAW "
                                "-v /var/run/docker.sock:/var/run/docker.sock "
                                "packetarch-agent:latest"
                            ),
                            detach=True,
                            remove=True,
                            name="packetarch-updater",
                            volumes={
                                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
                            },
                        )
                        logger.info("Updater container launched")
                    except Exception as e:
                        logger.error(f"Docker API fallback failed: {e}")
                        await self.ws.send({
                            "type": "UPDATE_STATUS",
                            "status": "failed",
                            "error": str(e),
                            "message": f"Failed to restart container: {e}. Manual restart required.",
                        })
            except subprocess.TimeoutExpired:
                logger.error("docker command timed out")
                if old_image_id and compose_file:
                    await self._rollback_image(docker_client, old_image_id, compose_file)
                await self.ws.send({
                    "type": "UPDATE_STATUS",
                    "status": "failed",
                    "error": "Timeout",
                    "message": "docker command timed out. Manual restart may be required.",
                })
            except Exception as e:
                logger.error(f"Failed to recreate container: {e}")
                if old_image_id and compose_file:
                    await self._rollback_image(docker_client, old_image_id, compose_file)
                await self.ws.send({
                    "type": "UPDATE_STATUS",
                    "status": "failed",
                    "error": str(e),
                    "message": f"Failed to recreate container: {e}. Manual restart may be required.",
                })

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading image: {e}")
            await self.ws.send({
                "type": "UPDATE_STATUS",
                "status": "failed",
                "error": f"HTTP {e.response.status_code}",
                "message": f"Failed to download image: HTTP {e.response.status_code}",
            })
        except Exception as e:
            logger.error(f"Update failed: {e}")
            await self.ws.send({
                "type": "UPDATE_STATUS",
                "status": "failed",
                "error": str(e),
                "message": f"Update failed: {e}",
            })
        finally:
            # Ensure temp file is cleaned up
            if tarball_path:
                try:
                    os.unlink(tarball_path)
                except Exception:
                    pass

    async def _rollback_image(
        self,
        docker_client: docker.DockerClient,
        old_image_id: str,
        compose_file: str | None,
    ) -> bool:
        """Attempt to rollback to the previous image.

        Args:
            docker_client: Docker client instance
            old_image_id: The image ID to rollback to
            compose_file: Path to docker-compose.yml (or None for restart fallback)

        Returns:
            True if rollback succeeded, False otherwise
        """
        logger.warning(f"Attempting rollback to image {old_image_id[:12]}...")

        try:
            # Re-tag the old image as latest
            old_image = docker_client.images.get(old_image_id)
            old_image.tag("packetarch-agent", "latest")
            logger.info(f"Re-tagged {old_image_id[:12]} as packetarch-agent:latest")

            # Restart with old image
            install_path = find_agent_install_path()
            if install_path and compose_file and os.path.isfile(compose_file):
                result = subprocess.run(
                    ["docker", "compose", "-f", compose_file, "up", "-d", "--force-recreate"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=install_path,
                )
            else:
                # Fallback to docker restart
                result = subprocess.run(
                    ["docker", "restart", "packetarch-agent"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

            if result.returncode == 0:
                logger.info("Rollback successful")
                return True
            else:
                logger.error(f"Rollback failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def stop(self) -> None:
        """Stop the agent."""
        logger.info("Stopping agent...")
        self._running = False
        self.pool.stop_all()
        self.ws.stop()


def main() -> None:
    """Main entry point."""
    try:
        config = AgentConfig.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Set log level from config
    logging.getLogger().setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    agent = PacketArchAgent(config)

    # Handle signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        agent.stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Run agent
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        logger.info("Agent exited")


if __name__ == "__main__":
    main()
