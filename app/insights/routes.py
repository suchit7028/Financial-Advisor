from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
import json
from datetime import datetime

from app import db
from app.models import AIInsight
from app.services.finance_engine import FinanceEngine
from app.services.ai_provider import get_ai_provider, compute_input_hash

insights_bp = Blueprint("insights", __name__)


@insights_bp.route("/insights", methods=["GET"])
@login_required
def index():
    selected_month = request.args.get("month", FinanceEngine.get_month_str())
    force_refresh = request.args.get("refresh", "0") == "1"

    # Deterministic analytics
    agg = FinanceEngine.get_monthly_aggregates(current_user.id, selected_month)
    health_score = FinanceEngine.compute_financial_health_score(current_user.id, current_user.profile_type, selected_month)
    overspending = FinanceEngine.detect_overspending(current_user.id, selected_month)
    ef_status = FinanceEngine.calculate_emergency_fund_status(current_user.id, current_user.profile_type, selected_month)

    # Student persona runway
    runway = None
    if current_user.profile_type == "student":
        runway = FinanceEngine.calculate_allowance_runway(current_user.id, selected_month)

    # Check cached AI insights
    cached_insight = (
        AIInsight.query.filter_by(user_id=current_user.id, month=selected_month, type="spending")
        .order_by(AIInsight.created_at.desc())
        .first()
    )

    input_payload = {
        "score": health_score["total_score"],
        "overspending": [o["category"] for o in overspending["top_3_to_fix"]],
        "expenses": float(agg["total_expenses"]),
        "income": float(agg["total_income"]),
        "ef_gap": ef_status["gap"]
    }
    input_hash = compute_input_hash(input_payload)

    ai_data = None
    if cached_insight and not force_refresh:
        # Use cache if hash matches or created recently
        ai_data = cached_insight.payload_json
    else:
        # Generate fresh AI insights
        ai = get_ai_provider()
        ai_data = ai.generate_spending_insights(
            persona=current_user.profile_type,
            currency=current_user.currency,
            health_score=health_score,
            overspending_data=overspending,
            emergency_fund_data=ef_status,
            needs_wants_data={"needs": float(agg["needs_total"]), "wants": float(agg["wants_total"])},
            category_breakdown=agg["expense_by_category"]
        )
        # Store in cache
        record = AIInsight(
            user_id=current_user.id,
            month=selected_month,
            type="spending",
            payload_json=ai_data,
            input_hash=input_hash
        )
        db.session.add(record)
        db.session.commit()
        if force_refresh:
            flash("AI insights refreshed with your latest spending data!", "success")

    return render_template(
        "insights/index.html",
        selected_month=selected_month,
        health_score=health_score,
        overspending=overspending,
        ef_status=ef_status,
        runway=runway,
        ai_data=ai_data,
        aggregates=agg
    )
