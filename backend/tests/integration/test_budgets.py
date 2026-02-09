from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient


def _current_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _previous_month() -> str:
    today = datetime.now(UTC).date()
    if today.month == 1:
        return f"{today.year - 1}-12"
    return f"{today.year}-{today.month - 1:02d}"


def _create_account(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": "Budget Account",
            "account_type": "CHECKING",
            "opening_balance": "0.00",
            "currency": "USD",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_category(
    client: TestClient,
    *,
    name: str,
    is_income: bool = False,
) -> dict[str, str]:
    response = client.post(
        "/api/v1/categories",
        json={"name": name, "is_income": is_income, "color": "#ABCDEF"},
    )
    assert response.status_code == 201
    return response.json()


def _create_budget(
    client: TestClient,
    *,
    category_id: str,
    month: str,
    limit_amount: str,
) -> dict[str, str]:
    response = client.post(
        "/api/v1/budgets",
        json={
            "category_id": category_id,
            "month": month,
            "limit_amount": limit_amount,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_expense_transaction(
    client: TestClient,
    *,
    account_id: str,
    category_id: str,
    amount: str,
) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "category_id": category_id,
            "amount": amount,
            "direction": "OUT",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 201


def test_create_budget_success(authenticated_client: TestClient) -> None:
    category = _create_category(authenticated_client, name="Groceries")
    month = _current_month()
    response = authenticated_client.post(
        "/api/v1/budgets",
        json={
            "category_id": category["id"],
            "month": month,
            "limit_amount": "500.00",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["category_id"] == category["id"]
    assert payload["month"] == month
    assert Decimal(payload["limit_amount"]) == Decimal("500.00")


def test_create_budget_duplicate_returns_conflict(authenticated_client: TestClient) -> None:
    category = _create_category(authenticated_client, name="Dining")
    month = _current_month()
    _create_budget(
        authenticated_client,
        category_id=category["id"],
        month=month,
        limit_amount="250.00",
    )

    response = authenticated_client.post(
        "/api/v1/budgets",
        json={
            "category_id": category["id"],
            "month": month,
            "limit_amount": "300.00",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "budget_already_exists"


def test_create_budget_rejects_income_categories(authenticated_client: TestClient) -> None:
    category = _create_category(authenticated_client, name="Salary", is_income=True)
    response = authenticated_client.post(
        "/api/v1/budgets",
        json={
            "category_id": category["id"],
            "month": _current_month(),
            "limit_amount": "5000.00",
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_budget_category"


def test_list_budgets_returns_pagination(authenticated_client: TestClient) -> None:
    month = _current_month()
    groceries = _create_category(authenticated_client, name="Groceries")
    transport = _create_category(authenticated_client, name="Transport")
    _create_budget(
        authenticated_client,
        category_id=groceries["id"],
        month=month,
        limit_amount="400.00",
    )
    _create_budget(
        authenticated_client,
        category_id=transport["id"],
        month=month,
        limit_amount="200.00",
    )

    response = authenticated_client.get("/api/v1/budgets?limit=1&offset=0")
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert payload["offset"] == 0
    assert payload["total"] == 2
    assert len(payload["items"]) == 1


def test_budget_progress_warning_and_exceeded(authenticated_client: TestClient) -> None:
    month = _current_month()
    account = _create_account(authenticated_client)

    groceries = _create_category(authenticated_client, name="Groceries")
    utilities = _create_category(authenticated_client, name="Utilities")
    _create_budget(
        authenticated_client,
        category_id=groceries["id"],
        month=month,
        limit_amount="500.00",
    )
    _create_budget(
        authenticated_client,
        category_id=utilities["id"],
        month=month,
        limit_amount="300.00",
    )

    _create_expense_transaction(
        authenticated_client,
        account_id=account["id"],
        category_id=groceries["id"],
        amount="400.00",
    )
    _create_expense_transaction(
        authenticated_client,
        account_id=account["id"],
        category_id=utilities["id"],
        amount="360.00",
    )

    response = authenticated_client.get(f"/api/v1/budgets/progress?month={month}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["month"] == month

    status_by_category = {item["category_name"]: item["status"] for item in payload["items"]}
    assert status_by_category["Groceries"] == "warning"
    assert status_by_category["Utilities"] == "exceeded"


def test_copy_previous_month_is_idempotent(authenticated_client: TestClient) -> None:
    category = _create_category(authenticated_client, name="Subscriptions")
    previous_month = _previous_month()
    target_month = _current_month()
    _create_budget(
        authenticated_client,
        category_id=category["id"],
        month=previous_month,
        limit_amount="120.00",
    )

    first = authenticated_client.post(
        "/api/v1/budgets/copy-previous",
        json={"target_month": target_month},
    )
    assert first.status_code == 200
    assert first.json()["created_count"] == 1

    second = authenticated_client.post(
        "/api/v1/budgets/copy-previous",
        json={"target_month": target_month},
    )
    assert second.status_code == 200
    assert second.json()["created_count"] == 0

    listing = authenticated_client.get(f"/api/v1/budgets?month={target_month}")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_budget_access_is_scoped_per_user(client: TestClient) -> None:
    # User A setup and budget creation.
    first_email = "budget-owner@example.com"
    assert (
        client.post(
            "/api/v1/auth/register", json={"email": first_email, "password": "password123"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": first_email, "password": "password123"}
        ).status_code
        == 200
    )
    category = _create_category(client, name="Owner-only")
    budget = _create_budget(
        client,
        category_id=category["id"],
        month=_current_month(),
        limit_amount="100.00",
    )
    assert client.post("/api/v1/auth/logout").status_code == 200

    # User B should not see User A's budget.
    second_email = "budget-reader@example.com"
    assert (
        client.post(
            "/api/v1/auth/register", json={"email": second_email, "password": "password123"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": second_email, "password": "password123"}
        ).status_code
        == 200
    )

    response = client.get(f"/api/v1/budgets/{budget['id']}")
    assert response.status_code == 404
    assert response.json()["code"] == "budget_not_found"
