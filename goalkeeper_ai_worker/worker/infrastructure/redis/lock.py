"""Lock distribuido por video (ADR-001/003 - AI_WORKER_CONSTITUTION.md).

Impede que dois Workers processem o mesmo video simultaneamente. Chave
`lock:video:{video_id}`, valor = identidade do dono (`owner_id`, tipicamente
`settings.instance_id`). `release`/`renew` usam script Lua atomico para so
agir se o valor ainda pertencer ao dono - evita que um Worker libere ou
renove o lock que outro ja assumiu apos expiracao.

Renovacao automatica por heartbeat/loop continuo NAO faz parte desta sprint
(W2) - so as primitivas, testaveis isoladamente. A composicao com um Job de
longa duracao e da W3.
"""
from __future__ import annotations

import redis.asyncio as redis
from redis.exceptions import RedisError

from worker.core.exceptions import QueueConnectionError

_LOCK_KEY_PREFIX = "lock:video:"

_RELEASE_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""

_RENEW_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("EXPIRE", KEYS[1], ARGV[2])
else
    return 0
end
"""


def _lock_key(video_id: str) -> str:
    return f"{_LOCK_KEY_PREFIX}{video_id}"


async def acquire(client: redis.Redis, video_id: str, owner_id: str, ttl_seconds: int) -> bool:
    """Tenta adquirir o lock do video. Retorna True se adquirido."""
    try:
        acquired = await client.set(_lock_key(video_id), owner_id, nx=True, ex=ttl_seconds)
    except RedisError as exc:
        raise QueueConnectionError(f"Falha ao adquirir lock do video {video_id}: {exc}") from exc
    return bool(acquired)


async def release(client: redis.Redis, video_id: str, owner_id: str) -> bool:
    """Libera o lock, apenas se ainda pertencer a `owner_id`. Retorna True se liberado."""
    try:
        result = await client.eval(_RELEASE_SCRIPT, 1, _lock_key(video_id), owner_id)
    except RedisError as exc:
        raise QueueConnectionError(f"Falha ao liberar lock do video {video_id}: {exc}") from exc
    return bool(result)


async def renew(client: redis.Redis, video_id: str, owner_id: str, ttl_seconds: int) -> bool:
    """Renova o TTL do lock, apenas se ainda pertencer a `owner_id`."""
    try:
        result = await client.eval(_RENEW_SCRIPT, 1, _lock_key(video_id), owner_id, ttl_seconds)
    except RedisError as exc:
        raise QueueConnectionError(f"Falha ao renovar lock do video {video_id}: {exc}") from exc
    return bool(result)
