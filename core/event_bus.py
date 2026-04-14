"""
Event Bus — Publish/Subscribe-System für Proaktivitäts-Tests.

Ermöglicht es, Bedingungen zu simulieren, auf die der Agent reagieren soll.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Event:
    event_type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    source: str = "system"


EventHandler = Callable[[Event], None]


class EventBus:
    """Einfaches Pub/Sub-System für Agent-Events."""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._event_log: list[Event] = []
        self._pending_events: list[Event] = []

    def subscribe(self, event_type: str, handler: EventHandler):
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def publish(self, event: Event):
        self._event_log.append(event)
        self._pending_events.append(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        for handler in self._handlers.get("*", []):
            handler(event)

    def emit(self, event_type: str, data: dict[str, Any] | None = None, source: str = "system"):
        self.publish(Event(event_type=event_type, data=data or {}, source=source))

    def get_pending(self) -> list[Event]:
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def get_log(self) -> list[Event]:
        return list(self._event_log)

    def clear(self):
        self._event_log.clear()
        self._pending_events.clear()


class ConditionMonitor:
    """Überwacht Bedingungen und feuert Events wenn sie eintreten."""

    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._conditions: list[dict] = []

    def add_condition(
        self,
        name: str,
        check_fn: Callable[[], bool],
        event_type: str,
        event_data: dict[str, Any] | None = None,
    ):
        self._conditions.append({
            "name": name,
            "check": check_fn,
            "event_type": event_type,
            "event_data": event_data or {},
            "triggered": False,
        })

    def check_all(self) -> list[str]:
        triggered = []
        for cond in self._conditions:
            if not cond["triggered"] and cond["check"]():
                cond["triggered"] = True
                self._bus.emit(cond["event_type"], cond["event_data"], source=cond["name"])
                triggered.append(cond["name"])
        return triggered

    def reset(self):
        for cond in self._conditions:
            cond["triggered"] = False


class HeartbeatSimulator:
    """Simuliert den Heartbeat-Mechanismus von OpenClaw."""

    def __init__(self, interval_seconds: float = 10.0):
        self.interval = interval_seconds
        self._beats: list[float] = []
        self._responses: list[Any] = []

    def beat(self) -> float:
        ts = time.time()
        self._beats.append(ts)
        return ts

    def record_response(self, response: Any):
        self._responses.append(response)

    @property
    def beat_count(self) -> int:
        return len(self._beats)

    @property
    def responses(self) -> list:
        return self._responses

    def get_action_beats(self) -> list[int]:
        """Indizes der Beats, bei denen der Agent eine Aktion ausgeführt hat."""
        indices = []
        for i, resp in enumerate(self._responses):
            if hasattr(resp, "actions") and resp.actions:
                indices.append(i)
        return indices

    def reset(self):
        self._beats.clear()
        self._responses.clear()
