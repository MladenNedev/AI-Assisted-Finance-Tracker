from uuid import uuid4

from app.core.cache import cache
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


def _csrf_headers(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    token = client.cookies.get(settings.csrf_cookie_name)
    return {settings.csrf_header_name: token} if token else {}


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
    settings = get_settings()
    assert response.cookies.get(settings.cookie_name) is not None
    assert response.cookies.get(settings.csrf_cookie_name) is not None
    assert settings.csrf_header_name in response.headers


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

    logout_response = client.post("/api/v1/auth/logout", headers=_csrf_headers(client))
    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "ok"}

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


def test_mutating_request_requires_csrf_header(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200

    missing_header = client.post(
        "/api/v1/accounts",
        json={
            "name": "No CSRF",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "USD",
        },
    )
    assert missing_header.status_code == 403
    assert missing_header.json()["code"] == "csrf_invalid"


def test_login_rate_limit_enforced(client: TestClient) -> None:
    settings = get_settings()
    original_limit = settings.rate_limit_login_limit
    original_window = settings.rate_limit_login_window_seconds

    settings.rate_limit_login_limit = 2
    settings.rate_limit_login_window_seconds = 60
    try:
        email = _unique_email()
        _register(client, email)
        forwarded_ip = f"198.51.100.{(int(uuid4().hex[:2], 16) % 200) + 1}"
        headers = {"X-Forwarded-For": forwarded_ip}

        first = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-password"},
            headers=headers,
        )
        second = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-password"},
            headers=headers,
        )
        third = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-password"},
            headers=headers,
        )

        assert first.status_code == 401
        assert second.status_code == 401
        assert third.status_code == 429
        assert third.json()["code"] == "rate_limited"
    finally:
        settings.rate_limit_login_limit = original_limit
        settings.rate_limit_login_window_seconds = original_window


def test_login_rate_limit_unavailable_fails_closed(
    client: TestClient,
    monkeypatch,
) -> None:
    email = _unique_email()
    _register(client, email)

    async def unavailable_increment(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(cache, "increment_with_ttl", unavailable_increment)

    settings = get_settings()
    original_fail_closed = settings.rate_limit_auth_fail_closed
    settings.rate_limit_auth_fail_closed = True
    try:
        forwarded_ip = f"198.51.100.{(int(uuid4().hex[:2], 16) % 200) + 1}"
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
            headers={"X-Forwarded-For": forwarded_ip},
        )
        assert response.status_code == 503
        assert response.json()["code"] == "rate_limit_unavailable"
    finally:
        settings.rate_limit_auth_fail_closed = original_fail_closed
