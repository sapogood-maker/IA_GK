"""Testes do consumer group do stream `processing_jobs` - Redis real."""
from __future__ import annotations

from worker.infrastructure.redis.consumer import (
    PROCESSING_JOBS_STREAM,
    ack_job,
    ensure_consumer_group,
    read_next_job,
)

GROUP = "test-group"
CONSUMER = "test-consumer-01"


async def test_ensure_consumer_group_is_idempotent(redis_client) -> None:
    """Criar o grupo duas vezes nao deve levantar excecao (BUSYGROUP ignorado)."""
    await ensure_consumer_group(redis_client, GROUP)
    await ensure_consumer_group(redis_client, GROUP)


async def test_read_next_job_returns_published_message(redis_client) -> None:
    """Uma mensagem publicada de verdade deve ser lida com job_id/video_id corretos."""
    await ensure_consumer_group(redis_client, GROUP)
    await redis_client.xadd(PROCESSING_JOBS_STREAM, {"job_id": "job-1", "video_id": "video-1"})

    message = await read_next_job(redis_client, GROUP, CONSUMER, block_ms=1000)

    assert message is not None
    assert message.job_id == "job-1"
    assert message.video_id == "video-1"


async def test_read_next_job_returns_none_when_no_message(redis_client) -> None:
    """Sem mensagem nova, deve retornar None apos o timeout de bloqueio."""
    await ensure_consumer_group(redis_client, GROUP)

    message = await read_next_job(redis_client, GROUP, CONSUMER, block_ms=200)

    assert message is None


async def test_ack_job_removes_message_from_pending(redis_client) -> None:
    """Apos o ACK, a mensagem nao deve mais aparecer como pendente do consumer."""
    await ensure_consumer_group(redis_client, GROUP)
    await redis_client.xadd(PROCESSING_JOBS_STREAM, {"job_id": "job-2", "video_id": "video-2"})
    message = await read_next_job(redis_client, GROUP, CONSUMER, block_ms=1000)
    assert message is not None

    await ack_job(redis_client, GROUP, message.message_id)

    pending = await redis_client.xpending(PROCESSING_JOBS_STREAM, GROUP)
    assert pending["pending"] == 0
