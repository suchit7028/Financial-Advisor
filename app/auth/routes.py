from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db, limiter
from app.models import User
from app.auth.forms import RegistrationForm, LoginForm, ProfileForm, DeleteAccountForm
from app.services.defaults import setup_user_defaults

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            profile_type=form.profile_type.data,
            currency=form.currency.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Initialize default categories and income sources for persona
        setup_user_defaults(user)

        flash("Your account has been created! You can now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page if next_page and next_page.startswith("/") else url_for("dashboard.index"))
        else:
            flash("Invalid email or password. Please check your credentials.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    delete_form = DeleteAccountForm()

    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.profile_type = form.profile_type.data
        current_user.currency = form.currency.data
        current_user.monthly_savings_goal = form.monthly_savings_goal.data or 0.0
        current_user.emergency_fund_target = form.emergency_fund_target.data or 0.0
        current_user.dependents = form.dependents.data or 0

        db.session.commit()
        flash("Your profile preferences have been successfully updated.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form, delete_form=delete_form)


@auth_bp.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        if current_user.check_password(form.password.data):
            user = current_user
            logout_user()
            db.session.delete(user)
            db.session.commit()
            flash("Your account and all associated financial records have been permanently deleted.", "info")
            return redirect(url_for("auth.register"))
        else:
            flash("Incorrect password. Account deletion aborted.", "danger")
    return redirect(url_for("auth.profile"))
