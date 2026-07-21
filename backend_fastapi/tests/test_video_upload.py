"""Testes de upload de video: validacao de arquivo (unitario, sem R2 real) e
autorizacao do endpoint de upload (403 antes de qualquer chamada ao R2)."""
from types import SimpleNamespace

from app.services.video_upload_service import VideoUploadService
from tests.conftest import auth_header, register_user


def _make_service():
    """VideoUploadService so precisa de settings para _validate_file - nao
    precisa de db/r2_service reais para este teste unitario."""
    service = VideoUploadService.__new__(VideoUploadService)
    service.settings = SimpleNamespace(
        allowed_video_extensions_list=["mp4", "mov", "avi", "mkv"]
    )
    return service


def test_validate_file_accepts_allowed_extension():
    service = _make_service()
    upload = SimpleNamespace(filename="treino.mp4", content_type="video/mp4")
    is_valid, error = service._validate_file(upload)
    assert is_valid is True
    assert error is None


def test_validate_file_rejects_disallowed_extension():
    service = _make_service()
    upload = SimpleNamespace(filename="documento.pdf", content_type="application/pdf")
    is_valid, error = service._validate_file(upload)
    assert is_valid is False
    assert "extension" in error.lower()


def test_validate_file_rejects_non_video_mime_type():
    service = _make_service()
    upload = SimpleNamespace(filename="treino.mp4", content_type="image/png")
    is_valid, error = service._validate_file(upload)
    assert is_valid is False
    assert "mime" in error.lower()


def test_validate_file_rejects_missing_filename():
    service = _make_service()
    upload = SimpleNamespace(filename="", content_type="video/mp4")
    is_valid, error = service._validate_file(upload)
    assert is_valid is False


async def test_upload_requires_authentication(client):
    response = await client.post(
        "/api/v1/videos/upload",
        params={"training_session_id": "00000000-0000-0000-0000-000000000000"},
        files={"file": ("treino.mp4", b"conteudo", "video/mp4")},
    )
    assert response.status_code == 401


async def test_upload_rejects_session_from_other_club(client):
    admin_token = await register_user(client, "admin@example.com")
    club_a = (
        await client.post(
            "/api/v1/clubs", json={"name": "Clube A"}, headers=auth_header(admin_token)
        )
    ).json()
    club_b = (
        await client.post(
            "/api/v1/clubs", json={"name": "Clube B"}, headers=auth_header(admin_token)
        )
    ).json()
    treinador_a_token = await register_user(
        client, "treinador_a@example.com", role="treinador", club_id=club_a["id"]
    )

    gk_b = (
        await client.post(
            "/api/v1/goalkeepers",
            json={"club_id": club_b["id"], "name": "Goleiro B"},
            headers=auth_header(admin_token),
        )
    ).json()
    session_b = (
        await client.post(
            "/api/v1/training-sessions",
            json={
                "goalkeeper_id": gk_b["id"],
                "title": "Treino B",
                "session_type": "Tecnico",
                "session_date": "2026-01-01T10:00:00Z",
            },
            headers=auth_header(admin_token),
        )
    ).json()

    # O check de autorizacao roda antes de qualquer chamada ao R2, entao
    # este teste nao precisa de credenciais reais do R2.
    response = await client.post(
        "/api/v1/videos/upload",
        params={"training_session_id": session_b["id"]},
        files={"file": ("invasao.mp4", b"conteudo", "video/mp4")},
        headers=auth_header(treinador_a_token),
    )
    assert response.status_code == 403
