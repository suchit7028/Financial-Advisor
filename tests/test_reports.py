import pytest
from decimal import Decimal
from datetime import date
from app import db
from app.models import Income, Expense, ExpenseCategory
from app.services.report_service import ReportService
from tests.conftest import login


def test_monthly_report_data_generation(app, user_a):
    """Test generating full monthly summary data."""
    with app.app_context():
        # Add income and expense
        db.session.add(Income(user_id=user_a.id, amount=Decimal("75000.00"), date=date(2026, 9, 1)))
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id, name="Rent").first()
        db.session.add(Expense(user_id=user_a.id, category_id=cat.id, amount=Decimal("25000.00"), date=date(2026, 9, 2), need_want="need"))
        db.session.commit()

        data = ReportService.generate_monthly_report_data(user_a, "2026-09")
        assert data["total_income"] == 75000.0
        assert data["total_expenses"] == 25000.0
        assert data["net_savings"] == 50000.0
        assert data["health_score"]["total_score"] > 0
        assert "ai_insights" in data


def test_reportlab_pdf_generation(app, user_a):
    """Test ReportLab compiles a valid PDF document without errors."""
    with app.app_context():
        data = ReportService.generate_monthly_report_data(user_a, "2026-09")
        pdf_buffer = ReportService.build_pdf_report(data)
        pdf_bytes = pdf_buffer.getvalue()

        # PDF files must begin with '%PDF'
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000  # Substantial PDF document created


def test_csv_export_format(app, user_a):
    """Test exporting CSV transactions."""
    with app.app_context():
        db.session.add(Income(user_id=user_a.id, amount=Decimal("50000.00"), date=date(2026, 9, 1), notes="Freelance Milestone 1"))
        cat = ExpenseCategory.query.filter_by(user_id=user_a.id, name="Groceries").first()
        db.session.add(Expense(user_id=user_a.id, category_id=cat.id, amount=Decimal("2500.00"), date=date(2026, 9, 5), notes="Weekly fruits"))
        db.session.commit()

        csv_stream = ReportService.export_transactions_csv(user_a.id, "2026-09")
        content = csv_stream.getvalue()

        assert "Transaction ID,Type,Date,Category / Source" in content
        assert "Freelance Milestone 1" in content
        assert "Weekly fruits" in content
        assert "2500.0" in content


def test_reports_http_download_pdf(client, user_a):
    """Test /reports/<yyyy-mm>/pdf route returns application/pdf."""
    login(client, user_a.email, "SecretPassword123!")
    res = client.get("/reports/2026-09/pdf")
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert res.data.startswith(b"%PDF")
