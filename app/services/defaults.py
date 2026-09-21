"""
Default Categories and Income Sources by Persona
------------------------------------------------
Initializes standard categories and default recurring sources when a user registers.
Users can edit, add, or archive them anytime.
"""

from typing import List, Dict
from app import db
from app.models import ExpenseCategory, IncomeSource, User


DEFAULT_CATEGORIES_BY_PERSONA = {
    "salaried": [
        {"name": "Rent", "kind": "need", "icon": "home"},
        {"name": "Groceries", "kind": "need", "icon": "shopping-cart"},
        {"name": "Transport", "kind": "need", "icon": "truck"},
        {"name": "Utilities", "kind": "need", "icon": "zap"},
        {"name": "EMI/Loans", "kind": "need", "icon": "credit-card"},
        {"name": "Health", "kind": "need", "icon": "activity"},
        {"name": "Dining out", "kind": "want", "icon": "coffee"},
        {"name": "Entertainment", "kind": "want", "icon": "film"},
        {"name": "Shopping", "kind": "want", "icon": "gift"},
        {"name": "Other", "kind": "other", "icon": "more-horizontal"},
    ],
    "student": [
        {"name": "Hostel/Rent", "kind": "need", "icon": "home"},
        {"name": "Food", "kind": "need", "icon": "coffee"},
        {"name": "Books/Education", "kind": "need", "icon": "book"},
        {"name": "Travel", "kind": "need", "icon": "map-pin"},
        {"name": "Subscriptions", "kind": "want", "icon": "play"},
        {"name": "Entertainment", "kind": "want", "icon": "film"},
        {"name": "Other", "kind": "other", "icon": "more-horizontal"},
    ],
    "freelancer": [
        {"name": "Rent", "kind": "need", "icon": "home"},
        {"name": "Food", "kind": "need", "icon": "coffee"},
        {"name": "Software/Tools", "kind": "need", "icon": "cpu"},
        {"name": "Project expenses", "kind": "need", "icon": "briefcase"},
        {"name": "Taxes (set-aside)", "kind": "need", "icon": "file-text"},
        {"name": "Health", "kind": "need", "icon": "activity"},
        {"name": "Travel", "kind": "want", "icon": "compass"},
        {"name": "Other", "kind": "other", "icon": "more-horizontal"},
    ],
    "household": [
        {"name": "Groceries", "kind": "need", "icon": "shopping-cart"},
        {"name": "Utilities", "kind": "need", "icon": "zap"},
        {"name": "Education", "kind": "need", "icon": "book"},
        {"name": "Healthcare", "kind": "need", "icon": "activity"},
        {"name": "Rent/EMI", "kind": "need", "icon": "home"},
        {"name": "Transport", "kind": "need", "icon": "truck"},
        {"name": "Household help", "kind": "need", "icon": "users"},
        {"name": "Entertainment", "kind": "want", "icon": "film"},
        {"name": "Other", "kind": "other", "icon": "more-horizontal"},
    ],
}


def setup_user_defaults(user: User):
    """Creates default categories and basic income source for a new user."""
    profile_type = user.profile_type or "salaried"
    cats = DEFAULT_CATEGORIES_BY_PERSONA.get(profile_type, DEFAULT_CATEGORIES_BY_PERSONA["salaried"])

    for cat_data in cats:
        cat = ExpenseCategory(
            user_id=user.id,
            name=cat_data["name"],
            kind=cat_data["kind"],
            icon=cat_data.get("icon", "tag"),
            is_archived=False
        )
        db.session.add(cat)

    # Add default primary income source
    source_name = "Primary Salary" if profile_type == "salaried" else (
        "Monthly Allowance" if profile_type == "student" else (
            "Primary Client" if profile_type == "freelancer" else "Household Primary Income"
        )
    )
    source_type = "salary" if profile_type in ("salaried", "household") else (
        "allowance" if profile_type == "student" else "freelance"
    )

    src = IncomeSource(
        user_id=user.id,
        name=source_name,
        type=source_type,
        is_recurring=True,
        expected_amount=0.0
    )
    db.session.add(src)
    db.session.commit()
