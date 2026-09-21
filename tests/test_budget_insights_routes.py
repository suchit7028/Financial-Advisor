import pytest
from decimal import Decimal
from datetime import date
from app import db
from app.models import BudgetPlan, BudgetItem, ExpenseCategory, Expense, Income, AIInsight
from tests.conftest import login


def test_budget_index_and_generate_routes(client, user_a, app):
    """Test viewing budget and proposal generation page."""
    login(client, user_a.email, "SecretPassword123!")

    # 1. Budget index (no plan yet)
    res_idx = client.get("/budget?month=2026-10")
    assert res_idx.status_code == 200
    assert b"Monthly Budget Management" in res_idx.data

    # 2. Proposal generation review page
    res_prop = client.get("/budget/generate?month=2026-10&income=70000")
    assert res_prop.status_code == 200
    assert b"AI Budget Proposal Review" in res_prop.data
    assert b"Customize Proposed Limits" in res_prop.data


def test_budget_accept_flow(client, user_a, app):
    """Test accepting and activating a budget proposal."""
    login(client, user_a.email, "SecretPassword123!")

    with app.app_context():
        cats = ExpenseCategory.query.filter_by(user_id=user_a.id).all()
        post_data = {
            "month": "2026-10",
            "total_income_basis": "75000.00",
            "generated_by": "ai"
        }
        for c in cats:
            post_data[f"limit_{c.id}"] = "5000.00"
            post_data[f"reason_{c.id}"] = f"Test limit for {c.name}"

    res = client.post("/budget/accept", data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Monthly budget for 2026-10 activated successfully!" in res.data

    with app.app_context():
        plan = BudgetPlan.query.filter_by(user_id=user_a.id, month="2026-10").first()
        assert plan is not None
        assert plan.status == "active"
        assert len(plan.items) == len(cats)


def test_insights_index_and_refresh(client, user_a, app):
    """Test viewing AI insights and force refreshing."""
    login(client, user_a.email, "SecretPassword123!")

    # Initial view
    res = client.get("/insights?month=2026-09")
    assert res.status_code == 200
    assert b"AI Financial Advisor & Insights" in res.data
    assert b"Financial Health Index" in res.data
    assert b"Scoring Breakdown" in res.data

    # Refresh
    res_ref = client.get("/insights?month=2026-09&refresh=1", follow_redirects=True)
    assert res_ref.status_code == 200
    assert b"AI insights refreshed" in res_ref.data


def test_reports_index_view(client, user_a):
    """Test reports index page rendering."""
    login(client, user_a.email, "SecretPassword123!")
    res = client.get("/reports")
    assert res.status_code == 200
    assert b"Monthly Financial Reports" in res.data
