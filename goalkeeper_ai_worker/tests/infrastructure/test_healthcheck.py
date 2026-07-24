"""Testes de worker.healthcheck (Deployment v1.0) - Redis real descartavel
e HTTP mockado (httpx.MockTransport), mesma disciplina de
test_backend_client.py ("Redis real, HTTP mockado")."""
from __future__ import annotations

import httpx
import pytest

from worker.config.settings import get_settings
from worker.healthcheck import _is_healthy

UNREACHABLE_REDIS_URL = "redis://localhost:1/0"
TEST_REDIS_URL = "redis://localhost:6381/0"


def _ok_transport() -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(200, json={"status": "ok"}))


def _down_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    return httpx.MockTransport(handler)


async def test_healthy_when_redis_and_backend_are_both_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", TEST_REDIS_URL)
    get_settings.cache_clear()

    healthy = await _is_healthy(transport=_ok_transport())

    assert healthy is True


async def test_unhealthy_when_redis_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_settings.cache_clear()

    healthy = await _is_healthy(transport=_ok_transport())

    assert healthy is False


async def test_unhealthy_when_backend_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", TEST_REDIS_URL)
    get_settings.cache_clear()

    healthy = await _is_healthy(transport=_down_transport())

    assert healthy is False


async def test_unhealthy_when_backend_returns_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_REDIS_URL", TEST_REDIS_URL)
    get_settings.cache_clear()
    error_transport = httpx.MockTransport(lambda request: httpx.Response(503))

    healthy = await _is_healthy(transport=error_transport)

    assert healthy is False
