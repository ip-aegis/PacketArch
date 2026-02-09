"""Process simulation controller — composition peer for UnifiedOrchestrator.

Unlike :class:`AdaptiveController` (adjusts poll intervals) or
:class:`AttackOrchestrator` (generates packets), the
:class:`ProcessSimController` mutates :class:`PayloadGenerator` state
before each poll cycle so that protocol engines read physically
modelled, correlated sensor values.

Thread safety follows the same model as ``AdaptiveController``:
- :meth:`handle_tick` called from orchestrator thread only.
- :meth:`set_pending_command` from async thread via atomic swap.
- :meth:`get_state_snapshot` is read-only, safe from any thread.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .binder import VariableBinder
from .faults import FaultScenario
from .process_model import ProcessModel
from .types import ProcessSimConfig, ProcessState, VariableBinding

if TYPE_CHECKING:
    from app.protocol_engines.payload_generator import PayloadGenerator
    from app.traffic_generator.scheduler import EventScheduler

logger = logging.getLogger(__name__)

# Maps deployment phase IDs to process states.
_PHASE_TO_STATE: dict[str, ProcessState] = {
    "startup": ProcessState.WARMING_UP,
    "steady_state": ProcessState.STEADY_STATE,
    "steady": ProcessState.STEADY_STATE,
    "maintenance": ProcessState.MAINTENANCE,
    "shutdown": ProcessState.SHUTDOWN,
}


class ProcessSimController:
    """Process simulation composition peer for the unified orchestrator.

    Schedules periodic ``process_sim_tick`` control events on the shared
    event heap.  Each tick advances all :class:`ProcessModel` instances,
    processes faults, and pushes correlated values into
    :class:`PayloadGenerator` sensor states via :class:`VariableBinder`.
    """

    def __init__(
        self,
        config: ProcessSimConfig,
        models: list[ProcessModel],
        flow_generators: dict[str, PayloadGenerator],
        binder: VariableBinder | None = None,
        faults: list[FaultScenario] | None = None,
    ) -> None:
        self._config = config
        self._models: dict[str, ProcessModel] = {m.model_id: m for m in models}
        self._flow_generators = flow_generators
        self._step_interval_ms = config.step_interval_ms
        self._last_step_ms: float = 0.0
        self._faults: list[FaultScenario] = faults or []
        self._pending_command: dict[str, Any] | None = None
        self._last_phase_id: str | None = None

        # Build or use provided binder
        if binder is not None:
            self._binder = binder
        elif config.bindings:
            self._binder = VariableBinder.from_dicts(config.bindings)
        else:
            self._binder = VariableBinder.auto_bind(self._models, flow_generators)

        logger.info(
            "ProcessSimController: %d model(s), %d binding(s), %d fault(s)",
            len(self._models),
            self._binder.binding_count,
            len(self._faults),
        )

    # ------------------------------------------------------------------
    # Event scheduling
    # ------------------------------------------------------------------

    def schedule_initial_events(
        self, scheduler: EventScheduler, warmup_ms: float = 100.0,
    ) -> None:
        """Schedule the first ``process_sim_tick`` after startup warmup."""
        first_tick = warmup_ms + self._step_interval_ms
        scheduler.schedule(first_tick, {"type": "process_sim_tick"})

    def handle_tick(
        self,
        current_time_ms: float,
        scheduler: EventScheduler,
    ) -> None:
        """Handle a ``process_sim_tick`` event.

        1. Process any pending command.
        2. Advance all models by dt.
        3. Check and apply faults.
        4. Push variable values to PayloadGenerators.
        5. Schedule next tick.
        """
        # Process pending command
        cmd = self._pending_command
        if cmd is not None:
            self._pending_command = None
            self._process_command(cmd, current_time_ms)

        # Calculate dt
        if self._last_step_ms > 0:
            dt_ms = current_time_ms - self._last_step_ms
        else:
            dt_ms = self._step_interval_ms
        dt_s = dt_ms / 1000.0
        self._last_step_ms = current_time_ms

        # Step all process models
        for model in self._models.values():
            model.step(dt_s)

        # Check and apply faults
        for fault in self._faults:
            # Check auto-trigger
            if not fault.is_active:
                max_sim = max(
                    (m.sim_time_s for m in self._models.values()), default=0.0,
                )
                fault.check_auto_trigger(max_sim, current_time_ms)
            # Apply active fault effects
            fault.step(self._models, current_time_ms)

        # Push correlated values to PayloadGenerators
        self._binder.push_values(self._models, self._flow_generators)

        # Schedule next tick
        scheduler.schedule(
            current_time_ms + self._step_interval_ms,
            {"type": "process_sim_tick"},
        )

    # ------------------------------------------------------------------
    # Deployment phase integration
    # ------------------------------------------------------------------

    def on_phase_change(self, phase_id: str) -> None:
        """Map a deployment phase to a process state.

        Called by the orchestrator when the adaptive controller detects
        a phase transition.
        """
        if phase_id == self._last_phase_id:
            return

        self._last_phase_id = phase_id
        new_state = _PHASE_TO_STATE.get(phase_id)
        if new_state is None:
            logger.debug("No process state mapping for phase '%s'", phase_id)
            return

        for model in self._models.values():
            model.force_state(new_state)
        logger.info("Phase '%s' -> process state '%s'", phase_id, new_state.value)

    # ------------------------------------------------------------------
    # Runtime commands
    # ------------------------------------------------------------------

    def set_pending_command(self, command: dict[str, Any]) -> None:
        """Atomic swap for commands from an async thread."""
        self._pending_command = command

    def _process_command(
        self, cmd: dict[str, Any], current_time_ms: float,
    ) -> None:
        action = cmd.get("action", "")
        if action == "trigger_fault":
            fault_name = cmd.get("fault_name", "")
            for fault in self._faults:
                if fault.name == fault_name:
                    fault.activate(current_time_ms)
                    break
        elif action == "force_state":
            state_str = cmd.get("state", "")
            try:
                state = ProcessState(state_str)
                for model in self._models.values():
                    model.force_state(state)
            except ValueError:
                logger.warning("Unknown process state: %s", state_str)
        elif action == "reset":
            for model in self._models.values():
                model.reset()
            for fault in self._faults:
                fault.reset()

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------

    def get_state_snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot for status reporting."""
        return {
            "enabled": self._config.enabled,
            "step_interval_ms": self._step_interval_ms,
            "models": {
                mid: model.get_snapshot()
                for mid, model in self._models.items()
            },
            "active_faults": [
                f.to_dict() for f in self._faults if f.is_active
            ],
            "binding_count": self._binder.binding_count,
        }
