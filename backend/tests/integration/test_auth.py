from uuid import uuid4

from app.core.config import get_settings
from fastapi.testclient import TestClient


def _unique_email() -> str:
    return f"user-{uuid4().hex}@example.com"


def _register(client: TestClient, email: str, password: str = "password123") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201


def test_register_success(client: TestClient) -> None:
    email = _unique_email()
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == email
    assert payload["id"]
    assert payload["created_at"]
    assert payload["updated_at"]


def test_register_duplicate_email(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_already_exists"


def test_login_sets_session_cookie(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    cookie_name = get_settings().cookie_name
    assert response.cookies.get(cookie_name) is not None


def test_login_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": _unique_email(), "password": "password123"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_error"


def test_me_after_login_returns_user(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


def test_logout_revokes_session(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "ok"}

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 401
