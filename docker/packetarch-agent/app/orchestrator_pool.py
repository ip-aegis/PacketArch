"""Orchestrator pool for managing multiple concurrent traffic generation scenarios.

Uses the shared protocol engines (UnifiedOrchestrator + LiveOutput) for traffic
generation, providing parity between PCAP and live traffic output.
"""

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
    bytes_sent: int = 0
    protocol_breakdown: dict[str, dict] | None = None
    flow_count: int = 0
    packets_per_second: float = 0.0
    bytes_per_second: float = 0.0
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
    output: Any = None  # LiveOutput — tracks packet_count
    orchestrator: Any = None  # UnifiedOrchestrator — tracks per-protocol stats
    stop_event: threading.Event = field(default_factory=threading.Event)
    adaptive_controller: Any = None  # AdaptiveController — optional
    attack_orchestrator: Any = None  # AttackOrchestrator — optional

    def __post_init__(self):
        self.status = ScenarioStatus(
            scenario_id=self.scenario_id,
            state=ScenarioState.STARTING,
        )


# Protocol port mapping
PROTOCOL_PORTS = {
    "modbus_tcp": 502,
    "modbus_rtu": 502,
    "s7comm": 102,
    "s7comm_plus": 102,
    "ethernet_ip": 44818,
    "cip_safety": 44818,
    "profinet": 0,
    "profisafe": 0,
    "bacnet_ip": 47808,
    "bacnet": 47808,
    "dnp3": 20000,
    "opcua": 4840,
    "opc_ua": 4840,
    "iec104": 2404,
    "iec_104": 2404,
    "iec61850": 102,
    "snmp": 161,
    "lldp": 0,
    "cdp": 0,
    "ethercat": 0,
    "fins": 9600,
    "slmp": 5000,
    "pccc": 44818,
    "codesys": 11740,
    "wmi": 135,
    "fanuc": 8193,
    "dcs": 502,
    "cloud_service": 443,
    "https": 443,
}

