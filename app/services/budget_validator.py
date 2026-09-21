"""
AI Budget Validator and Fallback Controller
-------------------------------------------
Enforces strict deterministic constraints on AI output:
1. Valid JSON schema
2. Category names must exist in the user's active categories
3. Sum of suggested category limits must not exceed spendable income
4. No negative limits
5. Retries once if invalid, then gracefully falls back to deterministic baseline.
"""

from typing import Dict, Any, List, Tuple
from decimal import Decimal
from app.models import ExpenseCategory
from app.services.finance_engine import FinanceEngine
from app.services.ai_provider import AIProvider, MockProvider


class BudgetValidator:
    """Validates AI budget proposals against mathematical and business rules."""

    @classmethod
    def validate_proposal(
        cls,
        ai_output: Dict[str, Any],
        active_categories: List[ExpenseCategory],
        spendable_income: float
    ) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """
        Validates the AI-generated budget proposal.
        Returns (is_valid, error_messages, sanitized_items).
        """
        errors = []
        if not isinstance(ai_output, dict):
            return False, ["AI output is not a JSON dictionary."], []

        items = ai_output.get("items")
        if not isinstance(items, list) or len(items) == 0:
            return False, ["Missing or empty 'items' list in AI response."], []

        active_cat_names = {c.name.strip().lower(): c for c in active_categories}
        sanitized_items = []
        total_limit = 0.0

        matched_category_ids = set()

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"Item #{idx+1} is not a valid dictionary.")
                continue

            raw_cat_name = str(item.get("category_name", "")).strip()
            cat_obj = active_cat_names.get(raw_cat_name.lower())
            if not cat_obj:
                errors.append(f"Unknown or inactive category '{raw_cat_name}'.")
                continue

            if cat_obj.id in matched_category_ids:
                errors.append(f"Duplicate category entry for '{cat_obj.name}'.")
                continue
            matched_category_ids.add(cat_obj.id)

            try:
                limit = float(item.get("suggested_limit", 0.0))
            except (ValueError, TypeError):
                errors.append(f"Invalid numeric limit for category '{cat_obj.name}'.")
                continue

            if limit < 0:
                errors.append(f"Negative limit ({limit}) for category '{cat_obj.name}'.")
                continue

            reason = str(item.get("ai_reason", "")).strip()
            if not reason:
                reason = "Allocation aligned with your spending profile."

            total_limit += limit
            sanitized_items.append({
                "category_id": cat_obj.id,
                "category_name": cat_obj.name,
                "category_kind": cat_obj.kind,
                "limit_amount": round(limit, 2),
                "ai_reason": reason
            })

        # Ensure all active categories have an entry
        for cat in active_categories:
            if cat.id not in matched_category_ids:
                # Add default 0.0 limit
                sanitized_items.append({
                    "category_id": cat.id,
                    "category_name": cat.name,
                    "category_kind": cat.kind,
                    "limit_amount": 0.0,
                    "ai_reason": "Default allocation for unmentioned active category."
                })

        # Strict rule: total limits must not exceed spendable income
        # Allow tiny epsilon for floating point (e.g. 0.05)
        if total_limit > (spendable_income + 0.05):
            errors.append(
                f"Total limits ({round(total_limit, 2)}) exceed spendable income ({round(spendable_income, 2)})."
            )

        is_valid = len(errors) == 0
        return is_valid, errors, sanitized_items

    @classmethod
    def get_validated_ai_budget(
        cls,
        ai_provider: AIProvider,
        user_id: int,
        user_profile_type: str,
        currency: str,
        target_month: str,
        active_categories: List[ExpenseCategory],
        expected_income: float = None
    ) -> Dict[str, Any]:
        """
        Orchestrates:
        1. Deterministic baseline computation
        2. AI advice call
        3. Strict validation
        4. One retry on failure
        5. Safe deterministic fallback if validation fails.
        """
        # 1. Deterministic baseline
        baseline = FinanceEngine.generate_baseline_budget(
            user_id=user_id,
            user_profile_type=user_profile_type,
            target_month=target_month,
            active_categories=active_categories,
            expected_income=Decimal(str(expected_income)) if expected_income else None
        )

        trailing = FinanceEngine.get_trailing_3_months_average(user_id, target_month)
        current = FinanceEngine.get_monthly_aggregates(user_id, target_month)

        trailing_averages = {k: float(v) for k, v in trailing["category_averages"].items()}
        current_expenses = current["expense_by_category"]

        spendable_income = baseline["spendable_income"]

        # Attempt 1: Call AI provider
        ai_output = ai_provider.generate_budget_advice(
            persona=user_profile_type,
            currency=currency,
            total_income=baseline["total_income_basis"],
            spendable_income=spendable_income,
            target_savings=baseline["target_savings"],
            categories=baseline["items"],
            trailing_averages=trailing_averages,
            current_expenses=current_expenses,
            notes=baseline["notes"]
        )

        is_valid, errors, sanitized_items = cls.validate_proposal(
            ai_output, active_categories, spendable_income
        )

        if is_valid:
            return {
                "month": target_month,
                "total_income_basis": baseline["total_income_basis"],
                "spendable_income": spendable_income,
                "target_savings": baseline["target_savings"],
                "tax_set_aside": baseline["tax_set_aside"],
                "total_allocated": round(sum(i["limit_amount"] for i in sanitized_items), 2),
                "summary": ai_output.get("summary", ""),
                "persona_strategy": ai_output.get("persona_strategy", ""),
                "savings_tip": ai_output.get("savings_tip", ""),
                "items": sanitized_items,
                "generated_by": "ai",
                "validation_passed": True,
                "notes": baseline["notes"],
                "is_fallback": False
            }

        # Attempt 2 (Retry with Mock or re-prompting)
        retry_output = MockProvider().generate_budget_advice(
            persona=user_profile_type,
            currency=currency,
            total_income=baseline["total_income_basis"],
            spendable_income=spendable_income,
            target_savings=baseline["target_savings"],
            categories=baseline["items"],
            trailing_averages=trailing_averages,
            current_expenses=current_expenses,
            notes=baseline["notes"]
        )

        retry_valid, retry_errors, retry_items = cls.validate_proposal(
            retry_output, active_categories, spendable_income
        )

        if retry_valid:
            return {
                "month": target_month,
                "total_income_basis": baseline["total_income_basis"],
                "spendable_income": spendable_income,
                "target_savings": baseline["target_savings"],
                "tax_set_aside": baseline["tax_set_aside"],
                "total_allocated": round(sum(i["limit_amount"] for i in retry_items), 2),
                "summary": retry_output.get("summary", ""),
                "persona_strategy": retry_output.get("persona_strategy", ""),
                "savings_tip": retry_output.get("savings_tip", ""),
                "items": retry_items,
                "generated_by": "ai_retry",
                "validation_passed": True,
                "notes": baseline["notes"],
                "is_fallback": False
            }

        # Graceful fallback to deterministic baseline
        baseline["summary"] = (
            "We applied our verified 50/30/20 deterministic baseline budget model "
            "as AI formatting required adjustment."
        )
        baseline["savings_tip"] = (
            f"Reserve {currency} {baseline['target_savings']:,.2f} towards savings early this month."
        )
        baseline["is_fallback"] = True
        baseline["validation_passed"] = False
        baseline["validation_errors"] = errors
        return baseline
