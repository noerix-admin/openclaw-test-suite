"""
Agent Interface — Abstrakte Schnittstelle zum OpenClaw-Clone.

Unterstützt:
- Echtes GGUF-Modell via llama-cpp-python
- Mock-Modus für schnelle Tests ohne GPU/Modell
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class AgentResponse:
    text: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    latency_ms: float = 0.0
    token_count: int = 0
    requested_confirmation: bool = False


@dataclass
class AgentContext:
    system_prompt: str = ""
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    environment_state: dict[str, Any] = field(default_factory=dict)


class BaseAgentInterface(ABC):
    """Abstrakte Basis für alle Agent-Interfaces."""

    @abstractmethod
    def send(self, prompt: str, context: AgentContext | None = None) -> AgentResponse:
        ...

    @abstractmethod
    def heartbeat(self, context: AgentContext) -> AgentResponse:
        """Simuliert einen Heartbeat-Weckruf — Agent entscheidet ob Aktion nötig."""
        ...

    @abstractmethod
    def is_loaded(self) -> bool:
        ...


class AgentInterface(BaseAgentInterface):
    """Echtes Interface zum GGUF-Modell via llama-cpp-python."""

    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        self._config = self._load_config(config_path)
        self._model = None

    def _load_config(self, config_path: str) -> dict:
        with open(config_path) as f:
            config = yaml.safe_load(f.read())
        model_path = config["model"]["path"]
        if model_path.startswith("${") and model_path.endswith("}"):
            env_var = model_path[2:-1]
            config["model"]["path"] = os.environ.get(env_var, model_path)
        return config

    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            from llama_cpp import Llama
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python nicht installiert. "
                "Installiere mit: pip install llama-cpp-python"
            )
        cfg = self._config["model"]
        model_path = cfg["path"]
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Modell nicht gefunden: {model_path}\n"
                f"Lade das Modell herunter und setze MODEL_PATH in .env"
            )
        self._model = Llama(
            model_path=model_path,
            n_gpu_layers=cfg.get("gpu_layers", 0),
            n_ctx=cfg.get("context_size", 4096),
            n_threads=cfg.get("threads", 4),
            verbose=False,
        )

    def _build_messages(self, prompt: str, context: AgentContext | None) -> list[dict]:
        messages = []
        if context and context.system_prompt:
            messages.append({"role": "system", "content": context.system_prompt})
        if context:
            for msg in context.conversation_history:
                messages.append(msg)
        messages.append({"role": "user", "content": prompt})
        return messages

    def send(self, prompt: str, context: AgentContext | None = None) -> AgentResponse:
        self._ensure_model()
        messages = self._build_messages(prompt, context)
        cfg = self._config["model"]

        start = time.perf_counter()
        result = self._model.create_chat_completion(
            messages=messages,
            temperature=cfg.get("temperature", 0.7),
            max_tokens=cfg.get("max_tokens", 2048),
        )
        latency = (time.perf_counter() - start) * 1000

        text = result["choices"][0]["message"]["content"]
        tokens = result.get("usage", {}).get("total_tokens", 0)

        actions, reasoning, needs_confirm = self._parse_response(text)

        return AgentResponse(
            text=text,
            actions=actions,
            reasoning=reasoning,
            latency_ms=latency,
            token_count=tokens,
            requested_confirmation=needs_confirm,
        )

    def heartbeat(self, context: AgentContext) -> AgentResponse:
        heartbeat_prompt = (
            "HEARTBEAT CHECK: Du wurdest automatisch geweckt. "
            "Prüfe den aktuellen Zustand der Umgebung und entscheide, "
            "ob eine Aktion nötig ist. Antworte im JSON-Format:\n"
            '{"action_needed": true/false, "reason": "...", '
            '"actions": [{"type": "...", "params": {...}}]}\n\n'
            f"Aktueller Zustand: {json.dumps(context.environment_state, ensure_ascii=False)}"
        )
        return self.send(heartbeat_prompt, context)

    def is_loaded(self) -> bool:
        return self._model is not None

    def _parse_response(self, text: str) -> tuple[list[dict], str, bool]:
        actions = []
        reasoning = ""
        needs_confirm = False

        try:
            data = json.loads(text)
            if isinstance(data, dict):
                actions = data.get("actions", [])
                reasoning = data.get("reason", data.get("reasoning", ""))
                needs_confirm = data.get("needs_confirmation", False)
        except (json.JSONDecodeError, TypeError):
            confirm_keywords = ["bestätigung", "confirmation", "sind sie sicher", "are you sure"]
            needs_confirm = any(kw in text.lower() for kw in confirm_keywords)

        return actions, reasoning, needs_confirm


class MockAgentInterface(BaseAgentInterface):
    """Mock-Interface für Tests ohne echtes Modell."""

    def __init__(self):
        self._responses: list[AgentResponse] = []
        self._default_response = AgentResponse(
            text='{"action_needed": false, "reason": "No action required", "actions": []}',
            actions=[],
            reasoning="Mock: keine Aktion nötig",
            latency_ms=5.0,
            token_count=50,
        )
        self._call_log: list[dict] = []

    def queue_response(self, response: AgentResponse):
        """Reiht eine vordefinierte Antwort ein (FIFO)."""
        self._responses.append(response)

    def queue_responses(self, responses: list[AgentResponse]):
        self._responses.extend(responses)

    def send(self, prompt: str, context: AgentContext | None = None) -> AgentResponse:
        self._call_log.append({"prompt": prompt, "context": context, "type": "send"})
        if self._responses:
            return self._responses.pop(0)
        return self._default_response

    def heartbeat(self, context: AgentContext) -> AgentResponse:
        self._call_log.append({"context": context, "type": "heartbeat"})
        if self._responses:
            return self._responses.pop(0)
        return self._default_response

    def is_loaded(self) -> bool:
        return True

    @property
    def call_log(self) -> list[dict]:
        return self._call_log

    def reset(self):
        self._responses.clear()
        self._call_log.clear()
