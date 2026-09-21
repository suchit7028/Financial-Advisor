"""
Monthly Financial Report Service and PDF / CSV Exporter
-------------------------------------------------------
Generates comprehensive monthly financial summaries.
Exports:
1. High-fidelity PDF report using ReportLab (pure-Python, zero external DLL dependencies)
2. CSV export of transactions.
"""

import os
import io
import csv
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)

from app.models import (
    User, Income, Expense, BudgetPlan, SavingsGoal, SavingsRecord, MonthlyReport
)
from app.services.finance_engine import FinanceEngine
from app.services.ai_provider import get_ai_provider, compute_input_hash


class ReportService:
    """Handles monthly report aggregation, PDF generation, and CSV transaction exports."""

    @classmethod
    def generate_monthly_report_data(cls, user: User, month_str: str) -> Dict[str, Any]:
        """
        Gathers all financial facts, compares budget vs. actual, runs health score,
        and includes AI insights for the monthly report.
        """
        # 1. Deterministic aggregates
        agg = FinanceEngine.get_monthly_aggregates(user.id, month_str)
        health_score = FinanceEngine.compute_financial_health_score(user.id, user.profile_type, month_str)
        overspending = FinanceEngine.detect_overspending(user.id, month_str)
        ef_status = FinanceEngine.calculate_emergency_fund_status(user.id, user.profile_type, month_str)

        # 2. Budget vs Actual comparison
        plan = BudgetPlan.query.filter_by(user_id=user.id, month=month_str, status="active").first()
        budget_comparison = []
        total_budget_limit = Decimal("0.00")

        if plan:
            for item in plan.items:
                cat_name = item.category.name if item.category else "Unknown"
                limit_amt = item.limit_amount
                actual_spent = Decimal(str(agg["expense_by_category"].get(cat_name, 0.0)))
                diff = limit_amt - actual_spent
                ratio = (actual_spent / limit_amt * 100) if limit_amt > 0 else 0.0

                if ratio > 100.0:
                    status = "Exceeded"
                elif ratio >= 80.0:
                    status = "Near Limit"
                else:
                    status = "On Track"

                budget_comparison.append({
                    "category": cat_name,
                    "kind": item.category.kind if item.category else "other",
                    "limit": float(limit_amt),
                    "actual": float(actual_spent),
                    "diff": float(diff),
                    "ratio": round(float(ratio), 1),
                    "status": status
                })
                total_budget_limit += limit_amt

        # 3. Monthly savings achieved vs goal
        monthly_goal = float(user.monthly_savings_goal)
        net_savings = float(agg["net_savings"])
        savings_goal_achieved = net_savings >= monthly_goal if monthly_goal > 0 else True
        savings_goal_pct = min(100.0, round((net_savings / monthly_goal * 100), 1)) if monthly_goal > 0 else 100.0

        # 4. AI Insights & advice
        ai = get_ai_provider()
        ai_insights = ai.generate_spending_insights(
            persona=user.profile_type,
            currency=user.currency,
            health_score=health_score,
            overspending_data=overspending,
            emergency_fund_data=ef_status,
            needs_wants_data={"needs": float(agg["needs_total"]), "wants": float(agg["wants_total"])},
            category_breakdown=agg["expense_by_category"]
        )

        currency_symbols = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
        currency_sym = currency_symbols.get(user.currency, "₹")

        return {
            "month": month_str,
            "user_name": user.name,
            "profile_type": user.profile_type.capitalize(),
            "currency": user.currency,
            "currency_symbol": currency_sym,
            "total_income": float(agg["total_income"]),
            "total_expenses": float(agg["total_expenses"]),
            "net_savings": net_savings,
            "savings_rate": agg["savings_rate"],
            "monthly_savings_goal": monthly_goal,
            "savings_goal_achieved": savings_goal_achieved,
            "savings_goal_pct": savings_goal_pct,
            "income_by_source": agg["income_by_source"],
            "expense_by_category": agg["expense_by_category"],
            "needs_total": float(agg["needs_total"]),
            "wants_total": float(agg["wants_total"]),
            "budget_comparison": budget_comparison,
            "total_budget_limit": float(total_budget_limit),
            "health_score": health_score,
            "top_overspends": overspending["top_3_to_fix"],
            "emergency_fund": ef_status,
            "ai_insights": ai_insights,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @classmethod
    def build_pdf_report(cls, report_data: Dict[str, Any]) -> io.BytesIO:
        """
        Creates a beautifully styled, corporate-quality PDF monthly financial report
        using ReportLab Platypus.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        # Custom palette
        PRIMARY = colors.HexColor("#0f172a")     # Slate 900
        SECONDARY = colors.HexColor("#1e293b")   # Slate 800
        ACCENT = colors.HexColor("#0d9488")      # Teal 600
        EMERALD = colors.HexColor("#10b981")     # Emerald 500
        ROSE = colors.HexColor("#ef4444")        # Rose 500
        AMBER = colors.HexColor("#f59e0b")       # Amber 500
        LIGHT_BG = colors.HexColor("#f8fafc")    # Slate 50
        BORDER = colors.HexColor("#e2e8f0")      # Slate 200

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=PRIMARY,
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#64748b")
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=PRIMARY,
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155")
        )
        badge_style = ParagraphStyle(
            "ScoreBadge",
            parent=styles["Normal"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#ffffff"),
            alignment=1
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Italic"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b")
        )

        elements = []
        sym = report_data.get("currency_symbol", "₹")

        # Header Block
        elements.append(Paragraph("Personal Finance Advisor Bot", title_style))
        elements.append(
            Paragraph(
                f"Monthly Financial Performance Report — <b>{report_data['month']}</b> | "
                f"Client: {report_data['user_name']} ({report_data['profile_type']})",
                subtitle_style
            )
        )
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=15))

        # KPI Summary Cards (Income, Expenses, Savings, Health Score)
        score_val = report_data["health_score"]["total_score"]
        score_rating = report_data["health_score"]["rating"]
        
        kpi_data = [
            [
                Paragraph("<b>Total Income</b>", subtitle_style),
                Paragraph("<b>Total Expenses</b>", subtitle_style),
                Paragraph("<b>Net Savings</b>", subtitle_style),
                Paragraph("<b>Financial Health</b>", subtitle_style)
            ],
            [
                Paragraph(f"<font size=13 color='#0f172a'><b>{sym} {report_data['total_income']:,.2f}</b></font>", body_style),
                Paragraph(f"<font size=13 color='#ef4444'><b>{sym} {report_data['total_expenses']:,.2f}</b></font>", body_style),
                Paragraph(f"<font size=13 color='#10b981'><b>{sym} {report_data['net_savings']:,.2f}</b></font><br/>"
                          f"<font size=8 color='#64748b'>Rate: {report_data['savings_rate']}%</font>", body_style),
                Paragraph(f"<font size=13 color='#0d9488'><b>{score_val}/100</b></font><br/>"
                          f"<font size=8 color='#64748b'>{score_rating}</font>", body_style)
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 15))

        # Budget vs Actual Section
        elements.append(Paragraph("Category Budget vs. Actual Spending", h2_style))
        budget_items = report_data.get("budget_comparison", [])

        if budget_items:
            b_rows = [
                [
                    Paragraph("<b>Category</b>", body_style),
                    Paragraph("<b>Type</b>", body_style),
                    Paragraph("<b>Budget Limit</b>", body_style),
                    Paragraph("<b>Actual Spent</b>", body_style),
                    Paragraph("<b>Utilization</b>", body_style),
                    Paragraph("<b>Status</b>", body_style)
                ]
            ]
            for bi in budget_items:
                status_color = "#10b981" if bi["status"] == "On Track" else ("#f59e0b" if bi["status"] == "Near Limit" else "#ef4444")
                b_rows.append([
                    Paragraph(bi["category"], body_style),
                    Paragraph(bi["kind"].capitalize(), body_style),
                    Paragraph(f"{sym} {bi['limit']:,.2f}", body_style),
                    Paragraph(f"{sym} {bi['actual']:,.2f}", body_style),
                    Paragraph(f"{bi['ratio']}%", body_style),
                    Paragraph(f"<font color='{status_color}'><b>{bi['status']}</b></font>", body_style)
                ])
            b_table = Table(b_rows, colWidths=[130, 60, 90, 90, 80, 90])
            b_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(b_table)
        else:
            elements.append(Paragraph("No active budget plan was activated for this month.", body_style))

        elements.append(Spacer(1, 15))

        # Overspending & Emergency Fund
        elements.append(Paragraph("Overspending Flags & Emergency Reserve", h2_style))
        top_over = report_data.get("top_overspends", [])
        ef = report_data.get("emergency_fund", {})

        over_text = "<b>Top Categories to Optimize:</b><br/>"
        if top_over:
            for o in top_over:
                reasons_str = "; ".join(o.get("reasons", []))
                over_text += f"• <b>{o['category']}</b>: Spent {sym} {o['actual_spend']:,.2f} ({reasons_str})<br/>"
        else:
            over_text += "• No overspending spikes detected this month.<br/>"

        ef_text = (
            f"<b>Emergency Fund Status:</b><br/>"
            f"• Target Reserve: {sym} {ef.get('target_amount', 0):,.2f} ({ef.get('target_months', 3)} months)<br/>"
            f"• Currently Saved: {sym} {ef.get('current_saved', 0):,.2f} ({ef.get('months_covered', 0)} months covered)<br/>"
            f"• Target Gap: {sym} {ef.get('gap', 0):,.2f} ({ef.get('progress_pct', 0)}% funded)"
        )

        alerts_data = [
            [Paragraph(over_text, body_style), Paragraph(ef_text, body_style)]
        ]
        alerts_table = Table(alerts_data, colWidths=[270, 270])
        alerts_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(alerts_table)
        elements.append(Spacer(1, 15))

        # AI Recommendations Block
        elements.append(Paragraph("AI Spending Insights & Strategy", h2_style))
        ai = report_data.get("ai_insights", {})
        ai_p = Paragraph(
            f"<b>Financial Health Diagnosis:</b> {ai.get('health_summary', '')}<br/><br/>"
            f"<b>Cost Optimization Actions:</b><br/>" +
            "<br/>".join([f"• {tip}" for tip in ai.get("cost_optimizations", [])]) +
            f"<br/><br/><b>Suggested Goals for Next Month:</b><br/>" +
            "<br/>".join([f"• {goal}" for goal in ai.get("next_month_goals", [])]),
            body_style
        )
        ai_table = Table([[ai_p]], colWidths=[540])
        ai_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, ACCENT),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(ai_table)
        elements.append(Spacer(1, 15))

        # Disclaimer
        elements.append(
            Paragraph(
                "<b>Disclaimer:</b> Personal Finance Advisor Bot generates insights for informational and educational "
                "purposes only. It does not provide certified financial, tax, or legal advice. All calculations are "
                "computed deterministically by system rules.",
                disclaimer_style
            )
        )

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @classmethod
    def export_transactions_csv(cls, user_id: int, month_str: Optional[str] = None) -> io.StringIO:
        """
        Exports all incomes and expenses for the user (optionally filtered by month)
        as a clean, structured CSV.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Transaction ID",
            "Type",
            "Date",
            "Category / Source",
            "Kind / Nature",
            "Amount",
            "Payment Method",
            "Need vs Want",
            "Notes"
        ])

        # Query incomes
        inc_query = Income.query.filter_by(user_id=user_id)
        if month_str:
            inc_query = inc_query.filter(Income.date.like(f"{month_str}%"))
        incomes = inc_query.order_by(Income.date.desc()).all()

        for inc in incomes:
            writer.writerow([
                f"INC-{inc.id}",
                "Income",
                inc.date.strftime("%Y-%m-%d"),
                inc.source.name if inc.source else "Other Income",
                inc.source.type if inc.source else "General",
                float(inc.amount),
                "-",
                "-",
                inc.notes or ""
            ])

        # Query expenses
        exp_query = Expense.query.filter_by(user_id=user_id)
        if month_str:
            exp_query = exp_query.filter(Expense.date.like(f"{month_str}%"))
        expenses = exp_query.order_by(Expense.date.desc()).all()

        for exp in expenses:
            writer.writerow([
                f"EXP-{exp.id}",
                "Expense",
                exp.date.strftime("%Y-%m-%d"),
                exp.category.name if exp.category else "Uncategorized",
                exp.category.kind if exp.category else "other",
                float(exp.amount),
                exp.payment_method or "-",
                exp.need_want,
                exp.notes or ""
            ])

        output.seek(0)
        return output
