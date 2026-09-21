import pytest
from decimal import Decimal
from datetime import date
from app import db
from app.models import Income, Expense, ExpenseCategory, IncomeSource
from tests.conftest import login


def test_income_crud(client, user_a, app):
    """Test creating, viewing, and deleting income entries."""
    login(client, user_a.email, "SecretPassword123!")

    # Add income
    res = client.post("/income", data={
        "amount": "65000.00",
        "source_id": "0",
        "date": "2026-09-01",
        "notes": "Consulting bonus"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Income entry recorded successfully!" in res.data

    with app.app_context():
        inc = Income.query.filter_by(user_id=user_a.id).first()
        assert inc is not None
        assert inc.amount == Decimal("65000.00")
        assert inc.notes == "Consulting bonus"

        inc_id = inc.id

    # Delete income
    res_del = client.post(f"/income/delete/{inc_id}", follow_redirects=True)
    assert res_del.status_code == 200
    assert b"Income entry deleted." in res_del.data

    with app.app_context():
        assert Income.query.get(inc_id) is None


def test_income_negative_amount_rejected(client, user_a):
    """Test validation blocks negative or zero amounts."""
    login(client, user_a.email, "SecretPassword123!")
    res = client.post("/income", data={
        "amount": "-500.00",
        "source_id": "0",
        "date": "2026-09-01",
        "notes": "Invalid"
    }, follow_redirects=True)
    assert b"Amount must be greater than zero." in res.data


def test_expense_crud(client, user_a, app):
    """Test logging and deleting expenses."""
    login(client, user_a.email, "SecretPassword123!")

    with app.app_context():
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id, name="Groceries").first()
        cat_id = cat.id

    res = client.post("/expenses", data={
        "amount": "3450.00",
        "category_id": str(cat_id),
        "date": "2026-09-05",
        "payment_method": "upi",
        "need_want": "need",
        "notes": "Organic supermarket"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Expense logged successfully!" in res.data

    with app.app_context():
        exp = Expense.query.filter_by(user_id=user_a.id).first()
        assert exp is not None
        assert exp.amount == Decimal("3450.00")
        assert exp.payment_method == "upi"
        exp_id = exp.id

    # Delete expense
    res_del = client.post(f"/expenses/delete/{exp_id}", follow_redirects=True)
    assert b"Expense entry removed." in res_del.data

    with app.app_context():
        assert Expense.query.get(exp_id) is None


def test_category_archive_and_restore(client, user_a, app):
    """Test category archiving preserves category but sets is_archived=True."""
    login(client, user_a.email, "SecretPassword123!")

    with app.app_context():
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id, name="Shopping").first()
        cat_id = cat.id

    # Archive
    res = client.post(f"/categories/archive/{cat_id}", follow_redirects=True)
    assert b"archived" in res.data

    with app.app_context():
        cat_check = ExpenseCategory.query.get(cat_id)
        assert cat_check.is_archived is True

    # Restore
    res_rest = client.post(f"/categories/restore/{cat_id}", follow_redirects=True)
    assert b"restored" in res_rest.data

    with app.app_context():
        cat_check = ExpenseCategory.query.get(cat_id)
        assert cat_check.is_archived is False


def test_idor_protection_cross_tenant_isolation(client, user_a, user_b, app):
    """Ensure User B cannot delete or modify User A's financial entries."""
    with app.app_context():
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id).first()
        exp_a = Expense(
            user_id=user_a.id,
            category_id=cat.id,
            amount=Decimal("1200.00"),
            date=date.today(),
            need_want="need"
        )
        db.session.add(exp_a)
        db.session.commit()
        exp_a_id = exp_a.id

    # Login as User B and attempt to delete User A's expense
    login(client, user_b.email, "BobSecretPassword123!")
    res = client.post(f"/expenses/delete/{exp_a_id}")
    # Must return 404 since it's filtered by current_user.id
    assert res.status_code == 404

    with app.app_context():
        # Ensure User A's expense was NOT deleted
        assert Expense.query.get(exp_a_id) is not None
