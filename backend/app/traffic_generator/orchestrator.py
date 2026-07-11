# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Traffic generation orchestrator.

Delegates to UnifiedOrchestrator for actual packet generation while
maintaining the existing API for backward compatibility with tasks.py.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from app.protocol_engines.output import PcapOutput, SpanPcapOutput, SplitPcapOutput
from app.protocol_engines.types import FlowContext
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from app.traffic_generator.models import GenerationResult, JobStatus

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for traffic generation."""

    job_id: str
    scenario_id: UUID
    total_duration_ms: int
    output_path: str | Path

    anomaly_injection_config: dict[str, Any] = field(default_factory=dict)
    # Optional attack playbook id from PLAYBOOK_REGISTRY (e.g. "TRITON_LIKE").
    # When set, the AttackOrchestrator is registered with the unified
    # orchestrator and bakes attack packets into the PCAP.
    attack_playbook_id: str | None = None
    # Optional dict overriding AttackPlaybookConfig fields: ``intensity``,
    # ``stage_overrides``, ``warmup_ms``, ``start_mode``. ``warmup_ms`` is
    # consumed by register_attack_orchestrator; the rest pass through to
    # AttackPlaybookConfig.from_dict().
    attack_config: dict[str, Any] | None = None
    # Optional dict for AdaptiveConfig.from_dict() — enables timing drift,
    # vendor profiles, schedules. When set, AdaptiveController is registered
    # so the PCAP captures realistic poll-interval variance.
    adaptive_config: dict[str, Any] | None = None
    # When False, skip BackgroundNoiseGenerator registration so the PCAP
    # contains zero broadcast/multicast ambient packets (ARP, NTP, LLDP,
    # STP, CDP, DHCP, IGMP, BACnet WhoIs, PROFINET DCP, SNMP traps).
    broadcast_traffic_enabled: bool = True
    # When True, suppress traffic types that produce phantom components in
    # asset-classification DPI tools (CV). v1: PROFINET PN-IO cyclic frames
    # (gated in profinet/engine.py). v2: ambient PROFINET DCP IdentifyRequest
    # multicasts (gated in BackgroundNoiseGenerator).
    clean_demo_mode: bool = False
    # When True (and an attack_playbook_id is set), the run produces three
    # PCAPs — the regular combined file plus a baseline-only and an
    # attack-only file — via SplitPcapOutput, instead of a single file.
    export_attack_pcap: bool = False
    # Multi-sensor topology mode. When set, the run fans out into one PCAP per
    # topology SPAN (per-zone + core) via SpanPcapOutput: each canonical frame
    # is reframed per the plan's segments. ``topology_plan`` is the validated
    # dict from ``topology_planner.preview()``.
    topology_plan: dict[str, Any] | None = None


class TrafficOrchestrator:
    """Orchestrates traffic generation across multiple flows.

    Wraps UnifiedOrchestrator with PCAP-specific configuration and
    AI-enhanced engine support.
    """

    def __init__(self, config: GenerationConfig):
        """Initialize traffic orchestrator.

        Args:
            config: Generation configuration
        """
        self.config = config
        self._flow_contexts: list[FlowContext] = []

    def add_flow(self, flow_context: FlowContext) -> None:
        """Add a flow to be generated.

        Args:
            flow_context: Flow context to add
        """
        self._flow_contexts.append(flow_context)
        logger.info(
            f"Added flow {flow_context.flow_id} with protocol {flow_context.protocol}"
        )

    def generate(self) -> GenerationResult:
        """Generate traffic for all flows.

        Delegates to UnifiedOrchestrator with PcapOutput.

        Returns:
            Generation result with statistics
        """
        from datetime import datetime

        start_time = datetime.utcnow()

        try:
            # Attack export: one run → three files (combined / baseline /
            # attack-only), routed by the __attack__ flow tag. Only meaningful
            # when a playbook is actually baked in.
            split_export = bool(
                self.config.export_attack_pcap and self.config.attack_playbook_id
            )
            combined_path = Path(self.config.output_path)
            attack_path = baseline_path = None
            if self.config.topology_plan is not None:
                # Multi-sensor topology: one PCAP per SPAN. Takes precedence —
                # attack split isn't composed with per-SPAN fan-out in v1.
                output = SpanPcapOutput(str(combined_path), self.config.topology_plan)
            elif split_export:
                stem = str(combined_path.with_suffix(""))
                attack_path = f"{stem}_attack.pcap"
                baseline_path = f"{stem}_baseline.pcap"
                output = SplitPcapOutput(
                    combined_path=str(combined_path),
                    baseline_path=baseline_path,
                    attack_path=attack_path,
                )
            else:
                output = PcapOutput(str(combined_path))
            unified = UnifiedOrchestrator(
                output=output,
                duration_ms=self.config.total_duration_ms,
            )

            # Add all flows (UnifiedOrchestrator uses get_engine internally)
            for fc in self._flow_contexts:
                unified.add_flow(fc)

            # Auto-create ambient noise generator from flow devices
            from app.protocol_engines.ambient import (
                AmbientDevice,
                BackgroundNoiseGenerator,
            )

            seen_devices: dict[str, AmbientDevice] = {}
            for fc in self._flow_contexts:
                for ctx in (fc.source, fc.destination):
                    if ctx.device_id not in seen_devices and ctx.ip_address:
                        fp = ctx.vendor_fingerprint or {}
                        seen_devices[ctx.device_id] = AmbientDevice(
                            device_id=ctx.device_id,
                            mac_address=ctx.mac_address,
                            ip_address=ctx.ip_address,
                            gateway_ip=ctx.ip_address.rsplit(".", 1)[0] + ".1",
                            protocols=[fc.protocol.value],
                            device_type=fp.get("device_type", ""),
                            vendor=fp.get("vendor", ""),
                            device_name=getattr(ctx, "device_name", "") or ctx.device_id,
                            vendor_fingerprint=fp,
                            # Carry scenario_id so the ambient FingerprintApplicator
                            # resolves the SAME canonical identity the protocol
                            # engines emit (PCAP/live identity lockstep).
                            scenario_id=getattr(ctx, "scenario_id", None),
                        )
                    elif ctx.device_id in seen_devices:
                        # Accumulate protocols from multiple flows
                        dev = seen_devices[ctx.device_id]
                        if fc.protocol.value not in dev.protocols:
                            dev.protocols.append(fc.protocol.value)
            if seen_devices and self.config.broadcast_traffic_enabled:
                ambient = BackgroundNoiseGenerator(
                    list(seen_devices.values()),
                    clean_demo_mode=self.config.clean_demo_mode,
                )
                unified.register_ambient_generator(ambient)
            elif seen_devices:
                logger.info(
                    "Broadcast/multicast traffic disabled by scenario toggle — "
                    "skipping ambient noise generator"
                )

            # Auto-create process simulation from vertical metadata
            try:
                vertical = None
                for fc in self._flow_contexts:
                    if isinstance(fc.config, dict):
                        vertical = fc.config.get("_vertical")
                        if vertical:
                            break
                if vertical:
                    from app.protocol_engines.process_sim import (
                        ProcessSimConfig,
                        ProcessSimController,
                        build_from_vertical,
                    )

                    models, faults = build_from_vertical(vertical)
                    if models:
                        flow_gens = {
                            fs.flow.flow_id: fs.flow.payload_generator
                            for fs in unified.flows
                            if fs.flow.payload_generator
                        }
                        config = ProcessSimConfig(enabled=True, vertical=vertical)
                        controller = ProcessSimController(
                            config, models, flow_gens, faults=faults,
                        )
                        unified.register_process_sim(controller)
            except Exception as e:
                logger.warning(f"Process simulation unavailable: {e}")

            # Adaptive traffic: register if config supplied. Drives
            # micro-variations + schedule + phase scheduler that bake realistic
            # poll-interval drift into the PCAP. Without this the PCAP shows
            # perfectly periodic polls — useful baseline, but not realistic.
            if self.config.adaptive_config:
                try:
                    from app.protocol_engines.adaptive import (
                        AdaptiveConfig,
                        AdaptiveController,
                    )

                    ad_cfg = AdaptiveConfig.from_dict(self.config.adaptive_config)
                    if ad_cfg.enabled:
                        ad_ctrl = AdaptiveController(
                            ad_cfg, total_flows=len(unified.flows)
                        )
                        unified.register_adaptive_controller(ad_ctrl)
                except Exception as e:
                    logger.warning(f"Adaptive controller unavailable: {e}")

            # Attack playbook: register if a playbook id is supplied. Bakes
            # attack stage packets (recon, exploit, C2, exfil, etc.) into the
            # PCAP starting after a configurable warmup. Devices are sourced
            # from the same flow contexts the ambient block uses.
            if self.config.attack_playbook_id:
                try:
                    from app.protocol_engines.attacks import (
                        AttackOrchestrator,
                        get_playbook,
                    )
                    from app.protocol_engines.attacks.types import (
                        AttackPlaybookConfig,
                    )

                    playbook = get_playbook(self.config.attack_playbook_id)
                    if playbook is None:
                        raise ValueError(
                            f"Unknown playbook '{self.config.attack_playbook_id}'"
                        )

                    raw_attack_cfg = dict(self.config.attack_config or {})
                    # PCAP path runs end-to-end at generation time; ignore
                    # live-control "manual" start mode — there's no runtime
                    # to send a START_ATTACK command.
                    raw_attack_cfg.setdefault("playbook_id", playbook.playbook_id)
                    if raw_attack_cfg.get("start_mode") == "manual":
                        raw_attack_cfg["start_mode"] = "with_deployment"
                    warmup_ms = raw_attack_cfg.pop("warmup_ms", None)

                    atk_cfg = AttackPlaybookConfig.from_dict(raw_attack_cfg)
                    devices_for_attack = [
                        {
                            "device_id": dev.device_id,
                            "ip_address": dev.ip_address,
                            "mac_address": dev.mac_address,
                            "vendor": dev.vendor,
                            "device_type": dev.device_type,
                            "protocols": list(dev.protocols),
                        }
                        for dev in seen_devices.values()
                    ]
                    attack_orch = AttackOrchestrator(
                        playbook=playbook,
                        devices=devices_for_attack,
                        config=atk_cfg,
                    )
                    unified.register_attack_orchestrator(
                        attack_orch, warmup_ms=warmup_ms
                    )
                except Exception as e:
                    logger.warning(f"Attack orchestrator unavailable: {e}")

            logger.info(f"Starting traffic generation for job {self.config.job_id}")
            logger.info(f"Duration: {self.config.total_duration_ms}ms")
            logger.info(f"Output: {self.config.output_path}")
            logger.info(f"Flows: {len(self._flow_contexts)}")

            result = unified.run()

            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            if result.error:
                logger.error(f"Generation failed: {result.error}")
                return GenerationResult(
                    job_id=self.config.job_id,
                    scenario_id=self.config.scenario_id,
                    status=JobStatus.FAILED,
                    error_message=result.error,
                    packets_generated=result.packets_generated,
                    duration_ms=duration_ms,
                    started_at=start_time,
                    completed_at=end_time,
                )

            # Assemble the artifact list + combined file size. SplitPcapOutput
            # and PcapOutput expose file_size differently (method vs property).
            if self.config.topology_plan is not None:
                combined_size = output.bytes_sent
                artifacts = [
                    {
                        "kind": "combined",
                        "filename": combined_path.name,
                        "packets": output.packet_count,
                        "size_bytes": combined_size,
                    }
                ]
                for span_id, path in output.span_paths().items():
                    artifacts.append(
                        {
                            "kind": f"span:{span_id}",
                            "filename": Path(path).name,
                            "packets": output.span_packet_counts.get(span_id, 0),
                            "size_bytes": 0,
                        }
                    )
            elif split_export:
                combined_size = output.file_size("combined")
                artifacts = [
                    {
                        "kind": kind,
                        "filename": Path(path).name,
                        "packets": output.packet_count_for(kind),
                        "size_bytes": output.file_size(kind),
                    }
                    for kind, path in (
                        ("combined", str(combined_path)),
                        ("baseline", baseline_path),
                        ("attack", attack_path),
                    )
                ]
            else:
                combined_size = output.file_size
                artifacts = [
                    {
                        "kind": "combined",
                        "filename": combined_path.name,
                        "packets": result.packets_generated,
                        "size_bytes": combined_size,
                    }
                ]

            logger.info(f"Generation complete: {result.packets_generated} packets")
            logger.info(f"File size: {combined_size} bytes")
            if split_export:
                logger.info(f"Attack-export artifacts: {artifacts}")

            return GenerationResult(
                job_id=self.config.job_id,
                scenario_id=self.config.scenario_id,
                status=JobStatus.COMPLETED,
                pcap_path=str(self.config.output_path),
                packets_generated=result.packets_generated,
                duration_ms=duration_ms,
                file_size_bytes=combined_size,
                artifacts=artifacts,
                started_at=start_time,
                completed_at=end_time,
            )

        except Exception as e:
            logger.error(f"Error during traffic generation: {e}", exc_info=True)
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return GenerationResult(
                job_id=self.config.job_id,
                scenario_id=self.config.scenario_id,
                status=JobStatus.FAILED,
                error_message=str(e),
                packets_generated=0,
                duration_ms=duration_ms,
                started_at=start_time,
                completed_at=end_time,
            )
