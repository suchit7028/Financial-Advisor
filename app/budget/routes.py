from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal

from app import db
from app.models import BudgetPlan, BudgetItem, ExpenseCategory, Expense
from app.services.finance_engine import FinanceEngine
from app.services.budget_validator import BudgetValidator
from app.services.ai_provider import get_ai_provider

budget_bp = Blueprint("budget", __name__)


@budget_bp.route("/budget", methods=["GET"])
@login_required
def index():
    selected_month = request.args.get("month", FinanceEngine.get_month_str())
    plan = BudgetPlan.query.filter_by(user_id=current_user.id, month=selected_month, status="active").first()

    # Aggregate current month expenses
    agg = FinanceEngine.get_monthly_aggregates(current_user.id, selected_month)
    trailing = FinanceEngine.get_trailing_3_months_average(current_user.id, selected_month)

    items_status = []
    total_budget = Decimal("0.00")
    total_spent = Decimal("0.00")

    if plan:
        for item in plan.items:
            cat_name = item.category.name if item.category else "Unknown"
            limit_amt = item.limit_amount
            spent = Decimal(str(agg["expense_by_category"].get(cat_name, 0.0)))
            total_budget += limit_amt
            total_spent += spent
            remaining = limit_amt - spent

            ratio = (spent / limit_amt * 100) if limit_amt > 0 else 0.0
            if ratio > 100.0:
                status = "exceeded"
            elif ratio >= 80.0:
                status = "near_limit"
            else:
                status = "on_track"

            items_status.append({
                "item_id": item.id,
                "category_id": item.category_id,
                "category_name": cat_name,
                "category_kind": item.category.kind if item.category else "other",
                "limit_amount": float(limit_amt),
                "actual_spent": float(spent),
                "remaining": float(remaining),
                "utilization_pct": round(float(ratio), 1),
                "status": status,
                "ai_reason": item.ai_reason or ""
            })

    total_income = agg["total_income"]
    unallocated = max(Decimal("0.00"), total_income - total_budget)

    return render_template(
        "budget/index.html",
        plan=plan,
        selected_month=selected_month,
        items=items_status,
        total_budget=total_budget,
        total_spent=total_spent,
        total_income=total_income,
        unallocated=unallocated,
        active_categories=ExpenseCategory.query.filter_by(user_id=current_user.id, is_archived=False).all()
    )


@budget_bp.route("/budget/generate", methods=["GET", "POST"])
@login_required
def generate_proposal():
    target_month = request.args.get("month", FinanceEngine.get_next_month(FinanceEngine.get_month_str()))
    active_cats = ExpenseCategory.query.filter_by(user_id=current_user.id, is_archived=False).all()

    if not active_cats:
        flash("Please create at least one expense category before generating a budget.", "warning")
        return redirect(url_for("tracking.categories"))

    expected_income = request.args.get("income", type=float)

    # Generate validated proposal using deterministic engine + AI
    ai = get_ai_provider()
    proposal = BudgetValidator.get_validated_ai_budget(
        ai_provider=ai,
        user_id=current_user.id,
        user_profile_type=current_user.profile_type,
        currency=current_user.currency,
        target_month=target_month,
        active_categories=active_cats,
        expected_income=expected_income
    )

    return render_template(
        "budget/review.html",
        proposal=proposal,
        target_month=target_month,
        active_categories=active_cats
    )


@budget_bp.route("/budget/accept", methods=["POST"])
@login_required
def accept_proposal():
    month = request.form.get("month")
    if not month:
        flash("Invalid month specified.", "danger")
        return redirect(url_for("budget.index"))

    income_basis = Decimal(request.form.get("total_income_basis", "0.00"))
    generated_by = request.form.get("generated_by", "ai")

    # Deactivate or replace any existing plan for this month
    existing_plan = BudgetPlan.query.filter_by(user_id=current_user.id, month=month).first()
    if existing_plan:
        db.session.delete(existing_plan)
        db.session.commit()

    plan = BudgetPlan(
        user_id=current_user.id,
        month=month,
        total_income_basis=income_basis,
        status="active",
        generated_by=generated_by
    )
    db.session.add(plan)
    db.session.flush()

    # Parse category limits submitted from the review form
    active_cats = ExpenseCategory.query.filter_by(user_id=current_user.id, is_archived=False).all()
    total_allocated = Decimal("0.00")

    for cat in active_cats:
        limit_val = request.form.get(f"limit_{cat.id}")
        reason_val = request.form.get(f"reason_{cat.id}", "")
        if limit_val is not None:
            try:
                amt = Decimal(limit_val)
                if amt < 0:
                    amt = Decimal("0.00")
            except Exception:
                amt = Decimal("0.00")

            item = BudgetItem(
                plan_id=plan.id,
                category_id=cat.id,
                limit_amount=amt,
                ai_reason=reason_val.strip() if reason_val else None
            )
            db.session.add(item)
            total_allocated += amt

    db.session.commit()
    flash(f"Monthly budget for {month} activated successfully! Total allocated: {total_allocated}", "success")
    return redirect(url_for("budget.index", month=month))
