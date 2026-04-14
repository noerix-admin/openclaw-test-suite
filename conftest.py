"""
Globale pytest-Konfiguration und Fixtures.
"""

import sys
from pathlib import Path

import pytest

# Projektroot zum Python-Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent))


def pytest_configure(config):
    """Registriere custom Marker."""
    config.addinivalue_line("markers", "live: Tests die das echte Modell benötigen")
    config.addinivalue_line("markers", "mock: Tests die nur Mock-Agent nutzen")


@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).parent


@pytest.fixture(scope="session")
def config(project_root):
    import yaml
    with open(project_root / "config.yaml") as f:
        return yaml.safe_load(f.read())
