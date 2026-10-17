# Judging guide — GrantCurrent v0.5

## One sentence

GrantCurrent helps a small fundraising team find **Canadian funding for WaterAid-country WASH work** and turns each lead into a source-linked, gate-checked, capacity-aware briefing note a fundraiser can act on.

## Exact briefing-note coverage

| Requirement | v0.5 implementation |
|---|---|
| Header | Funder, opportunity, recommendation, fit, confidence, readiness |
| Why it fits | Top three weighted rubric signals with evidence, plus inspectable full C1–C7 weighted breakdown |
| Eligibility | Full G1–G8 table with Pass / Fail / Uncertain, reason, quote, URL, retrieval date |
| Key dates | Confirmed / Inferred / Unknown labels with source |
| Money & effort | Grant range, likely ask, application type, fundraising/program hours, expected value, remaining capacity, fits? |
| Relationship path | Relationship status/strength, consent rule, verified channel, suggested ask, evidence |
| Risks & unknowns | Dedicated section generated from failed/uncertain gates, timing and access risk |
| Next step | Action, owner, internal due date |
| Sources | Dated source cards for every loaded evidence item |
| Human decision | Agree / override + reason, persisted to decision log |
| Operational handoff | Add to Pipeline; owner/stage/amount/deadline/notes editable |

## Strong demo sequence

1. **This week** — explain the hard rule: Canadian funding source + active WaterAid target country.
2. Open **Roncalli** — show the top-three fit rationale, expand full C1–C7, then show all G1–G8, confirmed/unknown dates, capacity and relationship path.
3. Open **GAC Canadian Climate Partnerships** — show attractive fit but **G6 Access Fail** and therefore a defensible decline.
4. **Gift Explorer** — search `WaterAid`, `Malawi`, `Nigeria`, or a funder to show actual giving/partnership evidence.
5. **Scope & settings** — add, deactivate, reactivate or permanently remove a country and show that the live prospect universe changes without code changes.
6. Edit a planning assumption or the weekly review cap, then return to the brief to show Money & effort / This week recalculated.
7. Record a human decision and add the prospect to **Pipeline**.
8. **Sources & AI** — show Local RAG plus optional OpenAI/Gemini/Microsoft research status and inspectable sources.

## Regression story

Synthetic challenge cases remain internal regression fixtures and are not mixed into live WaterAid prospects:

- O08 validates hidden-opportunity discovery.
- O11 validates conflicting-date handling.
- K3 validates a strategic “no” when capacity is insufficient.

The pitch: **we validated the logic on the challenge cases, then apply the same evidence-first controls to real Canadian-funder research.**
