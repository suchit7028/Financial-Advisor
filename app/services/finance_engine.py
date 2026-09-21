"""
Deterministic Finance Engine
----------------------------
Performs all mathematical and financial calculations deterministically in Python.
The AI model NEVER computes these numbers; it only interprets, advises, and personalizes.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from app.models import Income, Expense, ExpenseCategory, BudgetPlan, SavingsGoal, SavingsRecord


class FinanceEngine:
    """Core financial analytics and budget calculation engine."""

    @staticmethod
    def get_month_str(dt: Optional[date] = None) -> str:
        """Returns YYYY-MM string."""
        if dt is None:
            dt = date.today()
        return dt.strftime("%Y-%m")

    @staticmethod
    def get_previous_months(month_str: str, count: int = 3) -> List[str]:
        """Returns a list of previous `count` month strings in chronological order."""
        year, month = map(int, month_str.split("-"))
        dt = date(year, month, 1)
        months = []
        for _ in range(count):
            # step back one month
            if dt.month == 1:
                dt = date(dt.year - 1, 12, 1)
            else:
                dt = date(dt.year, dt.month - 1, 1)
            months.append(dt.strftime("%Y-%m"))
        return list(reversed(months))

    @staticmethod
    def get_next_month(month_str: str) -> str:
        year, month = map(int, month_str.split("-"))
        if month == 12:
            return f"{year + 1:04d}-01"
        return f"{year:04d}-{month + 1:02d}"

    @classmethod
    def get_monthly_aggregates(cls, user_id: int, month_str: str) -> Dict[str, Any]:
        """
        Aggregates incomes, expenses, categories, and savings for a specific month.
        """
        # Fetch month incomes
        incomes = (
            Income.query.filter(
                Income.user_id == user_id,
                Income.date.like(f"{month_str}%")
            ).all()
        )
        total_income = sum((inc.amount for inc in incomes), Decimal("0.00"))

        # Fetch month expenses
        expenses = (
            Expense.query.filter(
                Expense.user_id == user_id,
                Expense.date.like(f"{month_str}%")
            ).all()
        )
        total_expenses = sum((exp.amount for exp in expenses), Decimal("0.00"))

        # Income by source
        income_by_source = defaultdict(Decimal)
        for inc in incomes:
            s_name = inc.source.name if inc.source else "Other"
            income_by_source[s_name] += inc.amount

        # Expense by category & needs vs wants
        expense_by_category = defaultdict(Decimal)
        category_meta = {}
        needs_total = Decimal("0.00")
        wants_total = Decimal("0.00")

        for exp in expenses:
            cat_name = exp.category.name if exp.category else "Uncategorized"
            expense_by_category[cat_name] += exp.amount
            if cat_name not in category_meta and exp.category:
                category_meta[cat_name] = {
                    "id": exp.category.id,
                    "kind": exp.category.kind,
                    "icon": exp.category.icon
                }

            if exp.need_want == "need":
                needs_total += exp.amount
            else:
                wants_total += exp.amount

        net_savings = total_income - total_expenses
        savings_rate = (
            round(float(net_savings / total_income * 100), 2)
            if total_income > 0 else 0.0
        )

        return {
            "month": month_str,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
            "savings_rate": savings_rate,
            "income_by_source": {k: float(v) for k, v in income_by_source.items()},
            "expense_by_category": {k: float(v) for k, v in expense_by_category.items()},
            "category_meta": category_meta,
            "needs_total": needs_total,
            "wants_total": wants_total,
            "expense_count": len(expenses),
            "income_count": len(incomes)
        }

    @classmethod
    def get_trailing_3_months_average(cls, user_id: int, target_month: str) -> Dict[str, Any]:
        """
        Calculates trailing 3-month averages for income, total expense, and per-category spending.
        """
        prev_months = cls.get_previous_months(target_month, count=3)
        monthly_incomes = []
        monthly_expenses = []
        category_totals = defaultdict(list)

        for m in prev_months:
            agg = cls.get_monthly_aggregates(user_id, m)
            monthly_incomes.append(agg["total_income"])
            monthly_expenses.append(agg["total_expenses"])
            for cat, amount in agg["expense_by_category"].items():
                category_totals[cat].append(Decimal(str(amount)))

        avg_income = (
            sum(monthly_incomes, Decimal("0.00")) / len(monthly_incomes)
            if monthly_incomes else Decimal("0.00")
        )
        avg_expenses = (
            sum(monthly_expenses, Decimal("0.00")) / len(monthly_expenses)
            if monthly_expenses else Decimal("0.00")
        )

        category_averages = {}
        for cat, amounts in category_totals.items():
            # average over 3 months
            category_averages[cat] = sum(amounts, Decimal("0.00")) / Decimal("3")

        return {
            "months_analyzed": prev_months,
            "monthly_incomes": monthly_incomes,
            "monthly_expenses": monthly_expenses,
            "avg_income": avg_income,
            "avg_expenses": avg_expenses,
            "category_averages": category_averages,
            "lowest_income": min(monthly_incomes) if monthly_incomes else Decimal("0.00")
        }

    @classmethod
    def generate_baseline_budget(
        cls,
        user_id: int,
        user_profile_type: str,
        target_month: str,
        active_categories: List[ExpenseCategory],
        expected_income: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Generates a 100% deterministic baseline budget tailored by profile type.
        Rule: Sum of all category limits must be <= expected income.
        """
        trailing = cls.get_trailing_3_months_average(user_id, target_month)
        current_agg = cls.get_monthly_aggregates(user_id, target_month)

        # Determine income basis
        if expected_income is not None and expected_income > 0:
            income_basis = expected_income
        elif current_agg["total_income"] > 0:
            income_basis = current_agg["total_income"]
        elif trailing["avg_income"] > 0:
            income_basis = trailing["avg_income"]
        else:
            # Fallback to sum of recurring income sources or default 50000
            from app.models import IncomeSource
            sources = IncomeSource.query.filter_by(user_id=user_id).all()
            sum_sources = sum((s.expected_amount for s in sources), Decimal("0.00"))
            income_basis = sum_sources if sum_sources > 0 else Decimal("50000.00")

        # Persona-specific baseline adjustments
        tax_set_aside = Decimal("0.00")
        notes = []

        if user_profile_type == "freelancer":
            # Conservative baseline: lowest of last 3 months or 70% of average income
            conservative_basis = trailing["lowest_income"]
            seventy_pct = (trailing["avg_income"] * Decimal("0.70")).quantize(Decimal("0.01"))
            if conservative_basis > 0 and seventy_pct > 0:
                income_basis = min(conservative_basis, seventy_pct)
            elif seventy_pct > 0:
                income_basis = seventy_pct
            # Suggest 20% tax set-aside
            tax_set_aside = (income_basis * Decimal("0.20")).quantize(Decimal("0.01"))
            spendable_income = income_basis - tax_set_aside
            needs_ratio = Decimal("0.55")
            wants_ratio = Decimal("0.25")
            savings_ratio = Decimal("0.20")
            notes.append("Freelancer conservative baseline applied with 20% tax reserve.")

        elif user_profile_type == "student":
            # Student allowance: prioritize essentials, tighter wants cap (20%)
            spendable_income = income_basis
            needs_ratio = Decimal("0.65")
            wants_ratio = Decimal("0.20")
            savings_ratio = Decimal("0.15")
            notes.append("Student budget prioritizing essentials and low discretionary spend.")

        elif user_profile_type == "household":
            # Household manager: essentials 60%, wants 20%, savings 20%
            spendable_income = income_basis
            needs_ratio = Decimal("0.60")
            wants_ratio = Decimal("0.20")
            savings_ratio = Decimal("0.20")
            notes.append("Household budget prioritizing family essentials and education/health.")

        else:  # salaried
            spendable_income = income_basis
            needs_ratio = Decimal("0.50")
            wants_ratio = Decimal("0.30")
            savings_ratio = Decimal("0.20")
            notes.append("Standard 50/30/20 salaried budget baseline.")

        # Allocate budget between needs and wants categories
        needs_pool = (spendable_income * needs_ratio).quantize(Decimal("0.01"))
        wants_pool = (spendable_income * wants_ratio).quantize(Decimal("0.01"))
        target_savings = (spendable_income * savings_ratio).quantize(Decimal("0.01"))

        needs_cats = [c for c in active_categories if c.kind in ("need", "other")]
        wants_cats = [c for c in active_categories if c.kind == "want"]

        category_averages = trailing["category_averages"]

        # Helper to distribute pool among categories proportionally or equally
        def distribute_pool(pool: Decimal, categories: List[ExpenseCategory]) -> Dict[int, Decimal]:
            if not categories:
                return {}
            # Check if we have historical weights
            weights = {}
            for cat in categories:
                weights[cat.id] = category_averages.get(cat.name, Decimal("0.00"))

            total_historical = sum(weights.values(), Decimal("0.00"))

            allocations = {}
            if total_historical > 0:
                running_sum = Decimal("0.00")
                for i, cat in enumerate(categories):
                    if i == len(categories) - 1:
                        # assign remainder to last category to ensure exact match
                        allocations[cat.id] = (pool - running_sum).quantize(Decimal("0.01"))
                    else:
                        share = (weights[cat.id] / total_historical * pool).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                        allocations[cat.id] = share
                        running_sum += share
            else:
                # Distribute evenly
                even_share = (pool / Decimal(len(categories))).quantize(Decimal("0.01"))
                running_sum = Decimal("0.00")
                for i, cat in enumerate(categories):
                    if i == len(categories) - 1:
                        allocations[cat.id] = (pool - running_sum).quantize(Decimal("0.01"))
                    else:
                        allocations[cat.id] = even_share
                        running_sum += even_share

            return allocations

        needs_alloc = distribute_pool(needs_pool, needs_cats)
        wants_alloc = distribute_pool(wants_pool, wants_cats)

        items = []
        for cat in active_categories:
            if cat.id in needs_alloc:
                limit = max(Decimal("0.00"), needs_alloc[cat.id])
                reason = "Essential expense allocation based on baseline needs ratio."
            elif cat.id in wants_alloc:
                limit = max(Decimal("0.00"), wants_alloc[cat.id])
                reason = "Discretionary allowance allocation."
            else:
                limit = Decimal("0.00")
                reason = "Default allocation."

            items.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "category_kind": cat.kind,
                "limit_amount": float(limit),
                "ai_reason": reason
            })

        total_allocated = sum(item["limit_amount"] for item in items)

        return {
            "month": target_month,
            "total_income_basis": float(income_basis),
            "spendable_income": float(spendable_income),
            "target_savings": float(target_savings),
            "tax_set_aside": float(tax_set_aside),
            "total_allocated": float(total_allocated),
            "items": items,
            "notes": notes,
            "generated_by": "baseline"
        }

    @classmethod
    def detect_overspending(cls, user_id: int, month_str: str) -> Dict[str, Any]:
        """
        Detects budget overruns and spending spikes compared to historical 3-month averages.
        Returns top 3 categories needing attention.
        """
        current = cls.get_monthly_aggregates(user_id, month_str)
        trailing = cls.get_trailing_3_months_average(user_id, month_str)

        # Check active budget
        plan = BudgetPlan.query.filter_by(user_id=user_id, month=month_str, status="active").first()
        budget_limits = {}
        if plan:
            for item in plan.items:
                cat_name = item.category.name if item.category else "Unknown"
                budget_limits[cat_name] = float(item.limit_amount)

        flags = []
        for cat_name, actual_spend in current["expense_by_category"].items():
            hist_avg = float(trailing["category_averages"].get(cat_name, Decimal("0.00")))
            limit = budget_limits.get(cat_name)

            spike_pct = 0.0
            if hist_avg > 0:
                spike_pct = round(((actual_spend - hist_avg) / hist_avg * 100), 1)

            over_budget_pct = 0.0
            status = "normal"
            if limit and limit > 0:
                ratio = actual_spend / limit
                over_budget_pct = round(((actual_spend - limit) / limit * 100), 1)
                if ratio > 1.0:
                    status = "exceeded"
                elif ratio >= 0.8:
                    status = "near_limit"
                else:
                    status = "on_track"

            severity = 0
            reasons = []
            if status == "exceeded":
                severity += 3
                reasons.append(f"Exceeded budget limit by {over_budget_pct}%")
            elif status == "near_limit":
                severity += 1
                reasons.append(f"Reached 80%+ of budget limit")

            if spike_pct >= 25.0:
                severity += 2
                reasons.append(f"Unusual spike: {spike_pct}% higher than 3-month average")

            if severity > 0:
                flags.append({
                    "category": cat_name,
                    "actual_spend": actual_spend,
                    "budget_limit": limit,
                    "hist_avg": hist_avg,
                    "status": status,
                    "spike_pct": spike_pct,
                    "severity": severity,
                    "reasons": reasons
                })

        # Sort by severity and amount overspent
        flags.sort(key=lambda x: (x["severity"], x["actual_spend"]), reverse=True)
        top_3 = flags[:3]

        return {
            "month": month_str,
            "has_overspending": len(flags) > 0,
            "total_flagged_categories": len(flags),
            "top_3_to_fix": top_3,
            "all_flags": flags
        }

    @classmethod
    def calculate_allowance_runway(cls, user_id: int, month_str: str) -> Dict[str, Any]:
        """
        Special calculation for Student persona:
        Calculates days until money runs out based on daily burn rate.
        """
        agg = cls.get_monthly_aggregates(user_id, month_str)
        today = date.today()
        # Days passed in current month
        days_passed = max(1, today.day)
        total_days_in_month = 30  # approx
        days_remaining = max(0, total_days_in_month - days_passed)

        total_income = float(agg["total_income"])
        total_spent = float(agg["total_expenses"])
        remaining_balance = total_income - total_spent

        daily_burn_rate = total_spent / days_passed if days_passed > 0 else 0.0

        if daily_burn_rate > 0 and remaining_balance > 0:
            runway_days = round(remaining_balance / daily_burn_rate, 1)
        elif remaining_balance <= 0:
            runway_days = 0.0
        else:
            runway_days = float(days_remaining)

        is_critical = runway_days < days_remaining

        return {
            "days_passed": days_passed,
            "days_remaining_in_month": days_remaining,
            "daily_burn_rate": round(daily_burn_rate, 2),
            "remaining_balance": round(remaining_balance, 2),
            "runway_days": runway_days,
            "is_critical": is_critical
        }

    @classmethod
    def calculate_emergency_fund_status(
        cls, user_id: int, user_profile_type: str, target_month: str
    ) -> Dict[str, Any]:
        """
        Emergency fund guidance:
        Target = 3 months of essential expenses for salaried/student/household, 6 months for freelancers.
        """
        agg = cls.get_monthly_aggregates(user_id, target_month)
        monthly_essentials = agg["needs_total"]
        if monthly_essentials == 0:
            # fallback to 50% of total expenses or 15000
            monthly_essentials = (
                (agg["total_expenses"] * Decimal("0.60")).quantize(Decimal("0.01"))
                if agg["total_expenses"] > 0 else Decimal("20000.00")
            )

        multiplier = 6 if user_profile_type == "freelancer" else 3
        recommended_target = (monthly_essentials * Decimal(multiplier)).quantize(Decimal("0.01"))

        # Check existing emergency fund goal
        goal = SavingsGoal.query.filter_by(user_id=user_id, is_emergency_fund=True).first()
        current_saved = Decimal("0.00")
        if goal:
            records = SavingsRecord.query.filter_by(user_id=user_id, goal_id=goal.id).all()
            current_saved = sum((r.amount_saved for r in records), Decimal("0.00"))
            target_amount = goal.target_amount if goal.target_amount > 0 else recommended_target
        else:
            target_amount = recommended_target

        gap = max(Decimal("0.00"), target_amount - current_saved)
        months_covered = (
            round(float(current_saved / monthly_essentials), 1)
            if monthly_essentials > 0 else 0.0
        )
        progress_pct = (
            min(100.0, round(float(current_saved / target_amount * 100), 1))
            if target_amount > 0 else 0.0
        )

        return {
            "recommended_target": float(recommended_target),
            "current_saved": float(current_saved),
            "target_amount": float(target_amount),
            "months_covered": months_covered,
            "target_months": multiplier,
            "gap": float(gap),
            "progress_pct": progress_pct,
            "is_funded": gap == 0
        }

    @classmethod
    def compute_financial_health_score(
        cls, user_id: int, user_profile_type: str, month_str: str
    ) -> Dict[str, Any]:
        """
        Transparent, deterministic Financial Health Score (0 - 100).
        Scoring Rubric:
        - Savings Rate (0-35 points): >=20% gives full 35, 10-20% scaled 15-35, <10% scaled down.
        - Budget Adherence (0-30 points): % of categories within limit or spend <= income.
        - Emergency Fund Coverage (0-20 points): Months of essential expenses covered.
        - Expense Volatility & Discipline (0-15 points): Low variance and controlled discretionary spend.
        """
        agg = cls.get_monthly_aggregates(user_id, month_str)
        trailing = cls.get_trailing_3_months_average(user_id, month_str)
        ef_status = cls.calculate_emergency_fund_status(user_id, user_profile_type, month_str)

        # 1. Savings Rate Score (0 - 35)
        savings_rate = agg["savings_rate"]
        if savings_rate >= 25.0:
            savings_score = 35.0
        elif savings_rate >= 15.0:
            savings_score = 25.0 + ((savings_rate - 15.0) / 10.0 * 10.0)
        elif savings_rate > 0.0:
            savings_score = (savings_rate / 15.0) * 25.0
        else:
            savings_score = 0.0

        # 2. Budget Adherence Score (0 - 30)
        plan = BudgetPlan.query.filter_by(user_id=user_id, month=month_str, status="active").first()
        if plan and plan.items:
            within_count = 0
            for item in plan.items:
                cat_name = item.category.name if item.category else ""
                spent = agg["expense_by_category"].get(cat_name, 0.0)
                if spent <= float(item.limit_amount):
                    within_count += 1
            adherence_ratio = within_count / len(plan.items)
            budget_score = adherence_ratio * 30.0
        else:
            # Fallback if no formal budget set: compare expenses vs income
            if agg["total_income"] > 0:
                ratio = float(agg["total_expenses"] / agg["total_income"])
                if ratio <= 0.8:
                    budget_score = 26.0
                elif ratio <= 1.0:
                    budget_score = 18.0
                else:
                    budget_score = max(0.0, 18.0 - (ratio - 1.0) * 30.0)
            else:
                budget_score = 15.0

        # 3. Emergency Fund Coverage Score (0 - 20)
        target_months = ef_status["target_months"]
        covered_months = ef_status["months_covered"]
        ef_score = min(20.0, (covered_months / target_months) * 20.0)

        # 4. Expense Volatility & Discipline Score (0 - 15)
        wants_total = float(agg["wants_total"])
        total_exp = float(agg["total_expenses"])
        if total_exp > 0:
            wants_ratio = wants_total / total_exp
            # Ideally wants should be <= 30-35% of total expenses
            if wants_ratio <= 0.30:
                discipline_score = 15.0
            elif wants_ratio <= 0.45:
                discipline_score = 10.0
            else:
                discipline_score = max(3.0, 15.0 - (wants_ratio - 0.30) * 30.0)
        else:
            discipline_score = 10.0

        total_score = round(savings_score + budget_score + ef_score + discipline_score, 1)
        total_score = max(0.0, min(100.0, total_score))

        # Rating tier
        if total_score >= 80:
            rating = "Excellent"
            summary = "Your financial health is exceptionally strong. Savings and discipline are on point!"
        elif total_score >= 65:
            rating = "Good"
            summary = "Solid financial foundation. A few minor optimizations will elevate your resilience."
        elif total_score >= 50:
            rating = "Fair"
            summary = "Adequate stability, but overspending or emergency fund gaps need immediate attention."
        else:
            rating = "Needs Attention"
            summary = "High financial stress detected. Expenses exceed safe ratios or savings are depleted."

        return {
            "total_score": total_score,
            "rating": rating,
            "summary": summary,
            "breakdown": {
                "savings_score": round(savings_score, 1),
                "savings_score_max": 35,
                "budget_score": round(budget_score, 1),
                "budget_score_max": 30,
                "emergency_fund_score": round(ef_score, 1),
                "emergency_fund_score_max": 20,
                "discipline_score": round(discipline_score, 1),
                "discipline_score_max": 15
            }
        }
