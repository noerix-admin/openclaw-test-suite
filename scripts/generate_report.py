#!/usr/bin/env python3
"""
Generiert einen HTML-Report aus pytest-Ergebnissen.

Usage:
    python scripts/generate_report.py                    # Letzten Report anzeigen
    python scripts/generate_report.py --run              # Tests ausführen + Report
    python scripts/generate_report.py --input result.json # Aus JSON-Datei
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from jinja2 import Template

ROOT = Path(__file__).parent.parent

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Test Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #0f172a; color: #e2e8f0; padding: 2rem; }
        .header { text-align: center; margin-bottom: 2rem; }
        .header h1 { font-size: 2rem; color: #38bdf8; }
        .header .timestamp { color: #64748b; margin-top: 0.5rem; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                   gap: 1rem; margin-bottom: 2rem; }
        .card { background: #1e293b; border-radius: 12px; padding: 1.5rem; text-align: center; }
        .card .value { font-size: 2.5rem; font-weight: bold; }
        .card .label { color: #94a3b8; margin-top: 0.5rem; }
        .pass .value { color: #4ade80; }
        .warn .value { color: #fbbf24; }
        .fail .value { color: #f87171; }
        .score .value { color: #38bdf8; }
        .category { background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; }
        .category h2 { color: #38bdf8; margin-bottom: 1rem; border-bottom: 1px solid #334155;
                       padding-bottom: 0.5rem; }
        .test-row { display: flex; align-items: center; padding: 0.5rem 0;
                    border-bottom: 1px solid #1e293b; }
        .test-name { flex: 1; }
        .badge { padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem;
                 font-weight: 600; text-transform: uppercase; }
        .badge-pass { background: #064e3b; color: #4ade80; }
        .badge-warn { background: #451a03; color: #fbbf24; }
        .badge-fail { background: #450a0a; color: #f87171; }
        .badge-skip { background: #1e293b; color: #64748b; }
        .test-score { width: 80px; text-align: right; margin-right: 1rem; }
        .test-details { color: #64748b; font-size: 0.85rem; margin-left: 1rem; flex: 2; }
        .progress { height: 8px; background: #334155; border-radius: 4px; margin-top: 0.5rem; overflow: hidden; }
        .progress-bar { height: 100%; border-radius: 4px; transition: width 0.5s; }
        .progress-pass { background: #4ade80; }
        .progress-warn { background: #fbbf24; }
        .progress-fail { background: #f87171; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.75rem; text-align: left; }
        th { color: #94a3b8; font-weight: 500; }
    </style>
</head>
<body>
    <div class="header">
        <h1>OpenClaw Agent Test Report</h1>
        <div class="timestamp">{{ timestamp }}</div>
    </div>

    <div class="summary">
        <div class="card score">
            <div class="value">{{ "%.0f"|format(summary.total_score * 100) }}%</div>
            <div class="label">Gesamtscore</div>
        </div>
        <div class="card pass">
            <div class="value">{{ summary.by_verdict.pass }}</div>
            <div class="label">Bestanden</div>
        </div>
        <div class="card warn">
            <div class="value">{{ summary.by_verdict.warn }}</div>
            <div class="label">Warnung</div>
        </div>
        <div class="card fail">
            <div class="value">{{ summary.by_verdict.fail }}</div>
            <div class="label">Fehlgeschlagen</div>
        </div>
    </div>

    {% for cat_name, cat_data in categories.items() %}
    <div class="category">
        <h2>{{ cat_name | title }} (Score: {{ "%.0f"|format(cat_data.total_score * 100) }}%)</h2>
        <div class="progress">
            <div class="progress-bar progress-pass" style="width: {{ "%.0f"|format(cat_data.pass_rate * 100) }}%"></div>
        </div>
        <table>
            <thead>
                <tr><th>Test</th><th>Ergebnis</th><th>Score</th><th>Details</th></tr>
            </thead>
            <tbody>
                {% for result in results if result.category == cat_name %}
                <tr>
                    <td>{{ result.test_name }}</td>
                    <td><span class="badge badge-{{ result.verdict }}">{{ result.verdict }}</span></td>
                    <td>{{ "%.2f"|format(result.score) }}</td>
                    <td class="test-details">{{ result.details[:100] }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endfor %}
</body>
</html>"""


def run_tests_with_json():
    """Führt Tests aus und sammelt Ergebnisse als JSON."""
    json_path = ROOT / "reports" / f"results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    cmd = [
        sys.executable, "-m", "pytest", "tests/",
        f"--junit-xml={ROOT / 'reports' / 'junit.xml'}",
        "-v", "--tb=short", "--timeout=300",
    ]
    subprocess.run(cmd, cwd=ROOT)
    return json_path


def generate_html(data: dict, output_path: Path):
    """Generiert HTML-Report aus JSON-Daten."""
    template = Template(HTML_TEMPLATE)
    html = template.render(
        timestamp=data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
        summary=data.get("summary", {}),
        categories=data.get("categories", {}),
        results=data.get("results", []),
    )
    output_path.write_text(html, encoding="utf-8")
    return output_path


def create_sample_report():
    """Erstellt einen Beispiel-Report für Demo-Zwecke."""
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_tests": 0,
            "total_score": 0.0,
            "pass_rate": 0.0,
            "by_verdict": {"pass": 0, "warn": 0, "fail": 0, "skip": 0},
        },
        "categories": {},
        "results": [],
    }
    return data


def main():
    parser = argparse.ArgumentParser(description="OpenClaw HTML Report Generator")
    parser.add_argument("--run", action="store_true", help="Tests ausführen + Report generieren")
    parser.add_argument("--input", help="JSON-Input-Datei")
    parser.add_argument("--output", help="HTML-Output-Pfad")
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else ROOT / "reports" / f"report_{time.strftime('%Y%m%d_%H%M%S')}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    elif args.run:
        run_tests_with_json()
        json_files = sorted((ROOT / "reports").glob("results_*.json"), reverse=True)
        if json_files:
            with open(json_files[0]) as f:
                data = json.load(f)
        else:
            print("Keine JSON-Ergebnisse gefunden. Erstelle leeren Report.")
            data = create_sample_report()
    else:
        json_files = sorted((ROOT / "reports").glob("results_*.json"), reverse=True)
        if json_files:
            with open(json_files[0]) as f:
                data = json.load(f)
        else:
            print("Keine Ergebnisse gefunden. Verwende --run um Tests auszuführen.")
            data = create_sample_report()

    report_path = generate_html(data, output_path)
    print(f"\nReport generiert: {report_path}")


if __name__ == "__main__":
    main()
