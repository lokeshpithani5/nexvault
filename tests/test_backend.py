import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.init_db import init_db


@pytest_asyncio.fixture(autouse=True)
async def initialize_db():
    await init_db()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Verify health endpoint returns status HEALTHY and database connected."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "CONNECTED" in data["database"]
    assert data["storage_nodes"]["registered"] == 6


@pytest.mark.asyncio
async def test_valid_login(client: AsyncClient):
    """Verify valid login returns JWT access token and user metadata."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.INITIAL_ADMIN_EMAIL,
            "password": settings.INITIAL_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == settings.INITIAL_ADMIN_EMAIL
    assert data["user"]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient):
    """Verify invalid password returns 401 Unauthorized with structured error."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.INITIAL_ADMIN_EMAIL,
            "password": "WrongPassword999!",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"] is True
    assert data["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_signup_and_me_endpoint(client: AsyncClient):
    """Verify user registration, login, and current-user /me endpoint."""
    user_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    signup_res = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": user_email,
            "password": "SecurePassword123!",
            "full_name": "Test User",
        },
    )
    assert signup_res.status_code == 201
    user_data = signup_res.json()
    assert user_data["email"] == user_email
    assert user_data["role"] == "USER"

    # Login with new credentials
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": user_email,
            "password": "SecurePassword123!",
        },
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Call /me endpoint with Bearer token
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == user_email
    assert me_res.json()["role"] == "USER"


@pytest.mark.asyncio
async def test_admin_access(client: AsyncClient):
    """Verify admin user can access protected cluster admin endpoints."""
    # Login as admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.INITIAL_ADMIN_EMAIL,
            "password": settings.INITIAL_ADMIN_PASSWORD,
        },
    )
    admin_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Access cluster nodes
    nodes_res = await client.get("/api/v1/admin/nodes", headers=headers)
    assert nodes_res.status_code == 200
    nodes = nodes_res.json()
    assert len(nodes) == 6
    assert any(n["port"] == 5001 and n["zone"] == "Zone-A" for n in nodes)
    assert any(n["port"] == 5004 and n["zone"] == "Zone-B" for n in nodes)

    # Access cluster stats
    stats_res = await client.get("/api/v1/admin/nodes/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_nodes"] == 6

    # Access Chaos Lab operation as admin
    chaos_res = await client.post(
        "/api/v1/admin/chaos/scan-integrity",
        headers=headers,
    )
    assert chaos_res.status_code == 200
    assert chaos_res.json()["success"] is True


@pytest.mark.asyncio
async def test_user_blocked_from_admin_endpoint(client: AsyncClient):
    """Verify standard USER is blocked (403 Forbidden) from admin & Chaos Lab endpoints."""
    user_email = f"bob_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": user_email,
            "password": "BobPassword123!",
            "full_name": "Bob User",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": user_email,
            "password": "BobPassword123!",
        },
    )
    user_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    # Attempt to access admin nodes
    blocked_nodes = await client.get("/api/v1/admin/nodes", headers=headers)
    assert blocked_nodes.status_code == 403
    assert blocked_nodes.json()["code"] == "PERMISSION_DENIED"

    # Attempt to trigger Chaos Lab
    blocked_chaos = await client.post("/api/v1/admin/chaos/scan-integrity", headers=headers)
    assert blocked_chaos.status_code == 403
    assert blocked_chaos.json()["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_unauthorized_object_access(client: AsyncClient):
    """Verify that User A cannot access or list objects in User B's bucket."""
    email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
    email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"
    bucket_name = f"bucket-{uuid.uuid4().hex[:8]}"

    # Create User A
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email_a, "password": "PasswordUserA123!", "full_name": "User A"},
    )
    token_a = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": email_a, "password": "PasswordUserA123!"},
        )
    ).json()["access_token"]

    # Create User B
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email_b, "password": "PasswordUserB123!", "full_name": "User B"},
    )
    token_b = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": email_b, "password": "PasswordUserB123!"},
        )
    ).json()["access_token"]

    # User A creates a bucket
    create_bucket_res = await client.post(
        "/api/v1/buckets",
        json={"name": bucket_name},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_bucket_res.status_code == 201

    # User B attempts to access User A's bucket objects -> 403 Forbidden
    unauthorized_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert unauthorized_res.status_code == 403
    assert unauthorized_res.json()["code"] == "PERMISSION_DENIED"
