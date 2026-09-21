import pytest
from decimal import Decimal
from datetime import date
from app import db
from app.models import ExpenseCategory, Expense
from tests.conftest import login


def test_api_dashboard_endpoint(client, user_a, app):
    """Test /api/dashboard returns correct JSON structure."""
    login(client, user_a.email, "SecretPassword123!")

    res = client.get("/api/dashboard?month=2026-09")
    assert res.status_code == 200
    data = res.get_json()

    assert "kpis" in data
    assert "income_by_source" in data
    assert "expense_by_category" in data
    assert "trend" in data
    assert "budget_performance" in data
    assert "overspending" in data
    assert "emergency_fund" in data


def test_api_quick_add_expense(client, user_a, app):
    """Test AJAX quick-add expense endpoint."""
    login(client, user_a.email, "SecretPassword123!")

    with app.app_context():
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id).first()
        cat_id = cat.id

    payload = {
        "amount": "850.50",
        "category_id": cat_id,
        "date": "2026-09-12",
        "payment_method": "upi",
        "need_want": "want",
        "notes": "Fast food lunch"
    }

    res = client.post("/api/expenses", json=payload)
    assert res.status_code == 201
    res_data = res.get_json()
    assert res_data["success"] is True
    assert res_data["expense"]["amount"] == 850.50

    with app.app_context():
        exp = Expense.query.filter_by(user_id=user_a.id, amount=Decimal("850.50")).first()
        assert exp is not None
        assert exp.notes == "Fast food lunch"


def test_api_quick_add_expense_invalid(client, user_a):
    """Test error response when invalid data posted."""
    login(client, user_a.email, "SecretPassword123!")
    res = client.post("/api/expenses", json={"amount": "-10.00", "category_id": 9999})
    assert res.status_code == 400
    assert res.get_json()["success"] is False
