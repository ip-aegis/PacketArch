# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Agent manager for tracking connected WebSocket agents and routing commands."""

import asyncio
import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.services.device_identity_enricher import enrich_definition_serial_numbers

logger = logging.getLogger(__name__)


@dataclass
class AgentConnection:
    """Represents a connected agent."""

    agent_id: UUID
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    hostname: str | None = None
    platform: str | None = None
    version: str | None = None
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    running_scenarios: set[str] = field(default_factory=set)


@dataclass
class AgentUpdateStatus:
    """Tracks the status of an agent update."""

    agent_id: UUID
    # idle, initiated, queued, downloading, loading, restarting, swapping,
    # complete, failed, timeout
    status: str = "idle"
    progress: int | None = None  # Download progress 0-100
    message: str = "No update in progress"
    target_version: str | None = None
    target_sha: str | None = None  # optional image SHA to confirm against
    initiated_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


@dataclass
class ScenarioDeployment:
    """Tracks a scenario deployed to an agent."""

    scenario_id: str
    agent_id: UUID
    state: str = "starting"
    packets_sent: int = 0
    bytes_sent: int = 0
    protocol_breakdown: dict[str, dict] | None = None
    flow_count: int = 0
    packets_per_second: float = 0.0
    bytes_per_second: float = 0.0
    error_message: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)


