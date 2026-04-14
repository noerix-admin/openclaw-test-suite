"""
Tool-Usage-Tests — Prüft ob der Agent die richtigen Tools auswählt.
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


TOOL_SCENARIOS = [
    {
        "task": "Lies die Datei /data/report.csv",
        "available_tools": ["read_file", "write_file", "send_message", "search_web"],
        "expected_tool": "read_file",
    },
    {
        "task": "Sende eine Nachricht an das Team",
        "available_tools": ["read_file", "write_file", "send_message", "search_web"],
        "expected_tool": "send_message",
    },
    {
        "task": "Erstelle eine neue Datei mit dem Bericht",
        "available_tools": ["read_file", "write_file", "send_message", "search_web"],
        "expected_tool": "write_file",
    },
    {
        "task": "Suche nach aktuellen Nachrichten über KI",
        "available_tools": ["read_file", "write_file", "send_message", "search_web"],
        "expected_tool": "search_web",
    },
]


class TestToolUsage:
    """Tests für korrekte Tool-Auswahl."""

    @pytest.mark.parametrize("scenario", TOOL_SCENARIOS, ids=lambda s: s["expected_tool"])
    def test_selects_correct_tool(self, agent, scorer, scenario):
        """Agent wählt das passende Tool für die Aufgabe."""
        agent.queue_response(AgentResponse(
            text=f"Verwende {scenario['expected_tool']}.",
            actions=[{"type": scenario["expected_tool"], "params": {}}],
        ))

        context = AgentContext(available_tools=scenario["available_tools"])
        response = agent.send(scenario["task"], context)

        action_types = [a["type"] for a in response.actions]

        result = scorer.boolean_check(
            f"selects_{scenario['expected_tool']}",
            scenario["expected_tool"] in action_types,
            f"Task: {scenario['task']}, Tool: {action_types}",
        )
        assert result.passed

    def test_no_tool_when_unnecessary(self, agent, scorer):
        """Agent nutzt kein Tool wenn keines nötig ist."""
        agent.queue_response(AgentResponse(
            text="Python ist eine interpretierte Programmiersprache von Guido van Rossum.",
            actions=[],
        ))

        context = AgentContext(
            available_tools=["read_file", "write_file", "send_message"],
        )

        response = agent.send("Was ist Python?", context)

        result = scorer.boolean_check(
            "no_unnecessary_tool",
            len(response.actions) == 0,
            f"Agent nutzte {len(response.actions)} Tools (erwartet: 0)",
        )
        assert result.passed

    def test_tool_params_complete(self, agent, scorer):
        """Tool-Aufrufe enthalten vollständige Parameter."""
        agent.queue_response(AgentResponse(
            text="Datei wird gelesen.",
            actions=[{"type": "read_file", "params": {"path": "/data/test.csv"}}],
        ))

        response = agent.send(
            "Lies /data/test.csv",
            AgentContext(available_tools=["read_file"]),
        )

        if response.actions:
            action = response.actions[0]
            has_params = "params" in action and action["params"]
            result = scorer.boolean_check(
                "tool_params_complete",
                has_params,
                f"Params: {action.get('params', {})}",
            )
        else:
            result = scorer.boolean_check("tool_params_complete", False, "Keine Aktionen")

        assert result.passed
