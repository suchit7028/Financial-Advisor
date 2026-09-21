from datetime import datetime, date
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_type = db.Column(db.String(30), default="salaried", nullable=False)  # salaried, student, freelancer, household
    currency = db.Column(db.String(10), default="INR", nullable=False)  # INR, USD, EUR, GBP
    monthly_savings_goal = db.Column(db.Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    emergency_fund_target = db.Column(db.Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    dependents = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    income_sources = db.relationship("IncomeSource", backref="user", cascade="all, delete-orphan", lazy=True)
    incomes = db.relationship("Income", backref="user", cascade="all, delete-orphan", lazy=True)
    categories = db.relationship("ExpenseCategory", backref="user", cascade="all, delete-orphan", lazy=True)
    expenses = db.relationship("Expense", backref="user", cascade="all, delete-orphan", lazy=True)
    budget_plans = db.relationship("BudgetPlan", backref="user", cascade="all, delete-orphan", lazy=True)
    savings_goals = db.relationship("SavingsGoal", backref="user", cascade="all, delete-orphan", lazy=True)
    savings_records = db.relationship("SavingsRecord", backref="user", cascade="all, delete-orphan", lazy=True)
    ai_insights = db.relationship("AIInsight", backref="user", cascade="all, delete-orphan", lazy=True)
    monthly_reports = db.relationship("MonthlyReport", backref="user", cascade="all, delete-orphan", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} ({self.profile_type})>"


class IncomeSource(db.Model):
    """User defined or preset income source."""
    __tablename__ = "income_sources"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), default="salary", nullable=False)  # salary, freelance, allowance, investment, other
    is_recurring = db.Column(db.Boolean, default=True, nullable=False)
    expected_amount = db.Column(db.Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    incomes = db.relationship("Income", backref="source", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "is_recurring": self.is_recurring,
            "expected_amount": float(self.expected_amount)
        }


class Income(db.Model):
    """Recorded income transaction."""
    __tablename__ = "incomes"
    __table_args__ = (
        db.Index("idx_income_user_date", "user_id", "date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = db.Column(db.Integer, db.ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_id": self.source_id,
            "source_name": self.source.name if self.source else "Other",
            "amount": float(self.amount),
            "date": self.date.strftime("%Y-%m-%d"),
            "notes": self.notes or ""
        }


class ExpenseCategory(db.Model):
    """Custom or default expense category."""
    __tablename__ = "expense_categories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(20), default="need", nullable=False)  # need, want, savings, other
    icon = db.Column(db.String(50), default="tag", nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    expenses = db.relationship("Expense", backref="category", lazy=True)
    budget_items = db.relationship("BudgetItem", backref="category", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "icon": self.icon,
            "is_archived": self.is_archived
        }


class Expense(db.Model):
    """Recorded expense transaction."""
    __tablename__ = "expenses"
    __table_args__ = (
        db.Index("idx_expense_user_date", "user_id", "date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("expense_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    payment_method = db.Column(db.String(50), nullable=True)  # cash, card, upi, bank_transfer
    need_want = db.Column(db.String(20), default="need", nullable=False)  # need, want
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Uncategorized",
            "category_kind": self.category.kind if self.category else "other",
            "amount": float(self.amount),
            "date": self.date.strftime("%Y-%m-%d"),
            "payment_method": self.payment_method or "",
            "need_want": self.need_want,
            "notes": self.notes or ""
        }


class BudgetPlan(db.Model):
    """Monthly budget plan."""
    __tablename__ = "budget_plans"
    __table_args__ = (
        db.UniqueConstraint("user_id", "month", name="uq_user_budget_month"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    total_income_basis = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)  # draft, active, closed
    generated_by = db.Column(db.String(20), default="baseline", nullable=False)  # user, ai, baseline
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    items = db.relationship("BudgetItem", backref="plan", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "month": self.month,
            "total_income_basis": float(self.total_income_basis),
            "status": self.status,
            "generated_by": self.generated_by,
            "items": [item.to_dict() for item in self.items]
        }


class BudgetItem(db.Model):
    """Individual category limit within a budget plan."""
    __tablename__ = "budget_items"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("budget_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("expense_categories.id", ondelete="CASCADE"), nullable=False)
    limit_amount = db.Column(db.Numeric(12, 2), nullable=False)
    ai_reason = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Unknown",
            "limit_amount": float(self.limit_amount),
            "ai_reason": self.ai_reason or ""
        }


class SavingsGoal(db.Model):
    """Target savings goal or emergency fund."""
    __tablename__ = "savings_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    target_date = db.Column(db.Date, nullable=True)
    is_emergency_fund = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    records = db.relationship("SavingsRecord", backref="goal", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        total_saved = sum(float(r.amount_saved) for r in self.records)
        target = float(self.target_amount)
        progress_pct = min(100.0, round((total_saved / target * 100), 1)) if target > 0 else 0.0
        return {
            "id": self.id,
            "name": self.name,
            "target_amount": target,
            "total_saved": total_saved,
            "progress_pct": progress_pct,
            "target_date": self.target_date.strftime("%Y-%m-%d") if self.target_date else None,
            "is_emergency_fund": self.is_emergency_fund
        }


class SavingsRecord(db.Model):
    """Monthly contribution record towards a savings goal."""
    __tablename__ = "savings_records"
    __table_args__ = (
        db.UniqueConstraint("user_id", "goal_id", "month", name="uq_user_goal_month"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    amount_saved = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AIInsight(db.Model):
    """Cached AI insights and spending advice."""
    __tablename__ = "ai_insights"
    __table_args__ = (
        db.Index("idx_insight_user_month_type", "user_id", "month", "type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    type = db.Column(db.String(30), nullable=False)  # budget, spending, savings, health, emergency
    payload_json = db.Column(db.JSON, nullable=False)
    input_hash = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "month": self.month,
            "type": self.type,
            "payload": self.payload_json,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }


class MonthlyReport(db.Model):
    """Generated monthly report with snapshot and PDF artifact path."""
    __tablename__ = "monthly_reports"
    __table_args__ = (
        db.UniqueConstraint("user_id", "month", name="uq_user_report_month"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    summary_json = db.Column(db.JSON, nullable=False)
    pdf_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "month": self.month,
            "summary": self.summary_json,
            "pdf_path": self.pdf_path,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
