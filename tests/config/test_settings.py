import runpy
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

SETTINGS = Path(__file__).resolve().parents[2] / "config" / "settings.py"


def load(monkeypatch, **env):
    for key in ("DJANGO_SECRET_KEY", "DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return runpy.run_path(str(SETTINGS))


def test_production_mode_requires_a_secret_key(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        load(monkeypatch)


def test_debug_is_off_and_hosts_are_local_by_default(monkeypatch):
    settings = load(monkeypatch, DJANGO_SECRET_KEY="test-key")

    assert settings["DEBUG"] is False
    assert settings["ALLOWED_HOSTS"] == ["localhost", "127.0.0.1"]


def test_debug_mode_falls_back_to_a_dev_only_key(monkeypatch):
    settings = load(monkeypatch, DJANGO_DEBUG="1")

    assert settings["SECRET_KEY"].startswith("dev-only")
