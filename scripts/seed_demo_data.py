"""
Seed Realistic Financial Demo Data for 4 Personas
-------------------------------------------------
1. Salaried Professional (salaried@demo.com)
2. College Student (student@demo.com)
3. Freelancer / Consultant (freelancer@demo.com)
4. Household Manager (household@demo.com)

Generates 3 months of realistic historical transactions, budgets,
savings goals, and default categories so the demo works instantly.
"""

import os
import sys
from decimal import Decimal
from datetime import date, datetime, timedelta
import random

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import db, create_app
from app.models import (
    User, IncomeSource, Income, ExpenseCategory, Expense,
    BudgetPlan, BudgetItem, SavingsGoal, SavingsRecord
)
from app.services.defaults import setup_user_defaults
from app.services.finance_engine import FinanceEngine


def get_month_dates(year: int, month: int):
    """Returns sample dates spread throughout the month."""
    days = [3, 7, 12, 16, 21, 26, 28]
    dates = []
    for d in days:
        try:
            dates.append(date(year, month, d))
        except ValueError:
            pass
    return dates


def seed_salaried(app_context):
    print("Seeding Salaried Professional (salaried@demo.com)...")
    email = "salaried@demo.com"
    user = User.query.filter_by(email=email).first()
    if user:
        db.session.delete(user)
        db.session.commit()

    user = User(
        name="Rohan Sharma",
        email=email,
        profile_type="salaried",
        currency="INR",
        monthly_savings_goal=Decimal("18000.00"),
        emergency_fund_target=Decimal("150000.00"),
        dependents=0
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    setup_user_defaults(user)

    salary_src = IncomeSource.query.filter_by(user_id=user.id).first()
    salary_src.name = "Tech Corp Salary"
    salary_src.expected_amount = Decimal("85000.00")
    db.session.commit()

    cats = {c.name: c for c in ExpenseCategory.query.filter_by(user_id=user.id).all()}

    # 3 months: current, current-1, current-2
    today = date.today()
    current_month_str = FinanceEngine.get_month_str(today)
    months = FinanceEngine.get_previous_months(current_month_str, count=2) + [current_month_str]

    for m_idx, m_str in enumerate(months):
        yr, mo = map(int, m_str.split("-"))
        # Income on the 1st
        inc = Income(
            user_id=user.id,
            source_id=salary_src.id,
            amount=Decimal("85000.00"),
            date=date(yr, mo, 1),
            notes="Monthly salary direct deposit"
        )
        db.session.add(inc)

        # Realistic expenses
        exp_templates = [
            ("Rent", Decimal("25000.00"), "need", "Apartment rent", "bank_transfer", date(yr, mo, 2)),
            ("Groceries", Decimal("11500.00") if m_idx != 2 else Decimal("14500.00"), "need", "Supermarket & vegetables", "upi", date(yr, mo, 6)),
            ("Transport", Decimal("4500.00"), "need", "Metro & fuel", "card", date(yr, mo, 10)),
            ("Utilities", Decimal("3800.00"), "need", "Electricity & fiber wifi", "upi", date(yr, mo, 12)),
            ("EMI/Loans", Decimal("12000.00"), "need", "Car loan EMI", "bank_transfer", date(yr, mo, 15)),
            ("Health", Decimal("2200.00"), "need", "Pharmacy & vitamins", "upi", date(yr, mo, 18)),
            ("Dining out", Decimal("6800.00") if m_idx != 2 else Decimal("9200.00"), "want", "Weekend restaurants", "card", date(yr, mo, 20)),
            ("Entertainment", Decimal("3200.00"), "want", "Movies & concert", "card", date(yr, mo, 23)),
            ("Shopping", Decimal("4500.00") if m_idx != 2 else Decimal("7800.00"), "want", "Apparel & electronics", "upi", date(yr, mo, 25)),
            ("Other", Decimal("1500.00"), "other", "Miscellaneous household items", "cash", date(yr, mo, 27)),
        ]

        for cat_name, amt, kind, notes, method, exp_date in exp_templates:
            if cat_name in cats:
                exp = Expense(
                    user_id=user.id,
                    category_id=cats[cat_name].id,
                    amount=amt,
                    date=exp_date,
                    payment_method=method,
                    need_want=kind if kind in ("need", "want") else "need",
                    notes=notes
                )
                db.session.add(exp)

    # Active budget plan for current month
    plan = BudgetPlan(
        user_id=user.id,
        month=current_month_str,
        total_income_basis=Decimal("85000.00"),
        status="active",
        generated_by="ai"
    )
    db.session.add(plan)
    db.session.flush()

    limits = {
        "Rent": (Decimal("25000.00"), "Fixed monthly rental obligation"),
        "Groceries": (Decimal("12000.00"), "Sufficient grocery baseline"),
        "Transport": (Decimal("5000.00"), "Fuel and transit allowance"),
        "Utilities": (Decimal("4000.00"), "Estimated utilities"),
        "EMI/Loans": (Decimal("12000.00"), "Contractual EMI"),
        "Health": (Decimal("3000.00"), "Medical allowance"),
        "Dining out": (Decimal("6500.00"), "Discretionary dining cap"),
        "Entertainment": (Decimal("3500.00"), "Discretionary entertainment"),
        "Shopping": (Decimal("5000.00"), "Mindful shopping limit"),
        "Other": (Decimal("2000.00"), "Contingency buffer")
    }

    for c_name, (lim, reason) in limits.items():
        if c_name in cats:
            bi = BudgetItem(
                plan_id=plan.id,
                category_id=cats[c_name].id,
                limit_amount=lim,
                ai_reason=reason
            )
            db.session.add(bi)

    # Emergency fund goal
    ef_goal = SavingsGoal(
        user_id=user.id,
        name="Emergency Safety Reserve",
        target_amount=Decimal("150000.00"),
        is_emergency_fund=True
    )
    db.session.add(ef_goal)
    db.session.flush()

    # Add records for emergency fund
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[0], amount_saved=Decimal("35000.00")))
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[1], amount_saved=Decimal("35000.00")))
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[2], amount_saved=Decimal("20000.00")))

    db.session.commit()
    print("Salaried Professional seeded.")


