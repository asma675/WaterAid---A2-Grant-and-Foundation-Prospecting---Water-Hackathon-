# GrantCurrent v0.7 Classic — Funding Intelligence for Global WASH

GrantCurrent is a hackathon decision-support application for finding **Canadian funders and donors** for WASH projects in configurable WaterAid target countries, then deciding which opportunities deserve limited fundraising time.

> **Canadian funding source → global WaterAid project geography → evidence → eligibility → fit → effort/capacity → human decision.**

## Data boundary

The application uses two deliberately separate evidence layers:

1. **Synthetic historical demonstration data** from `L1_pipeline_history.csv` (104 fictional applications). This powers historical analytics and strategy demonstrations. It is **not WaterAid history**.
2. **Verified public funding evidence** for live prospecting. Current eligibility, deadlines and access rules must be supported by sourced public evidence and retrieval dates.

A visible synthetic-data warning appears throughout the historical analytics experience.

## Major v0.7 Classic modules

### 1. Overview
Dynamic executive intelligence dashboard with global filters and calculated KPIs:
- applications, amount requested, amount awarded, unique funders, completed applications
- stage-success rate vs positive-cash conversion rate
- fundraising hours, awarded CAD/hour, average funded award, lost/ineligible effort
- fiscal-year funding trends, outcomes by year, donor type, WASH theme, country, application efficiency and relationship patterns

### 2. Pipeline Explorer
- full 104-record historical pipeline table
- exact challenge columns preserved
- searchable, sortable and filterable
- comment-line-safe CSV import validation
- duplicate prevention by `record_id`
- CSV export
- clickable record detail
- current pursuit board: Qualified → Cultivating → Applying → Submitted → Won/Lost

### 3. Funder Intelligence
- derived historical funder profiles
- application count, countries, themes, requested/awarded funding, relationships, success/conversion rates, effort and loss reasons
- grounded deterministic **AI Insight Panel**
- Gift Explorer and verified public-contact views
- does not fabricate current donor eligibility or open-call facts

### 4. Opportunity Matching
Two complementary workflows:

**Verified public opportunities**
- requested judging filters: Recommendation, Hard gates, Relationship, Application type, Source freshness and Staff decision
- country filtering
- complete one-page briefing note: Header, C1–C7 fit, G1–G8 gates, key dates, money/effort, relationship path, risks, next step, sources and human decision

**User-entered opportunity scoring**
- 0–100 explainable prioritization model
- configurable weights: eligibility 25%, theme 20%, geography 15%, relationship 15%, historical outcomes 10%, effort 10%, timing 5%
- `Eligibility Unverified` overrides a preliminary score when essential eligibility evidence is missing
- funding stage tracked separately from technology maturity
- editable and removable saved opportunities

### 5. Fundraising Analytics
- awarded CAD/hour
- historical success and cash-conversion rates with sample sizes
- hours per funded application
- award-to-ask ratio
- donor concentration
- lost application effort
- fiscal-year comparisons
- highest-effort unsuccessful applications
- toggle to exclude the single largest award from efficiency comparisons

### 6. FundScope Advisor
Grounded deterministic strategy assistant using actual imported history. Suggested questions include unsuccessful applications, relationship strategy, excess effort, best-performing themes, top strategy recommendations, outlier sensitivity and application prioritization.

If no external LLM is configured, the interface explicitly labels the response as deterministic grounded analysis rather than pretending it is AI-generated.

### 7. Project Funding Planner
- create/edit/remove proposed WASH projects
- budget, existing funding, funding gap, beneficiaries, intervention, period, priority, readiness, owner, milestones and optional TRL
- link scored opportunities to projects
- scenario-test multiple grant pursuits against a staff-hour limit
- show requested funding, staff effort and a clearly-labelled planning indicator (not guaranteed funding)

### 8. Reports & Pitch Mode
- executive funding-strategy report
- PDF via browser Print / Save PDF
- CSV export
- 30/60/90-day action plan
- Hackathon Presentation Mode: Problem → Evidence → Insights → Solution → Priorities → Funding Impact → Next Steps

### 9. Administration
- add/edit/activate/deactivate/permanently remove target countries
- configurable scoring weights
- configurable capacity and cost assumptions
- data-quality issue reporting
- source/AI provider status
- audit log
- demo role-based access controls
- TRL reference guide

## Technology Readiness Levels (TRL)

The app includes TRL 1–9 as an **optional technology-maturity criterion**. The implementation follows Innovation Canada / ISED definitions and explains the NASA origin of the framework.

Important: **TRL is not the funding-application stage and is not a probability of receiving a grant.**

If an entered eligibility rule explicitly contains a TRL requirement (for example `TRL 6-8`), GrantCurrent checks the project TRL and can flag an eligibility conflict or missing TRL evidence.

Official Canadian reference: `https://ised-isde.canada.ca/site/innovation-canada/en/technology-readiness-levels`

## Analytical safeguards

- `Won` + `award_cad = 0` counts as stage success but not cash funding.
- Withdrawn and Not submitted are excluded from completed-decision denominators.
- `None` is preserved as a relationship category.
- blank notes are not interpreted as outcomes.
- historical associations are descriptive, not causal.
- sample sizes are displayed.
- no ML win-probability claim is made from this small dataset.
- current eligibility, deadlines and priorities require verified evidence.
- historical facts, inferred insights, planning assumptions and future forecasts are visibly separated.

## Seed benchmark validation

The imported synthetic history dynamically reconciles to:

- 104 applications
- 27 unique funders
- CAD 22,530,000 requested
- CAD 7,999,000 awarded
- 3,223 fundraising hours
- 35 Won outcomes
- 25 records with positive awards
- 10 Won outcomes with zero award

These values are tests, **not hardcoded dashboard values**.

## Demo RBAC

Server-side API permissions are enforced for the selected demo role:

- Administrator
- Fundraising Manager
- Analyst
- Project Manager
- Read-only Viewer

This is a hackathon identity simulation, not enterprise authentication. A live deployment should replace the selector with organizational SSO/OIDC/SAML and managed authorization policies.

## Run

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Open:
- App: `http://localhost:5173`
- API health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

The frontend calls `/api/v1` through the bundled Nginx proxy, so it does not depend on a separate browser CORS call to port 8000.

## Optional research providers

Local RAG works with no key. Optional server-side providers can be configured in `.env`:

```env
OPENAI_API_KEY=
GEMINI_API_KEY=
MICROSOFT_RESEARCH_URL=
MICROSOFT_RESEARCH_TOKEN=
```

External research remains discovery support; it does not bypass evidence, Canadian-funder jurisdiction, target-country, eligibility or human-decision controls.

## Tests

```powershell
$env:PYTHONPATH="backend"
pytest -q backend/tests
```

Expected v0.7 Classic result: **22 tests passing**.

## Production boundary

The build is hackathon-ready and production-structured, but a real donor/CRM deployment still needs organizational SSO, managed PostgreSQL, backups, secrets management, monitoring, DLP/egress controls, scheduled source-refresh workers, CRM integration, formal privacy/security review and operational ownership.
