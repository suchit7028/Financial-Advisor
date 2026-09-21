from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, DecimalField, DateField, SelectField,
    BooleanField, TextAreaField
)
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from datetime import date


class IncomeForm(FlaskForm):
    amount = DecimalField(
        "Amount",
        places=2,
        validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than zero.")]
    )
    source_id = SelectField("Income Source", coerce=int, validators=[Optional()])
    date = DateField("Date Received", default=date.today, validators=[DataRequired()])
    notes = StringField("Notes / Reference", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save Income")


class IncomeSourceForm(FlaskForm):
    name = StringField("Source Name", validators=[DataRequired(), Length(min=2, max=100)])
    type = SelectField(
        "Source Category",
        choices=[
            ("salary", "Salary"),
            ("freelance", "Freelance / Client Contract"),
            ("allowance", "Allowance"),
            ("investment", "Dividends / Investment Return"),
            ("business", "Business Revenue"),
            ("other", "Other")
        ],
        default="salary",
        validators=[DataRequired()]
    )
    is_recurring = BooleanField("Recurring Monthly Source", default=True)
    expected_amount = DecimalField(
        "Expected Monthly Amount",
        places=2,
        default=0.0,
        validators=[Optional(), NumberRange(min=0)]
    )
    submit = SubmitField("Save Source")


class ExpenseForm(FlaskForm):
    amount = DecimalField(
        "Amount",
        places=2,
        validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than zero.")]
    )
    category_id = SelectField("Expense Category", coerce=int, validators=[DataRequired()])
    date = DateField("Date of Expense", default=date.today, validators=[DataRequired()])
    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("upi", "UPI / Instant Transfer"),
            ("card", "Credit / Debit Card"),
            ("bank_transfer", "Net Banking / Transfer"),
            ("cash", "Cash"),
            ("other", "Other")
        ],
        default="upi",
        validators=[Optional()]
    )
    need_want = SelectField(
        "Nature",
        choices=[
            ("need", "Need (Essential)"),
            ("want", "Want (Discretionary)")
        ],
        default="need",
        validators=[DataRequired()]
    )
    notes = StringField("Notes / Vendor", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Log Expense")


class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(min=2, max=80)])
    kind = SelectField(
        "Default Nature",
        choices=[
            ("need", "Need (Essential - Rent, Utilities, Food)"),
            ("want", "Want (Discretionary - Dining, Entertainment)"),
            ("savings", "Savings / Debt Prepayment"),
            ("other", "Other")
        ],
        default="need",
        validators=[DataRequired()]
    )
    icon = SelectField(
        "Icon",
        choices=[
            ("home", "Home / Rent"),
            ("shopping-cart", "Groceries / Cart"),
            ("coffee", "Dining / Cafe"),
            ("truck", "Transport / Fuel"),
            ("zap", "Utilities / Bills"),
            ("credit-card", "EMI / Loans"),
            ("activity", "Health / Medical"),
            ("book", "Education / Books"),
            ("film", "Entertainment / Leisure"),
            ("cpu", "Tech / Tools"),
            ("gift", "Shopping / Gifts"),
            ("briefcase", "Work / Business"),
            ("tag", "General Tag")
        ],
        default="tag",
        validators=[DataRequired()]
    )
    submit = SubmitField("Save Category")