def seed_student(app_context):
    print("Seeding College Student (student@demo.com)...")
    email = "student@demo.com"
    user = User.query.filter_by(email=email).first()
    if user:
        db.session.delete(user)
        db.session.commit()

    user = User(
        name="Ananya Verma",
        email=email,
        profile_type="student",
        currency="INR",
        monthly_savings_goal=Decimal("1500.00"),
        emergency_fund_target=Decimal("25000.00"),
        dependents=0
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    setup_user_defaults(user)

    allowance_src = IncomeSource.query.filter_by(user_id=user.id).first()
    allowance_src.name = "Monthly Parental Allowance"
    allowance_src.expected_amount = Decimal("15000.00")
    db.session.commit()

    cats = {c.name: c for c in ExpenseCategory.query.filter_by(user_id=user.id).all()}

    today = date.today()
    current_month_str = FinanceEngine.get_month_str(today)
    months = FinanceEngine.get_previous_months(current_month_str, count=2) + [current_month_str]

    for m_idx, m_str in enumerate(months):
        yr, mo = map(int, m_str.split("-"))
        inc = Income(
            user_id=user.id,
            source_id=allowance_src.id,
            amount=Decimal("15000.00"),
            date=date(yr, mo, 1),
            notes="Monthly student allowance"
        )
        db.session.add(inc)

        exp_templates = [
            ("Hostel/Rent", Decimal("6000.00"), "need", "Hostel accommodation fee", "upi", date(yr, mo, 2)),
            ("Food", Decimal("4200.00") if m_idx != 2 else Decimal("5100.00"), "need", "College mess & canteen", "upi", date(yr, mo, 5)),
            ("Books/Education", Decimal("1200.00"), "need", "Engineering books & notes", "card", date(yr, mo, 11)),
            ("Travel", Decimal("800.00"), "need", "Bus pass & city commute", "cash", date(yr, mo, 14)),
            ("Subscriptions", Decimal("499.00"), "want", "Spotify & study tools", "card", date(yr, mo, 16)),
            ("Entertainment", Decimal("950.00") if m_idx != 2 else Decimal("1800.00"), "want", "Weekend movie & snacks", "upi", date(yr, mo, 22)),
            ("Other", Decimal("400.00"), "other", "Stationery", "cash", date(yr, mo, 27)),
        ]

        for cat_name, amt, kind, notes, method, exp_date in exp_templates:
            if cat_name in cats:
                exp = Expense(
                    user_id=user.id,
                    category_id=cats[cat_name].id,
                    amount=amt,
                    date=exp_date,
                    payment_method=method,
                    need_want=kind if kind in ("need", "want") else "need",
                    notes=notes
                )
                db.session.add(exp)

    # Budget
    plan = BudgetPlan(
        user_id=user.id,
        month=current_month_str,
        total_income_basis=Decimal("15000.00"),
        status="active",
        generated_by="ai"
    )
    db.session.add(plan)
    db.session.flush()

    limits = {
        "Hostel/Rent": (Decimal("6000.00"), "Fixed hostel room rate"),
        "Food": (Decimal("4500.00"), "Mess and nutritious meals"),
        "Books/Education": (Decimal("1500.00"), "Study materials & prints"),
        "Travel": (Decimal("1000.00"), "Public transit pass"),
        "Subscriptions": (Decimal("600.00"), "Entertainment & learning apps"),
        "Entertainment": (Decimal("1000.00"), "Strict discretionary cap"),
        "Other": (Decimal("400.00"), "Stationery cushion")
    }

    for c_name, (lim, reason) in limits.items():
        if c_name in cats:
            db.session.add(BudgetItem(plan_id=plan.id, category_id=cats[c_name].id, limit_amount=lim, ai_reason=reason))

    ef_goal = SavingsGoal(user_id=user.id, name="Student Emergency Reserve", target_amount=Decimal("20000.00"), is_emergency_fund=True)
    db.session.add(ef_goal)
    db.session.flush()
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[1], amount_saved=Decimal("5000.00")))
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[2], amount_saved=Decimal("4000.00")))

    db.session.commit()
    print("College Student seeded.")


