#!/usr/bin/env python3
"""
Automatisches Setup der OpenClaw Test Suite.

Dieses Script:
1. Prüft Python-Version
2. Installiert Dependencies
3. Prüft/konfiguriert .env
4. Lädt optional das GGUF-Modell herunter
5. Führt einen Smoke-Test aus

Usage:
    python setup_env.py              # Interaktives Setup
    python setup_env.py --skip-model # Setup ohne Modell-Download
    python setup_env.py --model-url URL # Eigene Modell-URL
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

# ANSI Farben
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

DEFAULT_MODEL_URL = (
    "https://huggingface.co/Jackrong/"
    "Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-GGUF/"
    "resolve/main/Qwen3.5-27B.Q6_K.gguf"
)


def log(msg, color=RESET):
    print(f"{color}{msg}{RESET}")


def check_python():
    log("\n[1/5] Python-Version pruefen...", BOLD)
    v = sys.version_info
    if v.major == 3 and v.minor >= 10:
        log(f"  OK: Python {v.major}.{v.minor}.{v.micro}", GREEN)
        return True
    else:
        log(f"  FEHLER: Python {v.major}.{v.minor} — mindestens 3.10 erforderlich", RED)
        return False


def install_dependencies():
    log("\n[2/5] Dependencies installieren...", BOLD)
    req_file = ROOT / "requirements.txt"

    # Erst alles ausser llama-cpp-python
    deps = []
    with open(req_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "llama-cpp-python" not in line:
                deps.append(line)

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install"] + deps,
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        log("  OK: Basis-Dependencies installiert", GREEN)
    else:
        log(f"  FEHLER: {result.stderr[-200:]}", RED)
        return False

    # llama-cpp-python separat versuchen
    log("  Versuche llama-cpp-python zu installieren (braucht C++ Compiler)...", YELLOW)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "llama-cpp-python>=0.3.0"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        log("  OK: llama-cpp-python installiert — Live-Tests verfuegbar!", GREEN)
    else:
        log("  WARNUNG: llama-cpp-python konnte nicht installiert werden.", YELLOW)
        log("  Mock-Tests funktionieren trotzdem. Fuer Live-Tests:", YELLOW)
        log("  → C++ Compiler installieren (Visual Studio Build Tools / gcc)", YELLOW)
        log("  → Dann: pip install llama-cpp-python", YELLOW)

    return True


def setup_env(model_path=None):
    log("\n[3/5] .env konfigurieren...", BOLD)

    env_file = ROOT / ".env"
    if env_file.exists() and not model_path:
        log(f"  .env existiert bereits: {env_file}", GREEN)
        return True

    if not model_path:
        models_dir = ROOT / "models"
        gguf_files = list(models_dir.glob("*.gguf")) if models_dir.exists() else []
        if gguf_files:
            model_path = str(gguf_files[0])
            log(f"  Modell gefunden: {model_path}", GREEN)
        else:
            model_path = str(ROOT / "models" / "Qwen3.5-27B.Q6_K.gguf")
            log(f"  Modell-Pfad gesetzt (Datei noch nicht vorhanden): {model_path}", YELLOW)

    env_file.write_text(f"MODEL_PATH={model_path}\n", encoding="utf-8")
    log(f"  .env erstellt: MODEL_PATH={model_path}", GREEN)
    return True


def download_model(url=None, skip=False):
    log("\n[4/5] GGUF-Modell...", BOLD)

    models_dir = ROOT / "models"
    models_dir.mkdir(exist_ok=True)

    existing = list(models_dir.glob("*.gguf"))
    if existing:
        size_gb = existing[0].stat().st_size / (1024**3)
        log(f"  OK: Modell vorhanden — {existing[0].name} ({size_gb:.1f} GB)", GREEN)
        return True

    if skip:
        log("  Uebersprungen (--skip-model). Mock-Tests funktionieren trotzdem.", YELLOW)
        return True

    url = url or DEFAULT_MODEL_URL
    filename = url.split("/")[-1]
    target = models_dir / filename

    log(f"  Download von: {url}", YELLOW)
    log(f"  Ziel: {target}", YELLOW)
    log(f"  Groesse: ~22 GB — das dauert eine Weile...", YELLOW)

    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id="Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-GGUF",
            filename="Qwen3.5-27B.Q6_K.gguf",
            local_dir=str(models_dir),
        )
        log(f"  OK: Modell heruntergeladen — {path}", GREEN)
        return True
    except ImportError:
        log("  huggingface-hub nicht installiert. Installiere...", YELLOW)
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface-hub"], check=True)
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id="Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2-GGUF",
            filename="Qwen3.5-27B.Q6_K.gguf",
            local_dir=str(models_dir),
        )
        log(f"  OK: Modell heruntergeladen — {path}", GREEN)
        return True
    except Exception as e:
        log(f"  FEHLER beim Download: {e}", RED)
        log(f"  Lade das Modell manuell herunter:", YELLOW)
        log(f"  {url}", YELLOW)
        log(f"  Speichere als: {target}", YELLOW)
        return False


def smoke_test():
    log("\n[5/5] Smoke-Test (Mock-Modus)...", BOLD)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--timeout=60"],
        capture_output=True, text=True, cwd=ROOT,
    )

    if result.returncode == 0:
        # Extrahiere letzte Zeile mit Ergebnissen
        lines = result.stdout.strip().split("\n")
        summary = lines[-1] if lines else "OK"
        log(f"  OK: {summary}", GREEN)
        return True
    else:
        log(f"  FEHLER:\n{result.stdout[-300:]}", RED)
        if result.stderr:
            log(f"  {result.stderr[-200:]}", RED)
        return False


def print_summary(results):
    log("\n" + "=" * 60, BOLD)
    log("  Setup Zusammenfassung", BOLD)
    log("=" * 60, BOLD)

    steps = [
        ("Python", results.get("python", False)),
        ("Dependencies", results.get("deps", False)),
        (".env Konfiguration", results.get("env", False)),
        ("GGUF-Modell", results.get("model", False)),
        ("Smoke-Test", results.get("smoke", False)),
    ]

    for name, ok in steps:
        icon = f"{GREEN}OK{RESET}" if ok else f"{RED}FEHLT{RESET}"
        print(f"  {name:.<40} {icon}")

    log("\nNaechste Schritte:", BOLD)
    if all(v for v in results.values()):
        log("  Alles bereit! Starte Tests mit:", GREEN)
        log("    python scripts/run_all_tests.py --mock-only  (schnell, ohne Modell)", RESET)
        log("    python scripts/run_all_tests.py              (mit echtem Modell)", RESET)
    else:
        if not results.get("model"):
            log("  → Modell herunterladen: python setup_env.py", YELLOW)
        log("  → Mock-Tests starten: python scripts/run_all_tests.py --mock-only", YELLOW)


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Test Suite Setup")
    parser.add_argument("--skip-model", action="store_true", help="Modell-Download ueberspringen")
    parser.add_argument("--model-url", help="Eigene GGUF-Modell-URL")
    parser.add_argument("--model-path", help="Pfad zu einem bereits heruntergeladenen Modell")
    args = parser.parse_args()

    log("=" * 60, BOLD)
    log("  OpenClaw Test Suite — Setup", BOLD)
    log("=" * 60, BOLD)

    results = {}
    results["python"] = check_python()
    if not results["python"]:
        log("\nAbbruch: Python >= 3.10 erforderlich.", RED)
        sys.exit(1)

    results["deps"] = install_dependencies()
    results["env"] = setup_env(model_path=args.model_path)
    results["model"] = download_model(url=args.model_url, skip=args.skip_model)
    results["smoke"] = smoke_test()

    print_summary(results)


if __name__ == "__main__":
    main()
