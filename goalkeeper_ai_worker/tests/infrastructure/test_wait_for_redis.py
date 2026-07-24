"""Testes de worker.wait_for_redis (Deployment v1.0) - Redis real
descartavel (mesma disciplina de tests/infrastructure/, nunca mockado)."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.wait_for_redis import _wait_until_reachable, main

UNREACHABLE_REDIS_URL = "redis://localhost:1/0"
TEST_REDIS_URL = "redis://localhost:6381/0"


async def test_wait_until_reachable_returns_true_immediately_when_redis_is_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", TEST_REDIS_URL)
    get_settings.cache_clear()

    reachable = await _wait_until_reachable(timeout_seconds=5.0)

    assert reachable is True


async def test_wait_until_reachable_gives_up_after_timeout_when_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_settings.cache_clear()

    reachable = await _wait_until_reachable(timeout_seconds=1.0)

    assert reachable is False


def test_main_returns_zero_when_redis_is_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", TEST_REDIS_URL)
    monkeypatch.setenv("WORKER_STARTUP_WAIT_TIMEOUT_SECONDS", "5")
    get_settings.cache_clear()

    assert main() == 0


def test_main_returns_one_when_redis_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", UNREACHABLE_REDIS_URL)
    monkeypatch.setenv("WORKER_STARTUP_WAIT_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()

    assert main() == 1
