"""Testes de worker.core.lifecycle."""
from __future__ import annotations

import asyncio

from worker.core.lifecycle import install_shutdown_handlers, wait_for_shutdown


async def test_wait_for_shutdown_returns_after_event_is_set() -> None:
    """wait_for_shutdown deve retornar assim que o evento e sinalizado."""
    shutdown_event = asyncio.Event()

    async def _trigger_shutdown() -> None:
        await asyncio.sleep(0.01)
        shutdown_event.set()

    asyncio.create_task(_trigger_shutdown())
    await asyncio.wait_for(wait_for_shutdown(shutdown_event), timeout=1)

    assert shutdown_event.is_set()


async def test_install_shutdown_handlers_does_not_raise() -> None:
    """Registrar os handlers de sinal do SO nao deve levantar excecao nesta plataforma."""
    shutdown_event = asyncio.Event()
    install_shutdown_handlers(shutdown_event)
