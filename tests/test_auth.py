import pytest
from app.models import User, ExpenseCategory, Income
from tests.conftest import login


def test_register_success(client, app):
    """Test standard user registration."""
    res = client.post("/register", data={
        "name": "New User",
        "email": "newuser@test.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "profile_type": "salaried",
        "currency": "INR"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Your account has been created!" in res.data

    with app.app_context():
        u = User.query.filter_by(email="newuser@test.com").first()
        assert u is not None
        assert u.name == "New User"
        assert u.currency == "INR"
        # Check default categories were created
        cats = ExpenseCategory.query.filter_by(user_id=u.id).all()
        assert len(cats) > 0


def test_register_duplicate_email(client, user_a):
    """Test registration rejects duplicate email."""
    res = client.post("/register", data={
        "name": "Alice Clone",
        "email": user_a.email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "profile_type": "student",
        "currency": "INR"
    }, follow_redirects=True)
    assert b"An account with this email already exists." in res.data


def test_register_weak_password(client):
    """Test short password rejection."""
    res = client.post("/register", data={
        "name": "Weak Pass User",
        "email": "weak@test.com",
        "password": "123",
        "confirm_password": "123",
        "profile_type": "salaried",
        "currency": "INR"
    }, follow_redirects=True)
    assert b"Password must be at least 8 characters long." in res.data


def test_login_logout(client, user_a):
    """Test login and logout cycle."""
    res = login(client, "alice@test.com", "SecretPassword123!")
    assert b"Welcome back, Alice Walker!" in res.data

    # Protected dashboard is now accessible
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200
    assert b"Financial Overview" in res_dash.data

    # Logout
    res_out = client.get("/logout", follow_redirects=True)
    assert b"You have been signed out safely." in res_out.data

    # Protected dashboard redirects to login
    res_dash2 = client.get("/dashboard", follow_redirects=True)
    assert b"Please log in to access this page." in res_dash2.data


def test_login_invalid_password(client, user_a):
    """Test invalid credentials rejected."""
    res = login(client, "alice@test.com", "WrongPassword!")
    assert b"Invalid email or password." in res.data


def test_profile_update(client, user_a, app):
    """Test updating profile parameters."""
    login(client, "alice@test.com", "SecretPassword123!")
    res = client.post("/profile", data={
        "name": "Alice Updated",
        "profile_type": "household",
        "currency": "USD",
        "monthly_savings_goal": "22000.00",
        "emergency_fund_target": "180000.00",
        "dependents": "3"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Your profile preferences have been successfully updated." in res.data

    with app.app_context():
        u = User.query.get(user_a.id)
        assert u.name == "Alice Updated"
        assert u.profile_type == "household"
        assert u.currency == "USD"
        assert u.dependents == 3
