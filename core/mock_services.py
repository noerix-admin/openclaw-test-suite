"""
Mock-Services — Simuliert externe Dienste für Tests.

Jeder Service zeichnet Aktionen auf, sodass Tests prüfen können,
welche Aktionen der Agent ausgeführt hat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionRecord:
    service: str
    action: str
    params: dict[str, Any]
    timestamp: float = 0.0


class MockMessagingService:
    """Simuliert WhatsApp/Discord/Telegram."""

    def __init__(self, name: str = "messaging"):
        self.name = name
        self.inbox: list[dict[str, str]] = []
        self.sent: list[dict[str, str]] = []
        self.action_log: list[ActionRecord] = []

    def add_incoming_message(self, sender: str, text: str, channel: str = "default"):
        self.inbox.append({"sender": sender, "text": text, "channel": channel})

    def send_message(self, recipient: str, text: str, channel: str = "default") -> bool:
        msg = {"recipient": recipient, "text": text, "channel": channel}
        self.sent.append(msg)
        self.action_log.append(ActionRecord(self.name, "send_message", msg))
        return True

    def get_unread_count(self) -> int:
        return len(self.inbox)

    def get_state(self) -> dict:
        return {
            "unread_count": len(self.inbox),
            "inbox_preview": [m["text"][:50] for m in self.inbox[:5]],
        }

    def reset(self):
        self.inbox.clear()
        self.sent.clear()
        self.action_log.clear()


class MockEmailService:
    """Simuliert E-Mail-Dienst."""

    def __init__(self):
        self.inbox: list[dict[str, str]] = []
        self.sent: list[dict[str, str]] = []
        self.action_log: list[ActionRecord] = []

    def add_email(self, sender: str, subject: str, body: str, priority: str = "normal"):
        self.inbox.append({
            "sender": sender, "subject": subject, "body": body, "priority": priority,
        })

    def send_email(self, to: str, subject: str, body: str) -> bool:
        email = {"to": to, "subject": subject, "body": body}
        self.sent.append(email)
        self.action_log.append(ActionRecord("email", "send_email", email))
        return True

    def get_state(self) -> dict:
        return {
            "unread_count": len(self.inbox),
            "high_priority_count": sum(1 for m in self.inbox if m["priority"] == "high"),
            "subjects": [m["subject"] for m in self.inbox[:5]],
        }

    def reset(self):
        self.inbox.clear()
        self.sent.clear()
        self.action_log.clear()


class MockFileSystem:
    """Simuliert Dateisystem-Operationen."""

    def __init__(self):
        self.files: dict[str, str] = {}
        self.action_log: list[ActionRecord] = []

    def write_file(self, path: str, content: str):
        self.files[path] = content
        self.action_log.append(ActionRecord("filesystem", "write", {"path": path}))

    def read_file(self, path: str) -> str | None:
        self.action_log.append(ActionRecord("filesystem", "read", {"path": path}))
        return self.files.get(path)

    def delete_file(self, path: str) -> bool:
        self.action_log.append(ActionRecord("filesystem", "delete", {"path": path}))
        if path in self.files:
            del self.files[path]
            return True
        return False

    def list_files(self) -> list[str]:
        return list(self.files.keys())

    def get_state(self) -> dict:
        return {"file_count": len(self.files), "files": list(self.files.keys())}

    def reset(self):
        self.files.clear()
        self.action_log.clear()


class MockAPIService:
    """Simuliert externe API-Aufrufe."""

    def __init__(self):
        self.endpoints: dict[str, Any] = {}
        self.call_log: list[ActionRecord] = []

    def register_endpoint(self, url: str, response: Any, status_code: int = 200):
        self.endpoints[url] = {"response": response, "status_code": status_code}

    def call(self, method: str, url: str, data: Any = None) -> dict:
        record = ActionRecord("api", method, {"url": url, "data": data})
        self.call_log.append(record)
        if url in self.endpoints:
            ep = self.endpoints[url]
            return {"status_code": ep["status_code"], "data": ep["response"]}
        return {"status_code": 404, "data": None}

    def reset(self):
        self.endpoints.clear()
        self.call_log.clear()


class MockServiceRegistry:
    """Zentrales Registry aller Mock-Services."""

    def __init__(self):
        self.messaging = MockMessagingService("whatsapp")
        self.discord = MockMessagingService("discord")
        self.email = MockEmailService()
        self.filesystem = MockFileSystem()
        self.api = MockAPIService()

    def get_full_state(self) -> dict:
        return {
            "whatsapp": self.messaging.get_state(),
            "discord": self.discord.get_state(),
            "email": self.email.get_state(),
            "filesystem": self.filesystem.get_state(),
        }

    def get_all_action_logs(self) -> list[ActionRecord]:
        logs = []
        logs.extend(self.messaging.action_log)
        logs.extend(self.discord.action_log)
        logs.extend(self.email.action_log)
        logs.extend(self.filesystem.action_log)
        logs.extend(self.api.call_log)
        return logs

    def reset_all(self):
        self.messaging.reset()
        self.discord.reset()
        self.email.reset()
        self.filesystem.reset()
        self.api.reset()
