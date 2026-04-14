"""
Recurring-Tasks-Tests — Prüft ob geplante wiederkehrende Aufgaben korrekt ausgeführt werden.
"""

import time
import pytest

from core.agent_interface import AgentContext, AgentResponse, MockAgentInterface
from core.scoring import Scorer


@pytest.fixture
def agent():
    return MockAgentInterface()


@pytest.fixture
def scorer():
    return Scorer()


class TestRecurringTasks:
    """Tests für wiederkehrende Aufgaben."""

    def test_daily_summary_task(self, agent, scorer):
        """Agent erstellt tägliche Zusammenfassung wenn geplant."""
        agent.queue_response(AgentResponse(
            text='{"action_needed": true, "reason": "Tägliche Zusammenfassung fällig", '
                 '"actions": [{"type": "create_summary", "params": {"period": "daily"}}]}',
            actions=[{"type": "create_summary", "params": {"period": "daily"}}],
        ))

        context = AgentContext(
            environment_state={
                "scheduled_tasks": [
                    {"name": "daily_summary", "schedule": "09:00", "last_run": "2026-04-12T09:00:00"},
                ],
                "current_time": "2026-04-13T09:00:00",
            },
        )

        response = agent.heartbeat(context)
        action_types = [a["type"] for a in response.actions]

        result = scorer.boolean_check(
            "daily_summary_executed",
            "create_summary" in action_types,
            f"Actions: {action_types}",
        )
        assert result.passed

    def test_skip_if_not_due(self, agent, scorer):
        """Agent überspringt Aufgabe wenn noch nicht fällig."""
        agent.queue_response(AgentResponse(
            text='{"action_needed": false, "reason": "Nächste Ausführung erst morgen"}',
            actions=[],
        ))

        context = AgentContext(
            environment_state={
                "scheduled_tasks": [
                    {"name": "daily_summary", "schedule": "09:00",
                     "last_run": "2026-04-13T09:00:00"},
                ],
                "current_time": "2026-04-13T14:00:00",
            },
        )

        response = agent.heartbeat(context)

        result = scorer.boolean_check(
            "skip_not_due",
            len(response.actions) == 0,
            "Agent hat korrekt keine Aktion ausgeführt",
        )
        assert result.passed

    def test_multiple_tasks_prioritized(self, agent, scorer):
        """Mehrere fällige Tasks werden nach Priorität ausgeführt."""
        agent.queue_response(AgentResponse(
            text='{"action_needed": true, "actions": ['
                 '{"type": "check_security", "params": {"priority": "high"}}, '
                 '{"type": "create_summary", "params": {"priority": "normal"}}]}',
            actions=[
                {"type": "check_security", "params": {"priority": "high"}},
                {"type": "create_summary", "params": {"priority": "normal"}},
            ],
        ))

        context = AgentContext(
            environment_state={
                "scheduled_tasks": [
                    {"name": "security_check", "schedule": "08:00", "priority": "high"},
                    {"name": "daily_summary", "schedule": "09:00", "priority": "normal"},
                ],
                "current_time": "2026-04-13T09:30:00",
            },
        )

        response = agent.heartbeat(context)
        action_types = [a["type"] for a in response.actions]

        result = scorer.boolean_check(
            "multiple_tasks_handled",
            len(response.actions) >= 2,
            f"Agent führte {len(response.actions)} Tasks aus: {action_types}",
        )
        assert result.passed
