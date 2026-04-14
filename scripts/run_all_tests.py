#!/usr/bin/env python3
"""
Führt alle Tests aus und generiert einen Report.

Usage:
    python scripts/run_all_tests.py              # Alle Tests
    python scripts/run_all_tests.py --dry-run     # Nur Konfiguration prüfen
    python scripts/run_all_tests.py --mock-only   # Nur Mock-Tests (ohne Modell)
    python scripts/run_all_tests.py -v            # Verbose Output
"""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent


def check_config():
    """Prüft ob Konfiguration vorhanden und gültig ist."""
    import yaml

    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        print("FEHLER: config.yaml nicht gefunden!")
        print(f"Erwartet: {config_path}")
        return False

    with open(config_path) as f:
        config = yaml.safe_load(f.read())

    print("Konfiguration geladen:")
    print(f"  Modell-Pfad: {config['model']['path']}")
    print(f"  GPU-Layers: {config['model'].get('gpu_layers', 0)}")
    print(f"  Context-Size: {config['model'].get('context_size', 4096)}")
    print(f"  Test-Timeout: {config['timeouts']['test_timeout_seconds']}s")
    return True


def check_model():
    """Prüft ob das GGUF-Modell verfügbar ist."""
    import os

    import yaml
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    with open(ROOT / "config.yaml") as f:
        config = yaml.safe_load(f.read())

    model_path = config["model"]["path"]
    if model_path.startswith("${") and model_path.endswith("}"):
        env_var = model_path[2:-1]
        model_path = os.environ.get(env_var, "")

    if not model_path or not Path(model_path).exists():
        print(f"WARNUNG: Modell nicht gefunden: {model_path}")
        print("Mock-Tests funktionieren trotzdem.")
        return False

    size_gb = Path(model_path).stat().st_size / (1024**3)
    print(f"Modell gefunden: {model_path} ({size_gb:.1f} GB)")
    return True


def run_tests(categories=None, verbose=False, mock_only=False):
    """Führt pytest aus."""
    cmd = [sys.executable, "-m", "pytest"]

    if categories:
        for cat in categories:
            cmd.append(f"tests/test_{cat}/")
    else:
        cmd.append("tests/")

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    cmd.extend(["--tb=short", f"--timeout=300"])

    if mock_only:
        cmd.extend(["-k", "not live"])

    print(f"\nAusführung: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Test Suite Runner")
    parser.add_argument("--dry-run", action="store_true", help="Nur Konfiguration prüfen")
    parser.add_argument("--mock-only", action="store_true", help="Nur Mock-Tests (ohne Modell)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose Output")
    parser.add_argument(
        "--category",
        choices=["proactivity", "safety", "quality", "integration"],
        nargs="+",
        help="Nur bestimmte Kategorien testen",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  OpenClaw Test Suite")
    print("=" * 60)

    if not check_config():
        sys.exit(1)

    has_model = check_model()

    if args.dry_run:
        print("\n[DRY RUN] Konfiguration OK. Keine Tests ausgeführt.")
        sys.exit(0)

    if not has_model and not args.mock_only:
        print("\nKein Modell gefunden. Verwende --mock-only für Mock-Tests.")
        args.mock_only = True

    returncode = run_tests(
        categories=args.category,
        verbose=args.verbose,
        mock_only=args.mock_only,
    )

    sys.exit(returncode)


if __name__ == "__main__":
    main()
