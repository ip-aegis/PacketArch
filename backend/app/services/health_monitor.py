"""Agent health monitoring and auto-recovery service.

Runs an asyncio background loop that monitors connected agents for:
- Heartbeat timeouts (agent connected but not sending heartbeats)
- Packet stalls (deployment running but 0 pps)
- Resource exhaustion (high CPU/memory sustained)
- Scenario errors (deployment in error state)

Provides auto-recovery: restarts stalled scenarios and redeploys
disconnected scenarios when agents reconnect.

All data is in-memory — rebuilds naturally from agent heartbeats/status.
"""

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


class HealthEventType(str, Enum):
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    PACKET_STALL = "packet_stall"
    RESOURCE_WARNING = "resource_warning"
    RESOURCE_CRITICAL = "resource_critical"
    SCENARIO_ERROR = "scenario_error"
    AGENT_DISCONNECTED = "agent_disconnected"
    AGENT_RECONNECTED = "agent_reconnected"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_SUCCEEDED = "recovery_succeeded"
    RECOVERY_FAILED = "recovery_failed"
    RECOVERY_LIMIT_REACHED = "recovery_limit_reached"


class HealthEventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class HealthEvent:
    id: str
    timestamp: datetime
    event_type: HealthEventType
    severity: HealthEventSeverity
    agent_id: str
    agent_name: str
    scenario_id: str | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "scenario_id": self.scenario_id,
            "message": self.message,
            "details": self.details,
            "acknowledged": self.acknowledged,
        }


@dataclass
class RecoveryAttempt:
    scenario_id: str
    agent_id: str
    attempted_at: datetime
    succeeded: bool = False
    error: str | None = None


@dataclass
class AgentHealthState:
    agent_id: UUID
    status: HealthStatus = HealthStatus.HEALTHY
    last_heartbeat_check: datetime | None = None
    heartbeat_missed: bool = False
    resource_warning_since: datetime | None = None
    stalled_scenarios: set[str] = field(default_factory=set)
    recovery_attempts: deque = field(
        default_factory=lambda: deque(maxlen=100)
    )
    # Track when deployments first entered "running" for grace period
    deployment_running_since: dict[str, datetime] = field(default_factory=dict)


@dataclass
class DisconnectedDeployment:
    agent_id: UUID
    agent_name: str
    scenario_id: str
    interface: str | None
    disconnected_at: datetime


