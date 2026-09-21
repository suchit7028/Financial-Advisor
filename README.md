# Personal Finance Advisor Bot

An AI-powered, production-ready web application that empowers individuals and families to take total control of their finances. The system records income, logs and categorizes expenses, generates tailored monthly budgets, monitors emergency cushions, and provides personalized AI-driven spending insights and downloadable financial statements.

---

## 1. Core Architecture & Philosophy

> **Deterministic Engine vs. AI Division of Responsibility:**
> - **All mathematical figures, budget allocations, emergency fund calculations, and financial health scores (0–100) are computed strictly by deterministic Python service layers.**
> - **The AI model (Google Gemini or Mock fallback) NEVER performs arithmetic.** It only explains, advises, personalizes commentary, and suggests actionable behavioral optimizations.
> - **Zero PII to AI:** Gemini receives strictly sanitized aggregates (category totals, income totals, goals)—never names, emails, account numbers, or notes.
> - **Strict Output Validation:** Every AI recommendation is schema-validated. If suggested limits exceed spendable income or fail formatting, the engine automatically falls back to deterministic benchmarks.

---

## 2. Tech Stack

- **Backend:** Python 3.11+, Flask 3.x, SQLAlchemy (ORM), Flask-Login, Flask-WTF (CSRF), Flask-Limiter
- **Database:** SQLite for local dev / testing; PostgreSQL-ready via `DATABASE_URL`
- **Frontend:** Jinja2 templates, Custom Vanilla CSS Fintech Design System, Chart.js 4.4, Feather Icons
- **PDF Generation:** ReportLab 4.x (zero native DLL dependencies, 100% pure Python)
- **AI Advisory:** Google GenAI SDK (`google-genai`), swappable via `AIProvider` (`GeminiProvider` / `MockProvider`)
- **Public Tunneling:** Ngrok with `ProxyFix` middleware for secure public demos

---

## 3. Four Target Personas

| Persona | Demo Email | Password | Strategy & Default Categories |
|---|---|---|---|
| **Salaried Professional** | `salaried@demo.com` | `Password123!` | 50/30/20 balanced model (Rent, Groceries, Transport, Utilities, EMI/Loans, Dining out, Entertainment, Shopping) |
| **College Student** | `student@demo.com` | `Password123!` | Limited allowance, allowance runway burn-rate alert, strict discretionary caps (Hostel/Rent, Food, Books/Education, Travel, Subscriptions, Entertainment) |
| **Freelancer / Consultant** | `freelancer@demo.com` | `Password123!` | Variable income, 20% tax reserve, conservative baseline, 6-month emergency fund cushion (Rent, Food, Software/Tools, Project expenses, Taxes, Travel) |
| **Household Manager** | `household@demo.com` | `Password123!` | Shared multi-income family budget, dependents tracking, essential priorities (Groceries, Utilities, Education, Healthcare, Rent/EMI, Household help) |

---

## 4. Setup & Local Installation

### Prerequisites
- Python 3.11+
- Git

### Quickstart

1. **Clone and navigate to repository:**
   ```bash
   git clone <repo-url>
   cd "Finance advisor"
   ```

2. **Initialize virtual environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   *(Optional)* To use Google Gemini API instead of the mock provider, set in `.env`:
   ```env
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

5. **Seed Demo Data:**
   Populate 3 months of realistic financial transactions for all 4 personas:
   ```bash
   python scripts/seed_demo_data.py
   ```

6. **Run the application:**
   ```bash
   python run.py
   ```
   Open your browser at `http://localhost:5000`.

---

## 5. Public Demo Deployment with Ngrok

To securely demonstrate the application to external stakeholders:

1. **Launch the Ngrok-ready server:**
   ```bash
   python scripts/run_with_ngrok.py
   ```
   *Note: This automatically enforces `ProxyFix` for HTTPS header forwarding and production cookie policies.*

2. **Start the Ngrok tunnel in another terminal:**
   ```bash
   ngrok http 5000
   ```

3. **Security Guidelines for Public Demos:**
   - Ngrok URLs are publicly accessible on the internet.
   - Use ONLY seeded demo accounts (`salaried@demo.com`, etc.). NEVER enter real bank accounts, PAN/Aadhaar numbers, or confidential personal information.
   - Ensure `SECRET_KEY` in `.env` is strong and unique.

---

## 6. Running Automated Tests

Run the full automated test suite with coverage:
```bash
.venv/Scripts/pytest -v --cov=app tests/
```

### Coverage Highlights:
- `tests/test_auth.py`: Registration, password hashing, session management, CSRF, and IDOR isolation.
- `tests/test_tracking.py`: Income/expense CRUD, negative amount validation, category archiving.
- `tests/test_finance_engine.py`: Deterministic 50/30/20 adaptations, freelancer 20% tax reserve, student runway burn-rate, and 0–100 health score rubric.
- `tests/test_budget_validator.py`: Strict limit validation ($\le$ income), retry logic, and fallback safety.
- `tests/test_api.py`: Chart.js JSON endpoints and `<15s` quick-add expense flow.
- `tests/test_reports.py`: High-fidelity ReportLab PDF generation and CSV transaction export.

---

## 7. Financial Advice Disclaimer

> **Important Notice:** The Personal Finance Advisor Bot is an educational and informational tool designed to facilitate budgeting discipline and personal spending clarity. It does not provide certified financial, investment, legal, or tax advice. All numerical figures, budget limits, and health scores are computed deterministically by system rules.
