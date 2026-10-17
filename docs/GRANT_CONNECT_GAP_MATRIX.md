# GrantCurrent v0.3 — Grant-database parity matrix

GrantCurrent does not copy Grant Connect branding, proprietary data or interface assets. It adopts useful product patterns: simple keyword search, saved searches, filterable award-history tables, source-linked funder research and prospect workflow.

| Capability | v0.3 status | Notes |
|---|---|---|
| Keyword/funder search | Implemented | Global + Funding Explorer search |
| Saved searches | Implemented | Gift Explorer local saved searches |
| Gift / award history | Implemented | Public Canadian awards with amount, focus, location, year and source |
| Column filters | Implemented | Gift Explorer funder/focus/location/year filters |
| Funder profiles | Implemented | Geography, access, themes, status, award signal |
| Public contact paths | Implemented | Program contacts with verification source |
| Source links | Implemented | First-party evidence always visible |
| Pipeline | Implemented | Qualified, Cultivating, Applying, Submitted, Won/Lost |
| Alerts / weekly review | Implemented | Current open/time-sensitive opportunities in This Week |
| Human decision log | Implemented | Agreement/override recorded in SQLite |
| AI discovery | Implemented optionally | Local RAG always; OpenAI/Gemini/Microsoft if configured |
| Canada-only jurisdiction rule | Implemented | Live queue rejects non-Canadian funders and overseas projects |
| Proprietary 12k+ curated funder database | Not parity | Public-data corpus is smaller; expand through scheduled ingestion and QA |
| Million-scale historical gift database | Not parity | Public government/fund recipient history included; CRA/open-data ingestion can expand it |
| Enterprise identity / CRM integrations | Future | Add SSO/RBAC and CRM connector before production rollout |

## Product advantage to emphasize

A grant database is excellent at **finding possible funders**.

GrantCurrent adds a decision layer:

**Canadian jurisdiction → evidence freshness → eligibility → fit → workload/value → human decision.**
