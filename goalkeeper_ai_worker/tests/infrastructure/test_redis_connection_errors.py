"""Confirma que falhas reais de conexao com o Redis viram QueueConnectionError
(hierarquia WorkerError), em vez de vazar excecoes cruas de `redis.exceptions`.

Usa um cliente apontado para uma porta sem nada escutando (falha real de
conexao, nao mockada) - deliberadamente distinto do fixture `redis_client`
(que aponta para o Redis de teste real e funcional)."""
from __future__ import annotations

import pytest
import redis.asyncio as redis

from worker.core.exceptions import QueueConnectionError
from worker.infrastructure.redis.consumer import ack_job, ensure_consumer_group, read_next_job
from worker.infrastructure.redis.lock import acquire

UNREACHABLE_URL = "redis://localhost:1/0"


def _unreachable_client() -> "redis.Redis":
    return redis.from_url(UNREACHABLE_URL, decode_responses=True, socket_connect_timeout=1)


async def test_ensure_consumer_group_wraps_connection_failure() -> None:
    client = _unreachable_client()
    with pytest.raises(QueueConnectionError):
        await ensure_consumer_group(client, "any-group")
    await client.aclose()


async def test_read_next_job_wraps_connection_failure() -> None:
    client = _unreachable_client()
    with pytest.raises(QueueConnectionError):
        await read_next_job(client, "any-group", "any-consumer", block_ms=200)
    await client.aclose()


async def test_ack_job_wraps_connection_failure() -> None:
    client = _unreachable_client()
    with pytest.raises(QueueConnectionError):
        await ack_job(client, "any-group", "0-0")
    await client.aclose()


async def test_lock_acquire_wraps_connection_failure() -> None:
    client = _unreachable_client()
    with pytest.raises(QueueConnectionError):
        await acquire(client, "video-x", "owner-x", ttl_seconds=60)
    await client.aclose()
