"""Teste de integracao (smoke test) do ciclo de vida completo em worker.main.

Desde a Sprint W3, run() delega ao WorkerOrchestrator, que exige Redis real
para criar o consumer group ao iniciar - por isso este teste vive em
tests/infrastructure/ (nao mais em tests/, como na W1) e aponta
WORKER_REDIS_URL para o Redis de teste descartavel."""
from __future__ import annotations

import asyncio

import pytest

from worker import main as main_module
from worker.config.settings import get_settings


@pytest.fixture(autouse=True)
def _point_to_test_redis(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WORKER_REDIS_URL", "redis://localhost:6381/0")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_run_starts_and_shuts_down_cleanly() -> None:
    """O ciclo completo (iniciar -> aguardar Jobs -> encerrar) deve funcionar
    de ponta a ponta contra um Redis real."""
    shutdown_event = asyncio.Event()
    task = asyncio.create_task(main_module.run(shutdown_event=shutdown_event))

    await asyncio.sleep(0.2)
    assert not task.done()

    shutdown_event.set()
    await asyncio.wait_for(task, timeout=5)

    assert task.done()
    assert task.exception() is None
