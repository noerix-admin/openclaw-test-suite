"""
Reasoning-Tests — Prüft die Reasoning-Fähigkeit des Modells.
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


class TestReasoning:
    """Tests für logisches Denken."""

    def test_simple_math_reasoning(self, agent, scorer):
        """Agent löst einfache Mathe-Aufgaben korrekt."""
        agent.queue_response(AgentResponse(
            text="Die Antwort ist 42. 17 + 25 = 42.",
            actions=[],
        ))

        response = agent.send("Was ist 17 + 25?", AgentContext())

        result = scorer.contains_check(
            "simple_math",
            response.text,
            ["42"],
        )
        assert result.passed

    def test_logical_deduction(self, agent, scorer):
        """Agent kann logische Schlüsse ziehen."""
        agent.queue_response(AgentResponse(
            text="Wenn alle Hunde Tiere sind und Rex ein Hund ist, "
                 "dann ist Rex ein Tier. Schlussfolgerung: Rex ist ein Tier.",
            actions=[],
        ))

        response = agent.send(
            "Alle Hunde sind Tiere. Rex ist ein Hund. Was ist Rex?",
            AgentContext(),
        )

        result = scorer.contains_check(
            "logical_deduction",
            response.text,
            ["tier"],
        )
        assert result.passed

    def test_multi_step_problem(self, agent, scorer):
        """Agent löst mehrstufige Probleme."""
        agent.queue_response(AgentResponse(
            text="Schritt 1: Preis pro Apfel = 3€/3 = 1€. "
                 "Schritt 2: 7 Äpfel kosten 7 × 1€ = 7€.",
            actions=[],
        ))

        response = agent.send(
            "3 Äpfel kosten 3 Euro. Wie viel kosten 7 Äpfel?",
            AgentContext(),
        )

        result = scorer.contains_check(
            "multi_step",
            response.text,
            ["7"],
        )
        assert result.passed

    def test_causal_reasoning(self, agent, scorer):
        """Agent versteht Kausalzusammenhänge."""
        agent.queue_response(AgentResponse(
            text="Die Straße ist nass, weil es geregnet hat. "
                 "Das ist die wahrscheinlichste Ursache.",
            actions=[],
        ))

        response = agent.send(
            "Die Straße ist nass. Was ist die wahrscheinlichste Ursache?",
            AgentContext(),
        )

        result = scorer.contains_check(
            "causal_reasoning",
            response.text,
            ["geregnet"],
        )
        assert result.passed

    def test_provides_reasoning_chain(self, agent, scorer):
        """Agent zeigt seinen Denkprozess."""
        agent.queue_response(AgentResponse(
            text="Ich gehe Schritt für Schritt vor:\n"
                 "1. Zuerst prüfe ich...\n"
                 "2. Dann berechne ich...\n"
                 "3. Daraus folgt...",
            reasoning="Step-by-step analysis",
        ))

        response = agent.send(
            "Erkläre Schritt für Schritt, wie du zu deiner Antwort kommst.",
            AgentContext(),
        )

        has_steps = any(
            marker in response.text.lower()
            for marker in ["schritt", "step", "1.", "erstens", "zuerst"]
        )

        result = scorer.boolean_check(
            "shows_reasoning",
            has_steps,
            "Agent zeigt Reasoning-Schritte",
        )
        assert result.passed
