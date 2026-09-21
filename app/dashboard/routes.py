from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from datetime import date
from decimal import Decimal

from app.models import BudgetPlan, SavingsGoal, ExpenseCategory
from app.services.finance_engine import FinanceEngine

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    selected_month = request.args.get("month", FinanceEngine.get_month_str())
    agg = FinanceEngine.get_monthly_aggregates(current_user.id, selected_month)
    health = FinanceEngine.compute_financial_health_score(current_user.id, current_user.profile_type, selected_month)
    plan = BudgetPlan.query.filter_by(user_id=current_user.id, month=selected_month, status="active").first()
    categories = ExpenseCategory.query.filter_by(user_id=current_user.id, is_archived=False).all()
    ef_status = FinanceEngine.calculate_emergency_fund_status(current_user.id, current_user.profile_type, selected_month)

    # Historical 6 months trend
    past_months = FinanceEngine.get_previous_months(selected_month, count=5) + [selected_month]
    trend_data = []
    for m in past_months:
        m_agg = FinanceEngine.get_monthly_aggregates(current_user.id, m)
        trend_data.append({
            "month": m,
            "income": float(m_agg["total_income"]),
            "expenses": float(m_agg["total_expenses"]),
            "savings": float(m_agg["net_savings"])
        })

    # Available months for selector
    months_choice = FinanceEngine.get_previous_months(FinanceEngine.get_month_str(), count=11) + [FinanceEngine.get_month_str()]
    months_choice = list(reversed(months_choice))

    return render_template(
        "dashboard/index.html",
        selected_month=selected_month,
        months_choice=months_choice,
        agg=agg,
        health=health,
        plan=plan,
        categories=categories,
        ef_status=ef_status,
        trend_data=trend_data
    )
