"""
AI Provider Interface and Implementations
-----------------------------------------
Enables swappable AI providers (GeminiProvider, MockProvider).
Adheres strictly to the PRD:
- ONLY aggregated data is passed to the AI (NEVER user names, emails, phones, or notes).
- The AI never calculates primary numbers; it suggests adjustments, explains choices, and advises.
- Output is structured JSON conforming to a strict schema.
"""

import os
import json
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


SYSTEM_PROMPT = """You are a supportive, knowledgeable Personal Financial Advisor Bot.
Your job is to provide practical, non-judgmental financial budgeting advice, spending pattern observations, cost optimization tips, and commentary on the user's financial health.

STRICT OPERATIONAL RULES:
1. Always use the specified user currency in all textual explanations.
2. Never recommend specific financial products, stock tickers, crypto, or lenders/loan companies.
3. Include no guarantees or promises of returns. Always sound realistic, encouraging, and actionable.
4. You will receive aggregated numbers calculated deterministically by our financial engine. Respect these constraints: the sum of your recommended budget category limits MUST be less than or equal to the total spendable income provided.
5. You MUST return ONLY valid JSON matching the exact requested JSON schema. Do not include markdown code block backticks if possible, or provide raw JSON that can be parsed directly.
"""


class AIProvider(ABC):
    """Abstract base class for financial AI advisory."""

    @abstractmethod
    def generate_budget_advice(
        self,
        persona: str,
        currency: str,
        total_income: float,
        spendable_income: float,
        target_savings: float,
        categories: list,
        trailing_averages: dict,
        current_expenses: dict,
        notes: list
    ) -> Dict[str, Any]:
        """Generate budget limit suggestions and explanations."""
        pass

    @abstractmethod
    def generate_spending_insights(
        self,
        persona: str,
        currency: str,
        health_score: dict,
        overspending_data: dict,
        emergency_fund_data: dict,
        needs_wants_data: dict,
        category_breakdown: dict
    ) -> Dict[str, Any]:
        """Generate comprehensive spending insights and optimization advice."""
        pass


class MockProvider(AIProvider):
    """
    Mock AI Provider used for unit tests, offline development,
    or when GEMINI_API_KEY is not configured.
    """

    def generate_budget_advice(
        self,
        persona: str,
        currency: str,
        total_income: float,
        spendable_income: float,
        target_savings: float,
        categories: list,
        trailing_averages: dict,
        current_expenses: dict,
        notes: list
    ) -> Dict[str, Any]:
        # Generate realistic advice matching the provided baseline
        items = []
        for cat in categories:
            cat_name = cat.get("category_name", "")
            cat_kind = cat.get("category_kind", "need")
            base_limit = cat.get("limit_amount", 0.0)

            if cat_kind == "need":
                reason = f"Essential baseline allocated for {cat_name} based on consistent monthly commitments."
            else:
                reason = f"Balanced discretionary allowance for {cat_name} to encourage mindful lifestyle spending."

            items.append({
                "category_name": cat_name,
                "suggested_limit": float(base_limit),
                "ai_reason": reason
            })

        advice_text = (
            f"Based on your {persona} profile, this budget reserves {currency} {target_savings:,.2f} "
            f"towards savings while ensuring all your core commitments are covered."
        )

        return {
            "summary": advice_text,
            "persona_strategy": f"Tailored for {persona} stability with prioritized essentials.",
            "items": items,
            "savings_tip": f"Automate a transfer of {currency} {target_savings:,.2f} on income day to build wealth effortlessly.",
            "is_mock": True
        }

    def generate_spending_insights(
        self,
        persona: str,
        currency: str,
        health_score: dict,
        overspending_data: dict,
        emergency_fund_data: dict,
        needs_wants_data: dict,
        category_breakdown: dict
    ) -> Dict[str, Any]:
        score = health_score.get("total_score", 70.0)
        rating = health_score.get("rating", "Good")

        top_fixes = overspending_data.get("top_3_to_fix", [])
        overspend_tips = []
        for fix in top_fixes:
            cat = fix.get("category", "")
            spike = fix.get("spike_pct", 0.0)
            overspend_tips.append(
                f"Your spending in '{cat}' was {spike}% higher than usual. "
                f"Consider auditing subscription renewals or dining receipts."
            )

        if not overspend_tips:
            overspend_tips.append("No critical overspending spikes detected this month. Excellent discipline!")

        ef_gap = emergency_fund_data.get("gap", 0.0)
        months_cov = emergency_fund_data.get("months_covered", 0.0)
        target_months = emergency_fund_data.get("target_months", 3)

        if ef_gap > 0:
            ef_advice = (
                f"You currently have {months_cov} months of essentials covered. "
                f"Aim to bridge the {currency} {ef_gap:,.2f} gap to reach your {target_months}-month safety cushion."
            )
        else:
            ef_advice = f"Your emergency fund is fully funded ({months_cov} months covered). Outstanding resilience!"

        return {
            "health_summary": f"Your financial health score is {score}/100 ({rating}). "
                              f"{health_score.get('summary', '')}",
            "overspending_insights": overspend_tips,
            "cost_optimizations": [
                "Review recurring app subscriptions and cancel unused gym or streaming passes.",
                "Plan groceries weekly with a shopping list to trim discretionary food waste by 10-15%.",
                "Utilize high-yield savings or recurring deposits for idle balances."
            ],
            "emergency_fund_guidance": ef_advice,
            "next_month_goals": [
                f"Keep discretionary spending under 30% of total expenses.",
                f"Maintain budget adherence across top 3 categories.",
                f"Increase savings by at least 5%."
            ],
            "is_mock": True
        }


