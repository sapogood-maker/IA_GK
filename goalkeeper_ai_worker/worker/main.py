"""Ponto de entrada do Goalkeeper AI Worker.

Sprint W1: inicializa configuracao e logging, e aguarda um sinal de
encerramento. Nao consome fila, nao chama a API do backend, nao acessa
Cloudflare R2 - essas integracoes comecam na Sprint W2 (ver
AI_WORKER_CONSTITUTION.md, Secao 13 - Roadmap).
"""
from __future__ import annotations

import asyncio
import logging

from worker import __version__
from worker.config.settings import get_settings
from worker.core.exceptions import WorkerError
from worker.core.lifecycle import install_shutdown_handlers, wait_for_shutdown
from worker.observability.logging_setup import configure_logging


async def run(shutdown_event: asyncio.Event | None = None) -> None:
    """Executa o ciclo de vida completo do Worker: inicia, aguarda, encerra.

    O parametro shutdown_event permite testar o ciclo de vida sem depender
    de sinais reais do sistema operacional - se omitido, handlers de
    SIGINT/SIGTERM sao registrados normalmente.
    """
    settings = get_settings()
    configure_logging(settings)
    logger = logging.getLogger(__name__)

    logger.info(
        "worker_starting instance_id=%s env=%s version=%s",
        settings.instance_id,
        settings.env,
        __version__,
    )

    event = shutdown_event if shutdown_event is not None else asyncio.Event()
    if shutdown_event is None:
        install_shutdown_handlers(event)

    logger.info("worker_ready_waiting_for_shutdown_signal")
    await wait_for_shutdown(event)

    logger.info("worker_shutting_down")


def main() -> None:
    """Wrapper sincrono para execucao via `python -m worker.main`."""
    try:
        asyncio.run(run())
    except WorkerError:
        logging.getLogger(__name__).exception("worker_failed_to_start")
        raise


if __name__ == "__main__":
    main()
