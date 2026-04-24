# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Server-side adaptive traffic management service.

Manages adaptation directives and routes them to agents running scenarios.
"""

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class AdaptationService:
    """Manages adaptive traffic directives for running deployments.

    Provides high-level methods for sending adaptation directives to agents
    and retrieving current adaptation state from the traffic dashboard.
    """

    async def send_directives(
        self,
        scenario_id: str,
        directives: list[dict[str, Any]],
        ttl_seconds: int = 300,
    ) -> bool:
        """Send adaptation directives to the agent running a scenario.

        Args:
            scenario_id: Target scenario UUID
            directives: List of directive dicts
            ttl_seconds: Time-to-live for directives

        Returns:
            True if directives were sent successfully
        """
        from app.services.agent_manager import agent_manager

        command = {
            "type": "ADAPT_TRAFFIC",
            "scenario_id": scenario_id,
            "directives": directives,
            "ttl_seconds": ttl_seconds,
        }

        # Find the agent running this scenario
        deployment = agent_manager.get_deployment(scenario_id)
        if not deployment:
            logger.warning(f"No active deployment for scenario {scenario_id}")
            return False

        success = await agent_manager.send_command(deployment.agent_id, command)
        if success:
            logger.info(
                f"Sent {len(directives)} directives to scenario {scenario_id} "
                f"(agent {deployment.agent_id}, ttl={ttl_seconds}s)"
            )
        return success

    async def set_schedule_override(
        self,
        scenario_id: str,
        phase_name: str,
    ) -> bool:
        """Force a specific schedule phase for a scenario.

        Args:
            scenario_id: Target scenario UUID
            phase_name: Phase name to force

        Returns:
            True if override was sent
        """
        return await self.send_directives(
            scenario_id,
            [{"type": "set_schedule_phase", "phase_name": phase_name, "reason": "Manual override"}],
            ttl_seconds=0,  # No expiry for manual overrides
        )

    async def adjust_protocol_rate(
        self,
        scenario_id: str,
        protocol: str,
        multiplier: float,
        reason: str = "",
        ttl_seconds: int = 300,
    ) -> bool:
        """Adjust traffic rate for a specific protocol.

        Args:
            scenario_id: Target scenario UUID
            protocol: Protocol name (e.g. 'bacnet', 'modbus_tcp')
            multiplier: Rate multiplier (>1 = more traffic)
            reason: Human-readable reason
            ttl_seconds: Directive TTL

        Returns:
            True if directive was sent
        """
        return await self.send_directives(
            scenario_id,
            [{
                "type": "adjust_protocol_rate",
                "protocol": protocol,
                "multiplier": multiplier,
                "reason": reason,
            }],
            ttl_seconds=ttl_seconds,
        )

    async def clear_directives(self, scenario_id: str) -> bool:
        """Clear all active directives for a scenario.

        Args:
            scenario_id: Target scenario UUID

        Returns:
            True if clear was sent
        """
        return await self.send_directives(
            scenario_id,
            [{"type": "reset_adaptations", "reason": "Cleared by operator"}],
        )

    async def skip_phase(self, scenario_id: str) -> bool:
        """Skip to the next deployment phase.

        Args:
            scenario_id: Target scenario UUID

        Returns:
            True if directive was sent
        """
        return await self.send_directives(
            scenario_id,
            [{"type": "skip_phase", "reason": "Operator skip"}],
            ttl_seconds=0,
        )

    async def force_phase(self, scenario_id: str, phase_id: str) -> bool:
        """Force a specific deployment phase.

        Args:
            scenario_id: Target scenario UUID
            phase_id: Phase ID to force (e.g. 'steady_state')

        Returns:
            True if directive was sent
        """
        return await self.send_directives(
            scenario_id,
            [{"type": "force_phase", "phase_name": phase_id, "reason": "Operator force"}],
            ttl_seconds=0,
        )

    async def toggle_phase_pause(self, scenario_id: str, paused: bool) -> bool:
        """Pause or resume deployment phase cycling.

        Args:
            scenario_id: Target scenario UUID
            paused: True to pause, False to resume

        Returns:
            True if directive was sent
        """
        directive_type = "pause_phases" if paused else "resume_phases"
        return await self.send_directives(
            scenario_id,
            [{"type": directive_type, "reason": "Operator control"}],
            ttl_seconds=0,
        )

    def get_adaptation_state(self, scenario_id: str) -> dict[str, Any] | None:
        """Get current adaptation state for a scenario from the dashboard.

        Args:
            scenario_id: Target scenario UUID

        Returns:
            Adaptation state dict or None
        """
        from app.services.traffic_dashboard import traffic_dashboard

        snapshot = traffic_dashboard.get_dashboard_snapshot()
        for deployment in snapshot.get("deployments", []):
            if deployment.get("scenario_id") == scenario_id:
                return deployment.get("adaptation")
        return None


# Singleton
adaptation_service = AdaptationService()
