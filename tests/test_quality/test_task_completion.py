"""
Task-Completion-Tests — Prüft ob der Agent Aufgaben vollständig erledigt.
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


class TestTaskCompletion:
    """Tests für Aufgaben-Vollständigkeit."""

    def test_completes_file_task(self, agent, scorer):
        """Agent schließt Datei-Aufgabe ab."""
        agent.queue_response(AgentResponse(
            text="Datei wurde erstellt und gespeichert.",
            actions=[
                {"type": "create_file", "params": {"path": "/reports/weekly.md", "content": "# Weekly Report"}},
            ],
        ))

        response = agent.send(
            "Erstelle eine Datei /reports/weekly.md mit einem Weekly Report.",
            AgentContext(available_tools=["create_file", "read_file"]),
        )

        has_create = any(a["type"] == "create_file" for a in response.actions)

        result = scorer.boolean_check(
            "completes_file_task",
            has_create,
            f"Aktionen: {[a['type'] for a in response.actions]}",
        )
        assert result.passed

    def test_completes_multi_step_task(self, agent, scorer):
        """Agent führt alle Schritte einer mehrstufigen Aufgabe aus."""
        agent.queue_response(AgentResponse(
            text="Daten gelesen, analysiert und Report erstellt.",
            actions=[
                {"type": "read_file", "params": {"path": "/data/sales.csv"}},
                {"type": "analyze", "params": {"type": "summary"}},
                {"type": "create_file", "params": {"path": "/reports/analysis.md"}},
            ],
        ))

        response = agent.send(
            "Lies die Sales-Daten, analysiere sie und erstelle einen Report.",
            AgentContext(available_tools=["read_file", "analyze", "create_file"]),
        )

        expected_steps = ["read_file", "analyze", "create_file"]
        actual_types = [a["type"] for a in response.actions]
        all_present = all(step in actual_types for step in expected_steps)

        result = scorer.boolean_check(
            "multi_step_complete",
            all_present,
            f"Erwartet: {expected_steps}, Erhalten: {actual_types}",
        )
        assert result.passed

    def test_handles_missing_prerequisites(self, agent, scorer):
        """Agent erkennt fehlende Voraussetzungen."""
        agent.queue_response(AgentResponse(
            text="Die angeforderte Datei existiert nicht. Soll ich sie erstellen?",
            actions=[],
            requested_confirmation=True,
        ))

        response = agent.send(
            "Aktualisiere die Datei /data/nonexistent.txt",
            AgentContext(environment_state={"file_exists": False}),
        )

        result = scorer.boolean_check(
            "handles_missing_prereqs",
            response.requested_confirmation or "nicht" in response.text.lower() or "exist" in response.text.lower(),
            "Agent erkannte fehlende Voraussetzung",
        )
        assert result.passed

    def test_reports_completion_status(self, agent, scorer):
        """Agent berichtet über den Abschluss-Status."""
        agent.queue_response(AgentResponse(
            text="Aufgabe abgeschlossen. 3 Dateien verarbeitet, 1 Report erstellt.",
            actions=[{"type": "create_file", "params": {"path": "/report.md"}}],
        ))

        response = agent.send(
            "Verarbeite alle CSV-Dateien und erstelle einen Bericht.",
            AgentContext(),
        )

        has_status = any(
            word in response.text.lower()
            for word in ["abgeschlossen", "erledigt", "fertig", "completed", "done"]
        )

        result = scorer.boolean_check(
            "reports_completion",
            has_status,
            "Agent berichtete über Abschluss-Status",
        )
        assert result.passed
