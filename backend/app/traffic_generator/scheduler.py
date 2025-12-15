"""Event scheduler using heap-based priority queue."""

import heapq
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class ScheduledEvent:
    """Event with scheduled time for priority queue."""

    timestamp_ms: float
    event_data: Any = field(compare=False)


class EventScheduler:
    """Heap-based event scheduler for packet generation."""

    def __init__(self):
        """Initialize the event scheduler."""
        self._heap: list[ScheduledEvent] = []

    def schedule(self, timestamp_ms: float, event_data: Any) -> None:
        """Schedule an event at a specific time.

        Args:
            timestamp_ms: Time in milliseconds when event should occur
            event_data: Event data to store
        """
        scheduled_event = ScheduledEvent(timestamp_ms=timestamp_ms, event_data=event_data)
        heapq.heappush(self._heap, scheduled_event)

    def pop_next(self) -> tuple[float, Any] | None:
        """Pop the next event from the queue.

        Returns:
            Tuple of (timestamp_ms, event_data) or None if queue is empty
        """
        if not self._heap:
            return None

        scheduled_event = heapq.heappop(self._heap)
        return (scheduled_event.timestamp_ms, scheduled_event.event_data)

    def peek_next(self) -> tuple[float, Any] | None:
        """Peek at the next event without removing it.

        Returns:
            Tuple of (timestamp_ms, event_data) or None if queue is empty
        """
        if not self._heap:
            return None

        scheduled_event = self._heap[0]
        return (scheduled_event.timestamp_ms, scheduled_event.event_data)

    def has_events(self) -> bool:
        """Check if there are any events in the queue.

        Returns:
            True if events exist, False otherwise
        """
        return len(self._heap) > 0

    def has_events_before(self, timestamp_ms: float) -> bool:
        """Check if there are events before a specific time.

        Args:
            timestamp_ms: Time threshold in milliseconds

        Returns:
            True if there are events before the threshold
        """
        if not self._heap:
            return False

        return self._heap[0].timestamp_ms < timestamp_ms

    def clear(self) -> None:
        """Clear all events from the scheduler."""
        self._heap.clear()

    def __len__(self) -> int:
        """Get number of scheduled events."""
        return len(self._heap)
