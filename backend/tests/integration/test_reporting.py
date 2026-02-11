from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.cache import cache
from app.core.config import get_settings
from fastapi.testclient import TestClient


def _create_account(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": "Reporting Account",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "USD",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_category(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/categories",
        json={"name": "Food", "is_income": False, "color": "#6A8CAF"},
    )
    assert response.status_code == 201
    return response.json()


def _create_transaction(
    client: TestClient,
    account_id: str,
    *,
    amount: str,
    direction: str,
    category_id: str | None = None,
    occurred_at: datetime | None = None,
) -> dict[str, str]:
    response = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "category_id": category_id,
            "amount": amount,
            "direction": direction,
            "occurred_at": (occurred_at or datetime.now(UTC)).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()


def test_reporting_dashboard_summary(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client)
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="120.00",
        direction="IN",
    )
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="45.00",
        direction="OUT",
    )

    response = authenticated_client.get("/api/v1/reporting/dashboard?period=month")
    assert response.status_code == 200
    payload = response.json()
    assert Decimal(payload["income"]) == Decimal("120.00")
    assert Decimal(payload["expenses"]) == Decimal("45.00")
    assert Decimal(payload["net"]) == Decimal("75.00")
    assert payload["account_count"] == 1
    assert len(payload["accounts"]) == 1


def test_reporting_dashboard_custom_range(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client)
    now = datetime.now(UTC)
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="80.00",
        direction="IN",
        occurred_at=now - timedelta(days=1),
    )

    response = authenticated_client.get(
        "/api/v1/reporting/dashboard",
        params={
            "period": "custom",
            "from_date": (now - timedelta(days=2)).isoformat(),
            "to_date": now.isoformat(),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "custom"


def test_reporting_cashflow_trend(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client)
    now = datetime.now(UTC)
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="25.00",
        direction="OUT",
        occurred_at=now - timedelta(days=2),
    )
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="100.00",
        direction="IN",
        occurred_at=now - timedelta(days=1),
    )

    response = authenticated_client.get(
        "/api/v1/reporting/cashflow",
        params={
            "from_date": (now - timedelta(days=3)).isoformat(),
            "to_date": now.isoformat(),
            "granularity": "day",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["granularity"] == "day"
    assert len(payload["points"]) >= 2


def test_reporting_category_breakdown(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client)
    category = _create_category(authenticated_client)
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="20.00",
        direction="OUT",
        category_id=category["id"],
    )
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="30.00",
        direction="OUT",
        category_id=category["id"],
    )

    now = datetime.now(UTC)
    response = authenticated_client.get(
        "/api/v1/reporting/categories",
        params={
            "from_date": (now - timedelta(days=30)).isoformat(),
            "to_date": now.isoformat(),
            "breakdown_type": "expense",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert Decimal(payload["total"]) == Decimal("50.00")
    assert len(payload["categories"]) >= 1
    assert payload["categories"][0]["category_name"] == "Food"


def test_reporting_category_trend(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client)
    category = _create_category(authenticated_client)
    now = datetime.now(UTC)
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="12.00",
        direction="OUT",
        category_id=category["id"],
        occurred_at=now - timedelta(days=3),
    )
    _create_transaction(
        authenticated_client,
        account["id"],
        amount="22.00",
        direction="OUT",
        category_id=category["id"],
        occurred_at=now - timedelta(days=1),
    )

    response = authenticated_client.get(
        "/api/v1/reporting/category-trend",
        params={
            "from_date": (now - timedelta(days=7)).isoformat(),
            "to_date": now.isoformat(),
            "granularity": "day",
            "breakdown_type": "expense",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["breakdown_type"] == "expense"
    assert len(payload["points"]) >= 1


def test_reporting_cache_invalidation_on_transaction_write(
    authenticated_client: TestClient,
) -> None:
    account = _create_account(authenticated_client)

    initial = authenticated_client.get("/api/v1/reporting/dashboard?period=month")
    assert initial.status_code == 200
    initial_income = Decimal(initial.json()["income"])

    _create_transaction(
        authenticated_client,
        account["id"],
        amount="200.00",
        direction="IN",
    )

    updated = authenticated_client.get("/api/v1/reporting/dashboard?period=month")
    assert updated.status_code == 200
    updated_income = Decimal(updated.json()["income"])
    assert updated_income >= initial_income + Decimal("200.00")


def test_reporting_rate_limit_unavailable_fails_open(
    authenticated_client: TestClient,
    monkeypatch,
) -> None:
    async def unavailable_increment(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(cache, "increment_with_ttl", unavailable_increment)

    settings = get_settings()
    original_fail_closed = settings.rate_limit_reporting_fail_closed
    settings.rate_limit_reporting_fail_closed = False
    try:
        response = authenticated_client.get("/api/v1/reporting/dashboard?period=month")
        assert response.status_code == 200
    finally:
        settings.rate_limit_reporting_fail_closed = original_fail_closed


def test_reporting_rate_limit_unavailable_fails_closed_when_enabled(
    authenticated_client: TestClient,
    monkeypatch,
) -> None:
    async def unavailable_increment(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(cache, "increment_with_ttl", unavailable_increment)

    settings = get_settings()
    original_fail_closed = settings.rate_limit_reporting_fail_closed
    settings.rate_limit_reporting_fail_closed = True
    try:
        response = authenticated_client.get("/api/v1/reporting/dashboard?period=month")
        assert response.status_code == 503
        assert response.json()["code"] == "rate_limit_unavailable"
    finally:
        settings.rate_limit_reporting_fail_closed = original_fail_closed
