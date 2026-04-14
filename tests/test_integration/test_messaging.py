"""
Messaging-Tests — Prüft Messaging-Integrationen (WhatsApp/Discord Mock).
"""

import pytest

from core.agent_interface import AgentContext, AgentResponse, MockAgentInterface
from core.mock_services import MockServiceRegistry
from core.scoring import Scorer


@pytest.fixture
def agent():
    return MockAgentInterface()


@pytest.fixture
def services():
    return MockServiceRegistry()


@pytest.fixture
def scorer():
    return Scorer()


class TestMessaging:
    """Tests für Messaging-Integrationen."""

    def test_receives_messages(self, services, scorer):
        """Mock empfängt eingehende Nachrichten."""
        services.messaging.add_incoming_message("Alice", "Hallo!")
        services.messaging.add_incoming_message("Bob", "Meeting um 14 Uhr?")

        state = services.messaging.get_state()

        result = scorer.boolean_check(
            "receives_messages",
            state["unread_count"] == 2,
            f"Ungelesene Nachrichten: {state['unread_count']}",
        )
        assert result.passed

    def test_sends_message(self, services, scorer):
        """Mock sendet Nachrichten und protokolliert sie."""
        services.messaging.send_message("Alice", "Ja, 14 Uhr passt!")

        result = scorer.boolean_check(
            "sends_message",
            len(services.messaging.sent) == 1,
            f"Gesendete Nachrichten: {len(services.messaging.sent)}",
        )
        assert result.passed
        assert services.messaging.sent[0]["recipient"] == "Alice"

    def test_discord_separate_from_whatsapp(self, services, scorer):
        """Discord und WhatsApp sind getrennte Services."""
        services.messaging.add_incoming_message("Alice", "WhatsApp Nachricht")
        services.discord.add_incoming_message("Bob", "Discord Nachricht")

        result = scorer.boolean_check(
            "services_separated",
            services.messaging.get_unread_count() == 1
            and services.discord.get_unread_count() == 1,
            "Nachrichten korrekt auf Services verteilt",
        )
        assert result.passed

    def test_agent_responds_to_message(self, agent, services, scorer):
        """Agent verarbeitet eingehende Nachrichten und antwortet."""
        services.messaging.add_incoming_message("Team", "Stand-up in 5 Minuten")

        agent.queue_response(AgentResponse(
            text="Erinnere den User an das Stand-up Meeting.",
            actions=[{"type": "notify_user", "params": {"message": "Stand-up in 5 Min!"}}],
        ))

        context = AgentContext(environment_state=services.get_full_state())
        response = agent.send("Neue Nachricht eingegangen. Was tun?", context)

        result = scorer.boolean_check(
            "responds_to_message",
            len(response.actions) > 0,
            f"Agent-Aktionen: {[a['type'] for a in response.actions]}",
        )
        assert result.passed

    def test_action_log_complete(self, services, scorer):
        """Alle Messaging-Aktionen werden geloggt."""
        services.messaging.send_message("A", "Test 1")
        services.messaging.send_message("B", "Test 2")
        services.discord.send_message("C", "Test 3")

        all_logs = services.get_all_action_logs()

        result = scorer.boolean_check(
            "action_log_complete",
            len(all_logs) == 3,
            f"Geloggte Aktionen: {len(all_logs)}",
        )
        assert result.passed
