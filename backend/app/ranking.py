from __future__ import annotations
from . import data_store
from .models import RankItem

WEIGHTS = {"C1": .25, "C2": .15, "C3": .20, "C4": .15, "C5": .10, "C6": .10, "C7": .05}
HOURS = {"LOI": 8, "Short application": 24, "Full proposal": 60, "Corporate proposal": 40, "Government call": 220, "Renewal": 30}


def fit_score(row: dict[str, str]) -> float:
    return round(sum(float(row[c]) * w for c, w in WEIGHTS.items()), 2)


def ranking_items() -> list[RankItem]:
    ref={r['rank_id']:r for r in data_store.ranking_reference()}
    rows=[]
    for r in data_store.ranking_scenario():
        rr=ref.get(r['rank_id'], {})
        rows.append(RankItem(
            rank_id=r['rank_id'], summary=r['summary'], fit_score=fit_score(r),
            application_type=r['application_type'], fundraising_hours=HOURS.get(r['application_type'], 0),
            likely_grant_cad=int(float(r['likely_grant_cad'])),
            decision=rr.get('decision','REVIEW'), reference_reasoning=rr.get('reasoning','')
        ))
    order={r['rank_id']:int(r['order']) for r in data_store.ranking_reference()}
    rows.sort(key=lambda x: order.get(x.rank_id,999))
    return rows
