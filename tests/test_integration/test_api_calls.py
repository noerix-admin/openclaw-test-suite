"""
API-Call-Tests — Prüft externe API-Aufrufe des Agenten.
"""

import pytest

from core.mock_services import MockServiceRegistry
from core.scoring import Scorer


@pytest.fixture
def services():
    return MockServiceRegistry()


@pytest.fixture
def scorer():
    return Scorer()


class TestAPICalls:
    """Tests für API-Integrationen."""

    def test_api_call_success(self, services, scorer):
        """Mock-API gibt korrekte Antwort bei registriertem Endpoint."""
        services.api.register_endpoint(
            "https://api.weather.com/current",
            {"temp": 22, "condition": "sunny"},
            200,
        )

        result_data = services.api.call("GET", "https://api.weather.com/current")

        result = scorer.boolean_check(
            "api_success",
            result_data["status_code"] == 200 and result_data["data"]["temp"] == 22,
            f"API Response: {result_data}",
        )
        assert result.passed

    def test_api_call_404(self, services, scorer):
        """Mock-API gibt 404 für unregistrierte Endpoints."""
        result_data = services.api.call("GET", "https://api.unknown.com/data")

        result = scorer.boolean_check(
            "api_404",
            result_data["status_code"] == 404,
            f"Status: {result_data['status_code']}",
        )
        assert result.passed

    def test_api_calls_logged(self, services, scorer):
        """Alle API-Aufrufe werden geloggt."""
        services.api.register_endpoint("https://api.test.com/a", {"ok": True})
        services.api.call("GET", "https://api.test.com/a")
        services.api.call("POST", "https://api.test.com/b", {"key": "value"})

        result = scorer.boolean_check(
            "api_logged",
            len(services.api.call_log) == 2,
            f"API-Calls geloggt: {len(services.api.call_log)}",
        )
        assert result.passed

    def test_api_post_with_data(self, services, scorer):
        """POST-Requests enthalten korrekte Daten."""
        services.api.register_endpoint("https://api.test.com/submit", {"id": 123}, 201)

        payload = {"name": "Test", "value": 42}
        result_data = services.api.call("POST", "https://api.test.com/submit", payload)

        logged = services.api.call_log[-1]
        result = scorer.boolean_check(
            "post_with_data",
            result_data["status_code"] == 201 and logged.params["data"] == payload,
            "POST-Request mit korrektem Payload geloggt",
        )
        assert result.passed
