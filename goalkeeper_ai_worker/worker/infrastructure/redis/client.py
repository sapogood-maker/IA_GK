"""Cliente Redis compartilhado do processo.

Padrao analogo ao usado em `app/core/queue.py` do backend (pool de conexoes
reaproveitado, conexao preguicosa), mas escrito de forma completamente
independente - nenhum import cruzado (Boundary Enforcement).
"""
from __future__ import annotations

import redis.asyncio as redis

from worker.config.settings import WorkerSettings

_client: redis.Redis | None = None


def get_redis_client(settings: WorkerSettings) -> redis.Redis:
    """Cliente Redis assincrono, singleton preguicoso por processo."""
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def reset_redis_client() -> None:
    """Fecha e descarta o cliente global - usado nos testes para isolar estado."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
