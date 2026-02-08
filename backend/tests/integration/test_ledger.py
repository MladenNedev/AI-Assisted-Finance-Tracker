from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_account(
    client: TestClient,
    *,
    name: str = "Primary checking",
    account_type: str = "CHECKING",
    opening_balance: str = "0.00",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "account_type": account_type,
            "opening_balance": opening_balance,
            "currency": "USD",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_category(
    client: TestClient,
    *,
    name: str = "Groceries",
    is_income: bool = False,
) -> dict[str, str]:
    response = client.post(
        "/api/v1/categories",
        json={"name": name, "is_income": is_income, "color": "#A1B2C3"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_account_returns_current_balance(authenticated_client: TestClient) -> None:
    payload = _create_account(authenticated_client, opening_balance="100.00")
    assert payload["name"] == "Primary checking"
    assert payload["account_type"] == "CHECKING"
    assert Decimal(payload["current_balance"]) == Decimal("100.00")


def test_balance_includes_signed_transactions(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client, opening_balance="100.00")

    response_in = authenticated_client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "50.00",
            "direction": "IN",
            "occurred_at": datetime.now(UTC).isoformat(),
            "merchant": "Salary",
        },
    )
    assert response_in.status_code == 201

    response_out = authenticated_client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "30.00",
            "direction": "OUT",
            "occurred_at": datetime.now(UTC).isoformat(),
            "merchant": "Groceries",
        },
    )
    assert response_out.status_code == 201

    balance_response = authenticated_client.get(f"/api/v1/accounts/{account['id']}/balance")
    assert balance_response.status_code == 200
    assert Decimal(balance_response.json()["balance"]) == Decimal("120.00")


def test_transaction_requires_positive_amount(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client)

    response = authenticated_client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "-1.00",
            "direction": "OUT",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_accounts_soft_delete_and_listing(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client, name="To archive")

    delete_response = authenticated_client.delete(f"/api/v1/accounts/{account['id']}")
    assert delete_response.status_code == 204

    active_only = authenticated_client.get("/api/v1/accounts")
    assert active_only.status_code == 200
    active_items = active_only.json()["items"]
    assert all(item["id"] != account["id"] for item in active_items)

    with_inactive = authenticated_client.get("/api/v1/accounts?include_inactive=true")
    assert with_inactive.status_code == 200
    with_inactive_payload = with_inactive.json()
    archived = next(item for item in with_inactive_payload["items"] if item["id"] == account["id"])
    assert archived["is_active"] is False
    assert with_inactive_payload["total"] >= 1


def test_transaction_cannot_use_other_users_account(client: TestClient) -> None:
    # User A
    first_email = "first-user@example.com"
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
    account = _create_account(client)
    assert client.post("/api/v1/auth/logout").status_code == 200

    # User B
    second_email = "second-user@example.com"
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

    response = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "20.00",
            "direction": "OUT",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 404
    assert response.json()["code"] == "account_not_found"


def test_category_create_list_and_update(authenticated_client: TestClient) -> None:
    category = _create_category(authenticated_client, name="Dining")
    assert category["name"] == "Dining"
    assert category["is_income"] is False

    list_response = authenticated_client.get("/api/v1/categories")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] >= 1
    assert any(item["id"] == category["id"] for item in payload["items"])

    update_response = authenticated_client.patch(
        f"/api/v1/categories/{category['id']}",
        json={"name": "Restaurants", "is_income": False, "color": "#0F0F0F"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Restaurants"


def test_transactions_filter_by_category(authenticated_client: TestClient) -> None:
    account = _create_account(authenticated_client)
    groceries = _create_category(authenticated_client, name="Groceries")
    salary = _create_category(authenticated_client, name="Salary", is_income=True)

    first = authenticated_client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "category_id": groceries["id"],
            "amount": "25.00",
            "direction": "OUT",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert first.status_code == 201

    second = authenticated_client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "category_id": salary["id"],
            "amount": "100.00",
            "direction": "IN",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert second.status_code == 201

    filtered = authenticated_client.get(f"/api/v1/transactions?category_id={groceries['id']}")
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert payload["items"][0]["category_id"] == groceries["id"]


def test_accounts_list_pagination_metadata(authenticated_client: TestClient) -> None:
    _create_account(authenticated_client, name="A1")
    _create_account(authenticated_client, name="A2")
    _create_account(authenticated_client, name="A3")

    response = authenticated_client.get("/api/v1/accounts?limit=2&offset=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert payload["total"] >= 3
    assert len(payload["items"]) <= 2
