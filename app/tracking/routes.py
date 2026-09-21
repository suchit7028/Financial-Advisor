from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from datetime import date
from decimal import Decimal

from app import db
from app.models import Income, IncomeSource, Expense, ExpenseCategory
from app.tracking.forms import IncomeForm, IncomeSourceForm, ExpenseForm, CategoryForm
from app.services.finance_engine import FinanceEngine

tracking_bp = Blueprint("tracking", __name__)


# ---------------------- INCOMES ----------------------

@tracking_bp.route("/income", methods=["GET", "POST"])
@login_required
def income():
    form = IncomeForm()
    # Populate sources dropdown
    sources = IncomeSource.query.filter_by(user_id=current_user.id).all()
    form.source_id.choices = [(0, "No Source (Other)")] + [(s.id, s.name) for s in sources]

    if form.validate_on_submit():
        src_id = form.source_id.data if form.source_id.data != 0 else None
        inc = Income(
            user_id=current_user.id,
            source_id=src_id,
            amount=form.amount.data,
            date=form.date.data,
            notes=form.notes.data.strip() if form.notes.data else None
        )
        db.session.add(inc)
        db.session.commit()
        flash("Income entry recorded successfully!", "success")
        return redirect(url_for("tracking.income"))

    # Selected month filter or current month
    selected_month = request.args.get("month", FinanceEngine.get_month_str())
    incomes = (
        Income.query.filter(
            Income.user_id == current_user.id,
            Income.date.like(f"{selected_month}%")
        ).order_by(Income.date.desc()).all()
    )
    total_income = sum((i.amount for i in incomes), Decimal("0.00"))

    source_form = IncomeSourceForm()
    return render_template(
        "tracking/income.html",
        form=form,
        source_form=source_form,
        incomes=incomes,
        sources=sources,
        total_income=total_income,
        selected_month=selected_month
    )


@tracking_bp.route("/income/delete/<int:income_id>", methods=["POST"])
@login_required
def delete_income(income_id):
    inc = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()
    db.session.delete(inc)
    db.session.commit()
    flash("Income entry deleted.", "info")
    return redirect(url_for("tracking.income"))


@tracking_bp.route("/income/source/add", methods=["POST"])
@login_required
def add_income_source():
    form = IncomeSourceForm()
    if form.validate_on_submit():
        src = IncomeSource(
            user_id=current_user.id,
            name=form.name.data.strip(),
            type=form.type.data,
            is_recurring=form.is_recurring.data,
            expected_amount=form.expected_amount.data or 0.0
        )
        db.session.add(src)
        db.session.commit()
        flash(f"Income source '{src.name}' added!", "success")
    else:
        flash("Failed to add income source. Please check the values.", "danger")
    return redirect(url_for("tracking.income"))


# ---------------------- EXPENSES ----------------------

@tracking_bp.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    form = ExpenseForm()
    # Active categories for current user
    categories = ExpenseCategory.query.filter_by(user_id=current_user.id, is_archived=False).all()
    form.category_id.choices = [(c.id, f"{c.name} ({c.kind.capitalize()})") for c in categories]

    if form.validate_on_submit():
        cat = ExpenseCategory.query.filter_by(id=form.category_id.data, user_id=current_user.id).first()
        need_want = form.need_want.data or (cat.kind if cat and cat.kind in ("need", "want") else "need")

        exp = Expense(
            user_id=current_user.id,
            category_id=form.category_id.data,
            amount=form.amount.data,
            date=form.date.data,
            payment_method=form.payment_method.data,
            need_want=need_want,
            notes=form.notes.data.strip() if form.notes.data else None
        )
        db.session.add(exp)
        db.session.commit()
        flash("Expense logged successfully!", "success")
        return redirect(url_for("tracking.expenses"))

    selected_month = request.args.get("month", FinanceEngine.get_month_str())
    cat_filter = request.args.get("category_id", type=int)

    query = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date.like(f"{selected_month}%")
    )
    if cat_filter:
        query = query.filter(Expense.category_id == cat_filter)

    expense_list = query.order_by(Expense.date.desc()).all()
    total_expenses = sum((e.amount for e in expense_list), Decimal("0.00"))

    return render_template(
        "tracking/expenses.html",
        form=form,
        expenses=expense_list,
        categories=categories,
        total_expenses=total_expenses,
        selected_month=selected_month,
        selected_category=cat_filter
    )


@tracking_bp.route("/expenses/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    exp = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    db.session.delete(exp)
    db.session.commit()
    flash("Expense entry removed.", "info")
    return redirect(url_for("tracking.expenses"))


# ---------------------- CATEGORIES ----------------------

@tracking_bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        # Check duplicate active category
        existing = ExpenseCategory.query.filter_by(
            user_id=current_user.id,
            name=form.name.data.strip(),
            is_archived=False
        ).first()
        if existing:
            flash(f"Category '{existing.name}' already exists!", "warning")
        else:
            cat = ExpenseCategory(
                user_id=current_user.id,
                name=form.name.data.strip(),
                kind=form.kind.data,
                icon=form.icon.data,
                is_archived=False
            )
            db.session.add(cat)
            db.session.commit()
            flash(f"Category '{cat.name}' created!", "success")
        return redirect(url_for("tracking.categories"))

    active_cats = ExpenseCategory.query.filter_by(user_id=current_user.id, is_archived=False).all()
    archived_cats = ExpenseCategory.query.filter_by(user_id=current_user.id, is_archived=True).all()

    return render_template(
        "tracking/categories.html",
        form=form,
        active_cats=active_cats,
        archived_cats=archived_cats
    )


@tracking_bp.route("/categories/archive/<int:category_id>", methods=["POST"])
@login_required
def archive_category(category_id):
    cat = ExpenseCategory.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    cat.is_archived = True
    db.session.commit()
    flash(f"Category '{cat.name}' archived. Past expenses are preserved.", "info")
    return redirect(url_for("tracking.categories"))


@tracking_bp.route("/categories/restore/<int:category_id>", methods=["POST"])
@login_required
def restore_category(category_id):
    cat = ExpenseCategory.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    cat.is_archived = False
    db.session.commit()
    flash(f"Category '{cat.name}' restored to active list.", "success")
    return redirect(url_for("tracking.categories"))
