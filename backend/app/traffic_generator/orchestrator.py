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

from app.protocol_engines.output import PcapOutput
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
            output = PcapOutput(str(self.config.output_path))
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
                        )
                    elif ctx.device_id in seen_devices:
                        # Accumulate protocols from multiple flows
                        dev = seen_devices[ctx.device_id]
                        if fc.protocol.value not in dev.protocols:
                            dev.protocols.append(fc.protocol.value)
            if seen_devices:
                ambient = BackgroundNoiseGenerator(list(seen_devices.values()))
                unified.register_ambient_generator(ambient)

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

            logger.info(f"Generation complete: {result.packets_generated} packets")
            logger.info(f"File size: {output.file_size} bytes")

            return GenerationResult(
                job_id=self.config.job_id,
                scenario_id=self.config.scenario_id,
                status=JobStatus.COMPLETED,
                pcap_path=str(self.config.output_path),
                packets_generated=result.packets_generated,
                duration_ms=duration_ms,
                file_size_bytes=output.file_size,
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
