"""Ponto de entrada do Goalkeeper AI Worker.

Sprint W3: inicializa configuracao, logging e as dependencias externas
(Redis, Worker API), e delega toda a execucao do Pipeline ao
WorkerOrchestrator. Nenhuma logica de negocio vive aqui - so
inicializacao e wiring (AI_WORKER_CONSTITUTION.md, Secao 1).
"""
from __future__ import annotations

import asyncio
import logging

from worker import __version__
from worker.config.settings import get_settings
from worker.core.exceptions import WorkerError
from worker.core.lifecycle import install_shutdown_handlers, wait_for_shutdown
from worker.infrastructure.backend_client.client import BackendClient
from worker.infrastructure.redis.client import get_redis_client
from worker.observability.logging_setup import configure_logging
from worker.orchestrator.orchestrator import WorkerOrchestrator


async def run(shutdown_event: asyncio.Event | None = None) -> None:
    """Inicializa o Worker e delega a execucao ao WorkerOrchestrator."""
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

    redis_client = get_redis_client(settings)

    logger.info("worker_ready_processing_jobs")
    async with BackendClient(settings) as backend_client:
        orchestrator = WorkerOrchestrator(settings, redis_client, backend_client)
        await orchestrator.run_forever(event)

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
