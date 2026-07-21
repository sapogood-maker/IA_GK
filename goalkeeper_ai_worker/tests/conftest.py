"""Fixtures compartilhadas dos testes do Worker."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from worker.config.settings import get_settings


@pytest.fixture(autouse=True)
def _worker_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Garante variaveis de ambiente minimas e limpa o cache de settings entre testes."""
    monkeypatch.setenv("WORKER_INSTANCE_ID", "worker-test-01")
    monkeypatch.setenv("WORKER_ENV", "test")
    monkeypatch.setenv("WORKER_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("WORKER_BACKEND_API_URL", "http://backend.test")
    monkeypatch.setenv("WORKER_API_KEY", "test-api-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
