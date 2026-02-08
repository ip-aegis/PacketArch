"""Traffic generation orchestrator.

Delegates to UnifiedOrchestrator for actual packet generation while
maintaining the existing API for backward compatibility with tasks.py
and AI-enhanced generation.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import UUID

from app.protocol_engines import get_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.output import PcapOutput
from app.protocol_engines.types import FlowContext
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from app.traffic_generator.models import GenerationResult, JobStatus

if TYPE_CHECKING:
    from app.protocol_engines.ai_enhanced_base import AIEnhancedEngineFactory

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for traffic generation."""

    job_id: str
    scenario_id: UUID
    total_duration_ms: int
    output_path: str | Path

    # AI-enhanced generation options
    use_ai_timing: bool = False
    use_learned_patterns: bool = False
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

        # AI-enhanced generation support
        self._ai_engine_factory: "AIEnhancedEngineFactory | None" = None
        self._ai_patterns_loaded = False

    async def load_ai_patterns(self, db_session: Any) -> None:
        """Load learned patterns from the database for AI-enhanced generation.

        Args:
            db_session: Database session
        """
        if not (self.config.use_ai_timing or self.config.use_learned_patterns):
            return

        from app.protocol_engines.ai_enhanced_base import AIEnhancedEngineFactory

        self._ai_engine_factory = AIEnhancedEngineFactory()
        await self._ai_engine_factory.load_patterns(db_session)
        self._ai_patterns_loaded = True

        logger.info("Loaded AI patterns for enhanced traffic generation")

    def _get_engine_for_flow(self, flow_context: FlowContext) -> ProtocolEngine:
        """Get the appropriate engine for a flow.

        Uses AI-enhanced engine if patterns are loaded and AI mode is enabled.
        """
        if self._ai_patterns_loaded and self._ai_engine_factory:
            return self._ai_engine_factory.create_engine(
                protocol=flow_context.protocol,
                anomaly_config=self.config.anomaly_injection_config,
            )
        else:
            return get_engine(flow_context.protocol)

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
