from __future__ import annotations

import csv
import io
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from .config import DATA_DIR
from . import runtime_store

EXPECTED_COLUMNS = [
    "record_id","fiscal_year","submitted_date","funder_id","funder_name","funder_type",
    "application_type","theme_code","country","ask_cad","fundraising_hours",
    "relationship_at_submission","outcome","award_cad","decision_date","reason_or_note",
]
OUTCOMES = {"Won", "Lost", "Ineligible", "Withdrawn", "Not submitted"}
SYNTHETIC_NOTICE = "SYNTHETIC - FICTIONAL ORGANIZATION FOR THE WATER CHALLENGE - NOT WATERAID DATA"


def _num(v: Any) -> float:
    try:
        if v in (None, ""):
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: row.get(k) for k in EXPECTED_COLUMNS}
    for k in ("ask_cad","fundraising_hours","award_cad"):
        out[k] = _num(out.get(k))
    # Preserve the literal category "None" as a valid relationship value.
    rel = out.get("relationship_at_submission")
    out["relationship_at_submission"] = "None" if rel is None or str(rel).strip()=="" else str(rel).strip()
    out["reason_or_note"] = "" if out.get("reason_or_note") is None else str(out.get("reason_or_note"))
    return out


def parse_csv_text(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#") and line.strip()]
    if not lines:
        return [], ["No CSV rows were found after skipping comment lines."]
    reader = csv.DictReader(lines)
    fields = reader.fieldnames or []
    missing = [c for c in EXPECTED_COLUMNS if c not in fields]
    extra = [c for c in fields if c not in EXPECTED_COLUMNS]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if extra:
        warnings.append("Extra columns were ignored: " + ", ".join(extra))
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(reader, start=2):
        rec = str(row.get("record_id") or "").strip()
        if not rec:
            warnings.append(f"Row {i}: missing record_id; skipped")
            continue
        if rec in seen:
            warnings.append(f"Row {i}: duplicate record_id {rec}; skipped")
            continue
        seen.add(rec)
        outcome = str(row.get("outcome") or "").strip()
        if outcome and outcome not in OUTCOMES:
            warnings.append(f"Row {i}: unrecognized outcome '{outcome}'")
        rows.append(_clean_row(row))
    return rows, warnings


def _ensure_table() -> None:
    with runtime_store._conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS funders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funder_key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            source TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS historical_applications (
            record_id TEXT PRIMARY KEY,
            fiscal_year TEXT,
            submitted_date TEXT,
            funder_id TEXT,
            funder_name TEXT,
            funder_type TEXT,
            application_type TEXT,
            theme_code TEXT,
            country TEXT,
            ask_cad REAL NOT NULL DEFAULT 0,
            fundraising_hours REAL NOT NULL DEFAULT 0,
            relationship_at_submission TEXT NOT NULL DEFAULT 'None',
            outcome TEXT,
            award_cad REAL NOT NULL DEFAULT 0,
            decision_date TEXT,
            reason_or_note TEXT,
            source TEXT NOT NULL DEFAULT 'L1_pipeline_history.csv',
            imported_at TEXT NOT NULL
        )''')
        c.commit()


def seed() -> dict[str, Any]:
    _ensure_table()
    path = DATA_DIR / "L1_pipeline_history.csv"
    text = path.read_text(encoding="utf-8-sig")
    rows, warnings = parse_csv_text(text)
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    with runtime_store._conn() as c:
        for r in rows:
            cur = c.execute('''INSERT OR IGNORE INTO historical_applications(
                record_id,fiscal_year,submitted_date,funder_id,funder_name,funder_type,application_type,
                theme_code,country,ask_cad,fundraising_hours,relationship_at_submission,outcome,award_cad,
                decision_date,reason_or_note,source,imported_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                r["record_id"],r["fiscal_year"],r["submitted_date"],r["funder_id"],r["funder_name"],r["funder_type"],
                r["application_type"],r["theme_code"],r["country"],r["ask_cad"],r["fundraising_hours"],
                r["relationship_at_submission"],r["outcome"],r["award_cad"],r["decision_date"],r["reason_or_note"],
                "L1_pipeline_history.csv", now
            ))
            inserted += int(cur.rowcount > 0)
        # Maintain a normalized Funders entity for downstream joins and administration.
        for r in rows:
            key = str(r.get("funder_id") or r.get("funder_name") or "").strip()
            name = str(r.get("funder_name") or key).strip()
            if key and name:
                c.execute('''INSERT OR IGNORE INTO funders(funder_key,name,category,source,created_at,updated_at)
                  VALUES(?,?,?,?,?,?)''', (key,name,r.get("funder_type"),"L1_pipeline_history.csv",now,now))
        c.commit()
    return {"rows": len(rows), "inserted": inserted, "warnings": warnings}


