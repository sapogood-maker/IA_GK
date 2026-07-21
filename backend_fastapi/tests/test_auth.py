"""Testes do fluxo de autenticacao: registro, bootstrap do primeiro admin,
login, refresh (rotacao) e protecao de /me."""
from tests.conftest import auth_header, register_user


async def test_bootstrap_first_user_becomes_admin(client):
    token = await register_user(client, "admin@example.com")

    me = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["role"] == "system_admin"
    assert me.json()["club_id"] is None


async def test_cannot_self_elevate_to_admin_after_bootstrap(client):
    await register_user(client, "admin@example.com")

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "hacker@example.com",
            "name": "Hacker",
            "password": "senha123",
            "role": "system_admin",
        },
    )
    assert response.status_code == 400


async def test_non_admin_registration_requires_existing_club(client):
    await register_user(client, "admin@example.com")

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sem_clube@example.com",
            "name": "Sem Clube",
            "password": "senha123",
            "role": "treinador",
        },
    )
    assert response.status_code == 400


async def test_non_admin_registration_rejects_unknown_club(client):
    await register_user(client, "admin@example.com")

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "fantasma@example.com",
            "name": "Fantasma",
            "password": "senha123",
            "role": "treinador",
            "club_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert response.status_code == 400


async def test_login_success(client):
    await register_user(client, "admin@example.com", password="senha123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "senha123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_invalid_password(client):
    await register_user(client, "admin@example.com", password="senha123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "senha_errada"},
    )
    assert response.status_code == 401


async def test_refresh_rotates_token(client):
    await register_user(client, "admin@example.com", password="senha123")
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "senha123"},
    )
    old_refresh_token = login.json()["refresh_token"]

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert refreshed.status_code == 200
    # O refresh_token e sempre rotacionado (novo a cada uso). O access_token
    # novo nao precisa necessariamente diferir byte a byte do anterior (nao
    # ha claim de unicidade nele, e isso nao importa para um token de vida
    # curta) - o que importa e que ele funciona.
    assert refreshed.json()["refresh_token"] != old_refresh_token

    me = await client.get(
        "/api/v1/auth/me", headers=auth_header(refreshed.json()["access_token"])
    )
    assert me.status_code == 200


async def test_refresh_with_invalid_token(client):
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "token-invalido"}
    )
    assert response.status_code == 401


async def test_me_requires_authentication(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_rejects_garbage_token(client):
    response = await client.get(
        "/api/v1/auth/me", headers=auth_header("token-nao-jwt")
    )
    assert response.status_code == 401
