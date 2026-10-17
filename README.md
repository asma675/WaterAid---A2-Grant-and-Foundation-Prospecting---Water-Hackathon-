# GrantCurrent v0.3 — Canadian Water Funding

**Find Canadian funders for Canadian water problems. Then decide what is worth pursuing.**

GrantCurrent is a light, stakeholder-friendly grant prospecting application for Canadian freshwater, watershed, stormwater, drinking-water, restoration and community environmental work.

The live prospect queue has a hard jurisdiction rule:

> **Canadian funder/program + project in Canada only.**

Foreign donors, overseas projects and international-development calls are blocked from the default prospect list.

## What v0.3 adds

- **Bright, simple stakeholder UI** inspired by familiar grant-database workflows without copying another product's branding/assets.
- **This week** review dashboard with action counts, human-review queue, filters, recommendation table, evidence, freshness and next actions.
- **Funding Explorer** with one plain-language search box plus optional province/issue/funder filters.
- **Gift Explorer** with keyword search, saved searches, filterable award-history columns and source links.
- **Canadian Funder profiles** with program access, geography, themes, published-award signal and verified public contact paths.
- **Pipeline** with Qualified → Cultivating → Applying → Submitted → Won/Lost.
- **Decision Log** so fundraiser agreements/overrides become auditable feedback.
- **Canada-only RAG** over 20+ curated public sources, domestic opportunities, award records, funder profiles and public contacts.
- **Optional OpenAI, Gemini and Microsoft/Copilot research workers** for discovery. External findings remain an unverified discovery queue until GrantCurrent verifies Canadian jurisdiction and evidence.
- **Source-conflict handling**: when two first-party pages disagree, the recommendation becomes REVIEW rather than inventing an answer.

## Included Canadian data examples

The public corpus includes current/recurring sources such as:

- Canada Water Agency freshwater funding and Freshwater Ecosystem Initiatives
- Great Lakes funded-project history
- EcoAction and funded-project history
- Ontario Great Lakes Local Action Fund
- Environmental Damages Fund
- TD Friends of the Environment Foundation
- Watershed Security Fund (British Columbia)
- Federation of Canadian Municipalities / Green Municipal Fund water opportunities
- Government of Canada Grants & Contributions award history

Time-sensitive records should always be re-verified before a real submission.

## Run with Docker (recommended)

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

- App: `http://localhost:5173`
- Development API docs: `http://localhost:8000/docs`

## Optional external research

Local Canadian RAG works without keys. Add any providers you actually want to use:

```env
OPENAI_API_KEY=
GEMINI_API_KEY=
MICROSOFT_RESEARCH_URL=
MICROSOFT_RESEARCH_TOKEN=
```

Provider results are discovery leads only. They are not automatically added to the ranked prospect list.

## Recommended demo flow

1. Open **This week** and show the Canada-only gate, actionable calls and human-review queue.
2. Open a `PURSUE` row and show the source, date, Canadian geography and next action.
3. Open a `REVIEW` row such as Lake Simcoe and show how conflicting first-party pages are surfaced rather than guessed.
4. Open **Gift Explorer** and search `Great Lakes` or `watershed` to show historical Canadian award patterns.
5. Open **Funders** to show access, geography, award-history signal and public program contacts.
6. Add one opportunity to **Pipeline**.
7. Record a human decision and show it under **Decisions**.
8. Open **Sources & AI** and show the Canadian RAG corpus plus optional OpenAI/Gemini/Microsoft provider status.

## Tests

```powershell
$env:PYTHONPATH="backend"
pytest -q backend/tests
```

Current build: **10 tests passing**.

## Production note

The code has production-oriented boundaries (source evidence, rate limiting, security headers, SQLite persistence, external-AI privacy separation), but a live organizational deployment still needs SSO/RBAC, managed secrets, managed database/backups, monitoring, DLP/egress controls and security/privacy review.
