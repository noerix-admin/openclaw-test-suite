"""
Test Runner — Orchestriert Tests und generiert Reports.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

from .scoring import ScoreAggregator, ScoreResult, Verdict


@dataclass
class TestRunResult:
    category: str
    test_name: str
    score_result: ScoreResult
    duration_ms: float = 0.0
    error: str | None = None


class TestRunner:
    """Zentraler Test-Runner mit Reporting."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f.read())
        self._results: list[TestRunResult] = []
        self._console = Console()

    def record(self, category: str, test_name: str, result: ScoreResult, duration_ms: float = 0.0):
        self._results.append(TestRunResult(
            category=category,
            test_name=test_name,
            score_result=result,
            duration_ms=duration_ms,
        ))

    def record_error(self, category: str, test_name: str, error: str):
        self._results.append(TestRunResult(
            category=category,
            test_name=test_name,
            score_result=ScoreResult(test_name, Verdict.FAIL, 0.0, f"Error: {error}"),
            error=error,
        ))

    @property
    def results(self) -> list[TestRunResult]:
        return self._results

    def get_category_results(self, category: str) -> list[TestRunResult]:
        return [r for r in self._results if r.category == category]

    def get_aggregator(self, category: str | None = None) -> ScoreAggregator:
        agg = ScoreAggregator()
        results = self.get_category_results(category) if category else self._results
        for r in results:
            agg.add(r.score_result)
        return agg

    def print_summary(self):
        table = Table(title="Test-Ergebnisse", show_lines=True)
        table.add_column("Kategorie", style="bold")
        table.add_column("Test", style="cyan")
        table.add_column("Ergebnis", justify="center")
        table.add_column("Score", justify="right")
        table.add_column("Details")

        verdict_styles = {
            Verdict.PASS: "[green]PASS[/green]",
            Verdict.WARN: "[yellow]WARN[/yellow]",
            Verdict.FAIL: "[red]FAIL[/red]",
            Verdict.SKIP: "[dim]SKIP[/dim]",
        }

        for r in self._results:
            table.add_row(
                r.category,
                r.test_name,
                verdict_styles[r.score_result.verdict],
                f"{r.score_result.score:.2f}",
                r.score_result.details[:80],
            )

        self._console.print(table)

        agg = self.get_aggregator()
        summary = agg.summary()
        self._console.print(f"\n[bold]Gesamt:[/bold] {summary['total_tests']} Tests, "
                           f"Score: {summary['total_score']:.1%}, "
                           f"Pass-Rate: {summary['pass_rate']:.1%}")
        self._console.print(f"  PASS: {summary['by_verdict']['pass']}, "
                           f"WARN: {summary['by_verdict']['warn']}, "
                           f"FAIL: {summary['by_verdict']['fail']}, "
                           f"SKIP: {summary['by_verdict']['skip']}")

    def export_json(self, path: str | None = None) -> str:
        output_dir = self.config.get("reporting", {}).get("output_dir", "reports")
        if path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            path = f"{output_dir}/results_{timestamp}.json"

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "summary": self.get_aggregator().summary(),
            "categories": {},
            "results": [],
        }

        categories = set(r.category for r in self._results)
        for cat in sorted(categories):
            data["categories"][cat] = self.get_aggregator(cat).summary()

        for r in self._results:
            data["results"].append({
                "category": r.category,
                "test_name": r.test_name,
                "verdict": r.score_result.verdict.value,
                "score": r.score_result.score,
                "details": r.score_result.details,
                "duration_ms": r.duration_ms,
                "error": r.error,
            })

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return path
