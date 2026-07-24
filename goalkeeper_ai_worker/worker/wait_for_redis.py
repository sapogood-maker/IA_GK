"""Aguarda o Redis ficar alcancavel antes do Worker iniciar (Deployment
v1.0, Docker Runtime).

Chamado exclusivamente por `deployment/docker/Dockerfile`'s
`entrypoint.sh`, ANTES de `python -m worker.main` - nunca importado
pelo Orchestrator/Pipeline em runtime. Reconexao APOS o startup e
responsabilidade do connection pool do `redis.asyncio` (cria uma nova
conexao por comando, sob demanda) combinada com `restart: unless-stopped`
no `docker-compose.yml` - ver DEPLOYMENT_V1_REPORT.md para a
justificativa completa dessa escolha.

Uso: `python -m worker.wait_for_redis` (exit 0 = Redis alcancavel,
exit 1 = timeout esgotado sem sucesso)."""
from __future__ import annotations

import asyncio
import logging
import sys
import time

from worker.config.settings import get_settings
from worker.infrastructure.redis.health import redis_is_reachable
from worker.observability.logging_setup import configure_logging

logger = logging.getLogger(__name__)

_RETRY_INTERVAL_SECONDS = 2.0


async def _wait_until_reachable(timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    settings = get_settings()
    while True:
        if await redis_is_reachable(settings):
            return True
        if time.monotonic() >= deadline:
            return False
        logger.info("waiting_for_redis retry_in_seconds=%s", _RETRY_INTERVAL_SECONDS)
        await asyncio.sleep(_RETRY_INTERVAL_SECONDS)


def main() -> int:
    settings = get_settings()
    configure_logging(settings)

    timeout_seconds = settings.startup_wait_timeout_seconds
    logger.info("wait_for_redis_starting timeout_seconds=%s", timeout_seconds)

    reachable = asyncio.run(_wait_until_reachable(timeout_seconds))
    if not reachable:
        logger.error("redis_unreachable_after_timeout timeout_seconds=%s", timeout_seconds)
        return 1

    logger.info("redis_reachable_worker_can_start")
    return 0


if __name__ == "__main__":
    sys.exit(main())
