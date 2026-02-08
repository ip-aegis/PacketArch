"""Flow coordinator for managing cross-flow dependencies and timing relationships.

Enables realistic multi-device coordination in OT traffic scenarios:
- Master-slave polling sequences
- Request-response timing relationships
- Synchronized operations across multiple devices
- Event-triggered cascade flows
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DependencyType(str, Enum):
    """Types of timing dependencies between flows."""

    TRIGGER = "trigger"  # Target fires after source completes
    DELAY_AFTER = "delay_after"  # Target waits N ms after source event
    SYNC_WITH = "sync_with"  # Target syncs poll cycle with source
    CASCADE = "cascade"  # Target polls all slaves in sequence


@dataclass
class FlowDependency:
    """Defines a timing relationship between flows.

    Attributes:
        source_flow_id: The flow that triggers the dependency
        target_flow_id: The flow that responds to the trigger
        dependency_type: Type of timing relationship
        delay_ms: Base delay after source event (milliseconds)
        jitter_ms: Random jitter to add to delay (milliseconds)
        priority: Execution priority for ordering (lower = higher priority)
        condition: Optional condition for triggering (e.g., "value > threshold")
    """

    source_flow_id: str
    target_flow_id: str
    dependency_type: DependencyType = DependencyType.TRIGGER
    delay_ms: float = 0.0
    jitter_ms: float = 0.0
    priority: int = 0
    condition: str | None = None


@dataclass
class FlowEvent:
    """Records a flow event for dependency tracking.

    Attributes:
        flow_id: Flow that generated the event
        timestamp_ms: When the event occurred
        event_type: Type of event (startup, poll, response, shutdown)
        metadata: Additional event data
    """

    flow_id: str
    timestamp_ms: float
    event_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


class FlowCoordinator:
    """Coordinates timing between related flows.

    Manages dependencies to ensure realistic timing relationships between
    devices in multi-controller, master-slave, and cascade scenarios.

    Example usage:
        ```python
        coordinator = FlowCoordinator()

        # HMI polls PLC1 after PLC1 polls its sensors
        coordinator.add_dependency(FlowDependency(
            source_flow_id="plc1_sensor_poll",
            target_flow_id="hmi_plc1_poll",
            dependency_type=DependencyType.TRIGGER,
            delay_ms=50,
            jitter_ms=10,
        ))

        # In orchestrator:
        if coordinator.should_trigger("hmi_plc1_poll", current_time):
            # Generate packets for HMI polling PLC1
            ...

        # After generating packets:
        coordinator.record_event("plc1_sensor_poll", current_time)
        ```
    """

    def __init__(self, dependencies: list[FlowDependency] | None = None):
        """Initialize flow coordinator.

        Args:
            dependencies: Initial list of flow dependencies
        """
        self.dependencies: list[FlowDependency] = dependencies or []
        self.flow_events: dict[str, FlowEvent] = {}  # Latest event per flow
        self.event_history: list[FlowEvent] = []  # All events for debugging
        self._dependency_map: dict[str, list[FlowDependency]] = {}  # target -> deps
        self._source_map: dict[str, list[FlowDependency]] = {}  # source -> deps

        # Build lookup maps
        if dependencies:
            for dep in dependencies:
                self._add_to_maps(dep)

    def add_dependency(self, dependency: FlowDependency) -> None:
        """Add a flow dependency.

        Args:
            dependency: The dependency to add
        """
        self.dependencies.append(dependency)
        self._add_to_maps(dependency)

    def _add_to_maps(self, dep: FlowDependency) -> None:
        """Add dependency to lookup maps."""
        # Map by target (for checking if flow should trigger)
        if dep.target_flow_id not in self._dependency_map:
            self._dependency_map[dep.target_flow_id] = []
        self._dependency_map[dep.target_flow_id].append(dep)

        # Map by source (for notifying dependents)
        if dep.source_flow_id not in self._source_map:
            self._source_map[dep.source_flow_id] = []
        self._source_map[dep.source_flow_id].append(dep)

    def remove_dependency(
        self, source_flow_id: str, target_flow_id: str
    ) -> bool:
        """Remove a dependency between flows.

        Args:
            source_flow_id: Source flow ID
            target_flow_id: Target flow ID

        Returns:
            True if dependency was found and removed
        """
        for dep in self.dependencies[:]:
            if dep.source_flow_id == source_flow_id and dep.target_flow_id == target_flow_id:
                self.dependencies.remove(dep)
                if dep in self._dependency_map.get(target_flow_id, []):
                    self._dependency_map[target_flow_id].remove(dep)
                if dep in self._source_map.get(source_flow_id, []):
                    self._source_map[source_flow_id].remove(dep)
                return True
        return False

    def get_dependencies_for_target(self, flow_id: str) -> list[FlowDependency]:
        """Get all dependencies where this flow is the target.

        Args:
            flow_id: Target flow ID

        Returns:
            List of dependencies that affect this flow
        """
        return self._dependency_map.get(flow_id, [])

    def get_dependents_of_source(self, flow_id: str) -> list[FlowDependency]:
        """Get all dependencies where this flow is the source.

        Args:
            flow_id: Source flow ID

        Returns:
            List of dependencies triggered by this flow
        """
        return self._source_map.get(flow_id, [])

    def should_trigger(
        self,
        flow_id: str,
        current_time_ms: float,
        independent_poll_interval_ms: float | None = None,
    ) -> tuple[bool, float | None]:
        """Check if a flow should execute based on its dependencies.

        Args:
            flow_id: The flow to check
            current_time_ms: Current simulation time in milliseconds
            independent_poll_interval_ms: Independent poll interval if no dependencies

        Returns:
            Tuple of (should_trigger, suggested_delay_ms).
            If should_trigger is True, suggested_delay_ms is the recommended delay
            before execution (including jitter).
        """
        dependencies = self.get_dependencies_for_target(flow_id)

        # No dependencies - flow can run independently
        if not dependencies:
            return True, None

        # Check each dependency
        for dep in dependencies:
            source_event = self.flow_events.get(dep.source_flow_id)

            if source_event is None:
                # Source hasn't fired yet - don't trigger
                if dep.dependency_type == DependencyType.TRIGGER:
                    return False, None
                continue

            # Calculate when target should fire
            trigger_time = source_event.timestamp_ms + dep.delay_ms
            if dep.jitter_ms > 0:
                trigger_time += random.uniform(-dep.jitter_ms / 2, dep.jitter_ms / 2)

            if dep.dependency_type == DependencyType.TRIGGER:
                # Should trigger after source, with delay
                if current_time_ms >= trigger_time:
                    delay = max(0, trigger_time - current_time_ms + dep.delay_ms)
                    if dep.jitter_ms > 0:
                        delay += random.uniform(0, dep.jitter_ms)
                    return True, delay

            elif dep.dependency_type == DependencyType.DELAY_AFTER:
                # Wait specific delay after source
                if current_time_ms >= trigger_time:
                    return True, dep.delay_ms + random.uniform(0, dep.jitter_ms)

            elif dep.dependency_type == DependencyType.SYNC_WITH:
                # Sync timing with source (fire at same rate, offset by delay)
                if current_time_ms >= trigger_time:
                    return True, dep.delay_ms

            elif dep.dependency_type == DependencyType.CASCADE:
                # Part of a cascade sequence - fire in order
                if current_time_ms >= trigger_time:
                    cascade_delay = dep.delay_ms * dep.priority
                    if dep.jitter_ms > 0:
                        cascade_delay += random.uniform(0, dep.jitter_ms)
                    return True, cascade_delay

        return False, None

    def record_event(
        self,
        flow_id: str,
        timestamp_ms: float,
        event_type: str = "poll",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record that a flow generated an event.

        Args:
            flow_id: Flow that generated the event
            timestamp_ms: When the event occurred
            event_type: Type of event
            metadata: Additional event data
        """
        event = FlowEvent(
            flow_id=flow_id,
            timestamp_ms=timestamp_ms,
            event_type=event_type,
            metadata=metadata or {},
        )
        self.flow_events[flow_id] = event
        self.event_history.append(event)

    def get_last_event(self, flow_id: str) -> FlowEvent | None:
        """Get the last recorded event for a flow.

        Args:
            flow_id: Flow ID

        Returns:
            Last event or None if no events recorded
        """
        return self.flow_events.get(flow_id)

    def get_next_triggers(
        self,
        current_time_ms: float,
        flows_to_check: list[str],
    ) -> list[tuple[str, float]]:
        """Get all flows that should trigger and their suggested delays.

        Args:
            current_time_ms: Current simulation time
            flows_to_check: List of flow IDs to check

        Returns:
            List of (flow_id, delay_ms) tuples, sorted by delay
        """
        triggers = []
        for flow_id in flows_to_check:
            should_trigger, delay = self.should_trigger(flow_id, current_time_ms)
            if should_trigger:
                triggers.append((flow_id, delay or 0))

        # Sort by delay (execute sooner first)
        triggers.sort(key=lambda x: x[1])
        return triggers

    def clear_history(self) -> None:
        """Clear event history (keeps latest events per flow)."""
        self.event_history.clear()

    def reset(self) -> None:
        """Reset all state (events and history)."""
        self.flow_events.clear()
        self.event_history.clear()

    def validate_no_cycles(self) -> list[str]:
        """Check for circular dependencies.

        Returns:
            List of error messages for any cycles found
        """
        errors = []
        visited = set()
        path = set()

        def dfs(flow_id: str, path_list: list[str]) -> bool:
            if flow_id in path:
                cycle = path_list[path_list.index(flow_id) :] + [flow_id]
                errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
                return True

            if flow_id in visited:
                return False

            visited.add(flow_id)
            path.add(flow_id)
            path_list.append(flow_id)

            for dep in self._source_map.get(flow_id, []):
                if dfs(dep.target_flow_id, path_list):
                    return True

            path.remove(flow_id)
            path_list.pop()
            return False

        # Check from each source
        all_sources = set(self._source_map.keys())
        for source in all_sources:
            dfs(source, [])

        return errors


