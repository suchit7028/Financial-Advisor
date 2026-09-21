from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime, date

from app import db, limiter
from app.models import Income, Expense, ExpenseCategory, BudgetPlan, AIInsight
from app.services.finance_engine import FinanceEngine
from app.services.budget_validator import BudgetValidator
from app.services.ai_provider import get_ai_provider, compute_input_hash
from app.services.report_service import ReportService

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/dashboard", methods=["GET"])
@login_required
def api_dashboard():
    """Returns all data needed by Chart.js charts."""
    month_str = request.args.get("month", FinanceEngine.get_month_str())
    agg = FinanceEngine.get_monthly_aggregates(current_user.id, month_str)
    health = FinanceEngine.compute_financial_health_score(current_user.id, current_user.profile_type, month_str)
    ef_status = FinanceEngine.calculate_emergency_fund_status(current_user.id, current_user.profile_type, month_str)
    overspending = FinanceEngine.detect_overspending(current_user.id, month_str)

    # 6-month historical trend
    months_window = FinanceEngine.get_previous_months(month_str, count=5) + [month_str]
    trend_labels = []
    trend_income = []
    trend_expense = []
    trend_savings = []

    for m in months_window:
        m_agg = FinanceEngine.get_monthly_aggregates(current_user.id, m)
        trend_labels.append(m)
        trend_income.append(float(m_agg["total_income"]))
        trend_expense.append(float(m_agg["total_expenses"]))
        trend_savings.append(float(m_agg["net_savings"]))

    # Budget vs Actual comparison
    plan = BudgetPlan.query.filter_by(user_id=current_user.id, month=month_str, status="active").first()
    budget_labels = []
    budget_limits = []
    actual_spends = []
    budget_colors = []

    if plan:
        for item in plan.items:
            cat_name = item.category.name if item.category else "Unknown"
            limit = float(item.limit_amount)
            actual = float(agg["expense_by_category"].get(cat_name, 0.0))
            budget_labels.append(cat_name)
            budget_limits.append(limit)
            actual_spends.append(actual)
            ratio = actual / limit if limit > 0 else 0.0
            if ratio > 1.0:
                budget_colors.append("#ef4444")  # red
            elif ratio >= 0.8:
                budget_colors.append("#f59e0b")  # amber
            else:
                budget_colors.append("#10b981")  # green

    return jsonify({
        "month": month_str,
        "kpis": {
            "total_income": float(agg["total_income"]),
            "total_expenses": float(agg["total_expenses"]),
            "net_savings": float(agg["net_savings"]),
            "savings_rate": agg["savings_rate"],
            "needs_total": float(agg["needs_total"]),
            "wants_total": float(agg["wants_total"]),
            "health_score": health["total_score"],
            "health_rating": health["rating"],
            "emergency_fund_progress": ef_status["progress_pct"]
        },
        "income_by_source": agg["income_by_source"],
        "expense_by_category": agg["expense_by_category"],
        "trend": {
            "labels": trend_labels,
            "income": trend_income,
            "expenses": trend_expense,
            "savings": trend_savings
        },
        "budget_performance": {
            "has_budget": plan is not None,
            "labels": budget_labels,
            "limits": budget_limits,
            "actuals": actual_spends,
            "colors": budget_colors
        },
        "overspending": overspending["top_3_to_fix"],
        "emergency_fund": ef_status
    })


@api_bp.route("/expenses", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def api_add_expense():
    """Quick Add Expense endpoint (used by AJAX floating modal for <15s logging)."""
    data = request.get_json() or request.form
    try:
        amount = Decimal(str(data.get("amount", 0)))
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than zero."}), 400

        cat_id = int(data.get("category_id"))
        cat = ExpenseCategory.query.filter_by(id=cat_id, user_id=current_user.id).first()
        if not cat:
            return jsonify({"success": False, "error": "Invalid category."}), 400

        exp_date_str = data.get("date")
        exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date() if exp_date_str else date.today()

        need_want = data.get("need_want") or (cat.kind if cat.kind in ("need", "want") else "need")
        payment_method = data.get("payment_method", "upi")
        notes = data.get("notes", "").strip()

        expense = Expense(
            user_id=current_user.id,
            category_id=cat.id,
            amount=amount,
            date=exp_date,
            payment_method=payment_method,
            need_want=need_want,
            notes=notes if notes else None
        )
        db.session.add(expense)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Expense logged successfully!",
            "expense": expense.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/incomes", methods=["POST"])
@login_required
def api_add_income():
    data = request.get_json() or request.form
    try:
        amount = Decimal(str(data.get("amount", 0)))
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than zero."}), 400

        source_id = data.get("source_id")
        if source_id and int(source_id) != 0:
            source_id = int(source_id)
        else:
            source_id = None

        inc_date_str = data.get("date")
        inc_date = datetime.strptime(inc_date_str, "%Y-%m-%d").date() if inc_date_str else date.today()
        notes = data.get("notes", "").strip()

        inc = Income(
            user_id=current_user.id,
            source_id=source_id,
            amount=amount,
            date=inc_date,
            notes=notes if notes else None
        )
        db.session.add(inc)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Income logged successfully!",
            "income": inc.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/insights", methods=["GET"])
@login_required
def api_get_insights():
    month_str = request.args.get("month", FinanceEngine.get_month_str())
    agg = FinanceEngine.get_monthly_aggregates(current_user.id, month_str)
    health = FinanceEngine.compute_financial_health_score(current_user.id, current_user.profile_type, month_str)
    overspending = FinanceEngine.detect_overspending(current_user.id, month_str)
    ef_status = FinanceEngine.calculate_emergency_fund_status(current_user.id, current_user.profile_type, month_str)

    ai = get_ai_provider()
    insights = ai.generate_spending_insights(
        persona=current_user.profile_type,
        currency=current_user.currency,
        health_score=health,
        overspending_data=overspending,
        emergency_fund_data=ef_status,
        needs_wants_data={"needs": float(agg["needs_total"]), "wants": float(agg["wants_total"])},
        category_breakdown=agg["expense_by_category"]
    )
    return jsonify({
        "month": month_str,
        "health_score": health,
        "insights": insights
    })


@api_bp.route("/export/transactions.csv", methods=["GET"])
@login_required
def api_export_csv():
    month = request.args.get("month")
    csv_stream = ReportService.export_transactions_csv(current_user.id, month)
    filename = f"transactions_{month or 'all'}.csv"
    return Response(
        csv_stream.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
