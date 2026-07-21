"""Consumer group do stream Redis `processing_jobs`.

Nome do stream e formato da mensagem (`job_id`, `video_id`) sao um contrato
do backend (`app/core/queue.py`) - replicados aqui como valores literais,
nunca por import cruzado (Boundary Enforcement).

Nesta sprint (W2) estas funcoes provam que o canal funciona: criar o grupo,
ler uma mensagem publicada de verdade, confirmar (ACK). A composicao num
laco de consumo continuo, com retry/timeout/checkpoint por Job, e da W3.
"""
from __future__ import annotations

import logging

import redis.asyncio as redis
from redis.exceptions import RedisError, ResponseError

from worker.contracts.queue_message import JobMessage
from worker.core.exceptions import QueueConnectionError

logger = logging.getLogger(__name__)

PROCESSING_JOBS_STREAM = "processing_jobs"


async def ensure_consumer_group(client: redis.Redis, group_name: str) -> None:
    """Cria o consumer group se ainda nao existir - idempotente.

    Usa MKSTREAM para o caso do stream ainda nao ter sido criado (nenhum
    video foi enviado ainda) e ignora BUSYGROUP, que so indica que o grupo
    ja existe (esperado a partir da segunda instancia de Worker em diante).
    """
    try:
        await client.xgroup_create(
            PROCESSING_JOBS_STREAM, group_name, id="$", mkstream=True
        )
        logger.info(
            "consumer_group_created stream=%s group=%s",
            PROCESSING_JOBS_STREAM, group_name,
        )
    except ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            logger.debug(
                "consumer_group_already_exists stream=%s group=%s",
                PROCESSING_JOBS_STREAM, group_name,
            )
        else:
            raise QueueConnectionError(
                f"Falha ao criar consumer group '{group_name}': {exc}"
            ) from exc
    except RedisError as exc:
        raise QueueConnectionError(
            f"Falha ao conectar ao Redis ao criar consumer group '{group_name}': {exc}"
        ) from exc


async def read_next_job(
    client: redis.Redis,
    group_name: str,
    consumer_name: str,
    block_ms: int = 5000,
) -> JobMessage | None:
    """Le a proxima mensagem nova do stream para este consumer, via XREADGROUP.

    Bloqueia ate `block_ms` milissegundos aguardando uma mensagem nova;
    retorna None se nada chegar nesse intervalo (permite ao chamador
    verificar o shutdown_event periodicamente, mesmo padrao de espera
    cooperativa ja usado em worker.core.lifecycle)."""
    try:
        response = await client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={PROCESSING_JOBS_STREAM: ">"},
            count=1,
            block=block_ms,
        )
    except RedisError as exc:
        raise QueueConnectionError(f"Falha ao ler mensagem do Redis: {exc}") from exc

    if not response:
        return None

    _, messages = response[0]
    message_id, fields = messages[0]
    return JobMessage(
        message_id=message_id,
        job_id=fields["job_id"],
        video_id=fields["video_id"],
    )


async def ack_job(client: redis.Redis, group_name: str, message_id: str) -> None:
    """Confirma o processamento de uma mensagem (XACK) - remove das pendentes."""
    try:
        await client.xack(PROCESSING_JOBS_STREAM, group_name, message_id)
    except RedisError as exc:
        raise QueueConnectionError(f"Falha ao confirmar mensagem {message_id}: {exc}") from exc
