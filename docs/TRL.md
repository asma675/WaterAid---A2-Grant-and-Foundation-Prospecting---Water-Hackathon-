# Technology Readiness Levels in GrantCurrent

GrantCurrent stores two different concepts:

1. **Funding stage** — Prospecting, Open call, LOI, Full proposal, Submitted, Awarded, Closed/declined.
2. **Technology Readiness Level (TRL)** — optional technology maturity from 1 to 9.

They are never treated as the same thing.

The TRL definitions shown in Administration are based on Innovation Canada / ISED. The UI also notes that NASA conceived the TRL approach in the 1970s and that the modern scale uses nine levels.

If a user-entered eligibility rule contains a recognizable requirement such as `TRL 6-8`, GrantCurrent compares it with the entered project TRL:

- no project TRL → **Eligibility Unverified**
- TRL outside the stated range → **Eligibility Conflict**
- TRL inside the range → criterion appears satisfied, but the user is still told to verify the exact first-party wording

TRL is never used as a grant win probability.