def seed_freelancer(app_context):
    print("Seeding Freelancer (freelancer@demo.com)...")
    email = "freelancer@demo.com"
    user = User.query.filter_by(email=email).first()
    if user:
        db.session.delete(user)
        db.session.commit()

    user = User(
        name="Vikram Mehta",
        email=email,
        profile_type="freelancer",
        currency="INR",
        monthly_savings_goal=Decimal("25000.00"),
        emergency_fund_target=Decimal("300000.00"),
        dependents=0
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    setup_user_defaults(user)

    # 3 distinct clients
    c1 = IncomeSource(user_id=user.id, name="FinTech Client US", type="freelance", is_recurring=True, expected_amount=Decimal("55000.00"))
    c2 = IncomeSource(user_id=user.id, name="Design Studio EU", type="freelance", is_recurring=False, expected_amount=Decimal("35000.00"))
    c3 = IncomeSource(user_id=user.id, name="Local Startup", type="freelance", is_recurring=False, expected_amount=Decimal("20000.00"))
    db.session.add_all([c1, c2, c3])
    db.session.commit()

    cats = {c.name: c for c in ExpenseCategory.query.filter_by(user_id=user.id).all()}

    today = date.today()
    current_month_str = FinanceEngine.get_month_str(today)
    months = FinanceEngine.get_previous_months(current_month_str, count=2) + [current_month_str]

    # Varying income across months
    income_matrix = [
        [(c1, Decimal("55000.00")), (c2, Decimal("40000.00")), (c3, Decimal("15000.00"))],  # 110k
        [(c1, Decimal("50000.00")), (c2, Decimal("20000.00"))],                             # 70k (lean month)
        [(c1, Decimal("60000.00")), (c2, Decimal("35000.00")), (c3, Decimal("25000.00"))]   # 120k
    ]

    for m_idx, m_str in enumerate(months):
        yr, mo = map(int, m_str.split("-"))
        for src, amt in income_matrix[m_idx]:
            inc = Income(user_id=user.id, source_id=src.id, amount=amt, date=date(yr, mo, 3), notes=f"Payment from {src.name}")
            db.session.add(inc)

        exp_templates = [
            ("Rent", Decimal("22000.00"), "need", "Co-living studio", "bank_transfer", date(yr, mo, 4)),
            ("Food", Decimal("9500.00"), "need", "Groceries & daily coffee", "upi", date(yr, mo, 8)),
            ("Software/Tools", Decimal("6200.00"), "need", "Figma, AWS, GitHub Copilot", "card", date(yr, mo, 10)),
            ("Project expenses", Decimal("7500.00"), "need", "Client asset licenses & fonts", "card", date(yr, mo, 14)),
            ("Taxes (set-aside)", Decimal("18000.00"), "need", "Quarterly advance tax reserve", "bank_transfer", date(yr, mo, 18)),
            ("Health", Decimal("3500.00"), "need", "Health insurance premium", "upi", date(yr, mo, 21)),
            ("Travel", Decimal("4500.00"), "want", "Client coworking & transit", "card", date(yr, mo, 24)),
            ("Other", Decimal("2500.00"), "other", "Hardware accessories", "upi", date(yr, mo, 27)),
        ]

        for cat_name, amt, kind, notes, method, exp_date in exp_templates:
            if cat_name in cats:
                exp = Expense(
                    user_id=user.id,
                    category_id=cats[cat_name].id,
                    amount=amt,
                    date=exp_date,
                    payment_method=method,
                    need_want=kind if kind in ("need", "want") else "need",
                    notes=notes
                )
                db.session.add(exp)

    # Budget (conservative baseline)
    plan = BudgetPlan(
        user_id=user.id,
        month=current_month_str,
        total_income_basis=Decimal("80000.00"),  # conservative
        status="active",
        generated_by="ai"
    )
    db.session.add(plan)
    db.session.flush()

    limits = {
        "Rent": (Decimal("22000.00"), "Fixed workspace studio rent"),
        "Food": (Decimal("10000.00"), "Essential daily sustenance"),
        "Software/Tools": (Decimal("7000.00"), "Critical freelance stack"),
        "Project expenses": (Decimal("8000.00"), "Project operating costs"),
        "Taxes (set-aside)": (Decimal("18000.00"), "Recommended 20% advance tax hold"),
        "Health": (Decimal("4000.00"), "Health protection"),
        "Travel": (Decimal("5000.00"), "Client visit travel pool"),
        "Other": (Decimal("2000.00"), "Contingency")
    }

    for c_name, (lim, reason) in limits.items():
        if c_name in cats:
            db.session.add(BudgetItem(plan_id=plan.id, category_id=cats[c_name].id, limit_amount=lim, ai_reason=reason))

    ef_goal = SavingsGoal(user_id=user.id, name="6-Month Freelance Runway", target_amount=Decimal("300000.00"), is_emergency_fund=True)
    db.session.add(ef_goal)
    db.session.flush()
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[0], amount_saved=Decimal("70000.00")))
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[1], amount_saved=Decimal("60000.00")))
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[2], amount_saved=Decimal("50000.00")))

    db.session.commit()
    print("Freelancer seeded.")


