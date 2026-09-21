import pytest
from decimal import Decimal
from datetime import date
from app import db
from app.models import Income, Expense, ExpenseCategory, BudgetPlan, BudgetItem, SavingsGoal, SavingsRecord
from app.services.finance_engine import FinanceEngine


def test_monthly_aggregates_and_savings_rate(app, user_a):
    """Test arithmetic for incomes, expenses, net savings, and savings rate."""
    with app.app_context():
        cats = {c.name: c for c in ExpenseCategory.query.filter_by(user_id=user_a.id).all()}
        month = "2026-09"

        # Incomes: 80,000 + 20,000 = 100,000
        db.session.add(Income(user_id=user_a.id, amount=Decimal("80000.00"), date=date(2026, 9, 1)))
        db.session.add(Income(user_id=user_a.id, amount=Decimal("20000.00"), date=date(2026, 9, 15)))

        # Expenses: Needs = 40,000; Wants = 20,000; Total = 60,000
        db.session.add(Expense(user_id=user_a.id, category_id=cats["Rent"].id, amount=Decimal("25000.00"), date=date(2026, 9, 2), need_want="need"))
        db.session.add(Expense(user_id=user_a.id, category_id=cats["Groceries"].id, amount=Decimal("15000.00"), date=date(2026, 9, 5), need_want="need"))
        db.session.add(Expense(user_id=user_a.id, category_id=cats["Dining out"].id, amount=Decimal("12000.00"), date=date(2026, 9, 10), need_want="want"))
        db.session.add(Expense(user_id=user_a.id, category_id=cats["Shopping"].id, amount=Decimal("8000.00"), date=date(2026, 9, 20), need_want="want"))
        db.session.commit()

        agg = FinanceEngine.get_monthly_aggregates(user_a.id, month)

        assert agg["total_income"] == Decimal("100000.00")
        assert agg["total_expenses"] == Decimal("60000.00")
        assert agg["net_savings"] == Decimal("40000.00")
        assert agg["savings_rate"] == 40.0
        assert agg["needs_total"] == Decimal("40000.00")
        assert agg["wants_total"] == Decimal("20000.00")


def test_baseline_budget_freelancer_conservative_and_tax(app, user_b):
    """Test freelancer conservative baseline and 20% tax set-aside."""
    with app.app_context():
        cats = ExpenseCategory.query.filter_by(user_id=user_b.id).all()
        month = "2026-09"

        # Baseline with expected income of 100,000
        baseline = FinanceEngine.generate_baseline_budget(
            user_id=user_b.id,
            user_profile_type="freelancer",
            target_month=month,
            active_categories=cats,
            expected_income=Decimal("100000.00")
        )

        assert baseline["total_income_basis"] == 100000.0
        # Tax set aside should be 20% = 20,000
        assert baseline["tax_set_aside"] == 20000.0
        assert baseline["spendable_income"] == 80000.0
        # Total category limits must be <= spendable income
        assert baseline["total_allocated"] <= baseline["spendable_income"] + 0.05


def test_student_runway_calculation(app, user_a):
    """Test student allowance runway calculation."""
    with app.app_context():
        month = FinanceEngine.get_month_str()
        # Allowance of 10,000
        db.session.add(Income(user_id=user_a.id, amount=Decimal("10000.00"), date=date.today()))
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id).first()
        # Spent 3,000
        db.session.add(Expense(user_id=user_a.id, category_id=cat.id, amount=Decimal("3000.00"), date=date.today(), need_want="need"))
        db.session.commit()

        runway = FinanceEngine.calculate_allowance_runway(user_a.id, month)
        assert runway["remaining_balance"] == 7000.0
        assert runway["daily_burn_rate"] > 0
        assert runway["runway_days"] > 0


def test_emergency_fund_target_multiplier(app, user_a, user_b):
    """Test emergency fund is 3 months for salaried, 6 months for freelancer."""
    with app.app_context():
        month = "2026-09"
        # 1. Salaried user
        ef_salaried = FinanceEngine.calculate_emergency_fund_status(user_a.id, "salaried", month)
        assert ef_salaried["target_months"] == 3

        # 2. Freelancer user
        ef_freelancer = FinanceEngine.calculate_emergency_fund_status(user_b.id, "freelancer", month)
        assert ef_freelancer["target_months"] == 6


def test_financial_health_score_rubric(app, user_a):
    """Test deterministic scoring between 0 and 100."""
    with app.app_context():
        month = "2026-09"
        # Seed healthy income and controlled expenses
        db.session.add(Income(user_id=user_a.id, amount=Decimal("80000.00"), date=date(2026, 9, 1)))
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id, name="Rent").first()
        db.session.add(Expense(user_id=user_a.id, category_id=cat.id, amount=Decimal("20000.00"), date=date(2026, 9, 2), need_want="need"))
        db.session.commit()

        score_res = FinanceEngine.compute_financial_health_score(user_a.id, "salaried", month)
        assert 0.0 <= score_res["total_score"] <= 100.0
        assert "savings_score" in score_res["breakdown"]
        assert "budget_score" in score_res["breakdown"]
        assert "emergency_fund_score" in score_res["breakdown"]
        assert "discipline_score" in score_res["breakdown"]
        assert score_res["rating"] in ["Excellent", "Good", "Fair", "Needs Attention"]


def test_overspending_detection(app, user_a):
    """Test detection of over-budget categories."""
    with app.app_context():
        month = "2026-09"
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id, name="Dining out").first()

        # Create active budget plan with limit of 5,000
        plan = BudgetPlan(user_id=user_a.id, month=month, total_income_basis=Decimal("50000.00"), status="active")
        db.session.add(plan)
        db.session.flush()
        db.session.add(BudgetItem(plan_id=plan.id, category_id=cat.id, limit_amount=Decimal("5000.00")))

        # Record expense of 8,000 (exceeded)
        db.session.add(Expense(user_id=user_a.id, category_id=cat.id, amount=Decimal("8000.00"), date=date(2026, 9, 10), need_want="want"))
        db.session.commit()

        over = FinanceEngine.detect_overspending(user_a.id, month)
        assert over["has_overspending"] is True
        assert len(over["top_3_to_fix"]) > 0
        top_cat = over["top_3_to_fix"][0]
        assert top_cat["category"] == "Dining out"
        assert top_cat["status"] == "exceeded"
