"""Testes de autenticacao do Worker: API Key exigida, separacao completa
do JWT humano (nenhum mecanismo funciona no lugar do outro)."""
import pytest

from tests.conftest import auth_header, register_user, worker_auth_header


@pytest.fixture
async def job_setup(client):
    """Cria clube/goleiro/sessao/video/job via o admin (bypassa checagem de
    clube) - usa os endpoints "legacy" (POST /videos, POST /processing-jobs)
    para nao depender de credenciais reais do R2 nos testes."""
    admin_token = await register_user(client, "admin@example.com")
    headers = auth_header(admin_token)

    club = (await client.post("/api/v1/clubs", json={"name": "Clube A"}, headers=headers)).json()
    gk = (
        await client.post(
            "/api/v1/goalkeepers",
            json={"club_id": club["id"], "name": "Goleiro"},
            headers=headers,
        )
    ).json()
    session = (
        await client.post(
            "/api/v1/training-sessions",
            json={
                "goalkeeper_id": gk["id"],
                "title": "Treino",
                "session_type": "Tecnico",
                "session_date": "2026-01-01T10:00:00Z",
            },
            headers=headers,
        )
    ).json()
    video = (
        await client.post(
            "/api/v1/videos",
            json={
                "training_session_id": session["id"],
                "filename": "treino.mp4",
                "r2_bucket": "goalkeeper-ai-videos",
                "r2_key": f"videos/{gk['id']}/2026/01/treino.mp4",
                "r2_url": "https://example.r2.cloudflarestorage.com/treino.mp4",
                "upload_status": "UPLOADED",
            },
            headers=headers,
        )
    ).json()
    job = (
        await client.post(
            "/api/v1/processing-jobs",
            json={"video_id": video["id"], "job_type": "video_processing"},
            headers=headers,
        )
    ).json()

    return {"admin_token": admin_token, "video": video, "job": job}


async def test_worker_endpoint_rejects_missing_api_key(client, job_setup):
    response = await client.get(f"/api/v1/worker/jobs/{job_setup['job']['id']}")
    assert response.status_code == 401


async def test_worker_endpoint_rejects_wrong_api_key(client, job_setup):
    response = await client.get(
        f"/api/v1/worker/jobs/{job_setup['job']['id']}",
        headers={"X-Worker-Api-Key": "chave-errada"},
    )
    assert response.status_code == 401


async def test_worker_endpoint_accepts_valid_api_key(client, job_setup):
    response = await client.get(
        f"/api/v1/worker/jobs/{job_setup['job']['id']}", headers=worker_auth_header()
    )
    assert response.status_code == 200
    assert response.json()["id"] == job_setup["job"]["id"]


async def test_worker_endpoint_rejects_human_jwt(client, job_setup):
    """Um JWT de usuario valido nao deve funcionar nos endpoints do
    Worker - os dois mecanismos de autenticacao sao completamente
    separados."""
    response = await client.get(
        f"/api/v1/worker/jobs/{job_setup['job']['id']}",
        headers=auth_header(job_setup["admin_token"]),
    )
    assert response.status_code == 401


async def test_human_endpoint_rejects_worker_api_key(client, job_setup):
    """A API Key do Worker nao deve funcionar em endpoints humanos."""
    response = await client.get(
        f"/api/v1/processing-jobs/{job_setup['job']['id']}", headers=worker_auth_header()
    )
    assert response.status_code == 401


async def test_queue_health_requires_admin_jwt_not_api_key(client, job_setup):
    # API Key nao funciona no endpoint de diagnostico (feito para humanos)
    response = await client.get("/api/v1/queue/health", headers=worker_auth_header())
    assert response.status_code == 401

    # JWT de admin funciona
    response = await client.get(
        "/api/v1/queue/health", headers=auth_header(job_setup["admin_token"])
    )
    assert response.status_code == 200
