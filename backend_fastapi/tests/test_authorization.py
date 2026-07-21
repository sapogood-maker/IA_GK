"""Testes de autorizacao: isolamento entre clubes, bypass de SYSTEM_ADMIN e
restricoes de papel (CRUD, R2, listagem de usuarios)."""
import pytest

from tests.conftest import auth_header, register_user


@pytest.fixture
async def setup(client):
    """Cria 2 clubes (A e B) e um treinador vinculado ao clube A."""
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

    return {
        "admin_token": admin_token,
        "club_a": club_a,
        "club_b": club_b,
        "treinador_a_token": treinador_a_token,
    }


# --- Clubes ---


async def test_non_admin_cannot_create_club(client, setup):
    response = await client.post(
        "/api/v1/clubs",
        json={"name": "Clube C"},
        headers=auth_header(setup["treinador_a_token"]),
    )
    assert response.status_code == 403


async def test_treinador_lists_only_own_club(client, setup):
    response = await client.get(
        "/api/v1/clubs", headers=auth_header(setup["treinador_a_token"])
    )
    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert ids == [setup["club_a"]["id"]]


async def test_treinador_cannot_get_other_club_by_id(client, setup):
    response = await client.get(
        f"/api/v1/clubs/{setup['club_b']['id']}",
        headers=auth_header(setup["treinador_a_token"]),
    )
    assert response.status_code == 403


# --- Goleiros ---


async def test_treinador_creates_goalkeeper_in_own_club(client, setup):
    response = await client.post(
        "/api/v1/goalkeepers",
        json={"club_id": setup["club_a"]["id"], "name": "Goleiro A"},
        headers=auth_header(setup["treinador_a_token"]),
    )
    assert response.status_code == 201


async def test_treinador_cannot_create_goalkeeper_in_other_club(client, setup):
    response = await client.post(
        "/api/v1/goalkeepers",
        json={"club_id": setup["club_b"]["id"], "name": "Invasor"},
        headers=auth_header(setup["treinador_a_token"]),
    )
    assert response.status_code == 403


async def test_treinador_lists_only_own_club_goalkeepers(client, setup):
    await client.post(
        "/api/v1/goalkeepers",
        json={"club_id": setup["club_a"]["id"], "name": "Goleiro A"},
        headers=auth_header(setup["treinador_a_token"]),
    )
    await client.post(
        "/api/v1/goalkeepers",
        json={"club_id": setup["club_b"]["id"], "name": "Goleiro B"},
        headers=auth_header(setup["admin_token"]),
    )

    response = await client.get(
        "/api/v1/goalkeepers", headers=auth_header(setup["treinador_a_token"])
    )
    assert response.status_code == 200
    names = [g["name"] for g in response.json()]
    assert names == ["Goleiro A"]


async def test_treinador_cannot_get_other_club_goalkeeper_by_id(client, setup):
    gk_b = (
        await client.post(
            "/api/v1/goalkeepers",
            json={"club_id": setup["club_b"]["id"], "name": "Goleiro B"},
            headers=auth_header(setup["admin_token"]),
        )
    ).json()

    response = await client.get(
        f"/api/v1/goalkeepers/{gk_b['id']}",
        headers=auth_header(setup["treinador_a_token"]),
    )
    assert response.status_code == 403


async def test_admin_sees_all_goalkeepers(client, setup):
    await client.post(
        "/api/v1/goalkeepers",
        json={"club_id": setup["club_a"]["id"], "name": "Goleiro A"},
        headers=auth_header(setup["treinador_a_token"]),
    )
    await client.post(
        "/api/v1/goalkeepers",
        json={"club_id": setup["club_b"]["id"], "name": "Goleiro B"},
        headers=auth_header(setup["admin_token"]),
    )

    response = await client.get(
        "/api/v1/goalkeepers", headers=auth_header(setup["admin_token"])
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- Sessoes de treino (escopo transitivo via Goalkeeper) ---


async def test_treinador_cannot_create_session_for_other_club_goalkeeper(client, setup):
    gk_b = (
        await client.post(
            "/api/v1/goalkeepers",
            json={"club_id": setup["club_b"]["id"], "name": "Goleiro B"},
            headers=auth_header(setup["admin_token"]),
        )
    ).json()

    response = await client.post(
        "/api/v1/training-sessions",
        json={
            "goalkeeper_id": gk_b["id"],
            "title": "Invasao",
            "session_type": "Tecnico",
            "session_date": "2026-01-01T10:00:00Z",
        },
        headers=auth_header(setup["treinador_a_token"]),
    )
    assert response.status_code == 403


async def test_treinador_lists_only_own_club_sessions(client, setup):
    gk_a = (
        await client.post(
            "/api/v1/goalkeepers",
            json={"club_id": setup["club_a"]["id"], "name": "Goleiro A"},
            headers=auth_header(setup["treinador_a_token"]),
        )
    ).json()
    await client.post(
        "/api/v1/training-sessions",
        json={
            "goalkeeper_id": gk_a["id"],
            "title": "Treino 1",
            "session_type": "Tecnico",
            "session_date": "2026-01-01T10:00:00Z",
        },
        headers=auth_header(setup["treinador_a_token"]),
    )

    response = await client.get(
        "/api/v1/training-sessions", headers=auth_header(setup["treinador_a_token"])
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


# --- Endpoints admin-only ---


async def test_non_admin_cannot_list_users(client, setup):
    response = await client.get(
        "/api/v1/users", headers=auth_header(setup["treinador_a_token"])
    )
    assert response.status_code == 403


async def test_admin_lists_all_users(client, setup):
    response = await client.get(
        "/api/v1/users", headers=auth_header(setup["admin_token"])
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_user_cannot_get_another_users_profile(client, setup):
    admin_me = await client.get(
        "/api/v1/auth/me", headers=auth_header(setup["admin_token"])
    )
    admin_id = admin_me.json()["id"]

    response = await client.get(
        f"/api/v1/users/{admin_id}", headers=auth_header(setup["treinador_a_token"])
    )
    assert response.status_code == 403


async def test_non_admin_cannot_access_r2_health(client, setup):
    response = await client.get(
        "/api/v1/r2/health", headers=auth_header(setup["treinador_a_token"])
    )
    assert response.status_code == 403
