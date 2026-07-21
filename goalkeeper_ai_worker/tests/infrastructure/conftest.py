"""Fixtures dos testes de infraestrutura - usam um Redis REAL e descartavel
(nunca mockado), mesma disciplina de validacao ja usada no backend."""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import redis.asyncio as redis

TEST_REDIS_URL = "redis://localhost:6381/0"


@pytest.fixture
async def redis_client() -> AsyncIterator["redis.Redis"]:
    """Cliente Redis real, contra um container descartavel de teste."""
    client = redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()
