#!/usr/bin/env python3
"""
Führt Tests einer bestimmten Kategorie aus.

Usage:
    python scripts/run_category.py proactivity
    python scripts/run_category.py safety -v
    python scripts/run_category.py quality --mock-only
    python scripts/run_category.py integration
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

CATEGORIES = {
    "proactivity": "Proaktivitäts-Tests (Heartbeat, Trigger, Scheduling)",
    "safety": "Safety & Guardrails (Boundaries, Injection, Leakage)",
    "quality": "Output-Qualität (Reasoning, Instructions, Completion)",
    "integration": "Integrations-Tests (Files, Messaging, API, Tools)",
}


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Category Test Runner")
    parser.add_argument(
        "category",
        choices=CATEGORIES.keys(),
        help="Test-Kategorie",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--mock-only", action="store_true")
    args = parser.parse_args()

    test_dir = ROOT / "tests" / f"test_{args.category}"
    if not test_dir.exists():
        print(f"FEHLER: Test-Verzeichnis nicht gefunden: {test_dir}")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"  {CATEGORIES[args.category]}")
    print(f"{'=' * 60}\n")

    cmd = [sys.executable, "-m", "pytest", str(test_dir)]
    if args.verbose:
        cmd.append("-v")
    cmd.extend(["--tb=short", "--timeout=300"])
    if args.mock_only:
        cmd.extend(["-k", "not live"])

    result = subprocess.run(cmd, cwd=ROOT)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
