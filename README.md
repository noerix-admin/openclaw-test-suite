# OpenClaw Agent Test Suite

Vollstaendige Testumgebung fuer OpenClaw-Clone Agenten. Testet Proaktivitaet, Safety, Output-Qualitaet und Integrationen.

## Architektur

```
openclaw-test-suite/
|-- core/                  # Test-Framework Kern
|   |-- agent_interface.py # Schnittstelle zum GGUF-Modell + Mock
|   |-- mock_services.py   # Simulierte Services (Messaging, E-Mail, Dateisystem, API)
|   |-- event_bus.py       # Pub/Sub fuer Proaktivitaets-Tests
|   |-- scoring.py         # Bewertungssystem (Pass/Warn/Fail)
|   +-- test_runner.py     # Orchestrierung und Reporting
|
|-- tests/                 # 4 Test-Kategorien
|   |-- test_proactivity/  # Heartbeat, Condition-Trigger, Recurring Tasks, Autonome Aktionen
|   |-- test_safety/       # Action Boundaries, Prompt Injection, Data Leakage, Runaway, Confirmation
|   |-- test_quality/      # Reasoning, Instruction Following, Task Completion, Context Handling
|   +-- test_integration/  # File Ops, Messaging, API Calls, Tool Usage
|
|-- scenarios/             # Vordefinierte YAML-Szenarien
|-- scripts/               # Runner-Scripts und Report-Generator
+-- reports/               # Generierte Reports (HTML/JSON)
```

## Setup

### 1. Voraussetzungen

- Python 3.10+
- (Optional) CUDA fuer GPU-Beschleunigung

### 2. Installation

```bash
cd openclaw-test-suite
pip install -r requirements.txt
```

### 3. Konfiguration

Kopiere `.env.example` nach `.env` und setze den Modell-Pfad:

```bash
cp .env.example .env
# Editiere .env und setze MODEL_PATH auf dein GGUF-Modell
```

Die `config.yaml` enthaelt alle weiteren Einstellungen:

| Einstellung | Beschreibung | Default |
|---|---|---|
| `model.gpu_layers` | Anzahl GPU-Layers | 35 |
| `model.context_size` | Kontextfenster | 8192 |
| `model.temperature` | Sampling-Temperatur | 0.7 |
| `model.max_tokens` | Max Output-Tokens | 2048 |
| `scoring.pass_threshold` | Ab wann PASS | 0.7 |
| `safety.blocked_actions` | Verbotene Aktionen | siehe config.yaml |

### 4. Konfiguration pruefen

```bash
python scripts/run_all_tests.py --dry-run
```

## Tests ausfuehren

### Alle Tests (Mock-Modus, ohne Modell)

```bash
python scripts/run_all_tests.py --mock-only
```

### Alle Tests (mit echtem Modell)

```bash
python scripts/run_all_tests.py
```

### Einzelne Kategorie

```bash
python scripts/run_category.py proactivity
python scripts/run_category.py safety -v
python scripts/run_category.py quality
python scripts/run_category.py integration
```

### Direkt mit pytest

```bash
# Alle Tests
pytest tests/ -v

# Einzelne Datei
pytest tests/test_safety/test_prompt_injection.py -v

# Einzelner Test
pytest tests/test_proactivity/test_heartbeat.py::TestHeartbeatBasic::test_agent_responds_to_heartbeat -v

# Nur Mock-Tests
pytest tests/ -k "not live"
```

### HTML-Report generieren

```bash
python scripts/generate_report.py --run
```

Report wird in `reports/` gespeichert.

## Test-Kategorien

### 1. Proaktivitaet (`test_proactivity/`)

Testet die OpenClaw-Besonderheit: autonomes Handeln ohne Benutzer-Prompt.

| Test | Prueft |
|---|---|
| `test_heartbeat.py` | Agent reagiert auf periodische Weckrufe, erkennt ob Aktion noetig |
| `test_condition_trigger.py` | Agent reagiert auf Bedingungen (z.B. volle Inbox) |
| `test_recurring_tasks.py` | Geplante Aufgaben werden korrekt ausgefuehrt |
| `test_autonomous_actions.py` | Agent waehlt selbststaendig richtige Aktionen |

### 2. Safety (`test_safety/`)

Stellt sicher, dass der Agent keine schaedlichen Aktionen ausfuehrt.

| Test | Prueft |
|---|---|
| `test_action_boundaries.py` | Blocklist/Allowlist fuer Aktionen |
| `test_prompt_injection.py` | Resistenz gegen 6 Injection-Vektoren |
| `test_data_leakage.py` | Keine Credentials/PII in Outputs |
| `test_runaway_prevention.py` | Keine Endlos-Loops oder Eskalation |
| `test_confirmation_flow.py` | Bestaetigung bei kritischen Aktionen |

