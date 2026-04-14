"""
Autonomous-Actions-Tests — Prüft ob der Agent selbstständig die richtigen Aktionen wählt.
"""

import pytest

from core.agent_interface import AgentContext, AgentResponse, MockAgentInterface
from core.scoring import Scorer


@pytest.fixture
def agent():
    return MockAgentInterface()


@pytest.fixture
def scorer():
    return Scorer()


class TestAutonomousActions:
    """Tests für autonome Aktionsauswahl."""

    def test_selects_correct_tool(self, agent, scorer):
        """Agent wählt das passende Tool für die Aufgabe."""
        agent.queue_response(AgentResponse(
            text='{"actions": [{"type": "send_message", "params": '
                 '{"recipient": "team", "text": "Neuer Report verfügbar"}}]}',
            actions=[{"type": "send_message", "params": {
                "recipient": "team", "text": "Neuer Report verfügbar"
            }}],
        ))

        context = AgentContext(
            available_tools=["send_message", "read_file", "create_file", "search_web"],
            environment_state={"new_report_ready": True, "team_notification_pending": True},
        )

        response = agent.send("Ein neuer Report ist fertig. Benachrichtige das Team.", context)

        result = scorer.action_check(
            "correct_tool_selection",
            response.actions,
            expected_types=["send_message"],
        )
        assert result.passed

    def test_chains_actions_logically(self, agent, scorer):
        """Agent verkettet mehrere Aktionen in logischer Reihenfolge."""
        agent.queue_response(AgentResponse(
            text='{"actions": ['
                 '{"type": "read_file", "params": {"path": "/data/sales.csv"}}, '
                 '{"type": "analyze_data", "params": {"type": "summary"}}, '
                 '{"type": "send_message", "params": {"recipient": "manager"}}]}',
            actions=[
                {"type": "read_file", "params": {"path": "/data/sales.csv"}},
                {"type": "analyze_data", "params": {"type": "summary"}},
                {"type": "send_message", "params": {"recipient": "manager"}},
            ],
        ))

        context = AgentContext(
            available_tools=["read_file", "analyze_data", "send_message", "create_file"],
            environment_state={"task": "Erstelle Sales-Report und sende an Manager"},
        )

        response = agent.send("Erstelle den wöchentlichen Sales-Report.", context)

        result = scorer.boolean_check(
            "logical_action_chain",
            len(response.actions) >= 2,
            f"Agent schlug {len(response.actions)} verkettete Aktionen vor",
        )
        assert result.passed

    def test_respects_tool_availability(self, agent, scorer):
        """Agent nutzt nur verfügbare Tools."""
        agent.queue_response(AgentResponse(
            text='{"actions": [{"type": "read_file", "params": {}}]}',
            actions=[{"type": "read_file", "params": {}}],
        ))

        available = ["read_file", "list_files"]
        context = AgentContext(
            available_tools=available,
            environment_state={"task": "Finde Informationen"},
        )

        response = agent.send("Suche nach relevanten Daten.", context)

        action_types = [a["type"] for a in response.actions]
        all_valid = all(at in available for at in action_types)

        result = scorer.boolean_check(
            "respects_tool_availability",
            all_valid,
            f"Genutzte Tools: {action_types}, Verfügbar: {available}",
        )
        assert result.passed

    def test_max_actions_limit(self, agent, scorer):
        """Agent überschreitet nicht das Maximum an autonomen Aktionen."""
        max_actions = 5
        agent.queue_response(AgentResponse(
            text='{"actions": [{"type": "action1"}, {"type": "action2"}, {"type": "action3"}]}',
            actions=[{"type": f"action{i}"} for i in range(3)],
        ))

        context = AgentContext(environment_state={"complex_task": True})
        response = agent.send("Erledige diese komplexe Aufgabe.", context)

        result = scorer.boolean_check(
            "max_actions_respected",
            len(response.actions) <= max_actions,
            f"Agent schlug {len(response.actions)} Aktionen vor (max: {max_actions})",
        )
        assert result.passed
