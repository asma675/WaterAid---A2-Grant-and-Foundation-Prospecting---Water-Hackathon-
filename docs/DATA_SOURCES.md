# Public data inventory

`challenge_pack/data/public_sources.json` is the app's discovery register. It currently contains **36 curated public sources** across:

- CRA / T3010 charity and qualified-donee open data;
- Government of Canada grants and contributions;
- Global Affairs Canada calls, unsolicited proposals and project history;
- IATI / d-portal;
- Philanthropic Foundations Canada and Community Foundations of Canada;
- first-party foundation/program pages and grant databases;
- water, climate, gender and community-funding programs.

Each source has a source tier, access rule, refresh cadence, intended use, tags and notes.

## Large CRA data

The repository does not duplicate the full CRA bulk CSV because it is large and changes annually. The exact current public resource URL is stored in `public_sources.json`.

After downloading it, run:

```bash
python backend/scripts/import_cra_peer_gifts.py /path/to/qualified_donees_2024_updated.csv
```

The importer keeps raw rows mentioning the challenge peer charities and writes `cra_peer_gifts_runtime.json`. It deliberately preserves raw evidence rather than guessing column meanings.

## Rebuild the inspectable RAG corpus

```bash
PYTHONPATH=backend python backend/scripts/build_rag_corpus.py
```

This writes `challenge_pack/data/rag_corpus.jsonl` for audit/demo purposes.

## Data-quality rule

A secondary directory can discover a lead, but a deadline, amount, eligibility rule or access rule should be verified against a first-party funder/government page before a real pursuit decision.
