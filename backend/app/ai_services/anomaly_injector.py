"""Anomaly injection service for realistic traffic anomalies.

This module provides the AnomalyInjector which manages anomaly injection
campaigns during traffic generation, supporting:
- Random anomaly injection based on probability
- Scheduled anomaly campaigns
- Triggered anomalies based on conditions
- Multi-flow coordinated anomalies
- External communication traffic (C2, exfil, exploits)
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Iterator

import numpy as np

from app.protocol_engines.types import FlowContext, PacketEvent
from app.protocol_engines.external.engine import (
    ExternalCommEngine,
    ExternalTrafficConfig,
    PacketEvent as ExternalPacketEvent,
)
from app.protocol_engines.external.ip_pools import (
    ExternalIPRegistry,
    get_c2_server_ip,
    get_exfil_destination_ip,
    get_attack_source_ip,
)
from app.protocol_engines.external.c2_patterns import list_beacon_patterns
from app.protocol_engines.external.exploit_patterns import list_exploit_patterns

logger = logging.getLogger(__name__)


@dataclass
class AnomalyEvent:
    """An anomaly event to be injected."""

    anomaly_id: str
    anomaly_type: str
    category: str
    severity: str
    parameters: dict[str, Any]
    target_flow_id: str | None = None
    start_time_ms: float = 0
    duration_cycles: int = 1
    remaining_cycles: int = 1


@dataclass
class AnomalyCampaign:
    """A coordinated anomaly campaign affecting multiple flows."""

    campaign_id: str
    name: str
    anomaly_events: list[AnomalyEvent] = field(default_factory=list)
    start_time_ms: float = 0
    end_time_ms: float | None = None
    is_active: bool = True


@dataclass
class ExternalAnomalyEvent:
    """An external communication anomaly event (C2, exfil, exploit)."""

    event_id: str
    event_type: str  # "c2_beacon", "dns_tunnel", "http_exfil", "exploit", "port_scan"
    category: str  # "external_communication"

    # Source/target configuration
    internal_device_ip: str
    external_ip: str | None = None  # Auto-generated if None

    # Timing
    start_time_ms: float = 0
    duration_ms: float = 300000  # 5 minutes default

    # Type-specific configuration
    c2_pattern: str | None = None  # For C2 beaconing
    c2_protocol: str = "http"  # "http", "https", "dns"
    beacon_count: int = 10

    exfil_protocol: str = "http"  # "http", "dns"
    exfil_data_size: int = 1024

    exploit_pattern: str | None = None  # For exploit attempts

    scan_type: str = "syn"  # For port scans
    scan_ot_ports: bool = True

    # IDS triggering
    use_realistic_ips: bool = False

    # Metadata
    mitre_technique: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExternalCampaign:
    """A coordinated external communication campaign."""

    campaign_id: str
    name: str
    scenario_id: str
    events: list[ExternalAnomalyEvent] = field(default_factory=list)
    start_time_ms: float = 0
    duration_ms: float = 300000
    is_active: bool = True
    use_realistic_ips: bool = False


class AnomalyInjector:
    """Service for injecting anomalies into traffic generation.

    The AnomalyInjector manages:
    - Loading anomaly templates from database
    - Random injection based on probability
    - Scheduled campaigns
    - Flow-specific anomaly state
    """

    def __init__(self, seed: int | None = None, scenario_id: str | None = None):
        """Initialize the anomaly injector.

        Args:
            seed: Optional random seed for reproducibility
            scenario_id: Optional scenario ID for IP registry
        """
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)
        self._scenario_id = scenario_id or "default"

        # Loaded templates
        self._templates: list[dict[str, Any]] = []

        # Active anomalies by flow
        self._active_anomalies: dict[str, list[AnomalyEvent]] = {}

        # Campaign tracking
        self._campaigns: list[AnomalyCampaign] = []

        # External communication tracking
        self._external_campaigns: list[ExternalCampaign] = []
        self._external_engine: ExternalCommEngine | None = None
        self._ip_registry: ExternalIPRegistry | None = None

        # Statistics
        self._injection_count = 0
        self._injection_by_type: dict[str, int] = {}
        self._external_packet_count = 0

    async def load_templates(self, db_session: Any) -> int:
        """Load anomaly templates from the database.

        Args:
            db_session: Database session

        Returns:
            Number of templates loaded
        """
        from sqlalchemy import select
        from app.models.anomaly_template import AnomalyTemplate

        result = await db_session.execute(
            select(AnomalyTemplate).where(AnomalyTemplate.is_active == True)
        )
        templates = result.scalars().all()

        self._templates = [t.to_injection_config() for t in templates]
        self._templates.extend([
            {
                "name": t.name,
                "description": t.description,
                "target_protocols": t.target_protocols,
                "target_device_types": t.target_device_types,
                **t.to_injection_config(),
            }
            for t in templates
        ])

        # Reset to avoid duplicates
        self._templates = []
        for t in templates:
            config = t.to_injection_config()
            config["name"] = t.name
            config["target_protocols"] = t.target_protocols
            config["target_device_types"] = t.target_device_types
            self._templates.append(config)

        logger.info(f"Loaded {len(self._templates)} anomaly templates")
        return len(self._templates)

    def add_template(self, template: dict[str, Any]) -> None:
        """Add an anomaly template manually.

        Args:
            template: Template configuration dictionary
        """
        self._templates.append(template)

    def should_inject(
        self,
        flow: FlowContext,
        current_time_ms: float,
    ) -> AnomalyEvent | None:
        """Check if an anomaly should be injected for a flow.

        Args:
            flow: Flow context
            current_time_ms: Current simulation time

        Returns:
            AnomalyEvent if injection should occur, None otherwise
        """
        # Check active anomalies first
        flow_anomalies = self._active_anomalies.get(flow.flow_id, [])
        for anomaly in flow_anomalies:
            if anomaly.remaining_cycles > 0:
                anomaly.remaining_cycles -= 1
                return anomaly

        # Clean up expired anomalies
        self._active_anomalies[flow.flow_id] = [
            a for a in flow_anomalies if a.remaining_cycles > 0
        ]

        # Check scheduled campaigns
        for campaign in self._campaigns:
            if not campaign.is_active:
                continue
            if campaign.start_time_ms <= current_time_ms:
                if campaign.end_time_ms is None or current_time_ms <= campaign.end_time_ms:
                    for event in campaign.anomaly_events:
                        if event.target_flow_id is None or event.target_flow_id == flow.flow_id:
                            if event.remaining_cycles > 0:
                                return event

        # Check random injection
        eligible_templates = self._get_eligible_templates(flow)
        for template in eligible_templates:
            if template.get("mode") == "random":
                prob = template.get("probability", 0.01)
                if self._random.random() < prob:
                    return self._create_anomaly_event(template, flow.flow_id)

        return None

    def _get_eligible_templates(self, flow: FlowContext) -> list[dict[str, Any]]:
        """Get templates eligible for a flow based on protocol and device type.

        Args:
            flow: Flow context

        Returns:
            List of eligible templates
        """
        eligible = []
        protocol = flow.protocol.value

        for template in self._templates:
            # Check protocol filter
            target_protocols = template.get("target_protocols")
            if target_protocols and protocol not in target_protocols:
                continue

            # Check device type filter
            target_types = template.get("target_device_types")
            if target_types:
                # Would need device type info from flow
                pass

            eligible.append(template)

        return eligible

    def _create_anomaly_event(
        self,
        template: dict[str, Any],
        flow_id: str,
    ) -> AnomalyEvent:
        """Create an anomaly event from a template.

        Args:
            template: Template configuration
            flow_id: Target flow ID

        Returns:
            AnomalyEvent instance
        """
        import uuid

        duration = template.get("duration_cycles", 1)

        event = AnomalyEvent(
            anomaly_id=str(uuid.uuid4()),
            anomaly_type=template.get("type", "unknown"),
            category=template.get("category", "unknown"),
            severity=template.get("severity", "medium"),
            parameters=template.get("parameters", {}),
            target_flow_id=flow_id,
            duration_cycles=duration,
            remaining_cycles=duration,
        )

        # Track active anomaly
        if flow_id not in self._active_anomalies:
            self._active_anomalies[flow_id] = []
        self._active_anomalies[flow_id].append(event)

        # Update statistics
        self._injection_count += 1
        anomaly_type = event.anomaly_type
        self._injection_by_type[anomaly_type] = self._injection_by_type.get(anomaly_type, 0) + 1

        logger.debug(f"Injecting anomaly {anomaly_type} into flow {flow_id}")
        return event

    def create_campaign(
        self,
        name: str,
        anomaly_types: list[str],
        start_time_ms: float,
        duration_ms: float | None = None,
        target_flows: list[str] | None = None,
    ) -> AnomalyCampaign:
        """Create a coordinated anomaly campaign.

        Args:
            name: Campaign name
            anomaly_types: Types of anomalies to include
            start_time_ms: Campaign start time
            duration_ms: Campaign duration (None for indefinite)
            target_flows: Specific flows to target (None for all)

        Returns:
            Created campaign
        """
        import uuid

        campaign = AnomalyCampaign(
            campaign_id=str(uuid.uuid4()),
            name=name,
            start_time_ms=start_time_ms,
            end_time_ms=start_time_ms + duration_ms if duration_ms else None,
        )

        # Create events for each anomaly type
        for anomaly_type in anomaly_types:
            # Find matching template
            template = next(
                (t for t in self._templates if t.get("type") == anomaly_type),
                None,
            )
            if template:
                for flow_id in (target_flows or [None]):
                    event = AnomalyEvent(
                        anomaly_id=str(uuid.uuid4()),
                        anomaly_type=anomaly_type,
                        category=template.get("category", "unknown"),
                        severity=template.get("severity", "medium"),
                        parameters=template.get("parameters", {}),
                        target_flow_id=flow_id,
                        start_time_ms=start_time_ms,
                        duration_cycles=template.get("duration_cycles", 10),
                        remaining_cycles=template.get("duration_cycles", 10),
                    )
                    campaign.anomaly_events.append(event)

        self._campaigns.append(campaign)
        logger.info(f"Created campaign '{name}' with {len(campaign.anomaly_events)} events")
        return campaign

    def apply_anomaly(
        self,
        event: AnomalyEvent,
        packet_events: list[PacketEvent],
        flow: FlowContext,
    ) -> list[PacketEvent]:
        """Apply an anomaly to a list of packet events.

        Args:
            event: Anomaly event to apply
            packet_events: Original packet events
            flow: Flow context

        Returns:
            Modified packet events
        """
        anomaly_type = event.anomaly_type
        params = event.parameters

        if anomaly_type == "timeout":
            # Drop response packets
            return [p for p in packet_events if p.direction != "response"]

        elif anomaly_type == "delayed":
            # Increase response delays
            delay_factor = params.get("delay_factor", 10.0)
            jitter_ms = params.get("jitter_ms", 0)

            modified = []
            for p in packet_events:
                if p.direction == "response":
                    extra_delay = (delay_factor - 1) * 10  # Assume 10ms base
                    extra_delay += self._rng.uniform(-jitter_ms, jitter_ms)
                    modified.append(PacketEvent(
                        timestamp_ms=p.timestamp_ms + extra_delay,
                        flow_id=p.flow_id,
                        packet_bytes=p.packet_bytes,
                        direction=p.direction,
                        metadata={**p.metadata, "anomaly": "delayed"},
                    ))
                else:
                    modified.append(p)
            return modified

        elif anomaly_type == "duplicate":
            # Duplicate response packets
            duplicate_count = params.get("duplicate_count", 2)
            interval_ms = params.get("interval_ms", 10)

            modified = []
            for p in packet_events:
                modified.append(p)
                if p.direction == "response":
                    for i in range(duplicate_count - 1):
                        modified.append(PacketEvent(
                            timestamp_ms=p.timestamp_ms + interval_ms * (i + 1),
                            flow_id=p.flow_id,
                            packet_bytes=p.packet_bytes,
                            direction=p.direction,
                            metadata={**p.metadata, "anomaly": "duplicate"},
                        ))
            return modified

        elif anomaly_type == "drop":
            # Drop packets based on probability
            drop_prob = params.get("drop_probability", 0.5)
            return [p for p in packet_events if self._random.random() > drop_prob]

        elif anomaly_type == "jitter_spike":
            # Add extra jitter to all packets
            jitter_mult = params.get("jitter_multiplier", 5.0)

            modified = []
            for p in packet_events:
                jitter = self._rng.exponential(10) * jitter_mult
                modified.append(PacketEvent(
                    timestamp_ms=p.timestamp_ms + jitter,
                    flow_id=p.flow_id,
                    packet_bytes=p.packet_bytes,
                    direction=p.direction,
                    metadata={**p.metadata, "anomaly": "jitter_spike"},
                ))
            return modified

        # Default: return unmodified
        return packet_events

    def get_statistics(self) -> dict[str, Any]:
        """Get injection statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_injections": self._injection_count,
            "by_type": self._injection_by_type,
            "active_campaigns": len([c for c in self._campaigns if c.is_active]),
            "templates_loaded": len(self._templates),
            "external": self.get_external_statistics(),
        }

    def reset(self) -> None:
        """Reset the injector state."""
        self._active_anomalies.clear()
        self._campaigns.clear()
        self._external_campaigns.clear()
        self._injection_count = 0
        self._injection_by_type.clear()
        self._external_packet_count = 0
        self._external_engine = None
        self._ip_registry = None

    # ==================== External Communication Methods ====================

    def configure_external_engine(
        self,
        use_realistic_ips: bool = False,
        c2_pattern: str = "jittered_1m",
        c2_protocol: str = "http",
        enable_exfil: bool = False,
        enable_exploits: bool = False,
        enable_recon: bool = False,
    ) -> None:
        """Configure the external communications engine.

        Args:
            use_realistic_ips: Use historical malicious IPs vs TEST-NET
            c2_pattern: Default C2 beaconing pattern
            c2_protocol: C2 protocol (http, https, dns)
            enable_exfil: Enable data exfiltration
            enable_exploits: Enable exploit attempts
            enable_recon: Enable reconnaissance (port scans)
        """
        config = ExternalTrafficConfig(
            use_realistic_ips=use_realistic_ips,
            scenario_id=self._scenario_id,
            c2_pattern=c2_pattern,
            c2_protocol=c2_protocol,
            enable_exfil=enable_exfil,
            enable_exploits=enable_exploits,
            enable_recon=enable_recon,
        )

        self._external_engine = ExternalCommEngine(config)
        self._ip_registry = ExternalIPRegistry(self._scenario_id)

        logger.info(
            f"Configured external engine: realistic_ips={use_realistic_ips}, "
            f"pattern={c2_pattern}, protocol={c2_protocol}"
        )

    def create_external_campaign(
        self,
        name: str,
        internal_devices: list[str],
        event_types: list[str],
        start_time_ms: float = 0,
        duration_ms: float = 300000,
        use_realistic_ips: bool = False,
        **kwargs,
    ) -> ExternalCampaign:
        """Create an external communication campaign.

        Args:
            name: Campaign name
            internal_devices: List of internal device IPs to compromise
            event_types: Types of events ("c2_beacon", "dns_tunnel", "http_exfil", "exploit", "port_scan")
            start_time_ms: Campaign start time
            duration_ms: Campaign duration
            use_realistic_ips: Use historical malicious IPs
            **kwargs: Additional event configuration

        Returns:
            Created campaign
        """
        import uuid

        campaign = ExternalCampaign(
            campaign_id=str(uuid.uuid4()),
            name=name,
            scenario_id=self._scenario_id,
            start_time_ms=start_time_ms,
            duration_ms=duration_ms,
            use_realistic_ips=use_realistic_ips,
        )

        # Create events for each type
        for event_type in event_types:
            for device_ip in internal_devices:
                event = self._create_external_event(
                    event_type=event_type,
                    internal_device_ip=device_ip,
                    start_time_ms=start_time_ms,
                    duration_ms=duration_ms,
                    use_realistic_ips=use_realistic_ips,
                    **kwargs,
                )
                campaign.events.append(event)

        self._external_campaigns.append(campaign)
        logger.info(
            f"Created external campaign '{name}' with {len(campaign.events)} events"
        )
        return campaign

    def _create_external_event(
        self,
        event_type: str,
        internal_device_ip: str,
        start_time_ms: float,
        duration_ms: float,
        use_realistic_ips: bool = False,
        **kwargs,
    ) -> ExternalAnomalyEvent:
        """Create a single external anomaly event.

        Args:
            event_type: Type of event
            internal_device_ip: Internal device IP
            start_time_ms: Start time
            duration_ms: Duration
            use_realistic_ips: Use historical malicious IPs
            **kwargs: Type-specific configuration

        Returns:
            ExternalAnomalyEvent instance
        """
        import uuid

        # Get MITRE technique based on event type
        mitre_map = {
            "c2_beacon": "T0885",
            "dns_tunnel": "T0884",
            "http_exfil": "T0882",
            "exploit": "T0869",
            "port_scan": "T0846",
        }

        event = ExternalAnomalyEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            category="external_communication",
            internal_device_ip=internal_device_ip,
            start_time_ms=start_time_ms,
            duration_ms=duration_ms,
            use_realistic_ips=use_realistic_ips,
            mitre_technique=mitre_map.get(event_type),
        )

        # Apply type-specific configuration
        if event_type == "c2_beacon":
            event.c2_pattern = kwargs.get("c2_pattern", "jittered_1m")
            event.c2_protocol = kwargs.get("c2_protocol", "http")
            event.beacon_count = kwargs.get("beacon_count", 10)

        elif event_type in ("dns_tunnel", "http_exfil"):
            event.exfil_protocol = "dns" if event_type == "dns_tunnel" else "http"
            event.exfil_data_size = kwargs.get("exfil_data_size", 1024)

        elif event_type == "exploit":
            event.exploit_pattern = kwargs.get("exploit_pattern", "buffer_overflow_generic")

        elif event_type == "port_scan":
            event.scan_type = kwargs.get("scan_type", "syn")
            event.scan_ot_ports = kwargs.get("scan_ot_ports", True)

        return event

    def generate_external_traffic(
        self,
        internal_devices: list[str],
        start_time_ms: float = 0,
        duration_ms: float = 300000,
    ) -> Iterator[PacketEvent]:
        """Generate external communication traffic for all active campaigns.

        Args:
            internal_devices: List of internal device IPs
            start_time_ms: Generation start time
            duration_ms: Generation duration

        Yields:
            PacketEvent instances
        """
        if not self._external_engine:
            self.configure_external_engine()

        # Process each active external campaign
        for campaign in self._external_campaigns:
            if not campaign.is_active:
                continue

            for event in campaign.events:
                yield from self._generate_event_traffic(event)

        # Also generate traffic from any pending external templates
        external_templates = [
            t for t in self._templates
            if t.get("category") == "external_communication"
        ]

        for template in external_templates:
            if self._random.random() < template.get("probability", 0.0):
                # Generate traffic based on template
                device_ip = self._random.choice(internal_devices) if internal_devices else "10.0.0.10"
                event = self._create_external_event(
                    event_type=template.get("type", "c2_beacon"),
                    internal_device_ip=device_ip,
                    start_time_ms=start_time_ms,
                    duration_ms=duration_ms,
                    c2_pattern=template.get("parameters", {}).get("pattern"),
                    c2_protocol=template.get("parameters", {}).get("protocol", "http"),
                    exploit_pattern=template.get("parameters", {}).get("exploit_type"),
                )
                yield from self._generate_event_traffic(event)

    def _generate_event_traffic(
        self,
        event: ExternalAnomalyEvent,
    ) -> Iterator[PacketEvent]:
        """Generate traffic for a single external event.

        Args:
            event: External anomaly event

        Yields:
            PacketEvent instances
        """
        if not self._external_engine:
            self.configure_external_engine()

        engine = self._external_engine

        if event.event_type == "c2_beacon":
            for ext_event in engine.generate_c2_beaconing(
                internal_device_ip=event.internal_device_ip,
                start_time_ms=int(event.start_time_ms),
                duration_ms=int(event.duration_ms),
                pattern_name=event.c2_pattern,
            ):
                yield self._convert_external_event(ext_event, event)

        elif event.event_type == "dns_tunnel":
            # Generate fake data to exfiltrate
            fake_data = bytes(
                self._random.getrandbits(8)
                for _ in range(event.exfil_data_size)
            )
            for ext_event in engine.generate_dns_tunnel(
                internal_device_ip=event.internal_device_ip,
                data=fake_data,
                start_time_ms=int(event.start_time_ms),
            ):
                yield self._convert_external_event(ext_event, event)

        elif event.event_type == "http_exfil":
            fake_data = bytes(
                self._random.getrandbits(8)
                for _ in range(event.exfil_data_size)
            )
            for ext_event in engine.generate_http_exfil(
                internal_device_ip=event.internal_device_ip,
                data=fake_data,
                start_time_ms=int(event.start_time_ms),
            ):
                yield self._convert_external_event(ext_event, event)

        elif event.event_type == "exploit":
            if event.exploit_pattern:
                for ext_event in engine.generate_exploit_attempt(
                    target_device_ip=event.internal_device_ip,
                    exploit_name=event.exploit_pattern,
                    start_time_ms=int(event.start_time_ms),
                ):
                    yield self._convert_external_event(ext_event, event)

        elif event.event_type == "port_scan":
            for ext_event in engine.generate_port_scan(
                target_device_ip=event.internal_device_ip,
                start_time_ms=int(event.start_time_ms),
                scan_ot_ports=event.scan_ot_ports,
            ):
                yield self._convert_external_event(ext_event, event)

        self._external_packet_count += 1

    def _convert_external_event(
        self,
        ext_event: ExternalPacketEvent,
        anomaly_event: ExternalAnomalyEvent,
    ) -> PacketEvent:
        """Convert external engine PacketEvent to internal PacketEvent.

        Args:
            ext_event: External packet event from engine
            anomaly_event: Parent anomaly event

        Returns:
            Internal PacketEvent
        """
        # Convert Scapy packet to bytes
        packet_bytes = bytes(ext_event.packet)

        return PacketEvent(
            timestamp_ms=ext_event.timestamp_ms,
            flow_id=f"external_{anomaly_event.event_id}",
            packet_bytes=packet_bytes,
            direction="outbound" if ext_event.event_type in ("c2_beacon", "http_exfil", "dns_tunnel") else "inbound",
            metadata={
                "anomaly": True,
                "anomaly_type": anomaly_event.event_type,
                "anomaly_category": "external_communication",
                "external_event_type": ext_event.event_type,
                "mitre_technique": anomaly_event.mitre_technique,
                **ext_event.metadata,
            },
        )

    def get_external_statistics(self) -> dict[str, Any]:
        """Get external traffic statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "external_campaigns": len(self._external_campaigns),
            "active_campaigns": len([c for c in self._external_campaigns if c.is_active]),
            "total_external_events": sum(len(c.events) for c in self._external_campaigns),
            "external_packets_generated": self._external_packet_count,
        }

    @staticmethod
    def list_available_external_patterns() -> dict[str, list[dict]]:
        """List all available external traffic patterns.

        Returns:
            Dictionary with beacon patterns and exploit patterns
        """
        return {
            "beacon_patterns": list_beacon_patterns(),
            "exploit_patterns": list_exploit_patterns(),
        }


class AnomalyScheduler:
    """Scheduler for coordinating anomaly injection across time.

    Provides advanced scheduling features:
    - Time-based triggers
    - Pattern-based injection (e.g., increasing frequency)
    - Correlated multi-flow anomalies
    """

    def __init__(self, injector: AnomalyInjector):
        """Initialize scheduler.

        Args:
            injector: AnomalyInjector instance
        """
        self.injector = injector
        self._scheduled_events: list[tuple[float, str, dict]] = []

    def schedule_at(
        self,
        time_ms: float,
        anomaly_type: str,
        parameters: dict[str, Any] | None = None,
        target_flows: list[str] | None = None,
    ) -> None:
        """Schedule an anomaly at a specific time.

        Args:
            time_ms: Time to inject
            anomaly_type: Type of anomaly
            parameters: Override parameters
            target_flows: Target flow IDs
        """
        self._scheduled_events.append((
            time_ms,
            anomaly_type,
            {"parameters": parameters, "target_flows": target_flows},
        ))
        self._scheduled_events.sort(key=lambda x: x[0])

    def schedule_pattern(
        self,
        pattern: str,
        anomaly_type: str,
        start_time_ms: float,
        end_time_ms: float,
        **kwargs,
    ) -> None:
        """Schedule anomalies following a pattern.

        Args:
            pattern: Pattern type ("linear", "burst", "random", "increasing")
            anomaly_type: Type of anomaly
            start_time_ms: Start time
            end_time_ms: End time
            **kwargs: Pattern-specific parameters
        """
        if pattern == "linear":
            # Evenly spaced injections
            count = kwargs.get("count", 10)
            interval = (end_time_ms - start_time_ms) / count
            for i in range(count):
                self.schedule_at(start_time_ms + i * interval, anomaly_type)

        elif pattern == "burst":
            # Bursts of injections
            burst_count = kwargs.get("burst_count", 3)
            burst_size = kwargs.get("burst_size", 5)
            burst_interval = (end_time_ms - start_time_ms) / burst_count

            for b in range(burst_count):
                burst_start = start_time_ms + b * burst_interval
                for i in range(burst_size):
                    self.schedule_at(burst_start + i * 100, anomaly_type)

        elif pattern == "increasing":
            # Increasing frequency over time
            count = kwargs.get("count", 20)
            for i in range(count):
                # Quadratic spacing - more frequent near end
                progress = (i / count) ** 2
                time = start_time_ms + progress * (end_time_ms - start_time_ms)
                self.schedule_at(time, anomaly_type)

        elif pattern == "random":
            # Random times within range
            count = kwargs.get("count", 10)
            rng = np.random.default_rng()
            times = rng.uniform(start_time_ms, end_time_ms, count)
            for t in times:
                self.schedule_at(t, anomaly_type)

    def get_scheduled_for_time(self, current_time_ms: float) -> list[tuple[str, dict]]:
        """Get anomalies scheduled for current time.

        Args:
            current_time_ms: Current simulation time

        Returns:
            List of (anomaly_type, config) tuples
        """
        due = []
        remaining = []

        for time, anomaly_type, config in self._scheduled_events:
            if time <= current_time_ms:
                due.append((anomaly_type, config))
            else:
                remaining.append((time, anomaly_type, config))

        self._scheduled_events = remaining
        return due
