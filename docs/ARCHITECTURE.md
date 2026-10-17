# Architecture

## Winning architecture

```text
Approved public sources
      │
      ▼
Scout ──> Snapshot store / change detection
      │
      ▼
Verifier ──> evidence objects (quote, URL, retrieved date, conflict flags)
      │
      ▼
Gatekeeper ──> G1–G8: PASS / FAIL / UNCERTAIN
      │              └── UNCERTAIN → REVIEW
      ▼
Strategist ──> C1–C7 weighted fit
      │
      ▼
Economist ──> effort + remaining hours + expected value
      │
      ▼
Evidence Auditor ──> source completeness / hallucination guard
      │
      ▼
Fundraiser brief ──> human accept / reject / reason code
      │
      └──────────────> calibration loop
```

## Why not “OpenAI agent vs Gemini agent vs Copilot agent”

That design duplicates model opinions without creating independent evidence. GrantCurrent separates **work responsibilities** instead. Model providers are execution engines behind the roles. This lets the charity swap providers, use a local model for sensitive steps, or run deterministic gates without changing the workflow.

## Data boundary

**Public zone:** funder pages, public annual reports, CRA records, federal grant data, public directories. This zone can be processed by approved external AI.

**Private zone:** donor identities, CRM records, board relationships, private notes, application history that contains personal data. This zone remains inside the client environment. Only derived, non-personal signals should cross into external model calls unless policy explicitly permits more.

## Production hardening beyond the hackathon

- Postgres + encrypted backups instead of demo in-memory reads.
- SSO/OIDC, role-based access, tenant isolation.
- Source-specific APIs/connectors instead of generic page fetching where possible.
- Queue workers for scheduled monitoring and content diffs.
- Full audit log with model/provider/version, prompt hash, source hash, and human override.
- Secret manager rather than `.env` in production.
- Egress allowlist and DLP policy.
- Regression test run on every prompt/model/rubric change.
