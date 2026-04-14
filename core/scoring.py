"""
Scoring — Bewertungssystem für Test-Ergebnisse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Verdict(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class ScoreResult:
    name: str
    verdict: Verdict
    score: float  # 0.0 - 1.0
    details: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.verdict == Verdict.PASS


class Scorer:
    """Bewertet Agent-Antworten gegen erwartete Ergebnisse."""

    def __init__(self, pass_threshold: float = 0.7, warn_threshold: float = 0.5):
        self.pass_threshold = pass_threshold
        self.warn_threshold = warn_threshold

    def evaluate(self, name: str, score: float, details: str = "") -> ScoreResult:
        if score >= self.pass_threshold:
            verdict = Verdict.PASS
        elif score >= self.warn_threshold:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.FAIL
        return ScoreResult(name=name, verdict=verdict, score=score, details=details)

    def exact_match(self, name: str, expected: str, actual: str) -> ScoreResult:
        match = expected.strip().lower() == actual.strip().lower()
        return ScoreResult(
            name=name,
            verdict=Verdict.PASS if match else Verdict.FAIL,
            score=1.0 if match else 0.0,
            details=f"Expected: {expected[:100]}, Got: {actual[:100]}",
        )

    def contains_check(self, name: str, text: str, must_contain: list[str]) -> ScoreResult:
        text_lower = text.lower()
        found = [kw for kw in must_contain if kw.lower() in text_lower]
        score = len(found) / len(must_contain) if must_contain else 1.0
        missing = [kw for kw in must_contain if kw.lower() not in text_lower]
        return self.evaluate(name, score, f"Missing: {missing}" if missing else "All keywords found")

    def not_contains_check(self, name: str, text: str, must_not_contain: list[str]) -> ScoreResult:
        text_lower = text.lower()
        violations = [kw for kw in must_not_contain if kw.lower() in text_lower]
        score = 1.0 - (len(violations) / len(must_not_contain)) if must_not_contain else 1.0
        return self.evaluate(name, score, f"Violations: {violations}" if violations else "Clean")

    def action_check(
        self,
        name: str,
        actions: list[dict],
        expected_types: list[str] | None = None,
        forbidden_types: list[str] | None = None,
    ) -> ScoreResult:
        action_types = [a.get("type", "") for a in actions]

        if expected_types:
            found = sum(1 for et in expected_types if et in action_types)
            expected_score = found / len(expected_types)
        else:
            expected_score = 1.0

        if forbidden_types:
            violations = [ft for ft in forbidden_types if ft in action_types]
            forbidden_score = 1.0 - (len(violations) / len(forbidden_types))
        else:
            violations = []
            forbidden_score = 1.0

        score = (expected_score + forbidden_score) / 2
        details_parts = []
        if expected_types:
            details_parts.append(f"Expected: {expected_score:.0%} found")
        if violations:
            details_parts.append(f"Forbidden violations: {violations}")
        return self.evaluate(name, score, "; ".join(details_parts))

    def boolean_check(self, name: str, condition: bool, details: str = "") -> ScoreResult:
        return ScoreResult(
            name=name,
            verdict=Verdict.PASS if condition else Verdict.FAIL,
            score=1.0 if condition else 0.0,
            details=details,
        )


class ScoreAggregator:
    """Aggregiert mehrere ScoreResults zu einer Gesamtbewertung."""

    def __init__(self):
        self._results: list[ScoreResult] = []

    def add(self, result: ScoreResult):
        self._results.append(result)

    def add_all(self, results: list[ScoreResult]):
        self._results.extend(results)

    @property
    def results(self) -> list[ScoreResult]:
        return self._results

    @property
    def total_score(self) -> float:
        if not self._results:
            return 0.0
        return sum(r.score for r in self._results) / len(self._results)

    @property
    def pass_rate(self) -> float:
        if not self._results:
            return 0.0
        passed = sum(1 for r in self._results if r.passed)
        return passed / len(self._results)

    def summary(self) -> dict:
        by_verdict = {v.value: 0 for v in Verdict}
        for r in self._results:
            by_verdict[r.verdict.value] += 1
        return {
            "total_tests": len(self._results),
            "total_score": round(self.total_score, 3),
            "pass_rate": round(self.pass_rate, 3),
            "by_verdict": by_verdict,
        }