def seed_household(app_context):
    print("Seeding Household Manager (household@demo.com)...")
    email = "household@demo.com"
    user = User.query.filter_by(email=email).first()
    if user:
        db.session.delete(user)
        db.session.commit()

    user = User(
        name="Kavita & Suresh Nair",
        email=email,
        profile_type="household",
        currency="INR",
        monthly_savings_goal=Decimal("35000.00"),
        emergency_fund_target=Decimal("350000.00"),
        dependents=2
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    setup_user_defaults(user)

    src1 = IncomeSource.query.filter_by(user_id=user.id).first()
    src1.name = "Primary Salary (Suresh)"
    src1.expected_amount = Decimal("95000.00")
    src2 = IncomeSource(user_id=user.id, name="Secondary Income (Kavita)", type="salary", is_recurring=True, expected_amount=Decimal("55000.00"))
    db.session.add(src2)
    db.session.commit()

    cats = {c.name: c for c in ExpenseCategory.query.filter_by(user_id=user.id).all()}

    today = date.today()
    current_month_str = FinanceEngine.get_month_str(today)
    months = FinanceEngine.get_previous_months(current_month_str, count=2) + [current_month_str]

    for m_idx, m_str in enumerate(months):
        yr, mo = map(int, m_str.split("-"))
        # 2 salaries on the 1st
        db.session.add(Income(user_id=user.id, source_id=src1.id, amount=Decimal("95000.00"), date=date(yr, mo, 1), notes="Suresh's monthly salary"))
        db.session.add(Income(user_id=user.id, source_id=src2.id, amount=Decimal("55000.00"), date=date(yr, mo, 1), notes="Kavita's monthly consulting salary"))

        exp_templates = [
            ("Rent/EMI", Decimal("38000.00"), "need", "Home mortgage loan EMI", "bank_transfer", date(yr, mo, 2)),
            ("Groceries", Decimal("26000.00") if m_idx != 2 else Decimal("31000.00"), "need", "Monthly family grocery & pantry", "card", date(yr, mo, 5)),
            ("Education", Decimal("22000.00"), "need", "School fees & afterschool tuition (2 kids)", "bank_transfer", date(yr, mo, 7)),
            ("Utilities", Decimal("9200.00"), "need", "Power, gas piped, water, fiber internet", "upi", date(yr, mo, 11)),
            ("Healthcare", Decimal("7800.00"), "need", "Pediatrician visit & family dental", "upi", date(yr, mo, 15)),
            ("Household help", Decimal("7500.00"), "need", "Housekeeping & cook salary", "bank_transfer", date(yr, mo, 17)),
            ("Transport", Decimal("8500.00"), "need", "Family car fuel & school van", "card", date(yr, mo, 21)),
            ("Entertainment", Decimal("6000.00") if m_idx != 2 else Decimal("9500.00"), "want", "Family outing, theme park & dinner", "card", date(yr, mo, 24)),
            ("Other", Decimal("3000.00"), "other", "Home repairs & gardening", "cash", date(yr, mo, 27)),
        ]

        for cat_name, amt, kind, notes, method, exp_date in exp_templates:
            if cat_name in cats:
                exp = Expense(
                    user_id=user.id,
                    category_id=cats[cat_name].id,
                    amount=amt,
                    date=exp_date,
                    payment_method=method,
                    need_want=kind if kind in ("need", "want") else "need",
                    notes=notes
                )
                db.session.add(exp)

    # Budget
    plan = BudgetPlan(
        user_id=user.id,
        month=current_month_str,
        total_income_basis=Decimal("150000.00"),
        status="active",
        generated_by="ai"
    )
    db.session.add(plan)
    db.session.flush()

    limits = {
        "Rent/EMI": (Decimal("38000.00"), "Fixed home loan EMI commitment"),
        "Groceries": (Decimal("28000.00"), "Standard family 4-person ration pool"),
        "Education": (Decimal("22000.00"), "School fees allocation for 2 dependents"),
        "Utilities": (Decimal("9500.00"), "Family home utilities"),
        "Healthcare": (Decimal("8000.00"), "Preventative and family health checkups"),
        "Household help": (Decimal("7500.00"), "Domestic support allowance"),
        "Transport": (Decimal("9000.00"), "Commuting and school transport"),
        "Entertainment": (Decimal("6000.00"), "Family leisure cap"),
        "Other": (Decimal("3000.00"), "Miscellaneous household maintenance")
    }

    for c_name, (lim, reason) in limits.items():
        if c_name in cats:
            db.session.add(BudgetItem(plan_id=plan.id, category_id=cats[c_name].id, limit_amount=lim, ai_reason=reason))

    ef_goal = SavingsGoal(user_id=user.id, name="Family Safety Cushion", target_amount=Decimal("350000.00"), is_emergency_fund=True)
    db.session.add(ef_goal)
    db.session.flush()
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[0], amount_saved=Decimal("90000.00")))
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[1], amount_saved=Decimal("90000.00")))
    db.session.add(SavingsRecord(user_id=user.id, goal_id=ef_goal.id, month=months[2], amount_saved=Decimal("80000.00")))

    db.session.commit()
    print("Household Manager seeded.")


def seed_all():
    app = create_app("development")
    with app.app_context():
        db.create_all()
        seed_salaried(app)
        seed_student(app)
        seed_freelancer(app)
        seed_household(app)
        print("\nAll 4 demo personas seeded successfully!")


if __name__ == "__main__":
    seed_all()
