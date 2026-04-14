"""
Heartbeat-Tests — Prüft ob der Agent bei periodischem Wecken korrekt reagiert.

OpenClaw-Besonderheit: Der Agent wird regelmäßig geweckt und entscheidet
selbstständig, ob eine Aktion nötig ist.
"""

import json
import pytest

from core.agent_interface import AgentContext, AgentResponse, MockAgentInterface
from core.event_bus import HeartbeatSimulator
from core.scoring import Scorer


@pytest.fixture
def agent():
    return MockAgentInterface()


@pytest.fixture
def scorer():
    return Scorer()


@pytest.fixture
def heartbeat():
    return HeartbeatSimulator(interval_seconds=10)


class TestHeartbeatBasic:
    """Grundlegende Heartbeat-Funktionalität."""

    def test_agent_responds_to_heartbeat(self, agent, heartbeat, scorer):
        """Agent muss auf jeden Heartbeat antworten (nicht hängen)."""
        agent.queue_response(AgentResponse(
            text='{"action_needed": false, "reason": "Alles in Ordnung"}',
            actions=[],
        ))

        context = AgentContext(
            system_prompt="Du bist ein proaktiver Assistent.",
            environment_state={"inbox_count": 0, "pending_tasks": 0},
        )

        heartbeat.beat()
        response = agent.heartbeat(context)
        heartbeat.record_response(response)

        result = scorer.boolean_check(
            "heartbeat_response",
            response.text != "",
            "Agent hat auf Heartbeat geantwortet",
        )
        assert result.passed

    def test_no_action_when_idle(self, agent, heartbeat, scorer):
        """Agent soll KEINE Aktion ausführen wenn nichts zu tun ist."""
        agent.queue_response(AgentResponse(
            text='{"action_needed": false, "reason": "Keine ausstehenden Aufgaben"}',
            actions=[],
        ))

        context = AgentContext(
            environment_state={"inbox_count": 0, "pending_tasks": 0, "alerts": []},
        )

        response = agent.heartbeat(context)

        result = scorer.boolean_check(
            "no_action_when_idle",
            len(response.actions) == 0,
            f"Agent hat {len(response.actions)} Aktionen ausgeführt (erwartet: 0)",
        )
        assert result.passed

    def test_action_when_needed(self, agent, scorer):
        """Agent soll Aktion ausführen wenn Bedingung erfüllt."""
        agent.queue_response(AgentResponse(
            text='{"action_needed": true, "reason": "50 ungelesene Nachrichten", '
                 '"actions": [{"type": "check_inbox", "params": {}}]}',
            actions=[{"type": "check_inbox", "params": {}}],
        ))

        context = AgentContext(
            environment_state={"inbox_count": 50, "pending_tasks": 3},
        )

        response = agent.heartbeat(context)

        result = scorer.boolean_check(
            "action_when_needed",
            len(response.actions) > 0,
            f"Agent hat {len(response.actions)} Aktionen vorgeschlagen",
        )
        assert result.passed

    def test_multiple_heartbeats_consistent(self, agent, heartbeat, scorer):
        """Agent soll über mehrere Heartbeats konsistent reagieren."""
        # 5 Heartbeats: 3x idle, 2x Aktion nötig
        responses = [
            AgentResponse(text='{"action_needed": false}', actions=[]),
            AgentResponse(text='{"action_needed": false}', actions=[]),
            AgentResponse(text='{"action_needed": true}',
                         actions=[{"type": "notify", "params": {}}]),
            AgentResponse(text='{"action_needed": false}', actions=[]),
            AgentResponse(text='{"action_needed": true}',
                         actions=[{"type": "summarize", "params": {}}]),
        ]
        agent.queue_responses(responses)

        states = [
            {"inbox_count": 0},
            {"inbox_count": 2},
            {"inbox_count": 25},
            {"inbox_count": 0},
            {"inbox_count": 50},
        ]

        for state in states:
            ctx = AgentContext(environment_state=state)
            heartbeat.beat()
            resp = agent.heartbeat(ctx)
            heartbeat.record_response(resp)

        action_beats = heartbeat.get_action_beats()
        result = scorer.boolean_check(
            "consistent_heartbeats",
            len(action_beats) == 2,
            f"Aktionen bei Beats {action_beats} (erwartet: 2 Aktions-Beats)",
        )
        assert result.passed


class TestHeartbeatDecisionQuality:
    """Qualität der Heartbeat-Entscheidungen."""

    def test_prioritizes_urgent_events(self, agent, scorer):
        """Agent soll dringende Events priorisieren."""
        agent.queue_response(AgentResponse(
            text=json.dumps({
                "action_needed": True,
                "reason": "Dringende E-Mail von CEO",
                "actions": [
                    {"type": "notify_user", "params": {"priority": "high"}},
                    {"type": "draft_reply", "params": {}},
                ],
            }),
            actions=[
                {"type": "notify_user", "params": {"priority": "high"}},
                {"type": "draft_reply", "params": {}},
            ],
        ))

        context = AgentContext(
            environment_state={
                "inbox_count": 5,
                "high_priority_emails": 1,
                "email_subjects": ["Q4 Budget - DRINGEND"],
                "pending_tasks": 2,
            },
        )

        response = agent.heartbeat(context)
        action_types = [a["type"] for a in response.actions]

        result = scorer.boolean_check(
            "prioritizes_urgent",
            "notify_user" in action_types,
            f"Aktionen: {action_types}",
        )
        assert result.passed

    def test_does_not_spam_actions(self, agent, heartbeat, scorer):
        """Agent soll nicht bei jedem Heartbeat Aktionen spammen."""
        # 10 Heartbeats mit minimalem State
        for _ in range(10):
            agent.queue_response(AgentResponse(
                text='{"action_needed": false}', actions=[],
            ))

        action_count = 0
        for _ in range(10):
            ctx = AgentContext(environment_state={"inbox_count": 1})
            heartbeat.beat()
            resp = agent.heartbeat(ctx)
            heartbeat.record_response(resp)
            action_count += len(resp.actions)

        result = scorer.boolean_check(
            "no_action_spam",
            action_count <= 3,
            f"Agent führte {action_count} Aktionen in 10 Beats aus (max 3 erlaubt)",
        )
        assert result.passed
