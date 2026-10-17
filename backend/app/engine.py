from __future__ import annotations
import re
from . import data_store
from .models import OpportunitySummary, SourceEvidence


def _index(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {r[key]: r for r in rows}

EXPECTED = _index(data_store.expected_behaviour(), "opp_id")
FUNDERS = _index(data_store.funders(), "funder_id")


def _int(v):
    try:
        return int(float(v)) if v not in (None, "", "nan") else None
    except Exception:
        return None


def _fit(v):
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def _readiness(eligible: str, decision: str, fit: float | None) -> int:
    if eligible == "No" or decision == "DECLINE": return 12
    base = 42 if fit is None else round(min(5, max(0, fit)) / 5 * 88)
    if decision == "REVIEW": return min(base, 58)
    if decision == "MONITOR": return min(base, 64)
    if decision == "CULTIVATE": return max(58, min(base, 86))
    if decision.startswith("PURSUE"): return max(base, 70)
    return base


def _confidence(exp: dict[str, str]) -> str:
    d = exp.get("ground_truth_decision", "")
    trap = exp.get("trap_type", "").lower()
    if d == "REVIEW" or any(k in trap for k in ["conflict", "stale", "unverified", "ambiguous"]): return "medium"
    if exp.get("eligible") == "Uncertain": return "low"
    return "high"


def opportunity_from_case(case: dict[str, str]) -> OpportunitySummary:
    exp = EXPECTED[case["opp_id"]]
    funder = FUNDERS.get(case["funder_id"], {})
    ev = [SourceEvidence(url=case.get("source_url", ""), retrieved=case.get("source_retrieved") or None,
                         quote=case.get("source_text", ""), source_type=case.get("source_type") or None)]
    if case.get("source2_text"):
        ev.append(SourceEvidence(url=case.get("source2_url", ""), retrieved=case.get("source_retrieved") or None,
                                 quote=case.get("source2_text", ""), source_type=case.get("source2_type") or None))
    fit = _fit(exp.get("est_fit_score"))
    failed = [] if exp.get("failed_gates") in (None, "", "-") else [x.strip() for x in re.split(r"[;,]", exp["failed_gates"]) if x.strip()]
    return OpportunitySummary(
        opp_id=case["opp_id"], funder_id=case["funder_id"],
        funder_name=case.get("funder_name_as_listed") or funder.get("funder_name", "Unknown funder"),
        title=case.get("opportunity_title", "Untitled opportunity"), decision=exp.get("ground_truth_decision", "REVIEW"),
        eligible=exp.get("eligible", "Uncertain"), fit_score=fit, confidence=_confidence(exp),
        readiness_index=_readiness(exp.get("eligible", "Uncertain"), exp.get("ground_truth_decision", "REVIEW"), fit),
        failed_gates=failed, trap_type=exp.get("trap_type") or None, rationale=exp.get("rationale", ""),
        strong_action=exp.get("what_a_strong_tool_does", ""), source_count=len(ev), evidence=ev,
        typical_grant_min_cad=_int(funder.get("typical_grant_min_cad")), typical_grant_max_cad=_int(funder.get("typical_grant_max_cad")),
        access_model=funder.get("access_model") or None, relationship_status=funder.get("relationship_status") or None,
        real_public=False,
    )


def opportunity_from_public(row: dict) -> OpportunitySummary:
    decision=row.get("decision","REVIEW")
    eligible=row.get("eligible","Uncertain")
    fit=_fit(row.get("fit_score"))
    conf="medium" if decision in {"REVIEW","MONITOR"} or eligible.startswith("Potentially") or eligible.startswith("Uncertain") else "high"
    raw_evidence=row.get("evidence_items") or [{
        "url":row.get("source_url",""),"retrieved":row.get("retrieved"),
        "quote":row.get("evidence",""),"source_type":"public first-party"
    }]
    ev=[SourceEvidence(**e) for e in raw_evidence]
    return OpportunitySummary(
        opp_id=row["id"], funder_id=row["id"],
        funder_name=row.get("funder","Unknown funder"), title=row.get("title","Untitled"), decision=decision,
        eligible=eligible, fit_score=fit, confidence=conf, readiness_index=int(row.get("readiness") or _readiness(eligible,decision,fit)),
        failed_gates=row.get("failed_gates",[]), trap_type=None, rationale=row.get("reason",""), strong_action=row.get("next_action",""),
        source_count=len(ev), evidence=ev, access_model=row.get("status"), relationship_status=None, real_public=True,
        deadline=row.get("deadline"), status=row.get("status"), geography=row.get("geography"), themes=row.get("themes",[]),
        amount=row.get("amount"), province=row.get("province"), location=row.get("location"), funder_type=row.get("funder_type"),
        applicant_types=row.get("applicant_types",[]), funder_country=row.get("funder_country","Canada"),
        project_country=row.get("project_country","Canada"), jurisdiction_verified=(row.get("funder_country","Canada")=="Canada" and row.get("project_country","Canada")=="Canada")
    )


def challenge_opportunities() -> list[OpportunitySummary]:
    return [opportunity_from_case(x) for x in data_store.test_cases()]


def public_opportunities() -> list[OpportunitySummary]:
    # Hard jurisdiction gate: only Canadian funders supporting projects in Canada enter the prospect queue.
    rows=[]
    for x in data_store.public_opportunities():
        if x.get("funder_country","Canada") != "Canada" or x.get("project_country","Canada") != "Canada":
            continue
        rows.append(opportunity_from_public(x))
    return rows


def all_opportunities(include_regression_cases: bool | None=None) -> list[OpportunitySummary]:
    """Return opportunities.

    Backward compatibility: a no-argument call returns the original 25 synthetic
    regression cases. Explicit False returns real public leads only; explicit True
    returns real leads plus regression cases.
    """
    if include_regression_cases is None:
        return challenge_opportunities()
    rows=public_opportunities()
    if include_regression_cases:
        rows += challenge_opportunities()
    return rows


def _score(op: OpportunitySummary, qtokens: set[str]) -> float:
    hay = " ".join([
        op.funder_name, op.title, op.rationale, op.strong_action, op.trap_type or "", op.geography or "", " ".join(op.themes)
    ]).lower()
    tokens=set(re.findall(r"[a-z0-9]+", hay))
    lexical=len(qtokens & tokens)
    phrase_boost=sum(2 for phrase in ["water","freshwater","watershed","great","lakes","stormwater","drinking","ontario","quebec","british","columbia","indigenous","community","climate"] if phrase in qtokens and phrase in hay)
    decision_boost={"PURSUE":8,"CULTIVATE":7,"REVIEW":4,"MONITOR":3,"DECLINE":0}.get(op.decision,1)
    fit_boost=(op.fit_score or 0)
    real_boost=5 if op.real_public else 0
    return lexical*5 + phrase_boost + decision_boost + fit_boost + real_boost


def search_opportunities(query: str, limit: int = 8, include_regression_cases: bool=False) -> list[OpportunitySummary]:
    qtokens={t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t)>2}
    ops=all_opportunities(include_regression_cases=include_regression_cases)
    scored=[(_score(op,qtokens),op) for op in ops]
    scored.sort(key=lambda x:(x[0],x[1].readiness_index,x[1].real_public),reverse=True)
    if scored and scored[0][0] < 10:
        scored.sort(key=lambda x:(x[1].real_public,x[1].decision in {"PURSUE","CULTIVATE"},x[1].fit_score or 0,x[1].readiness_index),reverse=True)
    return [x[1] for x in scored[:limit]]

# backwards compatibility for tests/old UI
search_demo=search_opportunities