@dataclass
class HealthMonitorConfig:
    check_interval_seconds: float = 10.0
    heartbeat_timeout_seconds: float = 90.0
    stall_detection_seconds: float = 30.0
    stall_grace_period_seconds: float = 60.0
    resource_warning_threshold: float = 85.0
    resource_critical_threshold: float = 95.0
    resource_sustained_seconds: float = 30.0
    max_recovery_attempts_per_hour: int = 3
    recovery_cooldown_seconds: float = 60.0
    auto_recovery_enabled: bool = True
    auto_redeploy_on_reconnect: bool = True
    max_events: int = 200
    disconnected_deployment_ttl_hours: float = 24.0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class HealthMonitorService:
    """Singleton health monitoring service."""

    def __init__(self) -> None:
        self._agent_health: dict[UUID, AgentHealthState] = {}
        self._events: deque[HealthEvent] = deque(maxlen=200)
        self._disconnected_deployments: dict[str, DisconnectedDeployment] = {}
        self.config = HealthMonitorConfig()
        self._task: asyncio.Task | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")

    async def stop(self) -> None:
        """Stop the background monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Health monitor stopped")

    # ------------------------------------------------------------------
    # Monitor loop
    # ------------------------------------------------------------------

    async def _monitor_loop(self) -> None:
        """Main monitoring loop — runs every check_interval_seconds."""
        while self._running:
            try:
                await asyncio.sleep(self.config.check_interval_seconds)
                await self._run_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor loop error: {e}", exc_info=True)

    async def _run_checks(self) -> None:
        """Execute all health checks."""
        from app.services.agent_manager import agent_manager
        from app.services.traffic_dashboard import traffic_dashboard

        now = datetime.now(timezone.utc)
        connections = agent_manager.get_all_connections()

        # Build set of connected agent IDs for offline detection
        connected_ids = {conn.agent_id for conn in connections}

        # Prune health state for agents we no longer track
        # (Keep offline agents for a while for event history)

        # --- Heartbeat timeout check ---
        for conn in connections:
            health = self._get_or_create_health(conn.agent_id)
            # AgentConnection.last_heartbeat is naive UTC — make it aware
            last_hb = conn.last_heartbeat.replace(tzinfo=timezone.utc) if conn.last_heartbeat.tzinfo is None else conn.last_heartbeat
            elapsed = (now - last_hb).total_seconds()

            if elapsed > self.config.heartbeat_timeout_seconds:
                if not health.heartbeat_missed:
                    health.heartbeat_missed = True
                    self._emit_event(
                        HealthEventType.HEARTBEAT_TIMEOUT,
                        HealthEventSeverity.WARNING,
                        conn.agent_id,
                        conn.hostname or str(conn.agent_id)[:8],
                        message=f"No heartbeat for {int(elapsed)}s (timeout: {int(self.config.heartbeat_timeout_seconds)}s)",
                        details={"elapsed_seconds": round(elapsed, 1)},
                    )
                health.status = max_status(health.status, HealthStatus.WARNING)
            else:
                health.heartbeat_missed = False

        # --- Resource exhaustion check ---
        for conn in connections:
            health = self._get_or_create_health(conn.agent_id)
            cpu = conn.cpu_percent
            mem = conn.memory_percent
            worst = max(cpu, mem)

            if worst > self.config.resource_critical_threshold:
                if health.resource_warning_since is None:
                    health.resource_warning_since = now
                sustained = (now - health.resource_warning_since).total_seconds()
                if sustained >= self.config.resource_sustained_seconds:
                    # Only emit once per sustained period
                    if health.status != HealthStatus.CRITICAL:
                        self._emit_event(
                            HealthEventType.RESOURCE_CRITICAL,
                            HealthEventSeverity.CRITICAL,
                            conn.agent_id,
                            conn.hostname or str(conn.agent_id)[:8],
                            message=f"CPU {cpu:.0f}%, Memory {mem:.0f}% (sustained {int(sustained)}s)",
                            details={"cpu_percent": cpu, "memory_percent": mem, "sustained_seconds": round(sustained, 1)},
                        )
                    health.status = HealthStatus.CRITICAL
            elif worst > self.config.resource_warning_threshold:
                if health.resource_warning_since is None:
                    health.resource_warning_since = now
                sustained = (now - health.resource_warning_since).total_seconds()
                if sustained >= self.config.resource_sustained_seconds:
                    if health.status not in (HealthStatus.WARNING, HealthStatus.CRITICAL):
                        self._emit_event(
                            HealthEventType.RESOURCE_WARNING,
                            HealthEventSeverity.WARNING,
                            conn.agent_id,
                            conn.hostname or str(conn.agent_id)[:8],
                            message=f"CPU {cpu:.0f}%, Memory {mem:.0f}% (sustained {int(sustained)}s)",
                            details={"cpu_percent": cpu, "memory_percent": mem, "sustained_seconds": round(sustained, 1)},
                        )
                    health.status = max_status(health.status, HealthStatus.WARNING)
            else:
                health.resource_warning_since = None
                # Only clear status if no other issues
                if not health.heartbeat_missed and not health.stalled_scenarios:
                    health.status = HealthStatus.HEALTHY

        # --- Packet stall detection ---
        stall_candidates = traffic_dashboard.get_stall_candidates(
            self.config.stall_detection_seconds
        )
        for candidate in stall_candidates:
            scenario_id = candidate["scenario_id"]
            agent_id_str = candidate["agent_id"]
            try:
                agent_uuid = UUID(agent_id_str)
            except ValueError:
                continue

            health = self._get_or_create_health(agent_uuid)

            # Grace period: skip if deployment hasn't been running long enough
            running_since = health.deployment_running_since.get(scenario_id)
            if running_since:
                running_duration = (now - running_since).total_seconds()
                if running_duration < self.config.stall_grace_period_seconds:
                    continue

            if scenario_id not in health.stalled_scenarios:
                health.stalled_scenarios.add(scenario_id)
                agent_name = candidate.get("agent_name", agent_id_str[:8])
                self._emit_event(
                    HealthEventType.PACKET_STALL,
                    HealthEventSeverity.WARNING,
                    agent_uuid,
                    agent_name,
                    scenario_id=scenario_id,
                    message=f"0 pps for {int(candidate['elapsed_seconds'])}s on {agent_name}",
                    details={
                        "pps": candidate["pps"],
                        "elapsed_seconds": round(candidate["elapsed_seconds"], 1),
                    },
                )
                health.status = max_status(health.status, HealthStatus.WARNING)

                # Auto-recovery
                if self.config.auto_recovery_enabled:
                    await self._maybe_recover(agent_uuid, agent_name, scenario_id)

        # Clear stalled flag for deployments that recovered
        active_stall_ids = {c["scenario_id"] for c in stall_candidates}
        for health in self._agent_health.values():
            recovered = health.stalled_scenarios - active_stall_ids
            health.stalled_scenarios -= recovered

        # --- Prune expired disconnected deployments ---
        ttl_seconds = self.config.disconnected_deployment_ttl_hours * 3600
        expired_keys = [
            k for k, v in self._disconnected_deployments.items()
            if (now - v.disconnected_at).total_seconds() > ttl_seconds
        ]
        for k in expired_keys:
            del self._disconnected_deployments[k]

        # --- Recompute overall status for agents with no issues ---
        for conn in connections:
            health = self._get_or_create_health(conn.agent_id)
            if (
                not health.heartbeat_missed
                and not health.stalled_scenarios
                and health.resource_warning_since is None
            ):
                health.status = HealthStatus.HEALTHY

    # ------------------------------------------------------------------
    # Event hooks (called from agent_hub.py)
    # ------------------------------------------------------------------

    async def on_agent_connected(self, agent_id: UUID, agent_name: str) -> None:
        """Called when an agent connects/reconnects."""
        health = self._get_or_create_health(agent_id)
        health.status = HealthStatus.HEALTHY
        health.heartbeat_missed = False
        health.resource_warning_since = None
        health.stalled_scenarios.clear()

        # Check for disconnected deployments to redeploy
        if self.config.auto_redeploy_on_reconnect:
            to_redeploy = [
                v for v in self._disconnected_deployments.values()
                if v.agent_id == agent_id
            ]
            if to_redeploy:
                self._emit_event(
                    HealthEventType.AGENT_RECONNECTED,
                    HealthEventSeverity.INFO,
                    agent_id,
                    agent_name,
                    message=f"Reconnected with {len(to_redeploy)} scenario(s) to redeploy",
                )
                # Schedule redeploy as separate task to avoid blocking WebSocket handler
                asyncio.create_task(
                    self._auto_redeploy_batch(agent_id, agent_name, to_redeploy)
                )

    async def on_agent_disconnected(
        self, agent_id: UUID, agent_name: str, running_scenarios: list[str]
    ) -> None:
        """Called when an agent disconnects. Saves running scenarios for redeploy."""
        health = self._get_or_create_health(agent_id)
        health.status = HealthStatus.OFFLINE

        now = datetime.now(timezone.utc)

        if running_scenarios:
            # Get interfaces from existing deployments in agent_manager
            from app.services.agent_manager import agent_manager
            for scenario_id in running_scenarios:
                key = f"{agent_id}:{scenario_id}"
                # Try to get the interface from the deployment record
                deployment = agent_manager._deployments.get(scenario_id)
                interface = None
                if deployment and deployment.agent_id == agent_id:
                    # We don't store interface in ScenarioDeployment, so we'll
                    # look it up from DB at redeploy time
                    pass

                self._disconnected_deployments[key] = DisconnectedDeployment(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    scenario_id=scenario_id,
                    interface=interface,
                    disconnected_at=now,
                )

            self._emit_event(
                HealthEventType.AGENT_DISCONNECTED,
                HealthEventSeverity.WARNING,
                agent_id,
                agent_name,
                message=f"Disconnected with {len(running_scenarios)} running scenario(s)",
                details={"running_scenarios": running_scenarios},
            )
        else:
            self._emit_event(
                HealthEventType.AGENT_DISCONNECTED,
                HealthEventSeverity.INFO,
                agent_id,
                agent_name,
                message="Disconnected (no running scenarios)",
            )

    def on_deployment_status(
        self, agent_id: UUID, scenario_id: str, pps: float, state: str
    ) -> None:
        """Called on each STATUS message. Tracks running-since for grace period."""
        health = self._get_or_create_health(agent_id)

        if state == "running":
            if scenario_id not in health.deployment_running_since:
                health.deployment_running_since[scenario_id] = datetime.now(timezone.utc)
            # Clear stall flag if pps recovered
            if pps > 0:
                health.stalled_scenarios.discard(scenario_id)
        elif state in ("stopped", "error", "disconnected"):
            health.deployment_running_since.pop(scenario_id, None)
            health.stalled_scenarios.discard(scenario_id)

    def on_deployment_error(
        self, agent_id: UUID, agent_name: str, scenario_id: str, error_msg: str
    ) -> None:
        """Called when a deployment enters error state."""
        self._emit_event(
            HealthEventType.SCENARIO_ERROR,
            HealthEventSeverity.CRITICAL,
            agent_id,
            agent_name,
            scenario_id=scenario_id,
            message=f"Scenario error: {error_msg[:200]}",
            details={"error": error_msg},
        )
        health = self._get_or_create_health(agent_id)
        health.status = max_status(health.status, HealthStatus.CRITICAL)

    # ------------------------------------------------------------------
    # Auto-recovery
    # ------------------------------------------------------------------

    async def _maybe_recover(
        self, agent_id: UUID, agent_name: str, scenario_id: str
    ) -> None:
        """Attempt auto-recovery of a stalled scenario if within rate limits."""
        health = self._get_or_create_health(agent_id)
        now = datetime.now(timezone.utc)

        # Check rate limit
        recent_count = self._count_recent_recoveries(scenario_id)
        if recent_count >= self.config.max_recovery_attempts_per_hour:
            self._emit_event(
                HealthEventType.RECOVERY_LIMIT_REACHED,
                HealthEventSeverity.CRITICAL,
                agent_id,
                agent_name,
                scenario_id=scenario_id,
                message=f"Recovery limit reached ({recent_count}/{self.config.max_recovery_attempts_per_hour} per hour)",
            )
            return

        # Check cooldown
        recent_for_scenario = [
            r for r in health.recovery_attempts
            if r.scenario_id == scenario_id
        ]
        if recent_for_scenario:
            last = recent_for_scenario[-1]
            elapsed = (now - last.attempted_at).total_seconds()
            if elapsed < self.config.recovery_cooldown_seconds:
                return

        # Attempt recovery
        attempt = RecoveryAttempt(
            scenario_id=scenario_id,
            agent_id=str(agent_id),
            attempted_at=now,
        )
        health.recovery_attempts.append(attempt)

        self._emit_event(
            HealthEventType.RECOVERY_STARTED,
            HealthEventSeverity.INFO,
            agent_id,
            agent_name,
            scenario_id=scenario_id,
            message=f"Auto-recovering stalled scenario (attempt {recent_count + 1}/{self.config.max_recovery_attempts_per_hour})",
        )

        try:
            from app.services.agent_manager import agent_manager

            # Stop the stalled scenario
            await agent_manager.stop_scenario(scenario_id)
            await asyncio.sleep(2.0)  # Brief pause before restart

            # Fetch fresh scenario definition from DB
            definition, interface = await self._fetch_scenario_for_redeploy(
                scenario_id, agent_id
            )
            if definition is None:
                attempt.error = "Scenario not found in database"
                self._emit_event(
                    HealthEventType.RECOVERY_FAILED,
                    HealthEventSeverity.WARNING,
                    agent_id,
                    agent_name,
                    scenario_id=scenario_id,
                    message="Recovery failed: scenario not found in database",
                )
                return

            # Redeploy
            success = await agent_manager.deploy_scenario(
                agent_id=agent_id,
                scenario_id=scenario_id,
                definition=definition,
                interface=interface,
            )

            if success:
                attempt.succeeded = True
                # Reset running_since for fresh grace period
                health.deployment_running_since[scenario_id] = datetime.now(timezone.utc)
                health.stalled_scenarios.discard(scenario_id)
                self._emit_event(
                    HealthEventType.RECOVERY_SUCCEEDED,
                    HealthEventSeverity.INFO,
                    agent_id,
                    agent_name,
                    scenario_id=scenario_id,
                    message="Scenario recovered successfully",
                )
            else:
                attempt.error = "Failed to send deploy command"
                self._emit_event(
                    HealthEventType.RECOVERY_FAILED,
                    HealthEventSeverity.WARNING,
                    agent_id,
                    agent_name,
                    scenario_id=scenario_id,
                    message="Recovery failed: could not send deploy command",
                )

        except Exception as e:
            attempt.error = str(e)
            self._emit_event(
                HealthEventType.RECOVERY_FAILED,
                HealthEventSeverity.WARNING,
                agent_id,
                agent_name,
                scenario_id=scenario_id,
                message=f"Recovery failed: {e}",
            )
            logger.error(f"Auto-recovery failed for scenario {scenario_id}: {e}")

    async def _auto_redeploy_batch(
        self,
        agent_id: UUID,
        agent_name: str,
        deployments: list[DisconnectedDeployment],
    ) -> None:
        """Redeploy a batch of disconnected scenarios after agent reconnection."""
        from app.services.agent_manager import agent_manager

        for dep in deployments:
            key = f"{dep.agent_id}:{dep.scenario_id}"
            try:
                definition, interface = await self._fetch_scenario_for_redeploy(
                    dep.scenario_id, agent_id
                )
                if definition is None:
                    logger.warning(
                        f"Cannot redeploy scenario {dep.scenario_id}: not found in DB"
                    )
                    self._disconnected_deployments.pop(key, None)
                    continue

                # Also create a DB deployment record
                await self._create_deployment_record(agent_id, dep.scenario_id, interface)

                success = await agent_manager.deploy_scenario(
                    agent_id=agent_id,
                    scenario_id=dep.scenario_id,
                    definition=definition,
                    interface=interface or dep.interface,
                )

                if success:
                    self._emit_event(
                        HealthEventType.RECOVERY_SUCCEEDED,
                        HealthEventSeverity.INFO,
                        agent_id,
                        agent_name,
                        scenario_id=dep.scenario_id,
                        message=f"Auto-redeployed after reconnection",
                    )
                    # Reset grace period
                    health = self._get_or_create_health(agent_id)
                    health.deployment_running_since[dep.scenario_id] = datetime.now(timezone.utc)
                else:
                    self._emit_event(
                        HealthEventType.RECOVERY_FAILED,
                        HealthEventSeverity.WARNING,
                        agent_id,
                        agent_name,
                        scenario_id=dep.scenario_id,
                        message="Auto-redeploy failed: could not send deploy command",
                    )

            except Exception as e:
                logger.error(
                    f"Auto-redeploy failed for scenario {dep.scenario_id}: {e}"
                )
                self._emit_event(
                    HealthEventType.RECOVERY_FAILED,
                    HealthEventSeverity.WARNING,
                    agent_id,
                    agent_name,
                    scenario_id=dep.scenario_id,
                    message=f"Auto-redeploy failed: {e}",
                )
            finally:
                self._disconnected_deployments.pop(key, None)

            # Small delay between redeploys to avoid flooding
            await asyncio.sleep(1.0)

    async def _fetch_scenario_for_redeploy(
        self, scenario_id: str, agent_id: UUID
    ) -> tuple[dict | None, str | None]:
        """Fetch scenario definition and interface from DB for redeploy.

        Returns:
            (definition, interface) or (None, None) if not found.
        """
        from sqlalchemy import select

        from app.core.database import async_session_maker
        from app.models.scenario import Scenario
        from app.models.traffic_agent import AgentDeployment, TrafficAgent

        try:
            async with async_session_maker() as db:
                # Get scenario definition
                result = await db.execute(
                    select(Scenario).where(Scenario.id == UUID(scenario_id))
                )
                scenario = result.scalar_one_or_none()
                if not scenario or not scenario.definition:
                    return None, None

                # Try to find the interface from the most recent deployment
                dep_result = await db.execute(
                    select(AgentDeployment.interface)
                    .where(
                        AgentDeployment.agent_id == agent_id,
                        AgentDeployment.scenario_id == UUID(scenario_id),
                    )
                    .order_by(AgentDeployment.started_at.desc())
                    .limit(1)
                )
                dep_row = dep_result.scalar_one_or_none()
                interface = dep_row if dep_row else None

                # Fallback: get agent's default interface
                if not interface:
                    agent_result = await db.execute(
                        select(TrafficAgent.default_interface)
                        .where(TrafficAgent.id == agent_id)
                    )
                    interface = agent_result.scalar_one_or_none()

                return scenario.definition, interface

        except Exception as e:
            logger.error(f"Failed to fetch scenario {scenario_id} for redeploy: {e}")
            return None, None

    async def _create_deployment_record(
        self, agent_id: UUID, scenario_id: str, interface: str | None
    ) -> None:
        """Create an AgentDeployment DB record for a redeployed scenario."""
        from app.core.database import async_session_maker
        from app.models.traffic_agent import AgentDeployment

        try:
            async with async_session_maker() as db:
                deployment = AgentDeployment(
                    agent_id=agent_id,
                    scenario_id=UUID(scenario_id),
                    interface=interface,
                )
                db.add(deployment)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to create deployment record: {e}")

    # ------------------------------------------------------------------
    # Query methods (for API)
    # ------------------------------------------------------------------

    def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        severity_filter: str | None = None,
        agent_filter: str | None = None,
    ) -> list[HealthEvent]:
        """Get health events, most recent first."""
        events = list(self._events)
        events.reverse()  # Most recent first

        if severity_filter:
            events = [e for e in events if e.severity.value == severity_filter]
        if agent_filter:
            events = [e for e in events if e.agent_id == agent_filter]

        return events[offset : offset + limit]

    def get_events_total(
        self,
        severity_filter: str | None = None,
        agent_filter: str | None = None,
    ) -> int:
        """Get total count of events matching filters."""
        events = list(self._events)
        if severity_filter:
            events = [e for e in events if e.severity.value == severity_filter]
        if agent_filter:
            events = [e for e in events if e.agent_id == agent_filter]
        return len(events)

    def get_unacknowledged_count(self) -> int:
        """Count of unacknowledged events."""
        return sum(1 for e in self._events if not e.acknowledged)

    def get_counts_by_severity(self) -> dict[str, int]:
        """Count events by severity."""
        counts = {"info": 0, "warning": 0, "critical": 0}
        for e in self._events:
            if not e.acknowledged:
                counts[e.severity.value] = counts.get(e.severity.value, 0) + 1
        return counts

    def get_agent_health(self, agent_id: UUID) -> AgentHealthState | None:
        """Get health state for a specific agent."""
        return self._agent_health.get(agent_id)

    def get_all_health_statuses(self) -> dict[UUID, HealthStatus]:
        """Get status map: agent_id -> HealthStatus."""
        return {
            aid: h.status for aid, h in self._agent_health.items()
        }

    def get_agent_health_detail(self, agent_id: UUID) -> dict[str, Any] | None:
        """Get detailed health info for a single agent."""
        health = self._agent_health.get(agent_id)
        if not health:
            return None
        return {
            "status": health.status.value,
            "heartbeat_ok": not health.heartbeat_missed,
            "resource_ok": health.resource_warning_since is None,
            "stalled_scenarios": list(health.stalled_scenarios),
            "recent_recoveries": self._count_recent_recoveries_for_agent(agent_id),
        }

    def get_all_health_details(self) -> dict[str, dict[str, Any]]:
        """Get health details for all tracked agents."""
        result = {}
        for aid, health in self._agent_health.items():
            result[str(aid)] = {
                "status": health.status.value,
                "heartbeat_ok": not health.heartbeat_missed,
                "resource_ok": health.resource_warning_since is None,
                "stalled_scenarios": list(health.stalled_scenarios),
                "recent_recoveries": self._count_recent_recoveries_for_agent(aid),
            }
        return result

    def acknowledge_event(self, event_id: str) -> bool:
        """Mark an event as acknowledged. Returns True if found."""
        for event in self._events:
            if event.id == event_id:
                event.acknowledged = True
                return True
        return False

    def clear_events(self) -> int:
        """Clear all events. Returns count cleared."""
        count = len(self._events)
        self._events.clear()
        return count

    def get_config_dict(self) -> dict[str, Any]:
        """Get current config as dict."""
        return {
            "check_interval_seconds": self.config.check_interval_seconds,
            "heartbeat_timeout_seconds": self.config.heartbeat_timeout_seconds,
            "stall_detection_seconds": self.config.stall_detection_seconds,
            "stall_grace_period_seconds": self.config.stall_grace_period_seconds,
            "resource_warning_threshold": self.config.resource_warning_threshold,
            "resource_critical_threshold": self.config.resource_critical_threshold,
            "resource_sustained_seconds": self.config.resource_sustained_seconds,
            "max_recovery_attempts_per_hour": self.config.max_recovery_attempts_per_hour,
            "recovery_cooldown_seconds": self.config.recovery_cooldown_seconds,
            "auto_recovery_enabled": self.config.auto_recovery_enabled,
            "auto_redeploy_on_reconnect": self.config.auto_redeploy_on_reconnect,
        }

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update config fields. Returns full config after update."""
        allowed = {
            "check_interval_seconds", "heartbeat_timeout_seconds",
            "stall_detection_seconds", "stall_grace_period_seconds",
            "resource_warning_threshold", "resource_critical_threshold",
            "resource_sustained_seconds", "max_recovery_attempts_per_hour",
            "recovery_cooldown_seconds", "auto_recovery_enabled",
            "auto_redeploy_on_reconnect",
        }
        for key, value in updates.items():
            if key in allowed and hasattr(self.config, key):
                setattr(self.config, key, value)
        return self.get_config_dict()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create_health(self, agent_id: UUID) -> AgentHealthState:
        """Get or create health state for an agent."""
        if agent_id not in self._agent_health:
            self._agent_health[agent_id] = AgentHealthState(agent_id=agent_id)
        return self._agent_health[agent_id]

    def _emit_event(
        self,
        event_type: HealthEventType,
        severity: HealthEventSeverity,
        agent_id: UUID,
        agent_name: str,
        scenario_id: str | None = None,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> HealthEvent:
        """Create and store a health event."""
        event = HealthEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            severity=severity,
            agent_id=str(agent_id),
            agent_name=agent_name,
            scenario_id=scenario_id,
            message=message,
            details=details or {},
        )
        self._events.append(event)
        logger.info(
            f"Health event [{severity.value}] {event_type.value}: {message}"
        )
        return event

    def _count_recent_recoveries(
        self, scenario_id: str, window_seconds: float = 3600
    ) -> int:
        """Count recovery attempts for a scenario within time window."""
        now = datetime.now(timezone.utc)
        count = 0
        for health in self._agent_health.values():
            for attempt in health.recovery_attempts:
                if (
                    attempt.scenario_id == scenario_id
                    and (now - attempt.attempted_at).total_seconds() < window_seconds
                ):
                    count += 1
        return count

    def _count_recent_recoveries_for_agent(
        self, agent_id: UUID, window_seconds: float = 3600
    ) -> int:
        """Count recovery attempts for an agent within time window."""
        health = self._agent_health.get(agent_id)
        if not health:
            return 0
        now = datetime.now(timezone.utc)
        return sum(
            1 for a in health.recovery_attempts
            if (now - a.attempted_at).total_seconds() < window_seconds
        )


def max_status(a: HealthStatus, b: HealthStatus) -> HealthStatus:
    """Return the more severe of two health statuses."""
    order = {
        HealthStatus.HEALTHY: 0,
        HealthStatus.WARNING: 1,
        HealthStatus.CRITICAL: 2,
        HealthStatus.OFFLINE: 3,
    }
    return a if order.get(a, 0) >= order.get(b, 0) else b


# Global singleton
health_monitor = HealthMonitorService()