# =============================================================================
# Convenience Functions
# =============================================================================


def create_master_slave_chain(
    master_flow_id: str,
    slave_flow_ids: list[str],
    inter_slave_delay_ms: float = 10.0,
    jitter_ms: float = 2.0,
) -> list[FlowDependency]:
    """Create a master-slave polling chain.

    Master polls first, then slaves are polled in sequence.

    Args:
        master_flow_id: The master/initiator flow
        slave_flow_ids: List of slave flows to poll in order
        inter_slave_delay_ms: Delay between each slave poll
        jitter_ms: Random jitter to add

    Returns:
        List of FlowDependency objects
    """
    dependencies = []

    # First slave triggers after master
    if slave_flow_ids:
        dependencies.append(
            FlowDependency(
                source_flow_id=master_flow_id,
                target_flow_id=slave_flow_ids[0],
                dependency_type=DependencyType.CASCADE,
                delay_ms=inter_slave_delay_ms,
                jitter_ms=jitter_ms,
                priority=0,
            )
        )

    # Each subsequent slave triggers after the previous
    for i in range(1, len(slave_flow_ids)):
        dependencies.append(
            FlowDependency(
                source_flow_id=slave_flow_ids[i - 1],
                target_flow_id=slave_flow_ids[i],
                dependency_type=DependencyType.CASCADE,
                delay_ms=inter_slave_delay_ms,
                jitter_ms=jitter_ms,
                priority=i,
            )
        )

    return dependencies


