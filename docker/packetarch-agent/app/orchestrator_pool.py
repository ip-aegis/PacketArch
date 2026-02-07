"""Orchestrator pool for managing multiple concurrent traffic generation scenarios."""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ScenarioState(str, Enum):
    """State of a scenario in the pool."""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ScenarioStatus:
    """Status information for a running scenario."""

    scenario_id: str
    state: ScenarioState
    packets_sent: int = 0
    error_message: str | None = None
    started_at: float | None = None
    stopped_at: float | None = None


@dataclass
class ScenarioContext:
    """Context for a running scenario."""

    scenario_id: str
    definition: dict[str, Any]
    interface: str
    status: ScenarioStatus = field(default_factory=lambda: ScenarioStatus("", ScenarioState.STARTING))
    thread: threading.Thread | None = None
    orchestrator: Any = None  # LiveTrafficOrchestrator
    cloud_scheduler: Any = None  # CloudTrafficScheduler
    stop_event: threading.Event = field(default_factory=threading.Event)

    def __post_init__(self):
        self.status = ScenarioStatus(
            scenario_id=self.scenario_id,
            state=ScenarioState.STARTING,
        )


class OrchestratorPool:
    """Manages multiple concurrent traffic generation scenarios."""

    def __init__(
        self,
        on_status_change: Callable[[str, ScenarioState, int, str | None], None] | None = None,
    ):
        """Initialize the orchestrator pool.

        Args:
            on_status_change: Callback when scenario status changes.
                              Args: (scenario_id, state, packets_sent, error_message)
        """
        self._scenarios: dict[str, ScenarioContext] = {}
        self._lock = threading.Lock()
        self._on_status_change = on_status_change

    @property
    def running_scenarios(self) -> list[str]:
        """Get list of running scenario IDs."""
        with self._lock:
            return [
                sid for sid, ctx in self._scenarios.items()
                if ctx.status.state in (ScenarioState.STARTING, ScenarioState.RUNNING)
            ]

    def get_status(self, scenario_id: str) -> ScenarioStatus | None:
        """Get status of a scenario."""
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if ctx:
                # Update packets_sent from orchestrator and cloud scheduler if running
                packets = 0
                if ctx.orchestrator and hasattr(ctx.orchestrator, 'packets_sent'):
                    packets += ctx.orchestrator.packets_sent
                if ctx.cloud_scheduler and hasattr(ctx.cloud_scheduler, 'packets_sent'):
                    packets += ctx.cloud_scheduler.packets_sent
                ctx.status.packets_sent = packets
                return ctx.status
            return None

    def get_all_statuses(self) -> list[ScenarioStatus]:
        """Get status of all scenarios."""
        with self._lock:
            statuses = []
            for ctx in self._scenarios.values():
                # Update packets_sent from orchestrator and cloud scheduler if running
                packets = 0
                if ctx.orchestrator and hasattr(ctx.orchestrator, 'packets_sent'):
                    packets += ctx.orchestrator.packets_sent
                if ctx.cloud_scheduler and hasattr(ctx.cloud_scheduler, 'packets_sent'):
                    packets += ctx.cloud_scheduler.packets_sent
                ctx.status.packets_sent = packets
                statuses.append(ctx.status)
            return statuses

    def start(
        self,
        scenario_id: str,
        definition: dict[str, Any],
        interface: str,
    ) -> bool:
        """Start a new scenario.

        Args:
            scenario_id: Unique scenario identifier
            definition: Scenario definition dict with devices and flows
            interface: Network interface for packet injection

        Returns:
            True if started successfully, False if already running
        """
        with self._lock:
            if scenario_id in self._scenarios:
                existing = self._scenarios[scenario_id]
                if existing.status.state in (ScenarioState.STARTING, ScenarioState.RUNNING):
                    logger.warning(f"Scenario {scenario_id} is already running")
                    return False
                # Clean up old context
                del self._scenarios[scenario_id]

            ctx = ScenarioContext(
                scenario_id=scenario_id,
                definition=definition,
                interface=interface,
            )
            self._scenarios[scenario_id] = ctx

        # Start in a thread
        thread = threading.Thread(
            target=self._run_scenario,
            args=(ctx,),
            name=f"scenario-{scenario_id[:8]}",
            daemon=True,
        )
        ctx.thread = thread
        thread.start()

        logger.info(f"Started scenario {scenario_id} on interface {interface}")
        return True

    def stop(self, scenario_id: str) -> bool:
        """Stop a running scenario.

        Args:
            scenario_id: Scenario to stop

        Returns:
            True if stop signal sent, False if not found
        """
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if not ctx:
                logger.warning(f"Scenario {scenario_id} not found")
                return False

            if ctx.status.state not in (ScenarioState.STARTING, ScenarioState.RUNNING):
                logger.warning(f"Scenario {scenario_id} is not running (state: {ctx.status.state})")
                return False

        # Signal stop
        ctx.stop_event.set()
        ctx.status.state = ScenarioState.STOPPING
        self._notify_status_change(ctx)

        # Stop the orchestrator if it exists
        if ctx.orchestrator:
            ctx.orchestrator._running = False

        # Stop the cloud scheduler if it exists
        if ctx.cloud_scheduler:
            ctx.cloud_scheduler.stop()

        logger.info(f"Stop signal sent to scenario {scenario_id}")
        return True

    def stop_all(self) -> int:
        """Stop all running scenarios.

        Returns:
            Number of scenarios stopped
        """
        count = 0
        for scenario_id in list(self._scenarios.keys()):
            if self.stop(scenario_id):
                count += 1
        return count

    def _run_scenario(self, ctx: ScenarioContext) -> None:
        """Run a scenario in a thread."""
        try:
            ctx.status.state = ScenarioState.STARTING
            ctx.status.started_at = time.time()
            self._notify_status_change(ctx)

            # Import here to avoid circular imports and allow copying live_orchestrator
            from app.live_orchestrator import (
                DeviceContext,
                FlowContext,
                LiveTrafficOrchestrator,
            )
            from app.cloud_traffic_scheduler import CloudTrafficScheduler

            # Parse the definition
            devices = ctx.definition.get("devices", {})
            flows = ctx.definition.get("flows", {})

            # Handle both dict and list formats
            if isinstance(devices, list):
                devices = {d.get("id", str(i)): d for i, d in enumerate(devices)}
            if isinstance(flows, list):
                flows = {f.get("id", str(i)): f for i, f in enumerate(flows)}

            if not flows:
                raise ValueError("No flows defined in scenario")

            # Create orchestrator in perpetual mode (None duration)
            orchestrator = LiveTrafficOrchestrator(ctx.interface, duration_ms=None)
            ctx.orchestrator = orchestrator

            # Register all devices for discovery
            all_device_contexts = []
            for device_id, device in devices.items():
                network = device.get("network", {})
                fingerprint = (
                    device.get("vendorFingerprint") or
                    device.get("vendor_fingerprint") or
                    device.get("fingerprint") or
                    {}
                )
                # Get CVE vulnerability overrides for vulnerable firmware versions
                vulnerability_override = device.get("cveIdentityOverrides")
                if vulnerability_override:
                    logger.info(f"Device {device_id} has CVE override: {vulnerability_override.get('cve_id', 'unknown')}")

                device_ctx = DeviceContext(
                    device_id=device_id,
                    mac_address=network.get("macAddress", "00:00:00:00:00:01"),
                    ip_address=network.get("ipAddress", "10.0.0.1"),
                    port=502,
                    vendor_fingerprint=fingerprint,
                    vulnerability_override=vulnerability_override,
                    device_name=device.get("name") or device.get("label"),
                    scenario_id=ctx.scenario_id,
                )
                all_device_contexts.append(device_ctx)

            orchestrator.set_all_devices(all_device_contexts)

            # Add flows
            for flow_id, flow_def in flows.items():
                flow_ctx = self._create_flow_context(flow_def, devices)
                if flow_ctx:
                    orchestrator.add_flow(flow_ctx)

            if not orchestrator.flows:
                raise ValueError("No valid flows to generate")

            # Start cloud traffic scheduler for cloud service links (separate from OT poll loop)
            cloud_links = ctx.definition.get("cloud_service_links", [])
            cloud_scheduler = None

            if cloud_links:
                cloud_scheduler = CloudTrafficScheduler(ctx.interface)
                ctx.cloud_scheduler = cloud_scheduler

                for link in cloud_links:
                    if not link.get("enabled", True):
                        continue

                    device_id = link.get("device_id")
                    device = devices.get(device_id)

                    if device:
                        cloud_scheduler.add_link(link, device)
                    else:
                        logger.warning(f"Device {device_id} not found for cloud link {link.get('id')}")

                if cloud_scheduler.tasks:
                    cloud_scheduler.start()
                    logger.info(
                        f"Started cloud scheduler with {len(cloud_scheduler.tasks)} cloud service links"
                    )

            # Update state to running
            ctx.status.state = ScenarioState.RUNNING
            self._notify_status_change(ctx)

            logger.info(f"Scenario {ctx.scenario_id} running with {len(orchestrator.flows)} flows")

            # Start a thread to monitor stop signal
            def stop_monitor():
                ctx.stop_event.wait()
                orchestrator._running = False

            monitor_thread = threading.Thread(target=stop_monitor, daemon=True)
            monitor_thread.start()

            # Run generation (perpetual mode) - this blocks until stopped
            orchestrator.run()

            # Stop cloud scheduler if running
            if cloud_scheduler:
                cloud_scheduler.stop()

            # Final status update (include cloud scheduler packets in total)
            total_packets = orchestrator.packets_sent
            if cloud_scheduler:
                total_packets += cloud_scheduler.packets_sent

            ctx.status.packets_sent = total_packets

            # Graceful shutdown
            ctx.status.state = ScenarioState.STOPPED
            ctx.status.stopped_at = time.time()
            self._notify_status_change(ctx)

            logger.info(
                f"Scenario {ctx.scenario_id} stopped. "
                f"Total packets: {total_packets} "
                f"(OT: {orchestrator.packets_sent}"
                f"{f', Cloud: {cloud_scheduler.packets_sent}' if cloud_scheduler else ''})"
            )

        except ImportError as e:
            logger.error(f"Failed to import live_orchestrator: {e}")
            ctx.status.state = ScenarioState.ERROR
            ctx.status.error_message = "Traffic generator not available"
            self._notify_status_change(ctx)

        except Exception as e:
            logger.error(f"Scenario {ctx.scenario_id} failed: {e}", exc_info=True)
            ctx.status.state = ScenarioState.ERROR
            ctx.status.error_message = str(e)
            ctx.status.stopped_at = time.time()
            self._notify_status_change(ctx)

    def _create_flow_context(
        self,
        flow_def: dict[str, Any],
        devices: dict[str, dict[str, Any]],
    ) -> Any | None:
        """Create a FlowContext from flow definition."""
        try:
            from app.live_orchestrator import DeviceContext, FlowContext

            source_device = devices.get(flow_def.get("sourceDeviceId"))
            target_device = devices.get(flow_def.get("targetDeviceId"))

            # Check for external flows (EWON Talk2M, etc.)
            flow_config = flow_def.get("config", {})
            is_external_flow = flow_config.get("external", False)

            if not source_device:
                logger.warning(f"Missing source device for flow {flow_def.get('id')}")
                return None

            if not target_device and not is_external_flow:
                logger.warning(f"Missing target device for flow {flow_def.get('id')}")
                return None

            protocol = flow_def.get("protocol", "modbus_tcp")

            # Get network info, fingerprints, and CVE overrides for source
            src_network = source_device.get("network", {})
            src_fingerprint = (
                source_device.get("vendorFingerprint") or
                source_device.get("vendor_fingerprint") or
                source_device.get("fingerprint") or
                {}
            )
            src_vulnerability = source_device.get("cveIdentityOverrides")

            # Protocol port mapping
            PROTOCOL_PORTS = {
                "modbus_tcp": 502,
                "s7comm": 102,
                "s7comm_plus": 102,
                "ethernet_ip": 44818,
                "bacnet_ip": 47808,
                "dnp3": 20000,
                "opcua": 4840,
                "opc_ua": 4840,
                "iec104": 2404,
                "https": 443,
            }
            default_port = PROTOCOL_PORTS.get(protocol, 44818)

            source = DeviceContext(
                device_id=source_device.get("id", ""),
                mac_address=src_network.get("macAddress", "00:00:00:00:00:01"),
                ip_address=src_network.get("ipAddress", "10.0.0.1"),
                port=flow_def.get("protocolConfig", {}).get("sourcePort", 50000),
                vendor_fingerprint=src_fingerprint,
                vulnerability_override=src_vulnerability,
                device_name=source_device.get("name") or source_device.get("label"),
            )

            # Handle external flows vs internal flows
            if is_external_flow:
                # External flow - destination is an external IP, not another device
                external_ip = flow_config.get("externalIp", "0.0.0.0")
                external_port = flow_config.get("externalPort", 443)

                destination = DeviceContext(
                    device_id="external_cloud",
                    mac_address="00:00:00:00:00:00",  # Placeholder - will use gateway
                    ip_address=external_ip,
                    port=external_port,
                )

                logger.info(
                    f"Created external flow {flow_def.get('id')}: "
                    f"{source.ip_address} -> {external_ip}:{external_port}"
                )
            else:
                # Internal flow - destination is another device
                dst_network = target_device.get("network", {})
                dst_fingerprint = (
                    target_device.get("vendorFingerprint") or
                    target_device.get("vendor_fingerprint") or
                    target_device.get("fingerprint") or
                    {}
                )
                dst_vulnerability = target_device.get("cveIdentityOverrides")

                destination = DeviceContext(
                    device_id=target_device.get("id", ""),
                    mac_address=dst_network.get("macAddress", "00:00:00:00:00:02"),
                    ip_address=dst_network.get("ipAddress", "10.0.0.2"),
                    port=flow_def.get("protocolConfig", {}).get("port", default_port),
                    unit_id=flow_def.get("protocolConfig", {}).get("unitId", 1),
                    vendor_fingerprint=dst_fingerprint,
                    vulnerability_override=dst_vulnerability,
                    device_name=target_device.get("name") or target_device.get("label"),
                )

            # Timing
            timing = flow_def.get("timing", {})
            timing_model = {
                "poll_interval_ms": timing.get("intervalMs", 1000),
                "jitter_min_ms": timing.get("jitterMs", 0) * -0.5,
                "jitter_max_ms": timing.get("jitterMs", 50) * 0.5,
            }

            # Merge flow config into protocolConfig for the orchestrator
            merged_config = flow_def.get("protocolConfig", {}).copy()
            merged_config.update(flow_config)

            return FlowContext(
                flow_id=flow_def.get("id", ""),
                source=source,
                destination=destination,
                protocol=protocol,
                config=merged_config,
                timing_model=timing_model,
            )

        except Exception as e:
            logger.error(f"Error creating flow context: {e}")
            return None

    def _notify_status_change(self, ctx: ScenarioContext) -> None:
        """Notify callback of status change."""
        if self._on_status_change:
            try:
                self._on_status_change(
                    ctx.scenario_id,
                    ctx.status.state,
                    ctx.status.packets_sent,
                    ctx.status.error_message,
                )
            except Exception as e:
                logger.error(f"Status change callback error: {e}")
