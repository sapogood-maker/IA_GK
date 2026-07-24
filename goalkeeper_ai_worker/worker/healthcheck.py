"""Health Check do Worker (Deployment v1.0, Docker Runtime).

Script standalone, chamado pela instrucao `HEALTHCHECK` do
`deployment/docker/Dockerfile` - nunca importado pelo Orchestrator ou
por qualquer Analyzer/Stage. Define "saudavel" como "capaz de fazer
trabalho util agora": as DUAS dependencias externas criticas do Worker
(Redis - fila de Jobs; a Worker API do backend - unico canal de
Job/download/upload) precisam estar alcancaveis. Deliberadamente NAO
verifica estado interno do loop de consumo (`WorkerOrchestrator.run_forever`,
Sprint W3) - nenhuma mudanca foi feita la para evitar um falso "unhealthy"
durante o processamento legitimo de um Job longo.

Uso: `python -m worker.healthcheck` (exit 0 = saudavel, exit 1 = nao).
"""
from __future__ import annotations

import asyncio
import logging
import sys

import httpx

from worker.config.settings import get_settings
from worker.infrastructure.redis.health import redis_is_reachable

logger = logging.getLogger(__name__)

_CHECK_TIMEOUT_SECONDS = 3.0


async def _backend_is_reachable(
    backend_api_url: str, timeout_seconds: float, transport: httpx.BaseTransport | None = None,
) -> bool:
    """`/health` e um endpoint publico do backend (sem autenticacao,
    confirmado em producao durante a validacao manual da W25-W27) -
    nenhuma API Key e necessaria so para checar alcancabilidade.
    `transport` e injetavel so para testes (`httpx.MockTransport` - mesma
    disciplina de `tests/infrastructure/test_backend_client.py`, "Redis
    real, HTTP mockado")."""
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, transport=transport) as client:
            response = await client.get(f"{backend_api_url}/health")
            return response.status_code < 400
    except Exception:
        return False


async def _is_healthy(transport: httpx.BaseTransport | None = None) -> bool:
    settings = get_settings()
    redis_ok = await redis_is_reachable(settings, timeout_seconds=_CHECK_TIMEOUT_SECONDS)
    backend_ok = await _backend_is_reachable(
        settings.backend_api_url, timeout_seconds=_CHECK_TIMEOUT_SECONDS, transport=transport,
    )
    if not redis_ok:
        logger.warning("healthcheck_failed dependency=redis")
    if not backend_ok:
        logger.warning("healthcheck_failed dependency=backend_api")
    return redis_ok and backend_ok


def main() -> int:
    healthy = asyncio.run(_is_healthy())
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