def create_hmi_plc_dependency(
    hmi_flow_id: str,
    plc_flow_id: str,
    response_delay_ms: float = 50.0,
    jitter_ms: float = 10.0,
) -> FlowDependency:
    """Create HMI -> PLC polling dependency.

    HMI typically polls PLC after PLC has updated its data.

    Args:
        hmi_flow_id: HMI polling flow
        plc_flow_id: PLC flow that HMI depends on
        response_delay_ms: Delay after PLC update
        jitter_ms: Random jitter

    Returns:
        FlowDependency object
    """
    return FlowDependency(
        source_flow_id=plc_flow_id,
        target_flow_id=hmi_flow_id,
        dependency_type=DependencyType.DELAY_AFTER,
        delay_ms=response_delay_ms,
        jitter_ms=jitter_ms,
    )


def create_redundant_sync(
    primary_flow_id: str,
    backup_flow_id: str,
    sync_delay_ms: float = 5.0,
) -> FlowDependency:
    """Create sync dependency for redundant controllers.

    Backup controller syncs timing with primary.

    Args:
        primary_flow_id: Primary controller flow
        backup_flow_id: Backup controller flow
        sync_delay_ms: Offset delay for backup

    Returns:
        FlowDependency object
    """
    return FlowDependency(
        source_flow_id=primary_flow_id,
        target_flow_id=backup_flow_id,
        dependency_type=DependencyType.SYNC_WITH,
        delay_ms=sync_delay_ms,
        jitter_ms=0,
    )


