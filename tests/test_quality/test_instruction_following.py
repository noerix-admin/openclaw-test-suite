"""
Instruction-Following-Tests — Prüft ob der Agent Anweisungen präzise befolgt.
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


class TestInstructionFollowing:
    """Tests für präzises Befolgen von Anweisungen."""

    def test_follows_format_instruction(self, agent, scorer):
        """Agent befolgt Format-Anweisungen."""
        agent.queue_response(AgentResponse(
            text="- Python\n- JavaScript\n- Rust",
            actions=[],
        ))

        response = agent.send(
            "Nenne 3 Programmiersprachen. Antworte NUR als Aufzählung mit Bindestrich.",
            AgentContext(),
        )

        has_bullets = response.text.count("-") >= 3 or response.text.count("•") >= 3

        result = scorer.boolean_check(
            "follows_format",
            has_bullets,
            f"Output format: {'Aufzählung erkannt' if has_bullets else 'Kein Aufzählungsformat'}",
        )
        assert result.passed

    def test_respects_language_constraint(self, agent, scorer):
        """Agent antwortet in der angeforderten Sprache."""
        agent.queue_response(AgentResponse(
            text="Berlin ist die Hauptstadt von Deutschland.",
            actions=[],
        ))

        response = agent.send(
            "Antworte auf Deutsch: Was ist die Hauptstadt von Deutschland?",
            AgentContext(),
        )

        result = scorer.contains_check(
            "german_response",
            response.text,
            ["berlin"],
        )
        assert result.passed

    def test_respects_length_constraint(self, agent, scorer):
        """Agent hält sich an Längenbeschränkungen."""
        short_text = "KI lernt aus Daten."
        agent.queue_response(AgentResponse(text=short_text, actions=[]))

        response = agent.send(
            "Erkläre KI in maximal einem Satz.",
            AgentContext(),
        )

        sentence_count = response.text.count(".") + response.text.count("!") + response.text.count("?")

        result = scorer.boolean_check(
            "respects_length",
            sentence_count <= 2,
            f"Sätze: {sentence_count} (max 1-2 erwartet)",
        )
        assert result.passed

    def test_follows_negative_instruction(self, agent, scorer):
        """Agent befolgt 'Tue X NICHT' Anweisungen."""
        agent.queue_response(AgentResponse(
            text="Python ist eine interpretierte Programmiersprache.",
            actions=[],
        ))

        response = agent.send(
            "Erkläre Python. Erwähne NICHT Java oder C++.",
            AgentContext(),
        )

        result = scorer.not_contains_check(
            "respects_negative",
            response.text,
            ["java", "c++"],
        )
        assert result.passed

    def test_follows_multi_part_instruction(self, agent, scorer):
        """Agent befolgt mehrteilige Anweisungen vollständig."""
        agent.queue_response(AgentResponse(
            text="## Zusammenfassung\nPython ist beliebt.\n\n"
                 "## Vorteile\n- Einfache Syntax\n- Große Community\n\n"
                 "## Nachteile\n- Langsamer als C++",
            actions=[],
        ))

        response = agent.send(
            "Schreibe über Python: "
            "1) Eine kurze Zusammenfassung, "
            "2) Vorteile als Liste, "
            "3) Nachteile als Liste.",
            AgentContext(),
        )

        has_structure = (
            ("zusammenfassung" in response.text.lower() or "summary" in response.text.lower())
            and ("vorteil" in response.text.lower() or "advantage" in response.text.lower())
        )

        result = scorer.boolean_check(
            "multi_part_followed",
            has_structure,
            "Mehrteilige Anweisung erkannt und befolgt",
        )
        assert result.passed
