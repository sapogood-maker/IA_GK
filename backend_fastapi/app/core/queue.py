"""Fila de processamento (Redis Streams) - somente infraestrutura e
publisher nesta sprint.

NENHUM consumer existe ainda (ver AI_WORKER_ARCHITECTURE.md secao 4 e
SPRINT7_REPORT.md). O backend so publica uma mensagem quando um
ProcessingJob e criado; o futuro AI Worker sera quem consome, criando seu
proprio consumer group ao iniciar - o backend nao precisa saber disso.

Escolha de Redis Streams (nao List/Pub-Sub) porque consumer groups ja
entregam, nativamente, exclusividade de mensagem entre multiplos workers e
reentrega em caso de falha - ver justificativa completa na secao 4 do
AI_WORKER_ARCHITECTURE.md.
"""
import logging
import time
from typing import Optional

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Nome do stream onde cada ProcessingJob criado e publicado. Um unico stream
# por enquanto - se no futuro fizer sentido separar por prioridade/perfil de
# hardware (ver AI_WORKER_ARCHITECTURE.md secao 7), isso vira um parametro,
# nao uma mudanca estrutural.
PROCESSING_JOBS_STREAM = "processing_jobs"

_client: Optional["redis.Redis"] = None


def get_redis_client() -> "redis.Redis":
    """Cliente Redis compartilhado (pool de conexoes reaproveitado entre
    chamadas). Conexao e estabelecida de forma preguicosa no primeiro
    comando, nao na construcao do cliente."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def publish_processing_job(job_id: str, video_id: str) -> Optional[str]:
    """Publica um job de processamento no stream.

    Retorna o ID da mensagem no stream em caso de sucesso, ou None se a
    publicacao falhar. Deliberadamente NAO propaga excecao: a fila e
    suplementar ao fluxo de upload enquanto nenhum Worker existe para
    consumi-la - uma falha aqui nao deve impedir o upload do video em si.

    Logging estruturado (chave=valor), sem Prometheus (fora do escopo desta
    sprint) - suficiente para auditar quantidade publicada, falhas e tempo.
    """
    start = time.monotonic()
    client = get_redis_client()

    try:
        message_id = await client.xadd(
            PROCESSING_JOBS_STREAM,
            {"job_id": job_id, "video_id": video_id},
        )
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "processing_job_published stream=%s job_id=%s video_id=%s "
            "message_id=%s duration_ms=%s",
            PROCESSING_JOBS_STREAM, job_id, video_id, message_id, duration_ms,
        )
        return message_id
    except Exception as e:
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        logger.error(
            "processing_job_publish_failed stream=%s job_id=%s video_id=%s "
            "duration_ms=%s error=%s",
            PROCESSING_JOBS_STREAM, job_id, video_id, duration_ms, e,
        )
        return None


async def get_queue_health() -> dict:
    """Diagnostico simples da fila (sem Prometheus): conectividade e
    tamanho atual do stream (mensagens ainda nao consumidas/confirmadas).
    Usado por GET /api/v1/worker/queue/health (admin-only)."""
    client = get_redis_client()
    try:
        length = await client.xlen(PROCESSING_JOBS_STREAM)
        return {
            "connected": True,
            "stream": PROCESSING_JOBS_STREAM,
            "stream_length": length,
        }
    except Exception as e:
        logger.error("queue_health_check_failed error=%s", e)
        return {
            "connected": False,
            "stream": PROCESSING_JOBS_STREAM,
            "stream_length": None,
        }
