import os
import sys
import pytest
from decimal import Decimal
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import User, ExpenseCategory, IncomeSource, Income, Expense, BudgetPlan, BudgetItem
from app.services.defaults import setup_user_defaults


@pytest.fixture
def app():
    """Create test application with in-memory database."""
    app = create_app("testing")
    ctx = app.app_context()
    ctx.push()
    db.session.expire_on_commit = False
    db.create_all()
    
    yield app

    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def user_a(app):
    """Primary test user."""
    user = User(
        name="Alice Walker",
        email="alice@test.com",
        profile_type="salaried",
        currency="INR",
        monthly_savings_goal=Decimal("15000.00"),
        emergency_fund_target=Decimal("120000.00")
    )
    user.set_password("SecretPassword123!")
    db.session.add(user)
    db.session.commit()
    setup_user_defaults(user)
    return user


@pytest.fixture
def user_b(app):
    """Secondary test user for multi-tenant and IDOR authorization tests."""
    user = User(
        name="Bob Miller",
        email="bob@test.com",
        profile_type="freelancer",
        currency="USD",
        monthly_savings_goal=Decimal("1000.00"),
        emergency_fund_target=Decimal("10000.00")
    )
    user.set_password("BobSecretPassword123!")
    db.session.add(user)
    db.session.commit()
    setup_user_defaults(user)
    return user


def login(client, email, password):
    """Helper to log in user."""
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True
    )