class AgentManager:
    """Manages connected WebSocket agents and routes commands."""

    # Error codes that are attack-injection-specific (don't kill deployment)
    _INJECTION_ERROR_CODES = frozenset({"INJECT_ATTACK_FAILED", "INVALID_COMMAND"})

    # Update statuses that are still in flight (not a terminal outcome). The
    # reaper expires these when stale; a reconnect heartbeat reporting the
    # target version/SHA transitions them to "complete".
    _UPDATE_NONTERMINAL = frozenset(
        {"initiated", "queued", "downloading", "loading", "restarting", "swapping"}
    )
    # How long an in-flight update may run with no confirmation before the
    # reaper fails it. Generous enough for a slow tarball pull + load +
    # recreate + reconnect on a connectivity-constrained CML VM.
    _UPDATE_DEADLINE_SECONDS = 300.0

    def __init__(self):
        """Initialize the agent manager."""
        self._connections: dict[UUID, AgentConnection] = {}
        self._deployments: dict[str, ScenarioDeployment] = {}  # scenario_id -> deployment
        self._pending_requests: dict[str, asyncio.Future] = {}  # request_id -> future
        self._update_statuses: dict[UUID, AgentUpdateStatus] = {}  # agent_id -> update status
        self._injection_results: dict[str, dict[str, Any]] = {}  # scenario_id -> injection outcome
        self._lock = asyncio.Lock()
        self._reaper_task: asyncio.Task | None = None

    @property
    def connected_agents(self) -> list[UUID]:
        """Get list of connected agent IDs."""
        return list(self._connections.keys())

    def is_connected(self, agent_id: UUID) -> bool:
        """Check if an agent is currently connected."""
        return agent_id in self._connections

    def get_connection(self, agent_id: UUID) -> AgentConnection | None:
        """Get connection info for an agent."""
        return self._connections.get(agent_id)

    def get_all_connections(self) -> list[AgentConnection]:
        """Get all connected agents."""
        return list(self._connections.values())

    async def register(self, agent_id: UUID, websocket: WebSocket) -> None:
        """Register a new agent connection.

        Args:
            agent_id: Agent UUID
            websocket: WebSocket connection
        """
        async with self._lock:
            # Close existing connection if any
            if agent_id in self._connections:
                old_conn = self._connections[agent_id]
                try:
                    await old_conn.websocket.close(code=1000, reason="New connection")
                except Exception:
                    pass

            self._connections[agent_id] = AgentConnection(
                agent_id=agent_id,
                websocket=websocket,
            )

        logger.info(f"Agent {agent_id} connected")

    async def unregister(self, agent_id: UUID) -> None:
        """Unregister an agent connection.

        Args:
            agent_id: Agent UUID
        """
        async with self._lock:
            if agent_id in self._connections:
                del self._connections[agent_id]

                # Mark all deployments for this agent as disconnected
                for deployment in self._deployments.values():
                    if deployment.agent_id == agent_id:
                        deployment.state = "disconnected"

        logger.info(f"Agent {agent_id} disconnected")

    async def send_command(self, agent_id: UUID, command: dict[str, Any]) -> bool:
        """Send a command to a specific agent.

        Args:
            agent_id: Target agent UUID
            command: Command dict to send

        Returns:
            True if sent successfully, False otherwise
        """
        conn = self._connections.get(agent_id)
        if not conn:
            logger.warning(f"Agent {agent_id} not connected")
            return False

        try:
            await conn.websocket.send_json(command)
            return True
        except Exception as e:
            logger.error(f"Failed to send command to agent {agent_id}: {e}")
            return False

    async def deploy_scenario(
        self,
        agent_id: UUID,
        scenario_id: str,
        definition: dict[str, Any],
        interface: str | None = None,
    ) -> bool:
        """Deploy a scenario to an agent.

        Args:
            agent_id: Target agent UUID
            scenario_id: Scenario UUID
            definition: Scenario definition dict
            interface: Optional interface override

        Returns:
            True if deployment command sent successfully
        """
        # Backfill serial numbers for legacy scenarios that may be missing them.
        # Primary generation happens at scenario creation time; this is a guardrail.
        enriched_definition = enrich_definition_serial_numbers(
            copy.deepcopy(definition), scenario_id, skip_existing=True
        )

        command: dict[str, Any] = {
            "type": "START_SCENARIO",
            "scenario_id": scenario_id,
            "definition": enriched_definition,
        }
        if interface:
            command["interface"] = interface

        success = await self.send_command(agent_id, command)
        if success:
            async with self._lock:
                self._deployments[scenario_id] = ScenarioDeployment(
                    scenario_id=scenario_id,
                    agent_id=agent_id,
                )
                conn = self._connections.get(agent_id)
                if conn:
                    conn.running_scenarios.add(scenario_id)

        return success

    async def stop_scenario(self, scenario_id: str) -> bool:
        """Stop a deployed scenario.

        Args:
            scenario_id: Scenario UUID to stop

        Returns:
            True if stop command sent successfully
        """
        success = False

        # First try in-memory deployment tracking
        deployment = self._deployments.get(scenario_id)
        if deployment:
            success = await self.send_command(deployment.agent_id, {
                "type": "STOP_SCENARIO",
                "scenario_id": scenario_id,
            })
        else:
            # If not found in deployments, search connected agents' running_scenarios
            # This handles cases where backend was restarted but agents are still running
            async with self._lock:
                for agent_id, conn in self._connections.items():
                    if scenario_id in conn.running_scenarios:
                        logger.info(f"Found scenario {scenario_id} running on agent {agent_id} via running_scenarios")
                        success = await self.send_command(agent_id, {
                            "type": "STOP_SCENARIO",
                            "scenario_id": scenario_id,
                        })
                        break

        if success:
            # Clear injection result cache to prevent stale status after stop
            async with self._lock:
                self._injection_results.pop(scenario_id, None)
        else:
            logger.warning(f"No deployment found for scenario {scenario_id}")

        return success

    async def send_adaptation_directive(
        self,
        scenario_id: str,
        directives: list[dict[str, Any]],
        ttl_seconds: int = 300,
    ) -> bool:
        """Send adaptive traffic directives to a running scenario.

        Args:
            scenario_id: Target scenario UUID
            directives: List of directive dicts
            ttl_seconds: Directive time-to-live

        Returns:
            True if directives were sent successfully
        """
        deployment = self._deployments.get(scenario_id)
        if not deployment:
            # Try searching connected agents
            for agent_id, conn in self._connections.items():
                if scenario_id in conn.running_scenarios:
                    return await self.send_command(agent_id, {
                        "type": "ADAPT_TRAFFIC",
                        "scenario_id": scenario_id,
                        "directives": directives,
                        "ttl_seconds": ttl_seconds,
                    })
            return False

        return await self.send_command(deployment.agent_id, {
            "type": "ADAPT_TRAFFIC",
            "scenario_id": scenario_id,
            "directives": directives,
            "ttl_seconds": ttl_seconds,
        })

    async def update_scenario(
        self,
        scenario_id: str,
        definition: dict[str, Any],
        interface: str | None = None,
    ) -> bool:
        """Update a running scenario with a new definition.

        Args:
            scenario_id: Scenario UUID
            definition: New scenario definition
            interface: Optional interface override

        Returns:
            True if update command sent successfully
        """
        deployment = self._deployments.get(scenario_id)
        if not deployment:
            logger.warning(f"No deployment found for scenario {scenario_id}")
            return False

        command: dict[str, Any] = {
            "type": "UPDATE_SCENARIO",
            "scenario_id": scenario_id,
            "definition": definition,
        }
        if interface:
            command["interface"] = interface

        return await self.send_command(deployment.agent_id, command)

    async def list_interfaces(self, agent_id: UUID, timeout: float = 10.0) -> list[dict[str, Any]]:
        """Request interface list from an agent.

        Args:
            agent_id: Target agent UUID
            timeout: Request timeout in seconds

        Returns:
            List of interface info dicts

        Raises:
            TimeoutError: If agent doesn't respond in time
            RuntimeError: If agent not connected
        """
        import uuid

        request_id = str(uuid.uuid4())
        future: asyncio.Future[list[dict[str, Any]]] = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            success = await self.send_command(agent_id, {
                "type": "LIST_INTERFACES",
                "request_id": request_id,
            })
            if not success:
                raise RuntimeError(f"Agent {agent_id} not connected")

            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_requests.pop(request_id, None)

    async def handle_message(self, agent_id: UUID, message: dict[str, Any]) -> None:
        """Handle a message from an agent.

        Args:
            agent_id: Source agent UUID
            message: Message dict
        """
        msg_type = message.get("type", "")

        if msg_type == "HEARTBEAT":
            await self._handle_heartbeat(agent_id, message)

        elif msg_type == "STATUS":
            await self._handle_status(agent_id, message)

        elif msg_type == "UPDATE_STATUS":
            await self.handle_update_status(agent_id, message)

        elif msg_type == "INTERFACES":
            await self._handle_interfaces(message)

        elif msg_type == "LOGS":
            await self._handle_logs(message)

        elif msg_type == "PING_RESPONSE":
            await self._handle_ping_response(message)

        elif msg_type == "ERROR":
            await self._handle_error(agent_id, message)

        elif msg_type == "PONG":
            # Heartbeat response, update last_heartbeat
            conn = self._connections.get(agent_id)
            if conn:
                conn.last_heartbeat = datetime.utcnow()

        else:
            logger.debug(f"Unknown message type from agent {agent_id}: {msg_type}")

    async def _handle_heartbeat(self, agent_id: UUID, message: dict[str, Any]) -> None:
        """Handle heartbeat message from agent."""
        conn = self._connections.get(agent_id)
        if conn:
            conn.last_heartbeat = datetime.utcnow()
            conn.cpu_percent = message.get("cpu", 0.0)
            conn.memory_percent = message.get("memory", 0.0)
            conn.hostname = message.get("hostname")
            conn.platform = message.get("platform")
            new_version = message.get("version")
            image_sha = message.get("image_sha")  # supervisor-era agents report this

            # Closed-loop update confirmation. Runs on EVERY heartbeat (not
            # only on a version *change*): an agent whose update failed may
            # keep heartbeating the OLD version on the SAME connection, which
            # a version-delta gate would never catch. We only ever mark
            # "complete" here (positive confirmation); the reaper is what
            # fails a stuck update after the deadline.
            await self.reconcile_update_on_heartbeat(agent_id, new_version, image_sha)

            conn.version = new_version

    async def _handle_status(self, agent_id: UUID, message: dict[str, Any]) -> None:
        """Handle scenario status update from agent."""
        scenario_id = message.get("scenario_id")
        if not scenario_id:
            return

        state = message.get("state", "unknown")

        async with self._lock:
            # Update in-memory deployment if it exists, or recreate after restart
            deployment = self._deployments.get(scenario_id)
            if not deployment and state not in ("stopped", "error"):
                # Recreate deployment tracking lost after backend restart
                deployment = ScenarioDeployment(
                    scenario_id=scenario_id,
                    agent_id=agent_id,
                )
                self._deployments[scenario_id] = deployment
                logger.info(
                    f"Restored deployment tracking for scenario {scenario_id} "
                    f"on agent {agent_id}"
                )
            if deployment:
                deployment.state = state
                deployment.packets_sent = message.get("packets_sent", 0)
                deployment.bytes_sent = message.get("bytes_sent", 0)
                deployment.protocol_breakdown = message.get("protocol_breakdown")
                deployment.flow_count = message.get("flow_count", 0)
                deployment.packets_per_second = message.get("packets_per_second", 0.0)
                deployment.bytes_per_second = message.get("bytes_per_second", 0.0)
                deployment.error_message = message.get("error")

            # Always update connection's running scenarios based on status
            conn = self._connections.get(agent_id)
            if conn:
                if state in ("stopped", "error"):
                    conn.running_scenarios.discard(scenario_id)
                else:
                    conn.running_scenarios.add(scenario_id)

        logger.debug(
            f"Scenario {scenario_id}: state={state}, "
            f"packets={message.get('packets_sent', 0)}"
        )

    async def _handle_interfaces(self, message: dict[str, Any]) -> None:
        """Handle interface list response from agent."""
        request_id = message.get("request_id")
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                future.set_result(message.get("interfaces", []))

    async def _handle_logs(self, message: dict[str, Any]) -> None:
        """Handle logs response from agent."""
        request_id = message.get("request_id")
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                future.set_result(message.get("logs", []))

    async def _handle_ping_response(self, message: dict[str, Any]) -> None:
        """Handle ping test response from agent."""
        request_id = message.get("request_id")
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                future.set_result(message)

    async def _handle_error(self, agent_id: UUID, message: dict[str, Any]) -> None:
        """Handle error message from agent."""
        scenario_id = message.get("scenario_id")
        error_msg = message.get("message", "Unknown error")
        error_code = message.get("code", "UNKNOWN")

        logger.error(f"Agent {agent_id} error [{error_code}]: {error_msg}")

        if scenario_id:
            async with self._lock:
                if error_code in self._INJECTION_ERROR_CODES:
                    # Attack injection failed — the deployment itself is fine
                    self._injection_results[scenario_id] = {
                        "status": "failed",
                        "message": error_msg,
                        "code": error_code,
                    }
                    logger.warning(
                        f"Attack injection failed for scenario {scenario_id}: {error_msg}"
                    )
                else:
                    deployment = self._deployments.get(scenario_id)
                    if deployment:
                        deployment.state = "error"
                        deployment.error_message = error_msg

    def get_deployment(self, scenario_id: str) -> ScenarioDeployment | None:
        """Get deployment info for a scenario."""
        return self._deployments.get(scenario_id)

    def get_injection_result(self, scenario_id: str) -> dict[str, Any] | None:
        """Get the injection result for a scenario (if any)."""
        return self._injection_results.get(scenario_id)

    def clear_injection_result(self, scenario_id: str) -> None:
        """Clear a previous injection result (called before retry)."""
        self._injection_results.pop(scenario_id, None)

    def get_agent_deployments(self, agent_id: UUID) -> list[ScenarioDeployment]:
        """Get all deployments for an agent."""
        return [d for d in self._deployments.values() if d.agent_id == agent_id]

    async def ping_agent(self, agent_id: UUID) -> bool:
        """Send a ping to an agent.

        Args:
            agent_id: Target agent UUID

        Returns:
            True if ping sent successfully
        """
        return await self.send_command(agent_id, {"type": "PING"})

    async def request_logs(
        self,
        agent_id: UUID,
        lines: int = 100,
        timeout: float = 15.0,
    ) -> list[str]:
        """Request recent logs from an agent.

        Args:
            agent_id: Target agent UUID
            lines: Number of log lines to retrieve
            timeout: Request timeout in seconds

        Returns:
            List of log lines

        Raises:
            TimeoutError: If agent doesn't respond in time
            RuntimeError: If agent not connected
        """
        import uuid

        request_id = str(uuid.uuid4())
        future: asyncio.Future[list[str]] = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            success = await self.send_command(agent_id, {
                "type": "GET_LOGS",
                "request_id": request_id,
                "lines": lines,
            })
            if not success:
                raise RuntimeError(f"Agent {agent_id} not connected")

            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_requests.pop(request_id, None)

    async def ping_with_timing(
        self,
        agent_id: UUID,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """Send a ping test to measure round-trip latency.

        Args:
            agent_id: Target agent UUID
            timeout: Request timeout in seconds

        Returns:
            Dict with latency measurements

        Raises:
            TimeoutError: If agent doesn't respond in time
            RuntimeError: If agent not connected
        """
        import time
        import uuid

        request_id = str(uuid.uuid4())
        future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        self._pending_requests[request_id] = future

        sent_at = time.time() * 1000  # ms

        try:
            success = await self.send_command(agent_id, {
                "type": "PING_TEST",
                "request_id": request_id,
                "sent_at": sent_at,
            })
            if not success:
                raise RuntimeError(f"Agent {agent_id} not connected")

            result = await asyncio.wait_for(future, timeout=timeout)
            received_at = time.time() * 1000

            return {
                "round_trip_ms": received_at - sent_at,
                "server_to_agent_ms": result.get("agent_received_at", 0) - sent_at,
                "agent_to_server_ms": received_at - result.get("agent_sent_at", received_at),
            }
        finally:
            self._pending_requests.pop(request_id, None)

    async def send_update_command(self, agent_id: UUID, target_version: str | None = None) -> bool:
        """Send update command to an agent and start tracking update status.

        The agent will download the latest image from this server and restart.

        Args:
            agent_id: Target agent UUID
            target_version: Expected version after update

        Returns:
            True if command sent successfully
        """
        # Initialize update status tracking
        async with self._lock:
            self._update_statuses[agent_id] = AgentUpdateStatus(
                agent_id=agent_id,
                status="initiated",
                message="Update command sent to agent",
                target_version=target_version,
                initiated_at=datetime.utcnow(),
            )

        success = await self.send_command(
            agent_id, {"type": "UPDATE_AGENT", "target_version": target_version}
        )

        if not success:
            async with self._lock:
                status = self._update_statuses.get(agent_id)
                if status:
                    status.status = "failed"
                    status.message = "Failed to send update command"
                    status.error = "WebSocket send failed"
                    status.completed_at = datetime.utcnow()

        return success

    def get_update_status(self, agent_id: UUID) -> AgentUpdateStatus:
        """Get the current update status for an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Update status object (returns idle status if no update in progress)
        """
        status = self._update_statuses.get(agent_id)
        if not status:
            return AgentUpdateStatus(
                agent_id=agent_id,
                status="idle",
                message="No update in progress",
            )
        return status

    def get_active_update_statuses(self) -> list[AgentUpdateStatus]:
        """Return all tracked (non-cleared) per-agent update statuses.

        Lets the UI poll once for every in-flight/just-finished update
        instead of N per-agent requests — used by the "Update All" bulk
        progress view and the Agents-tab "Updating…" indicators.
        """
        return list(self._update_statuses.values())

    async def handle_update_status(self, agent_id: UUID, message: dict[str, Any]) -> None:
        """Handle UPDATE_STATUS message from an agent.

        Args:
            agent_id: Agent UUID
            message: Status message from agent
        """
        status_str = message.get("status", "unknown")
        progress = message.get("progress")
        msg = message.get("message", "")
        error = message.get("error")

        async with self._lock:
            current = self._update_statuses.get(agent_id)
            if not current:
                # Create status if we're receiving update status without prior initiation
                # (e.g., agent was updating and we reconnected)
                current = AgentUpdateStatus(agent_id=agent_id)
                self._update_statuses[agent_id] = current

            current.status = status_str
            current.message = msg
            current.progress = progress
            current.error = error

            # Mark completion for terminal states
            if status_str in ("complete", "failed", "error"):
                current.completed_at = datetime.utcnow()

        logger.info(f"Agent {agent_id} update status: {status_str} - {msg}")

    async def reconcile_update_on_heartbeat(
        self, agent_id: UUID, version: str | None, image_sha: str | None = None
    ) -> None:
        """Positively confirm an in-flight update from a heartbeat.

        Called on every heartbeat. Marks a non-terminal update "complete" the
        moment the (re)connected agent reports the target version (or target
        SHA, if the backend recorded one). Does NOT mark failures here — a
        not-yet-matching version may simply mean the update is still running;
        the reaper (:meth:`expire_stale_updates`) fails it after the deadline.

        Args:
            agent_id: Agent UUID
            version: Version reported by the agent's heartbeat
            image_sha: Image SHA reported by supervisor-era agents (optional)
        """
        if not version and not image_sha:
            return
        async with self._lock:
            status = self._update_statuses.get(agent_id)
            if not status or status.status not in self._UPDATE_NONTERMINAL:
                return
            matched = False
            if status.target_sha and image_sha:
                matched = image_sha == status.target_sha
            elif status.target_version:
                matched = version == status.target_version
            else:
                # No target recorded — any reconnect heartbeat confirms it.
                matched = True
            if matched:
                status.status = "complete"
                status.message = f"Update confirmed: agent reporting v{version}"
                status.completed_at = datetime.utcnow()
                logger.info(f"Agent {agent_id} update confirmed at v{version}")

    async def expire_stale_updates(
        self, max_age_seconds: float | None = None
    ) -> int:
        """Fail any in-flight update that has run past the deadline.

        Without this, a stuck "restarting"/"swapping" (stranded agent, failed
        swap, agent that never reported back) would rot forever. Returns the
        number of statuses expired.
        """
        deadline = max_age_seconds or self._UPDATE_DEADLINE_SECONDS
        now = datetime.utcnow()
        expired = 0
        async with self._lock:
            for status in self._update_statuses.values():
                if status.status not in self._UPDATE_NONTERMINAL:
                    continue
                started = status.initiated_at or now
                age = (now - started).total_seconds()
                if age > deadline:
                    prior = status.status
                    status.status = "failed"
                    status.message = (
                        f"Update timed out after {int(age)}s with no "
                        f"confirmation (stuck at '{prior}')"
                    )
                    status.error = "timeout"
                    status.completed_at = now
                    expired += 1
        if expired:
            logger.warning(f"Expired {expired} stale agent update status(es)")
        return expired

    async def _update_reaper_loop(self, interval_seconds: float = 30.0) -> None:
        """Background loop that periodically expires stale update statuses."""
        logger.info("Agent update reaper started")
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await self.expire_stale_updates()
                except Exception as e:  # never let the reaper die on one bad sweep
                    logger.warning(f"update reaper sweep failed: {e}")
        except asyncio.CancelledError:
            logger.info("Agent update reaper stopped")
            raise

    def start_update_reaper(self) -> None:
        """Start the background update-status reaper (idempotent)."""
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._update_reaper_loop())

    async def stop_update_reaper(self) -> None:
        """Stop the background reaper."""
        if self._reaper_task and not self._reaper_task.done():
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass
        self._reaper_task = None

    def clear_update_status(self, agent_id: UUID) -> None:
        """Clear update status for an agent (e.g., after user acknowledges).

        Args:
            agent_id: Agent UUID
        """
        self._update_statuses.pop(agent_id, None)


# Global singleton instance
agent_manager = AgentManager()
