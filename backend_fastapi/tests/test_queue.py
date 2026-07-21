"""Testes da fila (Redis Streams) - so publisher, sem consumer (ver
app/core/queue.py). Usa um Redis de teste real (nao mockado), do mesmo
jeito que os testes de banco usam um Postgres real."""
from app.core.queue import PROCESSING_JOBS_STREAM, get_queue_health, get_redis_client, publish_processing_job
from tests.conftest import auth_header, register_user


async def test_publish_processing_job_writes_to_stream():
    message_id = await publish_processing_job("job-123", "video-456")
    assert message_id is not None

    client = get_redis_client()
    entries = await client.xrange(PROCESSING_JOBS_STREAM)
    assert len(entries) == 1
    _, fields = entries[0]
    assert fields["job_id"] == "job-123"
    assert fields["video_id"] == "video-456"


async def test_publish_processing_job_increments_stream_length():
    await publish_processing_job("job-1", "video-1")
    await publish_processing_job("job-2", "video-2")

    client = get_redis_client()
    length = await client.xlen(PROCESSING_JOBS_STREAM)
    assert length == 2


async def test_get_queue_health_reflects_published_jobs():
    await publish_processing_job("job-1", "video-1")

    health = await get_queue_health()
    assert health["connected"] is True
    assert health["stream_length"] == 1
    assert health["stream"] == PROCESSING_JOBS_STREAM


async def test_queue_health_endpoint_reflects_real_queue_state(client):
    admin_token = await register_user(client, "admin@example.com")

    await publish_processing_job("job-1", "video-1")
    await publish_processing_job("job-2", "video-2")

    response = await client.get(
        "/api/v1/queue/health", headers=auth_header(admin_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["stream_length"] == 2
