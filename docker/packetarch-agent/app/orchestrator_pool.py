# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
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
    # Multi-sensor topology (single-conductor): when set, the agent injects each
    # canonical frame's per-segment reframed copies onto the veth serving each
    # SPAN (from span_interface_map) via LiveTopologyOutput, instead of a single
    # LiveOutput on `interface`. Cross-zone flows are ROUTED, never isolation-dropped.
    topology_plan: dict[str, Any] | None = None
    span_interface_map: dict[str, str] | None = None
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
        topology_plan: dict[str, Any] | None = None,
        span_interface_map: dict[str, str] | None = None,
    ) -> bool:
        """Start a new scenario.

        Args:
            scenario_id: Unique scenario identifier
            definition: Scenario definition dict with devices and flows
            interface: Network interface for packet injection
            topology_plan: Optional multi-sensor topology plan. When set, this
                agent acts as the single conductor — injecting each frame's
                per-segment copies onto every SPAN's veth.
            span_interface_map: span_id -> veth for topology injection.

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
                topology_plan=topology_plan,
                span_interface_map=span_interface_map,
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

    def stop_attack(self, scenario_id: str) -> bool:
        """Stop the attack orchestrator for a scenario.

        Args:
            scenario_id: Scenario to stop attack for

        Returns:
            True if attack was stopped, False if none was running
        """
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if not ctx:
                return False
            self._sync_attack_orchestrator(ctx)
            if ctx.attack_orchestrator:
                # Send stop command to attack orchestrator
                try:
                    ctx.attack_orchestrator.set_pending_command({"type": "stop"})
                    logger.info(f"Stopped attack orchestrator for scenario {scenario_id}")
                except Exception as e:
                    logger.warning(f"Error stopping attack orchestrator: {e}")
                ctx.attack_orchestrator = None
                return True
            return False

    def stop(self, scenario_id: str) -> bool:
        """Stop a running scenario and its attack if present.

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

        # Stop attack orchestrator first (outside lock to avoid deadlock)
        self.stop_attack(scenario_id)

        # Then stop the scenario
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
            from app.protocol_engines.cell_isolation import (
                parse_config as parse_isolation_config,
                should_drop_flow as should_drop_for_isolation,
            )

            # Parse the definition
            devices = ctx.definition.get("devices", {})
            flows = ctx.definition.get("flows", {})
            zones = ctx.definition.get("zones", {})
            conduits = ctx.definition.get("conduits", {})
            isolation = parse_isolation_config(ctx.definition)
            # Topology (single-conductor) mode: cross-zone flows are the whole
            # point — force cell isolation OFF so they are routed per the plan,
            # never dropped.
            topology_mode = ctx.topology_plan is not None
            if topology_mode:
                isolation = {"mode": "off"}

            # Handle both dict and list formats
            if isinstance(devices, list):
                devices = {d.get("id", str(i)): d for i, d in enumerate(devices)}
            if isinstance(flows, list):
                flows = {f.get("id", str(i)): f for i, f in enumerate(flows)}

            if not flows:
                raise ValueError("No flows defined in scenario")

            # Create the output. In topology mode, the single conductor injects
            # each canonical frame's per-segment reframed copies onto every
            # SPAN's veth (LiveTopologyOutput); otherwise a single LiveOutput.
            if topology_mode:
                from app.protocol_engines.output import LiveTopologyOutput

                output = LiveTopologyOutput(
                    ctx.topology_plan, ctx.span_interface_map or {}
                )
                logger.info(
                    "Topology conductor: injecting across %d SPANs %s",
                    len(ctx.span_interface_map or {}),
                    list((ctx.span_interface_map or {}).values()),
                )
            else:
                output = LiveOutput(interface=ctx.interface)
            ctx.output = output
            orchestrator = UnifiedOrchestrator(output=output, duration_ms=None)
            ctx.orchestrator = orchestrator

            # Add OT protocol flows
            vertical = ctx.definition.get("vertical")
            flow_count = 0
            isolation_dropped = 0
            for flow_id, flow_def in flows.items():
                drop, reason = should_drop_for_isolation(
                    flow_def, devices, zones, conduits, isolation,
                )
                if drop:
                    isolation_dropped += 1
                    logger.info(
                        f"[cell-isolation] flow {flow_id} dropped: {reason}"
                    )
                    continue

                flow_ctx = self._create_flow_context(
                    flow_def,
                    devices,
                    vertical=vertical,
                    scenario_id=ctx.scenario_id,
                    clean_demo_mode=bool(
                        ctx.definition.get("clean_demo_mode", False)
                    ),
                )
                if flow_ctx:
                    orchestrator.add_flow(flow_ctx)
                    flow_count += 1

            if isolation_dropped:
                logger.info(
                    f"[cell-isolation] mode={isolation['mode']}: dropped "
                    f"{isolation_dropped} cross-cell flow(s) for scenario "
                    f"{ctx.scenario_id}"
                )

            # Cloud-service links use a SEPARATE wall-clock heartbeat
            # thread instead of the orchestrator's virtual-time heap. The
            # orchestrator's heap is flooded by PROFINET-cyclic and other
            # high-frequency OT events (3 PN flows × 125 pps × 25 s window
            # = ~9000 packets at vtime 5-15 s). Real injection throughput on
            # the agent's lo / ens3 interface is ~60 pps, so virtual time
            # falls 10× behind wall clock — a heartbeat scheduled at vtime
            # 36 s wouldn't fire until ~9 minutes of wall time elapsed,
            # which is the bug the user observed ("EWON has no external
            # comms": 4 cloud_service packets in 22 minutes). Heartbeats
            # are infrastructure keep-alives, not OT poll cycles — they
            # belong on a wall-clock cadence regardless of how busy the
            # OT event heap is.
            cloud_links = ctx.definition.get("cloud_service_links", [])
            cloud_heartbeat_specs: list[dict[str, Any]] = []
            for link in cloud_links:
                if not link.get("enabled", True):
                    continue
                spec = self._build_cloud_heartbeat_spec(link, devices)
                if spec:
                    cloud_heartbeat_specs.append(spec)

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

            # Initialize ambient noise generator (ARP, NTP, LLDP, STP, etc.).
            # Skipped entirely when the scenario toggle disables
            # broadcast/multicast traffic.
            broadcast_enabled = bool(
                ctx.definition.get("broadcast_traffic_enabled", True)
            )
            if not broadcast_enabled:
                logger.info(
                    "Broadcast/multicast traffic disabled by scenario toggle — "
                    "skipping ambient noise generator"
                )
            else:
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
                    zone_level_map: dict[str, int | None] = {}
                    for z in zones_list:
                        zid = z.get("id", "")
                        network_info = z.get("network", z)
                        zone_vlan_map[zid] = network_info.get("vlanId") or network_info.get("vlan")
                        # Floor-int the Purdue level (handles 3.5 DMZ → 3).
                        raw_lvl = z.get("level")
                        try:
                            zone_level_map[zid] = (
                                int(float(raw_lvl)) if raw_lvl is not None else None
                            )
                        except (TypeError, ValueError):
                            zone_level_map[zid] = None

                    def _collect_device_protocols(
                        dev_id: str,
                        all_flows: dict[str, Any],
                        device_def: dict[str, Any] | None = None,
                    ) -> list[str]:
                        protos: list[str] = []
                        for fdef in all_flows.values():
                            if fdef.get("sourceDeviceId") == dev_id or fdef.get("targetDeviceId") == dev_id:
                                p = fdef.get("protocol", "")
                                if p and p not in protos:
                                    protos.append(p)
                        # Merge protocols from the device definition so that
                        # ambient discovery covers all device capabilities,
                        # not only protocols present in flow definitions.
                        if device_def:
                            for p in device_def.get("protocols", []):
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
                                    # Match cell_isolation._zone_of priority:
                                    # zoneId (camelCase from frontend) takes
                                    # precedence over the snake-case alias.
                                    dev_zone = (
                                        dev.get("zoneId")
                                        or dev.get("zone_id")
                                        or dev.get("zone")
                                        or ""
                                    )
                                    seen_devices[dev_id] = AmbientDevice(
                                        device_id=dev_id,
                                        mac_address=mac,
                                        ip_address=ip,
                                        gateway_ip=ip.rsplit(".", 1)[0] + ".1",
                                        protocols=_collect_device_protocols(dev_id, flows, dev),
                                        device_type=dev.get("type", fp.get("device_type", "")),
                                        vendor=fp.get("vendor", ""),
                                        device_name=dev.get("name", dev_id),
                                        zone_id=dev_zone if dev_zone else None,
                                        vlan_id=zone_vlan_map.get(dev_zone),
                                        purdue_level=zone_level_map.get(dev_zone),
                                        vendor_fingerprint=fp,
                                        scenario_id=ctx.scenario_id,
                                    )
                    if seen_devices:
                        ambient = BackgroundNoiseGenerator(
                            list(seen_devices.values()),
                            cell_isolation_mode=isolation.get("mode", "off"),
                            cell_levels=frozenset(isolation.get("cell_levels", {0, 1, 2})),
                            clean_demo_mode=bool(
                                ctx.definition.get("clean_demo_mode", False)
                            ),
                        )
                        orchestrator.register_ambient_generator(ambient)
                        logger.info(
                            "Ambient noise enabled for %d devices "
                            "(cell_isolation=%s)",
                            len(seen_devices),
                            isolation.get("mode", "off"),
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

            # Start cloud-heartbeat thread BEFORE entering the orchestrator
            # run loop. The thread runs alongside orchestrator.run() and
            # uses wall-clock cadence, immune to virtual-time starvation
            # from PROFINET-cyclic and other high-frequency OT events.
            cloud_hb_thread: threading.Thread | None = None
            if cloud_heartbeat_specs:
                cloud_hb_thread = threading.Thread(
                    target=self._run_cloud_heartbeats,
                    args=(ctx, cloud_heartbeat_specs, ctx.interface),
                    name=f"cloud-hb-{ctx.scenario_id[:8]}",
                    daemon=True,
                )
                cloud_hb_thread.start()
                logger.info(
                    f"Cloud heartbeat thread started for {len(cloud_heartbeat_specs)} "
                    f"link(s) (wall-clock cadence)"
                )

            logger.info(f"Scenario {ctx.scenario_id} running with {flow_count} flows")

            # Run orchestration (blocks until stop_event is set)
            result = orchestrator.run(stop_event=ctx.stop_event)

            # Heartbeat thread is a daemon and watches the same stop_event,
            # so it exits as soon as orchestrator.run() returns. Join briefly
            # so stats are flushed before we report final packet counts.
            if cloud_hb_thread is not None:
                cloud_hb_thread.join(timeout=2.0)

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

        finally:
            # Cleanup attack orchestrator on exit (normal/error/crash)
            if ctx.attack_orchestrator:
                try:
                    ctx.attack_orchestrator.set_pending_command({"type": "stop"})
                    ctx.attack_orchestrator = None
                    logger.info(f"Cleaned up attack orchestrator for {ctx.scenario_id}")
                except Exception as e:
                    logger.error(f"Error stopping attack orchestrator in finally: {e}")

    def _create_flow_context(
        self,
        flow_def: dict[str, Any],
        devices: dict[str, dict[str, Any]],
        vertical: str | None = None,
        scenario_id: str | None = None,
        clean_demo_mode: bool = False,
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
                from app.protocol_engines.cloud_service.packets import (
                    gateway_mac_for_subnet,
                )

                external_ip = flow_config.get("externalIp", "0.0.0.0")
                external_port = flow_config.get("externalPort", 443)

                # Off-segment endpoint — every packet to/from it actually
                # transits the local gateway at L2 (see
                # gateway_mac_for_subnet docstring), not an all-zero MAC.
                destination = DeviceContext(
                    device_id="external_cloud",
                    mac_address=gateway_mac_for_subnet(
                        src_network.get("ipAddress", "10.0.0.1")
                    ),
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
            if clean_demo_mode:
                merged_config["clean_demo_mode"] = True

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

    def _build_cloud_heartbeat_spec(
        self,
        link: dict[str, Any],
        devices: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Build a wall-clock heartbeat spec for one cloud_service_link.

        Returns a dict consumed by the heartbeat thread, NOT a FlowContext —
        cloud heartbeats deliberately bypass the orchestrator's virtual-time
        heap (see _run_scenario for rationale).
        """
        from app.protocol_engines.cloud_service.packets import gateway_mac_for_subnet

        device_id = link.get("device_id")
        device = devices.get(device_id)
        if not device:
            logger.warning(
                f"Device {device_id} not found for cloud link {link.get('id')}"
            )
            return None

        network = device.get("network", {})
        cloud_svc = link.get("cloud_service", {})
        interval_ms = int(
            link.get("heartbeat_interval_ms", link.get("interval_ms", 30000))
        )
        # Clamp to sane bounds. <1 s would spam, >5 min wouldn't look like a
        # heartbeat to most cloud-relay services.
        interval_ms = max(1000, min(interval_ms, 300_000))

        # Pick a TLS ClientHello shape that matches the source device's
        # vendor. The minimalist 4-cipher default looks like an embedded
        # cellular gateway and matches Cyber Vision's JA3 → "Canon
        # printer" iconography rule, which surprises operators when a
        # jump_server / bastion shows up as a printer. Map common
        # remote-access device classes to richer ClientHellos so CV
        # renders the right icon.
        vendor = (device.get("vendor") or "").lower()
        fp = (
            device.get("vendorFingerprint")
            or device.get("vendor_fingerprint")
            or {}
        )
        vendor_family = (fp.get("vendor_family") or "").lower()
        device_type = (device.get("type") or "").lower()
        tls_profile = "embedded_minimal"
        if (
            vendor == "microsoft"
            or "windows" in vendor_family
            or device_type in {"jump_server", "bastion", "rdp_gateway"}
        ):
            tls_profile = "windows_schannel_2016"

        src_ip = network.get("ipAddress", "10.0.0.1")

        return {
            "flow_id": f"cloud-{link.get('id', device_id)}",
            "device_id": device_id,
            "src_mac": network.get("macAddress", "00:00:00:00:00:01"),
            "src_ip": src_ip,
            # Cloud endpoint is off-segment; every packet to/from it
            # actually transits the local gateway at L2 (see
            # gateway_mac_for_subnet docstring — NOT a broadcast marker,
            # a unicast IP conversation addressed to ff:ff:ff:ff:ff:ff is
            # itself a strong "this traffic is fake" signal to CV's DPI).
            "dst_mac": gateway_mac_for_subnet(src_ip),
            "dst_ip": cloud_svc.get(
                "primary_ip", link.get("cloud_ip", "0.0.0.0"),
            ),
            "dst_port": int(cloud_svc.get("port", link.get("port", 443))),
            "hostname": cloud_svc.get("hostname", link.get("hostname", "")),
            "tls_enabled": bool(
                cloud_svc.get("tls_enabled", link.get("tls_enabled", True))
            ),
            "tls_profile": tls_profile,
            "interval_ms": interval_ms,
        }

    def _run_cloud_heartbeats(
        self,
        ctx: "ScenarioContext",
        specs: list[dict[str, Any]],
        interface: str,
    ) -> None:
        """Wall-clock heartbeat loop for cloud_service flows.

        Runs in its own daemon thread per scenario. Each spec fires its
        TCP-SYN + TLS-ClientHello pair every `interval_ms` of WALL clock,
        completely independent of the orchestrator's event heap. This is
        the same model the original `cloud_traffic_scheduler.py` shipped
        with before the unified-orchestrator refactor.

        Stats are reported back to the orchestrator's `stats` accumulator
        under protocol="cloud_service" so the dashboard breakdown stays
        accurate.
        """
        from app.protocol_engines.cloud_service.engine import CloudServiceEngine
        from app.protocol_engines.types import (
            CloudServiceConversationState,
            DeviceContext,
            FlowContext,
            ProtocolType,
        )
        from scapy.packet import Raw
        from scapy.sendrecv import sendp

        engine = CloudServiceEngine()
        # Stagger first heartbeats over the first 30 s so all flows don't
        # fire simultaneously — a real eWON fleet doesn't synchronise.
        deadlines: list[tuple[float, dict[str, Any], CloudServiceConversationState, FlowContext]] = []
        now = time.monotonic()
        for i, spec in enumerate(specs):
            src = DeviceContext(
                device_id=spec["device_id"],
                mac_address=spec["src_mac"],
                ip_address=spec["src_ip"],
                port=0,
            )
            dst = DeviceContext(
                device_id=spec["flow_id"],
                mac_address=spec["dst_mac"],
                ip_address=spec["dst_ip"],
                port=spec["dst_port"],
            )
            flow = FlowContext(
                flow_id=spec["flow_id"],
                source=src,
                destination=dst,
                protocol=ProtocolType.CLOUD_SERVICE,
                config={
                    "hostname": spec["hostname"],
                    "tls_enabled": spec["tls_enabled"],
                    "tls_profile": spec.get("tls_profile", "embedded_minimal"),
                },
                timing_model={"poll_interval_ms": spec["interval_ms"]},
            )
            state = engine.create_initial_state(flow)
            first_fire = now + (1.0 + i * 1.5)  # 1 s, 2.5 s, 4 s, …
            deadlines.append((first_fire, spec, state, flow))
            logger.info(
                "cloud-heartbeat scheduled: flow=%s -> %s:%d interval=%dms",
                spec["flow_id"], spec["dst_ip"], spec["dst_port"],
                spec["interval_ms"],
            )

        while not ctx.stop_event.is_set():
            now = time.monotonic()
            # Find the next-due heartbeat
            next_idx = min(range(len(deadlines)), key=lambda i: deadlines[i][0])
            fire_at, spec, state, flow = deadlines[next_idx]

            sleep_for = fire_at - now
            if sleep_for > 0.0:
                # Wake periodically so stop_event is responsive
                if ctx.stop_event.wait(timeout=min(sleep_for, 1.0)):
                    return
                continue

            # Fire the heartbeat: generate_poll_cycle yields 1-2 packets
            try:
                pkts = list(engine.generate_poll_cycle(flow, state, cycle_time_ms=0.0))
                for pkt in pkts:
                    try:
                        sendp(
                            Raw(pkt.packet_bytes),
                            iface=interface,
                            verbose=False,
                        )
                        if ctx.orchestrator is not None:
                            ctx.orchestrator.stats.record_packet(
                                "cloud_service", len(pkt.packet_bytes),
                            )
                    except Exception as e:
                        logger.warning(
                            "cloud-heartbeat sendp failed flow=%s: %s",
                            spec["flow_id"], e,
                        )
            except Exception as e:
                logger.error(
                    "cloud-heartbeat generate failed flow=%s: %s",
                    spec["flow_id"], e,
                )

            # Re-arm for next interval
            deadlines[next_idx] = (
                fire_at + spec["interval_ms"] / 1000.0,
                spec, state, flow,
            )

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

    def _sync_attack_orchestrator(self, ctx: ScenarioContext) -> None:
        """Lazily sync ctx.attack_orchestrator from the UnifiedOrchestrator.

        After a hot-attach injection, the scenario thread creates the
        AttackOrchestrator and stores it on the UnifiedOrchestrator.
        This helper pulls the reference into ScenarioContext so that
        send_attack_command() and get_attack_state() work.
        """
        if ctx.attack_orchestrator is None and ctx.orchestrator is not None:
            orch_ref = getattr(ctx.orchestrator, "_attack_orchestrator", None)
            if orch_ref is not None:
                ctx.attack_orchestrator = orch_ref

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
            if not ctx:
                return False
            self._sync_attack_orchestrator(ctx)
            if not ctx.attack_orchestrator:
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
            if not ctx:
                return None
            self._sync_attack_orchestrator(ctx)
            if ctx.attack_orchestrator:
                return ctx.attack_orchestrator.get_state_snapshot()
            return None

    def inject_attack(self, scenario_id: str, attack_config: dict) -> bool:
        """Hot-attach an attack playbook to a running scenario.

        Thread-safe: sets a pending injection on the UnifiedOrchestrator
        via atomic swap.  The scenario thread picks it up on the next
        event-loop iteration and creates the AttackOrchestrator.

        Args:
            scenario_id: Target scenario
            attack_config: Dict with ``playbook_id`` and ``config``

        Returns:
            True if injection was queued
        """
        with self._lock:
            ctx = self._scenarios.get(scenario_id)
            if not ctx:
                logger.warning(f"inject_attack: scenario {scenario_id} not found")
                return False
            self._sync_attack_orchestrator(ctx)
            if ctx.attack_orchestrator is not None:
                logger.warning(
                    f"inject_attack: scenario {scenario_id} already has "
                    f"an attack orchestrator"
                )
                return False
            if not ctx.orchestrator:
                logger.warning(
                    f"inject_attack: scenario {scenario_id} has no orchestrator"
                )
                return False

            # Collect device list from the scenario definition
            devices = ctx.definition.get("devices", {})
            device_list = (
                list(devices.values()) if isinstance(devices, dict) else list(devices)
            )
            attack_config["devices"] = device_list

            # Atomic swap — scenario thread picks this up
            ctx.orchestrator.set_pending_attack_injection(attack_config)
            logger.info(
                f"Attack injection queued for scenario {scenario_id} "
                f"(playbook={attack_config.get('playbook_id')})"
            )
            return True

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
