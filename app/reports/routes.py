from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, Response
from flask_login import login_required, current_user
import json
from datetime import datetime

from app import db
from app.models import MonthlyReport
from app.services.finance_engine import FinanceEngine
from app.services.report_service import ReportService

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports")
@login_required
def index():
    # List historical reports or available months
    existing_reports = (
        MonthlyReport.query.filter_by(user_id=current_user.id)
        .order_by(MonthlyReport.month.desc())
        .all()
    )
    current_month = FinanceEngine.get_month_str()
    return render_template(
        "reports/index.html",
        reports=existing_reports,
        current_month=current_month
    )


@reports_bp.route("/reports/<month_str>")
@login_required
def view_report(month_str):
    # Check if report already stored in DB or generate snapshot
    report_record = MonthlyReport.query.filter_by(user_id=current_user.id, month=month_str).first()

    if report_record:
        report_data = report_record.summary_json
    else:
        # Generate fresh report snapshot and save
        report_data = ReportService.generate_monthly_report_data(current_user, month_str)
        report_record = MonthlyReport(
            user_id=current_user.id,
            month=month_str,
            summary_json=report_data
        )
        db.session.add(report_record)
        db.session.commit()

    return render_template(
        "reports/view.html",
        report=report_data,
        month_str=month_str
    )


@reports_bp.route("/reports/<month_str>/pdf")
@login_required
def download_pdf(month_str):
    report_record = MonthlyReport.query.filter_by(user_id=current_user.id, month=month_str).first()
    if report_record:
        report_data = report_record.summary_json
    else:
        report_data = ReportService.generate_monthly_report_data(current_user, month_str)

    pdf_buffer = ReportService.build_pdf_report(report_data)
    filename = f"finance_report_{current_user.name.lower().replace(' ', '_')}_{month_str}.pdf"

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


@reports_bp.route("/reports/export/csv")
@login_required
def export_csv():
    month_filter = request.args.get("month")
    csv_stream = ReportService.export_transactions_csv(current_user.id, month_filter)
    filename = f"transactions_{month_filter or 'all'}.csv"

    return Response(
        csv_stream.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