class GeminiProvider(AIProvider):
    """
    Google Gemini Provider using google-genai SDK.
    Accepts only aggregated metrics, never PII.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            self.client = None

    def _call_gemini(self, prompt: str) -> Optional[dict]:
        if not self.client:
            return None
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"{SYSTEM_PROMPT}\n\nTask:\n{prompt}",
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2
                }
            )
            text = response.text.strip()
            # Clean up if markdown backticks were included
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as err:
            print(f"[GeminiProvider Error] {err}")
            return None

    def generate_budget_advice(
        self,
        persona: str,
        currency: str,
        total_income: float,
        spendable_income: float,
        target_savings: float,
        categories: list,
        trailing_averages: dict,
        current_expenses: dict,
        notes: list
    ) -> Dict[str, Any]:
        prompt = f"""
You are advising a {persona} user on their monthly budget.
Currency: {currency}
Total Income Basis: {total_income}
Spendable Income (after tax/mandatory reserves): {spendable_income}
Target Savings: {target_savings}
Persona Notes: {json.dumps(notes)}

Categories with baseline allocations:
{json.dumps(categories, indent=2)}

Trailing 3-Month Category Averages:
{json.dumps(trailing_averages, indent=2)}

Respond with a JSON object with this exact structure:
{{
  "summary": "2-3 sentences explaining the budget rationale for this persona",
  "persona_strategy": "1-2 sentences on how this budget caters to their profile type",
  "items": [
    {{
      "category_name": "<exact category name>",
      "suggested_limit": <number, float or int>,
      "ai_reason": "Specific rationale for this limit"
    }}
  ],
  "savings_tip": "One high-impact, practical savings tip for this month"
}}
CRITICAL RULE: The sum of suggested_limit across all items must not exceed {spendable_income}.
"""
        result = self._call_gemini(prompt)
        if result and "items" in result:
            result["is_mock"] = False
            return result
        # Fall back to MockProvider on failure
        return MockProvider().generate_budget_advice(
            persona, currency, total_income, spendable_income, target_savings,
            categories, trailing_averages, current_expenses, notes
        )

    def generate_spending_insights(
        self,
        persona: str,
        currency: str,
        health_score: dict,
        overspending_data: dict,
        emergency_fund_data: dict,
        needs_wants_data: dict,
        category_breakdown: dict
    ) -> Dict[str, Any]:
        prompt = f"""
Analyze this user's monthly spending and financial health metrics:
Persona: {persona}
Currency: {currency}
Financial Health Score: {json.dumps(health_score)}
Overspending Detected: {json.dumps(overspending_data.get('top_3_to_fix', []))}
Emergency Fund Status: {json.dumps(emergency_fund_data)}
Needs vs Wants: {json.dumps(needs_wants_data)}
Category Spend Breakdown: {json.dumps(category_breakdown)}

Respond with a JSON object in this exact schema:
{{
  "health_summary": "1-2 sentences explaining their financial health score and current stance",
  "overspending_insights": [
    "Insight on flagged category 1",
    "Insight on flagged category 2"
  ],
  "cost_optimizations": [
    "Actionable tip 1",
    "Actionable tip 2",
    "Actionable tip 3"
  ],
  "emergency_fund_guidance": "Encouraging, practical guidance for building or maintaining emergency reserve",
  "next_month_goals": [
    "Goal 1",
    "Goal 2",
    "Goal 3"
  ]
}}
"""
        result = self._call_gemini(prompt)
        if result and "health_summary" in result:
            result["is_mock"] = False
            return result
        return MockProvider().generate_spending_insights(
            persona, currency, health_score, overspending_data,
            emergency_fund_data, needs_wants_data, category_breakdown
        )


def get_ai_provider() -> AIProvider:
    """Factory to instantiate the appropriate AI Provider."""
    provider_type = os.getenv("AI_PROVIDER", "mock").lower()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if provider_type == "gemini" and api_key:
        return GeminiProvider(api_key=api_key)
    return MockProvider()


def compute_input_hash(data: Any) -> str:
    """Computes a SHA256 hash of serialized data for caching."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
