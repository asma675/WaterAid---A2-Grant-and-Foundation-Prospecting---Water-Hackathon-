# RAG and multi-provider research

GrantCurrent separates **discovery** from **verification**.

## Local RAG corpus

The live corpus contains:

- WaterAid's current target-country list and organizational profile
- Canadian funder and donor profiles
- real/current or cultivation-oriented funding opportunities
- WaterAid and peer giving / partnership signals
- Canadian funder first-party pages
- Government of Canada international-assistance sources
- public professional contact routes

Synthetic challenge cases remain regression fixtures and are not included in the live RAG corpus.

## External research providers

When configured, OpenAI, Gemini and Microsoft/Copilot can broaden discovery. Their system instruction requires:

- Canadian funders/donors/programs only
- projects aligned to WaterAid target countries
- WASH, water security/scarcity, sanitation, hygiene, climate-resilient WASH, health systems, women/girls and related themes
- first-party sources for eligibility, deadlines, amounts and access
- no invented facts

Provider output is **not** automatically inserted into the ranked prospect database. It is an unverified lead until jurisdiction, project geography, eligibility and evidence checks pass.