# Map variant/safety protocol names to their parent engine ProtocolType values.
# Scenario templates use specific protocol strings (e.g. "profisafe", "s7comm_plus")
# but the traffic engine only has parent protocol implementations.
PROTOCOL_ALIASES = {
    "profisafe": "profinet",       # PROFIsafe uses PROFINET engine
    "s7comm_plus": "s7comm",       # S7comm+ uses S7comm engine
    "cip_safety": "ethernet_ip",   # CIP Safety uses EtherNet/IP engine
    "modbus": "modbus_tcp",        # Generic modbus alias
    "enip": "ethernet_ip",         # Short alias
    "bacnet_ip": "bacnet",         # BACnet/IP alias
}


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

    def _update_stats_from_orchestrator(self, ctx: ScenarioContext) -> None:
        """Pull live stats from the orchestrator and output into the status."""
        if ctx.output and hasattr(ctx.output, 'packet_count'):
            ctx.status.packets_sent = ctx.output.packet_count
        if ctx.output and hasattr(ctx.output, 'bytes_sent'):
            ctx.status.bytes_sent = ctx.output.bytes_sent
        if ctx.orchestrator and hasattr(ctx.orchestrator, 'get_stats_snapshot'):
            snapshot = ctx.orchestrator.get_stats_snapshot()
            if snapshot:
                ctx.status.protocol_breakdown = snapshot.get('protocol_stats')
                ctx.status.flow_count = snapshot.get('flow_count', 0)
                ctx.status.packets_per_second = snapshot.get('packets_per_second', 0.0)
                ctx.status.bytes_per_second = snapshot.get('bytes_per_second', 0.0)

    def get_status(self, scenario_id: str) -> ScenarioStatus | None:
        """Get status of a scenario."""
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if ctx:
                self._update_stats_from_orchestrator(ctx)
                return ctx.status
            return None

    def get_all_statuses(self) -> list[ScenarioStatus]:
        """Get status of all scenarios."""
        with self._lock:
            statuses = []
            for ctx in self._scenarios.values():
                self._update_stats_from_orchestrator(ctx)
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
                del self._scenarios[scenario_id]

            ctx = ScenarioContext(
                scenario_id=scenario_id,
                definition=definition,
                interface=interface,
            )
            self._scenarios[scenario_id] = ctx

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

        ctx.stop_event.set()
        ctx.status.state = ScenarioState.STOPPING
        self._notify_status_change(ctx)

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

    def check_thread_health(self) -> list[dict]:
        """Check health of all running scenario threads.

        Detects scenarios whose threads have died unexpectedly.
        Marks them as ERROR and notifies via status callback.

        Returns:
            List of unhealthy scenario dicts.
        """
        unhealthy = []
        with self._lock:
            for sid, ctx in self._scenarios.items():
                if ctx.status.state in (ScenarioState.STARTING, ScenarioState.RUNNING):
                    if ctx.thread is None or not ctx.thread.is_alive():
                        unhealthy.append({
                            "scenario_id": sid,
                            "state": ctx.status.state.value,
                            "thread_alive": ctx.thread.is_alive() if ctx.thread else False,
                        })
                        ctx.status.state = ScenarioState.ERROR
                        ctx.status.error_message = "Scenario thread died unexpectedly"
                        ctx.status.stopped_at = time.time()
                        self._notify_status_change(ctx)
        return unhealthy

    def _run_scenario(self, ctx: ScenarioContext) -> None:
        """Run a scenario using the shared UnifiedOrchestrator + LiveOutput."""
        try:
            ctx.status.state = ScenarioState.STARTING
            ctx.status.started_at = time.time()
            self._notify_status_change(ctx)

            from app.protocol_engines.output import LiveOutput
            from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
            from app.protocol_engines.types import (
                DeviceContext,
                FlowContext,
                ProtocolType,
            )

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

            # Create LiveOutput and UnifiedOrchestrator (perpetual mode)
            output = LiveOutput(interface=ctx.interface)
            ctx.output = output
            orchestrator = UnifiedOrchestrator(output=output, duration_ms=None)
            ctx.orchestrator = orchestrator

            # Add OT protocol flows
            vertical = ctx.definition.get("vertical")
            flow_count = 0
            for flow_id, flow_def in flows.items():
                flow_ctx = self._create_flow_context(
                    flow_def, devices, vertical=vertical, scenario_id=ctx.scenario_id,
                )
                if flow_ctx:
                    orchestrator.add_flow(flow_ctx)
                    flow_count += 1

            # Add cloud service links as regular flows via CloudServiceEngine
            cloud_links = ctx.definition.get("cloud_service_links", [])
            for link in cloud_links:
                if not link.get("enabled", True):
                    continue

                cloud_flow = self._create_cloud_flow(link, devices)
                if cloud_flow:
                    orchestrator.add_flow(cloud_flow)
                    flow_count += 1

            if flow_count == 0:
                raise ValueError("No valid flows to generate")

            # Initialize adaptive traffic controller (defaults to enabled)
            try:
                from app.protocol_engines.adaptive import AdaptiveConfig, AdaptiveController
                adaptive_dict = ctx.definition.get("adaptive_config", {})

                # Auto-populate phase schedule from scenario phases if present
                definition_phases = ctx.definition.get("phases", [])
                if definition_phases and not adaptive_dict.get("phase_schedule", {}).get("enabled"):
                    phase_configs = []
                    for p in definition_phases:
                        phase_configs.append({
                            "phase_id": p.get("phase_type", p.get("id", "")),
                            "name": p.get("name", ""),
                            "duration_seconds": p.get(
                                "live_duration_seconds",
                                p.get("duration_ms", 300000) / 1000,
                            ),
                            "rate_multiplier": p.get("traffic_multiplier", 1.0),
                            "active_flow_percent": p.get("active_flow_percent", 100.0),
                            "behaviors": p.get("behaviors", []),
                            "protocol_patterns": p.get("protocol_patterns", {}),
                            "color": p.get("color", "#1890ff"),
                        })
                    if phase_configs:
                        adaptive_dict.setdefault("phase_schedule", {})
                        adaptive_dict["phase_schedule"] = {
                            "enabled": True,
                            "cycle": True,
                            "phases": phase_configs,
                        }
                        logger.info(
                            f"Auto-populated phase schedule from {len(phase_configs)} "
                            f"scenario phases"
                        )

                adaptive_config = AdaptiveConfig.from_dict(adaptive_dict)
                if adaptive_config.enabled:
                    controller = AdaptiveController(adaptive_config, total_flows=flow_count)
                    orchestrator.register_adaptive_controller(controller)
                    ctx.adaptive_controller = controller
                    logger.info(f"Adaptive traffic enabled for scenario {ctx.scenario_id}")
            except Exception as e:
                logger.warning(f"Adaptive traffic unavailable: {e}")

            # Initialize attack orchestrator if playbook is configured
            try:
                attack_playbook_config = ctx.definition.get("attack_playbook")
                if attack_playbook_config and attack_playbook_config.get("playbook_id"):
                    from app.protocol_engines.attacks import (
                        AttackOrchestrator,
                        get_playbook,
                    )
                    from app.protocol_engines.attacks.types import AttackPlaybookConfig

                    playbook_id = attack_playbook_config["playbook_id"]
                    playbook = get_playbook(playbook_id)
                    if playbook:
                        config = AttackPlaybookConfig.from_dict(attack_playbook_config)
                        # Collect device list for target resolution
                        device_list = []
                        for dev_id, dev in devices.items():
                            device_list.append(dev)
                        attack_orch = AttackOrchestrator(
                            playbook=playbook,
                            devices=device_list,
                            config=config,
                        )
                        orchestrator.register_attack_orchestrator(attack_orch)
                        ctx.attack_orchestrator = attack_orch
                        logger.info(
                            f"Attack playbook '{playbook.name}' loaded for "
                            f"scenario {ctx.scenario_id}"
                        )
                    else:
                        logger.warning(
                            f"Attack playbook '{playbook_id}' not found, skipping"
                        )
            except Exception as e:
                logger.warning(f"Attack orchestrator unavailable: {e}")

            # Initialize ambient noise generator (ARP, NTP, LLDP, STP, etc.)
            try:
                from app.protocol_engines.ambient import (
                    AmbientDevice,
                    BackgroundNoiseGenerator,
                )

                # Build device-to-zone map and zone VLAN lookup
                zones_list = ctx.definition.get("zones", [])
                if isinstance(zones_list, dict):
                    zones_list = list(zones_list.values())
                zone_vlan_map: dict[str, int | None] = {}
                for z in zones_list:
                    zid = z.get("id", "")
                    network_info = z.get("network", z)
                    zone_vlan_map[zid] = network_info.get("vlanId") or network_info.get("vlan")

                def _collect_device_protocols(
                    dev_id: str, all_flows: dict[str, Any],
                ) -> list[str]:
                    protos: list[str] = []
                    for fdef in all_flows.values():
                        if fdef.get("sourceDeviceId") == dev_id or fdef.get("targetDeviceId") == dev_id:
                            p = fdef.get("protocol", "")
                            if p and p not in protos:
                                protos.append(p)
                    return protos

                seen_devices: dict[str, AmbientDevice] = {}
                for flow_id_iter, flow_def_iter in flows.items():
                    for dev_key in ("sourceDeviceId", "targetDeviceId"):
                        dev_id = flow_def_iter.get(dev_key)
                        dev = devices.get(dev_id) if dev_id else None
                        if dev and dev_id not in seen_devices:
                            network = dev.get("network", {})
                            ip = network.get("ipAddress", "")
                            mac = network.get("macAddress", "")
                            if ip and mac:
                                fp = dev.get("vendorFingerprint") or dev.get("vendor_fingerprint") or {}
                                dev_zone = dev.get("zone", "")
                                seen_devices[dev_id] = AmbientDevice(
                                    device_id=dev_id,
                                    mac_address=mac,
                                    ip_address=ip,
                                    gateway_ip=ip.rsplit(".", 1)[0] + ".1",
                                    protocols=_collect_device_protocols(dev_id, flows),
                                    device_type=dev.get("type", fp.get("device_type", "")),
                                    vendor=fp.get("vendor", ""),
                                    device_name=dev.get("name", dev_id),
                                    zone_id=dev_zone if dev_zone else None,
                                    vlan_id=zone_vlan_map.get(dev_zone),
                                    vendor_fingerprint=fp,
                                )
                if seen_devices:
                    ambient = BackgroundNoiseGenerator(list(seen_devices.values()))
                    orchestrator.register_ambient_generator(ambient)
                    logger.info(
                        f"Ambient noise enabled for {len(seen_devices)} devices"
                    )
            except Exception as e:
                logger.warning(f"Ambient noise unavailable: {e}")

            # Initialize process simulation
            try:
                process_sim_config = ctx.definition.get("process_sim", {})
                if not process_sim_config.get("enabled") and vertical:
                    # Auto-enable if vertical has a template
                    from app.protocol_engines.process_sim.templates import (
                        get_available_verticals,
                    )
                    if vertical in get_available_verticals():
                        process_sim_config = {"enabled": True, "vertical": vertical}
                if process_sim_config.get("enabled"):
                    from app.protocol_engines.process_sim import (
                        ProcessSimConfig,
                        ProcessSimController,
                        build_from_vertical,
                    )

                    ps_config = ProcessSimConfig.from_dict(process_sim_config)
                    ps_vertical = ps_config.vertical or vertical
                    if ps_vertical:
                        models, faults = build_from_vertical(ps_vertical)
                        if models:
                            flow_gens = {
                                fs.flow.flow_id: fs.flow.payload_generator
                                for fs in orchestrator.flows
                                if fs.flow.payload_generator
                            }
                            ps_controller = ProcessSimController(
                                ps_config, models, flow_gens, faults=faults,
                            )
                            orchestrator.register_process_sim(ps_controller)
                            logger.info(
                                f"Process simulation enabled for vertical '{ps_vertical}'"
                            )
            except Exception as e:
                logger.warning(f"Process simulation unavailable: {e}")

            # Update state to running
            ctx.status.state = ScenarioState.RUNNING
            self._notify_status_change(ctx)

            logger.info(f"Scenario {ctx.scenario_id} running with {flow_count} flows")

            # Run orchestration (blocks until stop_event is set)
            result = orchestrator.run(stop_event=ctx.stop_event)

            # Final status
            ctx.status.packets_sent = output.packet_count
            ctx.status.state = ScenarioState.STOPPED
            ctx.status.stopped_at = time.time()
            self._notify_status_change(ctx)

            logger.info(
                f"Scenario {ctx.scenario_id} stopped. "
                f"Packets: {output.packet_count}, "
                f"stopped_by_event={result.stopped_by_event}"
            )

        except ImportError as e:
            logger.error(f"Failed to import protocol engines: {e}")
            ctx.status.state = ScenarioState.ERROR
            ctx.status.error_message = f"Protocol engines not available: {e}"
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
        vertical: str | None = None,
        scenario_id: str | None = None,
    ) -> Any | None:
        """Create a FlowContext from flow definition."""
        try:
            from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType

            source_device = devices.get(flow_def.get("sourceDeviceId"))
            target_device = devices.get(flow_def.get("targetDeviceId"))

            flow_config = flow_def.get("config", {})
            is_external_flow = flow_config.get("external", False)

            if not source_device:
                logger.warning(f"Missing source device for flow {flow_def.get('id')}")
                return None

            if not target_device and not is_external_flow:
                logger.warning(f"Missing target device for flow {flow_def.get('id')}")
                return None

            protocol_str = flow_def.get("protocol", "modbus_tcp")

            # Map variant protocol names to their parent engine type
            engine_protocol_str = PROTOCOL_ALIASES.get(protocol_str, protocol_str)

            # Map protocol string to ProtocolType enum
            try:
                protocol = ProtocolType(engine_protocol_str)
            except ValueError:
                logger.warning(f"Unknown protocol '{protocol_str}', skipping flow")
                return None

            default_port = PROTOCOL_PORTS.get(protocol_str, 44818)

            # Build source DeviceContext
            src_network = source_device.get("network", {})
            src_fingerprint = (
                source_device.get("vendorFingerprint") or
                source_device.get("vendor_fingerprint") or
                source_device.get("fingerprint") or
                {}
            )

            source = DeviceContext(
                device_id=source_device.get("id", ""),
                mac_address=src_network.get("macAddress", "00:00:00:00:00:01"),
                ip_address=src_network.get("ipAddress", "10.0.0.1"),
                port=flow_def.get("protocolConfig", {}).get("sourcePort", 50000),
                vendor_fingerprint=src_fingerprint,
                scenario_id=scenario_id,
                device_name=source_device.get("name"),
            )

            # Build destination DeviceContext
            if is_external_flow:
                external_ip = flow_config.get("externalIp", "0.0.0.0")
                external_port = flow_config.get("externalPort", 443)

                destination = DeviceContext(
                    device_id="external_cloud",
                    mac_address="00:00:00:00:00:00",
                    ip_address=external_ip,
                    port=external_port,
                )
            else:
                dst_network = target_device.get("network", {})
                dst_fingerprint = (
                    target_device.get("vendorFingerprint") or
                    target_device.get("vendor_fingerprint") or
                    target_device.get("fingerprint") or
                    {}
                )

                destination = DeviceContext(
                    device_id=target_device.get("id", ""),
                    mac_address=dst_network.get("macAddress", "00:00:00:00:00:02"),
                    ip_address=dst_network.get("ipAddress", "10.0.0.2"),
                    port=flow_def.get("protocolConfig", {}).get("port", default_port),
                    unit_id=flow_def.get("protocolConfig", {}).get("unitId", 1),
                    vendor_fingerprint=dst_fingerprint,
                    scenario_id=scenario_id,
                    device_name=target_device.get("name"),
                )

            # Timing model
            timing = flow_def.get("timing", {})
            jitter_ms = timing.get("jitterMs", 50)
            timing_model = {
                "poll_interval_ms": timing.get("intervalMs", 1000),
                "response_delay_ms": timing.get("responseDelayMs", 5.0),
                "jitter": {
                    "type": "uniform",
                    "min_ms": -abs(jitter_ms) * 0.5,
                    "max_ms": abs(jitter_ms) * 0.5,
                },
            }

            # Merge flow config into protocolConfig
            merged_config = flow_def.get("protocolConfig", {}).copy()
            merged_config.update(flow_config)
            if vertical:
                merged_config["_vertical"] = vertical

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

    def _create_cloud_flow(
        self,
        link: dict[str, Any],
        devices: dict[str, dict[str, Any]],
    ) -> Any | None:
        """Create a FlowContext for a cloud service link."""
        try:
            from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType

            device_id = link.get("device_id")
            device = devices.get(device_id)
            if not device:
                logger.warning(f"Device {device_id} not found for cloud link {link.get('id')}")
                return None

            network = device.get("network", {})

            source = DeviceContext(
                device_id=device_id,
                mac_address=network.get("macAddress", "00:00:00:00:00:01"),
                ip_address=network.get("ipAddress", "10.0.0.1"),
                port=0,
            )

            # Backend sends nested cloud_service object; fall back to flat keys for compat
            cloud_svc = link.get("cloud_service", {})

            destination = DeviceContext(
                device_id=f"cloud-{link.get('id', 'unknown')}",
                mac_address="ff:ff:ff:ff:ff:ff",
                ip_address=cloud_svc.get("primary_ip", link.get("cloud_ip", "0.0.0.0")),
                port=cloud_svc.get("port", link.get("port", 443)),
            )

            interval_ms = link.get("heartbeat_interval_ms", link.get("interval_ms", 30000))

            return FlowContext(
                flow_id=f"cloud-{link.get('id', device_id)}",
                source=source,
                destination=destination,
                protocol=ProtocolType.CLOUD_SERVICE,
                config={
                    "hostname": cloud_svc.get("hostname", link.get("hostname", "")),
                    "tls_enabled": cloud_svc.get("tls_enabled", link.get("tls_enabled", True)),
                },
                timing_model={
                    "poll_interval_ms": interval_ms,
                },
            )

        except Exception as e:
            logger.error(f"Error creating cloud flow: {e}")
            return None

    def apply_directives(self, scenario_id: str, directives: list[dict]) -> bool:
        """Apply adaptive traffic directives to a running scenario.

        Thread-safe: sets pending directives on the controller via atomic swap.

        Args:
            scenario_id: Target scenario
            directives: List of directive dicts from ADAPT_TRAFFIC message

        Returns:
            True if directives were accepted
        """
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if not ctx or not ctx.adaptive_controller:
                return False
            ctx.adaptive_controller.set_pending_directives(directives)
            logger.info(f"Applied {len(directives)} directives to scenario {scenario_id}")
            return True

    def get_adaptation_state(self, scenario_id: str) -> dict | None:
        """Get adaptive controller state for a scenario.

        Args:
            scenario_id: Target scenario

        Returns:
            Adaptation state dict or None
        """
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if ctx and ctx.adaptive_controller:
                return ctx.adaptive_controller.get_state_snapshot()
            return None

    def send_attack_command(self, scenario_id: str, command: dict) -> bool:
        """Send a runtime command to the attack orchestrator.

        Thread-safe: uses atomic command swap on the orchestrator.

        Args:
            scenario_id: Target scenario
            command: Command dict (type: start|stop|advance_stage|pause)

        Returns:
            True if command was accepted
        """
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if not ctx or not ctx.attack_orchestrator:
                return False
            ctx.attack_orchestrator.set_pending_command(command)
            logger.info(f"Sent attack command '{command.get('type')}' to scenario {scenario_id}")
            return True

    def get_attack_state(self, scenario_id: str) -> dict | None:
        """Get attack orchestrator state for a scenario.

        Args:
            scenario_id: Target scenario

        Returns:
            Attack state dict or None
        """
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if ctx and ctx.attack_orchestrator:
                return ctx.attack_orchestrator.get_state_snapshot()
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
