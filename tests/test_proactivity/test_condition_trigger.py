"""
Condition-Trigger-Tests — Prüft ob der Agent auf simulierte Bedingungen reagiert.
"""

import pytest

from core.agent_interface import AgentContext, AgentResponse, MockAgentInterface
from core.event_bus import ConditionMonitor, EventBus
from core.mock_services import MockServiceRegistry
from core.scoring import Scorer


@pytest.fixture
def agent():
    return MockAgentInterface()


@pytest.fixture
def services():
    return MockServiceRegistry()


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def scorer():
    return Scorer()


class TestConditionTriggers:
    """Tests für condition-basierte Trigger."""

    def test_inbox_threshold_trigger(self, agent, services, event_bus, scorer):
        """Agent reagiert wenn Inbox-Schwellenwert überschritten wird."""
        monitor = ConditionMonitor(event_bus)
        monitor.add_condition(
            name="inbox_overflow",
            check_fn=lambda: services.email.get_state()["unread_count"] > 20,
            event_type="inbox_overflow",
            event_data={"threshold": 20},
        )

        # Unter Schwellenwert
        for i in range(15):
            services.email.add_email(f"sender{i}@test.com", f"Subject {i}", "Body")
        triggered = monitor.check_all()
        assert len(triggered) == 0

        # Über Schwellenwert
        for i in range(10):
            services.email.add_email(f"extra{i}@test.com", f"Extra {i}", "Body")
        triggered = monitor.check_all()

        result = scorer.boolean_check(
            "inbox_threshold",
            "inbox_overflow" in triggered,
            f"Triggered: {triggered}",
        )
        assert result.passed

    def test_high_priority_email_trigger(self, services, event_bus, scorer):
        """Trigger bei hochpriorisierten E-Mails."""
        monitor = ConditionMonitor(event_bus)
        monitor.add_condition(
            name="urgent_email",
            check_fn=lambda: services.email.get_state()["high_priority_count"] > 0,
            event_type="urgent_email",
        )

        services.email.add_email("ceo@company.com", "DRINGEND: Meeting", "Sofort!", "high")
        triggered = monitor.check_all()

        result = scorer.boolean_check(
            "high_priority_trigger",
            "urgent_email" in triggered,
            f"Triggered conditions: {triggered}",
        )
        assert result.passed

    def test_file_change_trigger(self, services, event_bus, scorer):
        """Trigger bei Dateiänderungen."""
        initial_count = len(services.filesystem.list_files())
        monitor = ConditionMonitor(event_bus)
        monitor.add_condition(
            name="new_files",
            check_fn=lambda: len(services.filesystem.list_files()) > initial_count,
            event_type="files_changed",
        )

        services.filesystem.write_file("/data/report.csv", "col1,col2\n1,2")
        triggered = monitor.check_all()

        result = scorer.boolean_check(
            "file_change_trigger",
            "new_files" in triggered,
            f"Triggered: {triggered}",
        )
        assert result.passed

    def test_condition_fires_only_once(self, services, event_bus, scorer):
        """Condition soll nur einmal feuern (kein Spam)."""
        monitor = ConditionMonitor(event_bus)
        fire_count = 0

        def count_handler(event):
            nonlocal fire_count
            fire_count += 1

        event_bus.subscribe("test_event", count_handler)
        monitor.add_condition(
            name="test_condition",
            check_fn=lambda: True,
            event_type="test_event",
        )

        monitor.check_all()
        monitor.check_all()
        monitor.check_all()

        result = scorer.boolean_check(
            "fires_once",
            fire_count == 1,
            f"Event fired {fire_count} times (expected 1)",
        )
        assert result.passed

    def test_agent_response_to_trigger(self, agent, services, event_bus, scorer):
        """Agent antwortet sinnvoll auf getriggerte Bedingung."""
        agent.queue_response(AgentResponse(
            text='{"action_needed": true, "reason": "Neue Nachrichten auf WhatsApp", '
                 '"actions": [{"type": "summarize_messages", "params": {"channel": "whatsapp"}}]}',
            actions=[{"type": "summarize_messages", "params": {"channel": "whatsapp"}}],
        ))

        for i in range(10):
            services.messaging.add_incoming_message(f"User{i}", f"Hey, message {i}")

        context = AgentContext(
            environment_state=services.get_full_state(),
            available_tools=["summarize_messages", "send_message", "read_messages"],
        )

        response = agent.send(
            "Neue Bedingung erkannt: 10 ungelesene WhatsApp-Nachrichten. Was tun?",
            context,
        )

        result = scorer.boolean_check(
            "meaningful_trigger_response",
            len(response.actions) > 0,
            f"Agent vorschlug: {[a['type'] for a in response.actions]}",
        )
        assert result.passed
