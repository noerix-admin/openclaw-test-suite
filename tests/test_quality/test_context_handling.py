"""
Context-Handling-Tests — Prüft Kontextverständnis über mehrere Turns.
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


class TestContextHandling:
    """Tests für Multi-Turn-Kontextverständnis."""

    def test_remembers_previous_context(self, agent, scorer):
        """Agent erinnert sich an vorherige Konversation."""
        agent.queue_response(AgentResponse(text="Die Hauptstadt ist Berlin.", actions=[]))
        agent.queue_response(AgentResponse(
            text="Berlin hat etwa 3,7 Millionen Einwohner.",
            actions=[],
        ))

        ctx = AgentContext(conversation_history=[])

        agent.send("Was ist die Hauptstadt von Deutschland?", ctx)
        ctx.conversation_history.append({"role": "user", "content": "Was ist die Hauptstadt von Deutschland?"})
        ctx.conversation_history.append({"role": "assistant", "content": "Die Hauptstadt ist Berlin."})

        response = agent.send("Wie viele Einwohner hat sie?", ctx)

        result = scorer.contains_check(
            "remembers_context",
            response.text,
            ["berlin", "million"],
        )
        assert result.passed

    def test_handles_topic_switch(self, agent, scorer):
        """Agent handhabt Themenwechsel korrekt."""
        agent.queue_response(AgentResponse(
            text="Das Wetter morgen wird sonnig bei 22°C.",
            actions=[],
        ))

        ctx = AgentContext(conversation_history=[
            {"role": "user", "content": "Erzähl mir über Python."},
            {"role": "assistant", "content": "Python ist eine Programmiersprache."},
        ])

        response = agent.send("Wie wird das Wetter morgen?", ctx)

        has_weather = any(
            w in response.text.lower()
            for w in ["wetter", "sonnig", "regen", "temperatur", "°c", "weather", "22"]
        )

        result = scorer.boolean_check(
            "handles_topic_switch",
            has_weather,
            "Agent wechselte zum neuen Thema",
        )
        assert result.passed

    def test_uses_environment_context(self, agent, scorer):
        """Agent nutzt Umgebungskontext für bessere Antworten."""
        agent.queue_response(AgentResponse(
            text="Du hast 5 ungelesene E-Mails, davon 2 mit hoher Priorität von CEO und CTO.",
            actions=[],
        ))

        ctx = AgentContext(
            environment_state={
                "email": {"unread_count": 5, "high_priority_count": 2},
                "calendar": {"next_meeting": "14:00 Team-Standup"},
            },
        )

        response = agent.send("Was steht an?", ctx)

        result = scorer.contains_check(
            "uses_env_context",
            response.text,
            ["5", "mail"],
        )
        assert result.passed

    def test_long_conversation_coherence(self, agent, scorer):
        """Agent bleibt über lange Konversation kohärent."""
        history = []
        topics = [
            ("Erstelle eine Einkaufsliste", "Einkaufsliste: Milch, Brot, Eier, Käse"),
            ("Füge Tomaten hinzu", "Aktualisiert: Milch, Brot, Eier, Käse, Tomaten"),
            ("Entferne Käse", "Aktualisiert: Milch, Brot, Eier, Tomaten"),
            ("Was steht auf der Liste?", "Aktuelle Liste: Milch, Brot, Eier, Tomaten"),
        ]

        for user_msg, assistant_msg in topics:
            agent.queue_response(AgentResponse(text=assistant_msg, actions=[]))

        final_response = None
        ctx = AgentContext(conversation_history=history)

        for user_msg, assistant_msg in topics:
            final_response = agent.send(user_msg, ctx)
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": assistant_msg})

        result = scorer.not_contains_check(
            "long_convo_coherence",
            final_response.text,
            ["käse"],  # Käse wurde entfernt
        )
        assert result.passed
