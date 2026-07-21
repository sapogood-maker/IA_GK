"""Testes funcionais dos endpoints do Worker: detalhes do job, atualizacao
de status e URLs assinadas (R2 mockado - nao dependem de credenciais reais
do R2, pois o objetivo e validar o endpoint, nao o R2Service em si, que ja
e testado manualmente nas sprints anteriores)."""
from app.core.r2 import get_r2_service
from app.main import app
from tests.conftest import auth_header, register_user, worker_auth_header
from tests.test_worker_auth import job_setup  # noqa: F401 (reaproveita a fixture)


class FakeR2Service:
    """Substitui o R2Service real via dependency override - sem chamadas
    de rede, sem precisar de credenciais reais do R2."""

    async def generate_presigned_url(self, r2_key, expiration_seconds=3600):
        return f"https://fake-r2.example.com/{r2_key}?download&exp={expiration_seconds}"

    async def generate_presigned_upload_url(self, r2_key, expiration_seconds=3600, content_type="application/octet-stream"):
        return f"https://fake-r2.example.com/{r2_key}?upload&exp={expiration_seconds}&ct={content_type}"


async def test_get_job_details(client, job_setup):
    response = await client.get(
        f"/api/v1/worker/jobs/{job_setup['job']['id']}", headers=worker_auth_header()
    )
    assert response.status_code == 200
    assert response.json()["video_id"] == job_setup["video"]["id"]


async def test_get_job_details_not_found(client, job_setup):
    response = await client.get(
        "/api/v1/worker/jobs/00000000-0000-0000-0000-000000000000",
        headers=worker_auth_header(),
    )
    assert response.status_code == 404


async def test_update_job_status_to_running_sets_started_at(client, job_setup):
    response = await client.put(
        f"/api/v1/worker/jobs/{job_setup['job']['id']}/status",
        json={"status": "DOWNLOADING", "progress": 5.0, "worker_id": "worker-01"},
        headers=worker_auth_header(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DOWNLOADING"
    assert body["progress"] == 5.0
    assert body["worker_id"] == "worker-01"
    assert body["started_at"] is not None
    assert body["completed_at"] is None


async def test_update_job_status_to_completed_sets_completed_at(client, job_setup):
    response = await client.put(
        f"/api/v1/worker/jobs/{job_setup['job']['id']}/status",
        json={"status": "COMPLETED", "progress": 100.0},
        headers=worker_auth_header(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["completed_at"] is not None


async def test_update_job_status_to_failed_records_error_message(client, job_setup):
    response = await client.put(
        f"/api/v1/worker/jobs/{job_setup['job']['id']}/status",
        json={"status": "FAILED", "error_message": "modelo indisponivel"},
        headers=worker_auth_header(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["error_message"] == "modelo indisponivel"
    assert body["completed_at"] is not None


async def test_download_url_uses_video_r2_key(client, job_setup):
    app.dependency_overrides[get_r2_service] = lambda: FakeR2Service()
    try:
        response = await client.post(
            f"/api/v1/worker/jobs/{job_setup['job']['id']}/download-url",
            headers=worker_auth_header(),
        )
    finally:
        del app.dependency_overrides[get_r2_service]

    assert response.status_code == 200
    body = response.json()
    assert job_setup["video"]["r2_key"] in body["url"]
    assert body["expires_in_seconds"] == 3600


async def test_upload_url_generates_scoped_artifact_key(client, job_setup):
    app.dependency_overrides[get_r2_service] = lambda: FakeR2Service()
    try:
        response = await client.post(
            f"/api/v1/worker/jobs/{job_setup['job']['id']}/artifacts/upload-url",
            json={"filename": "thumbnail_01.jpg", "content_type": "image/jpeg"},
            headers=worker_auth_header(),
        )
    finally:
        del app.dependency_overrides[get_r2_service]

    assert response.status_code == 200
    body = response.json()
    assert job_setup["job"]["id"] in body["r2_key"]
    assert "thumbnail_01.jpg" in body["r2_key"]
    assert body["r2_key"] in body["url"]


async def test_non_admin_user_still_cannot_call_worker_endpoints(client, job_setup):
    """Reforca a separacao: mesmo um usuario humano nao-admin (com JWT
    valido) nao acessa endpoints do Worker."""
    club = (
        await client.get("/api/v1/clubs", headers=auth_header(job_setup["admin_token"]))
    ).json()[0]
    treinador_token = await register_user(
        client, "treinador@example.com", role="treinador", club_id=club["id"]
    )
    response = await client.get(
        f"/api/v1/worker/jobs/{job_setup['job']['id']}",
        headers=auth_header(treinador_token),
    )
    assert response.status_code == 401
