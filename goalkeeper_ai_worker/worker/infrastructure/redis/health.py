"""Verificacao de disponibilidade do Redis (Deployment v1.0, Docker
Runtime) - usada por `worker.wait_for_redis` (aguardar antes de iniciar
o processo) e `worker.healthcheck` (liveness continua do container).

Deliberadamente separada de `client.py` (Sprint W2, singleton
preguicoso reaproveitado pelo Orchestrator durante o processamento real
de Jobs) - esta funcao abre e fecha uma conexao efemera e descartavel a
cada chamada, nunca reaproveita o singleton do processo, e nunca e
chamada pelo Pipeline/Orchestrator em runtime."""
from __future__ import annotations

import redis.asyncio as redis

from worker.config.settings import WorkerSettings


async def redis_is_reachable(settings: WorkerSettings, timeout_seconds: float = 3.0) -> bool:
    """`True` se um PING no Redis configurado responde dentro do timeout,
    `False` para qualquer falha (conexao recusada, timeout, DNS, etc.) -
    nunca propaga a excecao, ja que o objetivo e um booleano de
    diagnostico, no wait-loop de startup ou no HEALTHCHECK do container."""
    client = redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
    )
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()
