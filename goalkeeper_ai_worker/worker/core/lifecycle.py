"""Ciclo de vida do processo do Worker: inicializacao e encerramento gracioso.

Nesta sprint (W1) o Worker apenas aguarda um sinal de encerramento - nao
consome fila, nao processa Jobs, nao implementa retry/heartbeat/scheduler.
A espera por trabalho real (Redis Streams, consumer group) e introduzida
na Sprint W2 (ver AI_WORKER_CONSTITUTION.md, Secao 13 - Roadmap).
"""
from __future__ import annotations

import asyncio
import signal
from collections.abc import Iterable

_SHUTDOWN_SIGNALS: tuple[signal.Signals, ...] = (signal.SIGINT, signal.SIGTERM)


def install_shutdown_handlers(
    shutdown_event: asyncio.Event,
    signals: Iterable[signal.Signals] = _SHUTDOWN_SIGNALS,
) -> None:
    """Registra handlers de sinal do SO que sinalizam o shutdown_event.

    Usa signal.signal (em vez de loop.add_signal_handler) por portabilidade:
    add_signal_handler nao e suportado no event loop padrao do Windows.
    """
    loop = asyncio.get_running_loop()

    def _handle_signal(signum: int, frame: object) -> None:
        loop.call_soon_threadsafe(shutdown_event.set)

    for sig in signals:
        try:
            signal.signal(sig, _handle_signal)
        except (ValueError, OSError):
            # Sinal indisponivel nesta plataforma/thread - ignorado propositalmente.
            continue


async def wait_for_shutdown(shutdown_event: asyncio.Event) -> None:
    """Bloqueia ate que o shutdown_event seja sinalizado."""
    await shutdown_event.wait()
