from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, SelectField,
    DecimalField, IntegerField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Optional
)
from app.models import User


class RegistrationForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long.")
        ]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    profile_type = SelectField(
        "Financial Profile Type",
        choices=[
            ("salaried", "Salaried Professional (Fixed income, lifestyle & savings balance)"),
            ("student", "College Student (Limited allowance, tight discretionary cap)"),
            ("freelancer", "Freelancer / Consultant (Variable income, tax reserves, 6-mo cushion)"),
            ("household", "Household Manager (Shared family budget, education & utilities)")
        ],
        default="salaried",
        validators=[DataRequired()]
    )
    currency = SelectField(
        "Currency",
        choices=[
            ("INR", "₹ INR (Indian Rupee)"),
            ("USD", "$ USD (US Dollar)"),
            ("EUR", "€ EUR (Euro)"),
            ("GBP", "£ GBP (British Pound)")
        ],
        default="INR",
        validators=[DataRequired()]
    )
    submit = SubmitField("Create Free Account")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower().strip()).first()
        if user:
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class ProfileForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=80)])
    profile_type = SelectField(
        "Profile Type",
        choices=[
            ("salaried", "Salaried Professional"),
            ("student", "College Student"),
            ("freelancer", "Freelancer / Consultant"),
            ("household", "Household Manager")
        ],
        validators=[DataRequired()]
    )
    currency = SelectField(
        "Currency",
        choices=[
            ("INR", "₹ INR (Indian Rupee)"),
            ("USD", "$ USD (US Dollar)"),
            ("EUR", "€ EUR (Euro)"),
            ("GBP", "£ GBP (British Pound)")
        ],
        validators=[DataRequired()]
    )
    monthly_savings_goal = DecimalField(
        "Monthly Savings Goal",
        places=2,
        default=0.0,
        validators=[Optional(), NumberRange(min=0)]
    )
    emergency_fund_target = DecimalField(
        "Emergency Fund Target",
        places=2,
        default=0.0,
        validators=[Optional(), NumberRange(min=0)]
    )
    dependents = IntegerField(
        "Number of Dependents",
        default=0,
        validators=[Optional(), NumberRange(min=0, max=20)]
    )
    submit = SubmitField("Update Profile")


class DeleteAccountForm(FlaskForm):
    password = PasswordField(
        "Confirm Password to Delete Account",
        validators=[DataRequired()]
    )
    submit = SubmitField("Permanently Delete My Account & All Data")