### 3. Qualitaet (`test_quality/`)

Bewertet die Output-Qualitaet des LLM.

| Test | Prueft |
|---|---|
| `test_reasoning.py` | Logisches Denken, Kausalitaet, Denkschritte |
| `test_instruction_following.py` | Format, Sprache, Laenge, Negativ-Anweisungen |
| `test_task_completion.py` | Vollstaendigkeit, Mehrstufige Aufgaben |
| `test_context_handling.py` | Multi-Turn-Kontext, Themenwechsel |

### 4. Integration (`test_integration/`)

Testet die Anbindung an externe Services.

| Test | Prueft |
|---|---|
| `test_file_operations.py` | Lesen/Schreiben/Loeschen, Path-Traversal-Schutz |
| `test_messaging.py` | WhatsApp/Discord Mock, Nachrichten senden/empfangen |
| `test_api_calls.py` | HTTP-Requests, Fehlerbehandlung |
| `test_tool_usage.py` | Korrekte Tool-Auswahl, Parameter-Vollstaendigkeit |

## Eigene Tests hinzufuegen

### Neuen Test schreiben

```python
# tests/test_safety/test_my_custom.py
import pytest
from core.agent_interface import AgentContext, AgentResponse, MockAgentInterface
from core.scoring import Scorer

@pytest.fixture
def agent():
    return MockAgentInterface()

@pytest.fixture
def scorer():
    return Scorer()

class TestMyCustom:
    def test_something(self, agent, scorer):
        agent.queue_response(AgentResponse(
            text="Erwartete Antwort",
            actions=[{"type": "expected_action", "params": {}}],
        ))

        response = agent.send("Mein Test-Prompt", AgentContext())

        result = scorer.boolean_check(
            "my_test",
            len(response.actions) > 0,
            "Agent hat wie erwartet reagiert",
        )
        assert result.passed
```

### Neues Szenario hinzufuegen

Erstelle eine YAML-Datei in `scenarios/`:

```yaml
scenarios:
  - name: mein_szenario
    description: "Beschreibung"
    input: "Prompt an den Agent"
    expected_actions:
      - type: erwartete_aktion
    success_criteria:
      - "Kriterium 1"
      - "Kriterium 2"
```

## Mock vs. Live Modus

| Modus | Beschreibung | Benoetigt Modell |
|---|---|---|
| Mock | Verwendet `MockAgentInterface` mit vordefinierten Antworten | Nein |
| Live | Verwendet echtes GGUF-Modell via `llama-cpp-python` | Ja |

Alle Tests laufen standardmaessig im **Mock-Modus**. Um Live-Tests zu schreiben, markiere sie mit `@pytest.mark.live`:

```python
@pytest.mark.live
def test_real_model_reasoning(self):
    agent = AgentInterface()  # Echtes Modell
    response = agent.send("Was ist 2+2?")
    assert "4" in response.text
```

## Bewertungssystem

| Verdict | Score | Bedeutung |
|---|---|---|
| PASS | >= 0.7 | Test bestanden |
| WARN | >= 0.5 | Grenzwertig, Verbesserung empfohlen |
| FAIL | < 0.5 | Test fehlgeschlagen |
| SKIP | - | Test uebersprungen |

Schwellenwerte konfigurierbar in `config.yaml`:

```yaml
scoring:
  pass_threshold: 0.7
  warn_threshold: 0.5
```

## Ergebnisse interpretieren

Nach einem Testlauf findest du:

1. **Terminal-Output**: Schnelluebersicht mit Pass/Fail pro Test
2. **JSON-Report** (`reports/results_*.json`): Maschinenlesbare Ergebnisse
3. **HTML-Report** (`reports/report_*.html`): Visueller Report mit Scores und Diagrammen

### Typische Probleme und Loesungen

| Problem | Moegliche Ursache | Loesung |
|---|---|---|
| Proaktivitaets-Tests FAIL | Agent reagiert nicht auf Heartbeat | System-Prompt anpassen, Heartbeat-Prompt-Format pruefen |
| Safety-Tests FAIL | Agent fuehrt verbotene Aktionen aus | Guardrails im System-Prompt verstaerken |
| Quality-Tests WARN | Antworten teilweise korrekt | Temperature senken, Prompt-Engineering verbessern |
| Integration-Tests FAIL | Tool-Auswahl falsch | Available-Tools-Liste im Kontext pruefen |
