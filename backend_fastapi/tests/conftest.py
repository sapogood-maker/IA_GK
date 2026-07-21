"""Configuracao compartilhada dos testes automatizados.

Usa um banco de teste separado (nunca o banco de desenvolvimento/producao).
O schema e recriado do zero antes de cada teste via Base.metadata.create_all
- essa e uma excecao deliberada e isolada aos testes: a aplicacao em si
(app/main.py) nao usa mais create_all, so o Alembic (ver SPRINT6_REPORT.md).
Recriar via create_all aqui mantem os testes rapidos e independentes do
historico de migrations.
"""
import asyncio
import os

import pytest

# Precisa ser definido ANTES de importar qualquer modulo de app/, pois
# app.core.config.get_settings() e cacheado (lru_cache) na primeira chamada.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://goalkeeper_user:goalkeeper_pass@localhost:5433/goalkeeper_ai_test",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-automated-tests-32-chars-long")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("WORKER_API_KEY", "test-worker-api-key-for-automated-tests")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.queue import get_redis_client  # noqa: E402
from app.db.base import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

_engine = create_async_engine(TEST_DATABASE_URL, future=True)
_TestSessionLocal = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """O AsyncEngine acima e criado uma unica vez, atrelado ao event loop
    ativo nesse momento. Sem isso, o event loop padrao do pytest-asyncio
    (escopo de funcao) muda a cada teste e quebra o pool de conexoes do
    asyncpg ("cannot perform operation: another operation is in progress")."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def _reset_schema():
    """Recria o schema do zero antes de cada teste - garante isolamento
    total entre testes sem depender de rollback de transacao."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(autouse=True)
async def _reset_redis():
    """Limpa o Redis de teste antes de cada teste - mesmo principio do
    _reset_schema, para os testes de fila (app/core/queue.py) nao
    interferirem uns nos outros."""
    client = get_redis_client()
    await client.flushdb()
    yield


@pytest_asyncio.fixture
async def client():
    async def _override_get_db():
        async with _TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def worker_auth_header() -> dict:
    return {"X-Worker-Api-Key": os.environ["WORKER_API_KEY"]}


async def register_user(client, email, password="senha123", name="Usuario Teste", role=None, club_id=None):
    """Helper reutilizado pelos testes de autorizacao: registra um usuario e
    devolve o access_token."""
    payload = {"email": email, "name": name, "password": password}
    if role is not None:
        payload["role"] = role
    if club_id is not None:
        payload["club_id"] = club_id
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
