"""Teste de integracao (smoke test) do ciclo de vida completo em worker.main."""
from __future__ import annotations

import asyncio

from worker import main as main_module


async def test_run_starts_and_shuts_down_cleanly() -> None:
    """O ciclo completo (iniciar -> aguardar -> encerrar) deve funcionar de ponta a ponta."""
    shutdown_event = asyncio.Event()
    task = asyncio.create_task(main_module.run(shutdown_event=shutdown_event))

    await asyncio.sleep(0.05)
    assert not task.done()

    shutdown_event.set()
    await asyncio.wait_for(task, timeout=1)

    assert task.done()
    assert task.exception() is None
