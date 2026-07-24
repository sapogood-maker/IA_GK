"""Testes de worker.infrastructure.redis.health (Deployment v1.0) - Redis
real descartavel (test_redis_url) e uma URL genuinamente inalcancavel
(porta 1, mesmo padrao de test_redis_connection_errors.py) - nunca mockado."""
from __future__ import annotations

import pytest

from worker.config.settings import get_settings
from worker.infrastructure.redis.health import redis_is_reachable

UNREACHABLE_REDIS_URL = "redis://localhost:1/0"
TEST_REDIS_URL = "redis://localhost:6381/0"


async def test_redis_is_reachable_returns_true_for_a_real_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", TEST_REDIS_URL)
    get_settings.cache_clear()

    reachable = await redis_is_reachable(get_settings(), timeout_seconds=2.0)

    assert reachable is True


async def test_redis_is_reachable_returns_false_when_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_settings.cache_clear()

    reachable = await redis_is_reachable(get_settings(), timeout_seconds=1.0)

    assert reachable is False