def create_alarm_trigger(
    sensor_flow_id: str,
    alarm_flow_id: str,
    alarm_delay_ms: float = 100.0,
    condition: str | None = None,
) -> FlowDependency:
    """Create alarm trigger dependency.

    Alarm flow fires after sensor reading indicates alarm condition.

    Args:
        sensor_flow_id: Sensor polling flow
        alarm_flow_id: Alarm notification flow
        alarm_delay_ms: Delay before alarm
        condition: Optional condition string

    Returns:
        FlowDependency object
    """
    return FlowDependency(
        source_flow_id=sensor_flow_id,
        target_flow_id=alarm_flow_id,
        dependency_type=DependencyType.TRIGGER,
        delay_ms=alarm_delay_ms,
        jitter_ms=50.0,
        condition=condition,
    )


def sample_function_code(distribution: dict[int | str, Any]) -> int:
    """Sample a function code from a learned distribution.

    Args:
        distribution: Dict mapping function codes to frequency/weight info

    Returns:
        Sampled function code
    """
    # Build weighted list
    codes = []
    weights = []

    for code, info in distribution.items():
        code_int = int(code)
        # Handle both simple frequency and nested dict with frequency
        if isinstance(info, (int, float)):
            weight = float(info)
        elif isinstance(info, dict):
            weight = info.get("frequency", info.get("weight", 1.0))
        else:
            weight = 1.0

        codes.append(code_int)
        weights.append(weight)

    if not codes:
        return 3  # Default Modbus read holding registers

    # Weighted random selection
    total = sum(weights)
    r = random.random() * total
    cumulative = 0.0

    for code, weight in zip(codes, weights):
        cumulative += weight
        if r <= cumulative:
            return code

    return codes[-1]


def sample_address_range(patterns: list[dict[str, Any]]) -> tuple[int, int]:
    """Sample an address range from learned patterns.

    Args:
        patterns: List of address pattern dicts with start, end, frequency

    Returns:
        Tuple of (start_address, quantity)
    """
    if not patterns:
        return 0, 10  # Default range

    # Weighted selection of pattern
    weights = [p.get("frequency", p.get("count", 1)) for p in patterns]
    total = sum(weights)
    r = random.random() * total
    cumulative = 0.0

    selected = patterns[0]
    for pattern, weight in zip(patterns, weights):
        cumulative += weight
        if r <= cumulative:
            selected = pattern
            break

    # Extract range from selected pattern
    start = selected.get("start", selected.get("start_address", 0))
    end = selected.get("end", selected.get("end_address", start + 10))
    quantity = min(end - start, selected.get("quantity", 10))

    return start, max(1, quantity)
