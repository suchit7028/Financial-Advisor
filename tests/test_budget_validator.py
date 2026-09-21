import pytest
from app.models import ExpenseCategory
from app.services.budget_validator import BudgetValidator
from app.services.ai_provider import MockProvider, AIProvider


class MalformedAIProvider(AIProvider):
    """AI Provider returning invalid JSON structure to trigger validator retry/fallback."""
    def generate_budget_advice(self, *args, **kwargs):
        return {"garbage": "no items list"}

    def generate_spending_insights(self, *args, **kwargs):
        return {"bad": "data"}


class ExceedingLimitsAIProvider(AIProvider):
    """AI Provider proposing limits exceeding spendable income."""
    def generate_budget_advice(self, persona, currency, total_income, spendable_income, *args, **kwargs):
        return {
            "summary": "Over generous budget",
            "items": [
                {"category_name": "Rent", "suggested_limit": spendable_income * 2.0, "ai_reason": "Too high"}
            ]
        }

    def generate_spending_insights(self, *args, **kwargs):
        return {}


def test_validator_with_mock_provider(app, user_a):
    """Test standard flow with MockProvider produces valid proposal."""
    with app.app_context():
        cats = ExpenseCategory.query.filter_by(user_id=user_a.id).all()
        proposal = BudgetValidator.get_validated_ai_budget(
            ai_provider=MockProvider(),
            user_id=user_a.id,
            user_profile_type="salaried",
            currency="INR",
            target_month="2026-10",
            active_categories=cats,
            expected_income=60000.0
        )
        assert proposal["validation_passed"] is True
        assert proposal["total_allocated"] <= proposal["spendable_income"] + 0.05
        assert len(proposal["items"]) == len(cats)


def test_validator_catches_malformed_ai_and_falls_back(app, user_a):
    """Test fallback when AI returns invalid structure."""
    with app.app_context():
        cats = ExpenseCategory.query.filter_by(user_id=user_a.id).all()
        proposal = BudgetValidator.get_validated_ai_budget(
            ai_provider=MalformedAIProvider(),
            user_id=user_a.id,
            user_profile_type="salaried",
            currency="INR",
            target_month="2026-10",
            active_categories=cats,
            expected_income=50000.0
        )
        # Should succeed via retry with MockProvider or fallback
        assert proposal["total_allocated"] <= proposal["spendable_income"] + 0.05
        assert len(proposal["items"]) > 0


def test_validator_rejects_limits_exceeding_income(app, user_a):
    """Test validator rejects proposals where sum of limits > spendable income."""
    with app.app_context():
        cats = ExpenseCategory.query.filter_by(user_id=user_a.id).all()
        invalid_output = {
            "items": [
                {"category_name": cats[0].name, "suggested_limit": 100000.0, "ai_reason": "Too much"}
            ]
        }
        is_valid, errors, _ = BudgetValidator.validate_proposal(
            invalid_output, cats, spendable_income=50000.0
        )
        assert is_valid is False
        assert any("exceed spendable income" in err for err in errors)


def test_validator_rejects_negative_limits(app, user_a):
    """Test validator rejects negative suggested amounts."""
    with app.app_context():
        cats = ExpenseCategory.query.filter_by(user_id=user_a.id).all()
        invalid_output = {
            "items": [
                {"category_name": cats[0].name, "suggested_limit": -500.0, "ai_reason": "Negative"}
            ]
        }
        is_valid, errors, _ = BudgetValidator.validate_proposal(
            invalid_output, cats, spendable_income=50000.0
        )
        assert is_valid is False
        assert any("Negative limit" in err for err in errors)
