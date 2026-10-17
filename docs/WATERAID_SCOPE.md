# WaterAid scope — GrantCurrent v0.5

## Geography policy

1. **Funding source / donor / funder must be Canadian.**
2. **Project geography must overlap at least one active configured target country.**
3. The baseline list is seeded from WaterAid's public country list, but users can change the active scope in the application.
4. External research providers receive the current active-country list, not a static hard-coded country universe.

## Country management

Open **Scope & settings** to:

- add a country,
- edit country / region / source,
- deactivate or reactivate a country,
- permanently remove a configured country.

Changes persist in SQLite and immediately affect ranked opportunities, RAG country context and external research instructions. Baseline-country deletion is persisted with a tombstone so a removed country is not silently re-seeded; explicitly adding it again restores it.

## Baseline list

The packaged baseline includes the WaterAid-country list used in v0.4. The app preserves the prior website-count discrepancy rather than silently inventing a reconciliation. Client/mentor-confirmed geography should be treated as authoritative when supplied.