def import_text(text: str) -> dict[str, Any]:
    _ensure_table()
    rows, warnings = parse_csv_text(text)
    inserted = 0
    duplicates = 0
    now = datetime.now(timezone.utc).isoformat()
    with runtime_store._conn() as c:
        for r in rows:
            cur = c.execute('''INSERT OR IGNORE INTO historical_applications(
                record_id,fiscal_year,submitted_date,funder_id,funder_name,funder_type,application_type,
                theme_code,country,ask_cad,fundraising_hours,relationship_at_submission,outcome,award_cad,
                decision_date,reason_or_note,source,imported_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                r["record_id"],r["fiscal_year"],r["submitted_date"],r["funder_id"],r["funder_name"],r["funder_type"],
                r["application_type"],r["theme_code"],r["country"],r["ask_cad"],r["fundraising_hours"],
                r["relationship_at_submission"],r["outcome"],r["award_cad"],r["decision_date"],r["reason_or_note"],
                "user_upload", now
            ))
            if cur.rowcount:
                inserted += 1
            else:
                duplicates += 1
        c.commit()
    return {"valid_rows": len(rows), "inserted": inserted, "duplicates": duplicates, "warnings": warnings}


def all_rows() -> list[dict[str, Any]]:
    seed()
    with runtime_store._conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM historical_applications ORDER BY fiscal_year, submitted_date, record_id")]
    return rows


def _matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    mapping = {
        "year":"fiscal_year", "country":"country", "theme":"theme_code", "funder_type":"funder_type",
        "relationship":"relationship_at_submission", "outcome":"outcome", "application_type":"application_type",
        "funder":"funder_name"
    }
    for f, col in mapping.items():
        v = filters.get(f)
        if v and v != "ALL" and str(row.get(col) or "") != str(v):
            return False
    q = str(filters.get("q") or "").strip().lower()
    if q:
        hay = " ".join(str(row.get(k) or "") for k in EXPECTED_COLUMNS).lower()
        if q not in hay:
            return False
    return True


def filtered_rows(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = all_rows()
    filters = filters or {}
    return [r for r in rows if _matches(r, filters)]


def filter_options() -> dict[str, list[str]]:
    rows = all_rows()
    def u(k: str): return sorted({str(r.get(k)) for r in rows if r.get(k) not in (None, "")})
    return {
        "year": u("fiscal_year"), "country": u("country"), "theme": u("theme_code"),
        "funder_type": u("funder_type"), "relationship": u("relationship_at_submission"),
        "outcome": u("outcome"), "application_type": u("application_type"), "funder": u("funder_name"),
    }


def _rate(n: float, d: float) -> float:
    return round((n / d * 100.0), 1) if d else 0.0


def _group(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[str(r.get(key) or "Unknown")].append(r)
    out=[]
    for name, rr in groups.items():
        completed=[x for x in rr if x.get("outcome") not in ("Withdrawn","Not submitted")]
        won=[x for x in rr if x.get("outcome")=="Won"]
        funded=[x for x in rr if _num(x.get("award_cad"))>0]
        hours=sum(_num(x.get("fundraising_hours")) for x in rr)
        awarded=sum(_num(x.get("award_cad")) for x in rr)
        asked=sum(_num(x.get("ask_cad")) for x in rr)
        out.append({
            "label":name,"n":len(rr),"completed_n":len(completed),"won_n":len(won),"funded_n":len(funded),
            "stage_success_rate":_rate(len(won),len(completed)),"cash_conversion_rate":_rate(len(funded),len(completed)),
            "requested_cad":asked,"awarded_cad":awarded,"fundraising_hours":hours,
            "awarded_per_hour":round(awarded/hours,2) if hours else 0,
            "award_to_ask_ratio":round(awarded/asked,4) if asked else 0,
        })
    return sorted(out,key=lambda x:(-x["awarded_cad"],x["label"]))


def _outcomes_by_year(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by[str(r.get("fiscal_year") or "Unknown")][str(r.get("outcome") or "Unknown")] += 1
    out=[]
    for year in sorted(by):
        row={"fiscal_year":year,"total":sum(by[year].values())}
        for outcome in ["Won","Lost","Ineligible","Withdrawn","Not submitted"]:
            row[outcome]=by[year].get(outcome,0)
        out.append(row)
    return out


def _donor_concentration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by=defaultdict(float)
    total=0.0
    for r in rows:
        amt=_num(r.get("award_cad")); total+=amt; by[str(r.get("funder_name") or "Unknown")]+=amt
    top=sorted(by.items(),key=lambda x:-x[1])[:5]
    return {"top_funders":[{"funder":k,"awarded_cad":v,"share_pct":_rate(v,total)} for k,v in top],"top_1_share_pct":_rate(top[0][1],total) if top and total else 0,"top_5_share_pct":_rate(sum(v for _,v in top),total) if total else 0}


def _high_effort_rejections(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bad=[r for r in rows if r.get("outcome") in ("Lost","Ineligible")]
    return sorted(bad,key=lambda r:-_num(r.get("fundraising_hours")))[:10]

def analytics(filters: dict[str, Any] | None = None, exclude_largest_award: bool = False) -> dict[str, Any]:
    rows=filtered_rows(filters)
    comparison_rows=list(rows)
    excluded_record=None
    if exclude_largest_award and comparison_rows:
        excluded_record=max(comparison_rows,key=lambda r:_num(r.get("award_cad")))
        comparison_rows=[r for r in comparison_rows if r.get("record_id")!=excluded_record.get("record_id")]
    completed=[r for r in rows if r.get("outcome") not in ("Withdrawn","Not submitted")]
    won=[r for r in rows if r.get("outcome")=="Won"]
    funded=[r for r in rows if _num(r.get("award_cad"))>0]
    total_ask=sum(_num(r.get("ask_cad")) for r in rows)
    total_award=sum(_num(r.get("award_cad")) for r in rows)
    total_hours=sum(_num(r.get("fundraising_hours")) for r in rows)
    lost_effort=sum(_num(r.get("fundraising_hours")) for r in rows if r.get("outcome") in ("Lost","Ineligible"))
    funded_hours=sum(_num(r.get("fundraising_hours")) for r in funded)
    metrics={
        "total_applications":len(rows),
        "total_requested_cad":total_ask,
        "total_awarded_cad":total_award,
        "unique_funders":len({r.get("funder_id") for r in rows if r.get("funder_id")}),
        "completed_applications":len(completed),
        "won_outcomes":len(won),
        "positive_awards":len(funded),
        "stage_success_rate":_rate(len(won),len(completed)),
        "funding_conversion_rate":_rate(len(funded),len(completed)),
        "fundraising_hours":total_hours,
        "awarded_per_fundraising_hour":round(total_award/total_hours,2) if total_hours else 0,
        "avg_award_per_funded_application":round(total_award/len(funded),2) if funded else 0,
        "fundraising_hours_per_funded_application":round(funded_hours/len(funded),2) if funded else 0,
        "award_to_ask_ratio":round(total_award/total_ask,4) if total_ask else 0,
        "lost_application_effort_hours":lost_effort,
        "denominators":{
            "stage_success_rate":"Won / completed decisions; Withdrawn and Not submitted excluded",
            "funding_conversion_rate":"Applications with award_cad > 0 / completed decisions; Withdrawn and Not submitted excluded",
        }
    }
    return {
        "synthetic":True,"synthetic_notice":SYNTHETIC_NOTICE,"filters":filters or {},"metrics":metrics,
        "groups":{
            "fiscal_year":_group(comparison_rows,"fiscal_year"),
            "outcome":_group(comparison_rows,"outcome"),
            "funder_type":_group(comparison_rows,"funder_type"),
            "theme":_group(comparison_rows,"theme_code"),
            "country":_group(comparison_rows,"country"),
            "application_type":_group(comparison_rows,"application_type"),
            "relationship":_group(comparison_rows,"relationship_at_submission"),
        },
        "outcomes_by_year": _outcomes_by_year(comparison_rows),
        "donor_concentration": _donor_concentration(comparison_rows),
        "high_effort_rejections": _high_effort_rejections(comparison_rows),
        "outlier":{
            "excluded": bool(exclude_largest_award and excluded_record),
            "record": excluded_record,
            "note":"Efficiency comparisons only: the largest award is excluded from grouped efficiency charts when this toggle is on. Headline totals still reflect the selected records."
        },
        "sample_warning":"Historical patterns are descriptive associations, not causal evidence or statistically validated funding probabilities. Small groups can be unstable; sample sizes are always shown.",
    }


def benchmark_check() -> dict[str, Any]:
    a=analytics()
    m=a["metrics"]
    expected={"total_applications":104,"unique_funders":27,"total_requested_cad":22530000,"total_awarded_cad":7999000,"fundraising_hours":3223,"won_outcomes":35,"positive_awards":25}
    checks={k:{"expected":v,"actual":m.get(k),"pass":abs(float(m.get(k,0))-float(v))<1e-6} for k,v in expected.items()}
    won_zero=sum(1 for r in all_rows() if r.get("outcome")=="Won" and _num(r.get("award_cad"))==0)
    checks["won_zero_award"]={"expected":10,"actual":won_zero,"pass":won_zero==10}
    return {"pass":all(x["pass"] for x in checks.values()),"checks":checks}


def funder_profiles() -> list[dict[str, Any]]:
    rows=all_rows()
    groups: dict[str,list[dict[str,Any]]] = defaultdict(list)
    for r in rows: groups[str(r.get("funder_id") or r.get("funder_name"))].append(r)
    out=[]
    for key,rr in groups.items():
        completed=[x for x in rr if x.get("outcome") not in ("Withdrawn","Not submitted")]
        won=[x for x in rr if x.get("outcome")=="Won"]
        funded=[x for x in rr if _num(x.get("award_cad"))>0]
        reasons=Counter([str(x.get("reason_or_note") or "").strip() for x in rr if x.get("outcome") in ("Lost","Ineligible") and str(x.get("reason_or_note") or "").strip()])
        awarded=sum(_num(x.get("award_cad")) for x in rr)
        asked=sum(_num(x.get("ask_cad")) for x in rr)
        hours=sum(_num(x.get("fundraising_hours")) for x in rr)
        rels=Counter(str(x.get("relationship_at_submission") or "None") for x in rr)
        rate=_rate(len(won),len(completed))
        cash=_rate(len(funded),len(completed))
        if len(rr)<2:
            confidence="Low"
        elif len(rr)<5:
            confidence="Medium"
        else:
            confidence="Higher"
        if cash>=50 and awarded>0:
            insight="Historically promising"
        elif cash>=25:
            insight="Mixed but potentially useful"
        else:
            insight="Limited historical cash conversion"
        out.append({
            "funder_id":rr[0].get("funder_id"),"funder_name":rr[0].get("funder_name"),"funder_type":rr[0].get("funder_type"),
            "application_count":len(rr),"countries":sorted({str(x.get("country")) for x in rr if x.get("country")}),
            "themes":sorted({str(x.get("theme_code")) for x in rr if x.get("theme_code")}),
            "requested_cad":asked,"awarded_cad":awarded,"relationships":dict(rels),
            "stage_success_rate":rate,"cash_conversion_rate":cash,"avg_fundraising_hours":round(hours/len(rr),1) if rr else 0,
            "unsuccessful_reasons":[{"reason":k,"n":v} for k,v in reasons.most_common(5)],
            "historical_pattern":insight,"confidence":confidence,
            "ai_insight":f"{insight}: {len(funded)} of {len(completed)} completed applications produced positive cash awards ({cash:.1f}%). Based on {len(rr)} historical records; this is descriptive evidence, not a prediction.",
        })
    return sorted(out,key=lambda x:(-x["awarded_cad"],x["funder_name"] or ""))


def advisor(question: str, exclude_largest_award: bool = False) -> dict[str, Any]:
    q=(question or "").lower()
    a=analytics(exclude_largest_award=exclude_largest_award)
    m=a["metrics"]
    rows=all_rows()
    citations=[]
    title="Grounded fundraising analysis"
    bullets=[]
    if "unsuccess" in q or "lost" in q:
        bad=[r for r in rows if r.get("outcome") in ("Lost","Ineligible")]
        reasons=Counter(str(r.get("reason_or_note") or "No reason recorded") for r in bad)
        title="What explains unsuccessful applications?"
        for reason,n in reasons.most_common(5): bullets.append(f"{reason}: {n} records")
        citations=[r["record_id"] for r in bad[:8]]
    elif "relationship" in q:
        g=a["groups"]["relationship"]
        title="Which funder relationships should we strengthen?"
        for x in sorted(g,key=lambda z:-z["cash_conversion_rate"])[:5]: bullets.append(f"{x['label']}: {x['cash_conversion_rate']}% cash conversion across n={x['n']} records")
    elif "hours" in q or "effort" in q:
        g=a["groups"]["application_type"]
        title="Where are we investing too many fundraising hours?"
        for x in sorted(g,key=lambda z:z["awarded_per_hour"])[:5]: bullets.append(f"{x['label']}: {x['awarded_per_hour']:.0f} CAD awarded per fundraising hour across n={x['n']}")
    elif "theme" in q:
        g=a["groups"]["theme"]
        title="Which WASH themes perform best historically?"
        for x in sorted(g,key=lambda z:-z["awarded_cad"])[:5]: bullets.append(f"{x['label']}: {x['awarded_cad']:.0f} CAD awarded; {x['cash_conversion_rate']}% cash conversion; n={x['n']}")
    elif "exclude" in q or "large award" in q or "outlier" in q:
        full=analytics(exclude_largest_award=False)
        ex=analytics(exclude_largest_award=True)
        title="What changes if we exclude the unusually large award?"
        out=ex["outlier"]["record"] or {}
        bullets=[f"Largest award record: {out.get('record_id','Unknown')} ({_num(out.get('award_cad')):,.0f} CAD).",
                 "The exclusion applies to grouped efficiency comparisons, not to headline historical totals.",
                 f"Headline historical funding remains {full['metrics']['total_awarded_cad']:,.0f} CAD because the record is still part of the source dataset."]
    elif "prioritize" in q or "top five" in q or "strategy" in q:
        title="Top five evidence-backed funding strategy recommendations"
        rel=sorted(a["groups"]["relationship"],key=lambda z:-z["cash_conversion_rate"])
        app=sorted(a["groups"]["application_type"],key=lambda z:-z["awarded_per_hour"])
        theme=sorted(a["groups"]["theme"],key=lambda z:-z["awarded_cad"])
        bullets=[
            f"Protect scarce fundraising time: historical lost/ineligible effort totals {m['lost_application_effort_hours']:,.0f} hours.",
            f"Prioritize stronger relationship categories where justified; best observed cash conversion is {rel[0]['label']} at {rel[0]['cash_conversion_rate']}% (n={rel[0]['n']})." if rel else "Relationship evidence is unavailable.",
            f"Use application-efficiency evidence: {app[0]['label']} has the highest observed awarded CAD/hour ({app[0]['awarded_per_hour']:,.0f}; n={app[0]['n']})." if app else "Application efficiency evidence is unavailable.",
            f"Focus on historically funded WASH themes where strategically aligned; {theme[0]['label']} has {theme[0]['awarded_cad']:,.0f} CAD historically awarded (n={theme[0]['n']})." if theme else "Theme evidence is unavailable.",
            "Keep eligibility, current deadlines and donor priorities separately verified; historical performance does not establish current eligibility."
        ]
    else:
        title="FundScope Advisor summary"
        bullets=[
            f"The synthetic history contains {m['total_applications']} applications to {m['unique_funders']} funders.",
            f"Positive cash awards occurred in {m['positive_awards']} completed records; cash conversion is {m['funding_conversion_rate']}% using the documented denominator.",
            f"Fundraising teams invested {m['fundraising_hours']:,.0f} hours and observed {m['awarded_per_fundraising_hour']:,.0f} CAD awarded per hour historically.",
            "Ask a suggested question for a more targeted analysis."
        ]
    return {
        "mode":"deterministic_grounded_analysis","title":title,"answer":bullets,"supporting_record_ids":citations,
        "assumptions":["Seed history is synthetic hackathon data, not WaterAid records.","Associations are descriptive and not causal.","Current donor eligibility and open calls require separately verified evidence."],
        "sample_size":len(rows),"metrics":m,"outlier_mode":exclude_largest_award,
    }


def csv_export(filters: dict[str, Any] | None = None) -> str:
    rows=filtered_rows(filters)
    buf=io.StringIO()
    w=csv.DictWriter(buf,fieldnames=EXPECTED_COLUMNS)
    w.writeheader()
    for r in rows: w.writerow({k:r.get(k) for k in EXPECTED_COLUMNS})
    return buf.getvalue()
