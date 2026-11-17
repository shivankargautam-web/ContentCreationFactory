import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_register_login_me_refresh(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": "First@Example.com", "password": "Password1"}
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"  # first user bootstraps as admin
    assert resp.json()["email"] == "first@example.com"

    second = await client.post(
        "/api/v1/auth/register", json={"email": "b@example.com", "password": "Password1"}
    )
    assert second.json()["role"] == "editor"

    tokens = (
        await client.post("/api/v1/auth/login", json={"email": "first@example.com", "password": "Password1"})
    ).json()
    assert tokens["token_type"] == "bearer" and tokens["expires_in"] > 0
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "first@example.com"

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    bad = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401


async def test_auth_errors(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "Password1"})
    dup = await client.post("/api/v1/auth/register", json={"email": "A@example.com", "password": "Password1"})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "email_taken"
    wrong = await client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "nope"})
    assert wrong.status_code == 401
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    weak = await client.post("/api/v1/auth/register", json={"email": "c@example.com", "password": "short"})
    assert weak.status_code == 422


async def test_admin_role_management(client: AsyncClient, admin_headers: dict, editor_headers: dict) -> None:
    users = (await client.get("/api/v1/users", headers=admin_headers)).json()
    assert users["total"] == 2
    editor = next(u for u in users["items"] if u["email"] == "editor@example.com")
    assert (await client.get("/api/v1/users", headers=editor_headers)).status_code == 403
    resp = await client.patch(
        f"/api/v1/users/{editor['id']}/role", json={"role": "viewer"}, headers=admin_headers
    )
    assert resp.status_code == 200 and resp.json()["role"] == "viewer"


async def test_health(client: AsyncClient) -> None:
    assert (await client.get("/health/live")).json() == {"status": "ok"}
    ready = await client.get("/health/ready")
    assert ready.status_code == 200 and ready.json()["checks"]["database"] == "ok"
