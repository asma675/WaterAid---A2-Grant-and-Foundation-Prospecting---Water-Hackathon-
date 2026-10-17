from __future__ import annotations

import json
import re
from datetime import datetime, timezone, date
from typing import Any

from . import runtime_store
from .historical import funder_profiles

DEFAULT_SCORING = {
    "eligibility_evidence": 25,
    "thematic_alignment": 20,
    "geographic_alignment": 15,
    "donor_relationship": 15,
    "historical_outcomes": 10,
    "application_effort": 10,
    "timing_readiness": 5,
}

TRL_LEVELS = [
    {"trl":1,"stage":"Fundamental research","name":"Basic principles observed and reported","description":"Scientific research begins to translate into applied R&D; basic principles are observed and reported."},
    {"trl":2,"stage":"Fundamental research","name":"Technology concept and/or application formulated","description":"Practical applications are formulated from observed principles; work is primarily analytical."},
    {"trl":3,"stage":"Research / proof of concept","name":"Analytical and experimental proof of concept","description":"Active R&D validates critical functions through analysis, laboratory studies or experiments."},
    {"trl":4,"stage":"Technology development","name":"Component validation in a laboratory environment","description":"Basic components are integrated and validated together in a laboratory environment."},
    {"trl":5,"stage":"Technology development","name":"Component validation in a relevant or simulated environment","description":"Integrated components are tested in an environment that more closely represents intended use."},
    {"trl":6,"stage":"Technology demonstration","name":"System/subsystem prototype demonstration in a relevant or simulated environment","description":"A near-desired configuration or prototype is demonstrated in a relevant or simulated operational environment."},
    {"trl":7,"stage":"Technology demonstration","name":"Prototype demonstration in an operational environment","description":"A prototype at or near planned operational configuration is demonstrated in a real-world operational environment."},
    {"trl":8,"stage":"System complete / qualification","name":"Actual technology completed and qualified through tests and demonstrations","description":"The final technology has been proven to work under expected conditions and is qualified for intended use."},
    {"trl":9,"stage":"Operational deployment","name":"Actual technology proven through successful deployment","description":"The final technology is successfully used in real-life operational conditions."},
]
TRL_SOURCE = "https://ised-isde.canada.ca/site/innovation-canada/en/technology-readiness-levels"
TRL_NASA_SOURCE = "https://www.nasa.gov/aeronautics/technology-readiness-levels-demystified/"

ROLE_PERMISSIONS = {
    "Administrator": {"read","write_projects","write_opportunities","write_pipeline","write_admin","write_decisions","import_history"},
    "Fundraising Manager": {"read","write_projects","write_opportunities","write_pipeline","write_decisions","write_settings","import_history"},
    "Analyst": {"read","write_opportunities"},
    "Project Manager": {"read","write_projects","write_opportunities"},
    "Read-only Viewer": {"read"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema() -> None:
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
        c.execute('''CREATE TABLE IF NOT EXISTS scoring_configurations (
            id INTEGER PRIMARY KEY CHECK(id=1),
            weights_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS funding_opportunities_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            country TEXT NOT NULL,
            wash_theme TEXT NOT NULL,
            beneficiaries TEXT,
            project_description TEXT,
            funding_requirement REAL NOT NULL DEFAULT 0,
            expected_application_effort REAL NOT NULL DEFAULT 0,
            potential_donor TEXT,
            relationship_status TEXT,
            eligibility_requirements TEXT,
            submission_deadline TEXT,
            evidence_links TEXT,
            trl INTEGER,
            funding_stage TEXT NOT NULL DEFAULT 'Prospecting',
            score REAL NOT NULL DEFAULT 0,
            priority TEXT NOT NULL DEFAULT 'Low',
            eligibility_status TEXT NOT NULL DEFAULT 'Eligibility Unverified',
            score_json TEXT NOT NULL DEFAULT '{}',
            unknown_json TEXT NOT NULL DEFAULT '[]',
            risks_json TEXT NOT NULL DEFAULT '[]',
            recommendations_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS wash_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            country TEXT NOT NULL,
            community TEXT,
            beneficiaries INTEGER,
            intervention TEXT,
            total_budget REAL NOT NULL DEFAULT 0,
            existing_funding REAL NOT NULL DEFAULT 0,
            implementation_period TEXT,
            priority TEXT NOT NULL DEFAULT 'Medium',
            readiness TEXT NOT NULL DEFAULT 'Planning',
            trl INTEGER,
            owner TEXT,
            milestones TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS project_funding_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            opportunity_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(project_id, opportunity_id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS fundraising_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            opportunity_id INTEGER,
            title TEXT NOT NULL,
            owner TEXT,
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            role TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        )''')
        if not c.execute("SELECT id FROM scoring_configurations WHERE id=1").fetchone():
            c.execute("INSERT INTO scoring_configurations(id,weights_json,updated_at) VALUES(1,?,?)", (json.dumps(DEFAULT_SCORING),_now()))
        if not c.execute("SELECT id FROM user_profiles LIMIT 1").fetchone():
            c.execute("INSERT INTO user_profiles(display_name,role,active,created_at,updated_at) VALUES(?,?,?,?,?)", ("Demo Administrator","Administrator",1,_now(),_now()))
        c.commit()


def audit(action: str, entity_type: str, entity_id: Any=None, details: Any=None, role: str="Administrator", actor: str="Demo User") -> None:
    ensure_schema()
    with runtime_store._conn() as c:
        c.execute("INSERT INTO audit_logs(actor,role,action,entity_type,entity_id,details,created_at) VALUES(?,?,?,?,?,?,?)",
                  (actor,role,action,entity_type,str(entity_id) if entity_id is not None else None,json.dumps(details,default=str) if details is not None else None,_now()))
        c.commit()


def permissions(role: str) -> set[str]:
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["Read-only Viewer"])


def role_info() -> dict[str, Any]:
    return {"roles":[{"role":r,"permissions":sorted(p)} for r,p in ROLE_PERMISSIONS.items()],"note":"Hackathon build enforces selected roles server-side through an API role header. Production deployment should replace the demo identity selector with organizational SSO/OIDC."}


def get_scoring() -> dict[str, Any]:
    ensure_schema()
    with runtime_store._conn() as c:
        row=c.execute("SELECT * FROM scoring_configurations WHERE id=1").fetchone()
    return {"weights":json.loads(row["weights_json"]),"updated_at":row["updated_at"],"sum":sum(json.loads(row["weights_json"]).values())}


def set_scoring(weights: dict[str, Any], role: str="Administrator") -> dict[str, Any]:
    ensure_schema()
    clean={k:float(weights.get(k,0)) for k in DEFAULT_SCORING}
    total=sum(clean.values())
    if abs(total-100)>0.01:
        raise ValueError(f"Scoring weights must total 100; received {total:g}")
    with runtime_store._conn() as c:
        c.execute("UPDATE scoring_configurations SET weights_json=?,updated_at=? WHERE id=1",(json.dumps(clean),_now()))
        c.commit()
    audit("update","scoring_configuration",1,clean,role)
    return get_scoring()


def _relationship_score(status: str | None) -> float:
    s=(status or "").strip().lower()
    if any(k in s for k in ("active","warm","strong","existing")): return 100
    if any(k in s for k in ("lapsed","known","medium")): return 65
    if any(k in s for k in ("cold","none","unknown")): return 35
    return 50


def _historical_score(donor: str | None) -> tuple[float,str]:
    if not donor: return 50,"No donor selected; neutral historical score."
    match=next((x for x in funder_profiles() if str(x.get("funder_name") or "").lower()==donor.lower()),None)
    if not match: return 50,"No exact donor match in the synthetic history; neutral score."
    cash=float(match.get("cash_conversion_rate") or 0)
    return max(10,min(100,cash*1.5+25)), f"Historical cash conversion for this synthetic funder is {cash:.1f}% across n={match.get('application_count',0)} records."


def _timing_score(deadline: str | None) -> tuple[float,str]:
    if not deadline: return 40,"No deadline supplied."
    try:
        d=date.fromisoformat(deadline)
        days=(d-date.today()).days
    except Exception:
        return 40,"Deadline could not be parsed."
    if days<0: return 0,"Deadline has passed."
    if days<7: return 20,f"Only {days} days remain."
    if days<21: return 55,f"{days} days remain; timeline is tight."
    if days<45: return 80,f"{days} days remain."
    return 100,f"{days} days remain; timeline is comfortable."


def _trl_requirement(text: str) -> tuple[int,int] | None:
    t=(text or "").lower().replace("–","-").replace("—","-")
    m=re.search(r"trl(?:s)?\s*(\d)\s*(?:-|to|through)\s*(\d)",t)
    if m:
        a,b=int(m.group(1)),int(m.group(2)); return (min(a,b),max(a,b))
    m=re.search(r"trl(?:s)?\s*(\d)",t)
    if m:
        v=int(m.group(1)); return (v,v)
    return None

def score_opportunity(payload: dict[str, Any], active_countries: set[str]) -> dict[str, Any]:
    cfg=get_scoring()["weights"]
    unknown=[]; risks=[]; recommendations=[]
    eligibility_text=str(payload.get("eligibility_requirements") or "").strip()
    evidence=str(payload.get("evidence_links") or "").strip()
    if not eligibility_text or not evidence:
        eligibility=20 if (eligibility_text or evidence) else 0
        unknown.append("Essential eligibility evidence is incomplete.")
        recommendations.append("Add a first-party eligibility source and quote before treating this opportunity as verified.")
        eligibility_status="Eligibility Unverified"
    else:
        eligibility=90
        eligibility_status="Eligibility Evidence Present"
    trl_req=_trl_requirement(eligibility_text)
    trl=payload.get("trl")
    if trl_req:
        lo,hi=trl_req
        if not trl:
            eligibility=min(eligibility,20)
            eligibility_status="Eligibility Unverified"
            unknown.append(f"The eligibility text appears to require TRL {lo}{'-'+str(hi) if hi!=lo else ''}, but the project TRL has not been entered.")
            recommendations.append("Assess and document the project Technology Readiness Level before eligibility is confirmed.")
        elif not (lo <= int(trl) <= hi):
            eligibility=0
            eligibility_status="Eligibility Conflict"
            risks.append(f"The entered TRL {trl} does not meet the apparent funder requirement TRL {lo}{'-'+str(hi) if hi!=lo else ''}.")
        else:
            recommendations.append(f"TRL criterion appears satisfied: project TRL {trl} is within the stated TRL {lo}{'-'+str(hi) if hi!=lo else ''} range. Verify the exact wording in the first-party source.")
    theme=str(payload.get("wash_theme") or "").lower()
    thematic=100 if any(x in theme for x in ("wash","water","sanitation","hygiene","climate","health","gender")) else 65
    country=str(payload.get("country") or "")
    geographic=100 if country in active_countries else 0
    if geographic==0:
        risks.append("Project country is not in the active WaterAid target-country scope.")
    relationship=_relationship_score(payload.get("relationship_status"))
    historical,hist_note=_historical_score(payload.get("potential_donor"))
    effort=float(payload.get("expected_application_effort") or 0)
    if effort<=8: effort_score=100
    elif effort<=24: effort_score=85
    elif effort<=60: effort_score=65
    elif effort<=120: effort_score=40
    else: effort_score=20
    timing,timing_note=_timing_score(payload.get("submission_deadline"))
    components={
        "eligibility_evidence":{"score":eligibility,"weight":cfg["eligibility_evidence"],"note":eligibility_status},
        "thematic_alignment":{"score":thematic,"weight":cfg["thematic_alignment"],"note":"Rule-based match to WASH/core-adjacent terms."},
        "geographic_alignment":{"score":geographic,"weight":cfg["geographic_alignment"],"note":f"{country} {'is' if geographic else 'is not'} in the active target-country scope."},
        "donor_relationship":{"score":relationship,"weight":cfg["donor_relationship"],"note":f"Relationship entered as {payload.get('relationship_status') or 'Unknown'}."},
        "historical_outcomes":{"score":historical,"weight":cfg["historical_outcomes"],"note":hist_note},
        "application_effort":{"score":effort_score,"weight":cfg["application_effort"],"note":f"Expected fundraising effort: {effort:g} hours."},
        "timing_readiness":{"score":timing,"weight":cfg["timing_readiness"],"note":timing_note},
    }
    score=sum(v["score"]*v["weight"]/100 for v in components.values())
    if eligibility_status=="Eligibility Unverified": priority="Eligibility Unverified"
    elif eligibility_status=="Eligibility Conflict": priority="Low"
    elif geographic==0: priority="Low"
    elif score>=75: priority="High"
    elif score>=55: priority="Medium"
    else: priority="Low"
    if trl:
        level=next((x for x in TRL_LEVELS if x["trl"]==int(trl)),None)
        if level:
            recommendations.append(f"Technology maturity: TRL {trl} — {level['name']}. Treat TRL as an eligibility criterion only when the funder explicitly specifies a TRL range.")
    if effort>60: risks.append("High fundraising effort may crowd out other applications; scenario-test staff capacity before pursuing.")
    if timing<55: risks.append(timing_note)
    if not risks: risks.append("No major rule-based risk detected; current donor eligibility and deadline still require source verification.")
    return {"score":round(score,1),"priority":priority,"eligibility_status":eligibility_status,"components":components,"unknown":unknown,"risks":risks,"recommendations":recommendations}


def _row_to_opp(r) -> dict[str, Any]:
    d=dict(r)
    d["score_breakdown"] = json.loads(d.pop("score_json") or "{}")
    d["unknown"] = json.loads(d.pop("unknown_json") or "[]")
    d["risks"] = json.loads(d.pop("risks_json") or "[]")
    d["recommendations"] = json.loads(d.pop("recommendations_json") or "[]")
    return d


def list_opportunities() -> list[dict[str, Any]]:
    ensure_schema()
    with runtime_store._conn() as c:
        return [_row_to_opp(r) for r in c.execute("SELECT * FROM funding_opportunities_user ORDER BY updated_at DESC,id DESC")]


def create_opportunity(payload: dict[str, Any], active_countries: set[str], role: str="Administrator") -> dict[str, Any]:
    ensure_schema(); scored=score_opportunity(payload,active_countries); now=_now()
    fields={
        "project_name":payload.get("project_name"),"country":payload.get("country"),"wash_theme":payload.get("wash_theme"),
        "beneficiaries":payload.get("beneficiaries"),"project_description":payload.get("project_description"),
        "funding_requirement":float(payload.get("funding_requirement") or 0),"expected_application_effort":float(payload.get("expected_application_effort") or 0),
        "potential_donor":payload.get("potential_donor"),"relationship_status":payload.get("relationship_status"),
        "eligibility_requirements":payload.get("eligibility_requirements"),"submission_deadline":payload.get("submission_deadline"),
        "evidence_links":payload.get("evidence_links"),"trl":payload.get("trl"),"funding_stage":payload.get("funding_stage") or "Prospecting",
        "score":scored["score"],"priority":scored["priority"],"eligibility_status":scored["eligibility_status"],
        "score_json":json.dumps(scored["components"]),"unknown_json":json.dumps(scored["unknown"]),"risks_json":json.dumps(scored["risks"]),
        "recommendations_json":json.dumps(scored["recommendations"]),"created_at":now,"updated_at":now,
    }
    with runtime_store._conn() as c:
        cur=c.execute('''INSERT INTO funding_opportunities_user(project_name,country,wash_theme,beneficiaries,project_description,
          funding_requirement,expected_application_effort,potential_donor,relationship_status,eligibility_requirements,
          submission_deadline,evidence_links,trl,funding_stage,score,priority,eligibility_status,score_json,unknown_json,risks_json,
          recommendations_json,created_at,updated_at) VALUES(:project_name,:country,:wash_theme,:beneficiaries,:project_description,
          :funding_requirement,:expected_application_effort,:potential_donor,:relationship_status,:eligibility_requirements,
          :submission_deadline,:evidence_links,:trl,:funding_stage,:score,:priority,:eligibility_status,:score_json,:unknown_json,
          :risks_json,:recommendations_json,:created_at,:updated_at)''',fields)
        oid=cur.lastrowid;c.commit(); row=c.execute("SELECT * FROM funding_opportunities_user WHERE id=?",(oid,)).fetchone()
    audit("create","funding_opportunity",oid,{"project_name":fields["project_name"],"score":scored["score"]},role)
    return _row_to_opp(row)


def delete_opportunity(oid: int, role: str="Administrator") -> bool:
    ensure_schema()
    with runtime_store._conn() as c:
        cur=c.execute("DELETE FROM funding_opportunities_user WHERE id=?",(oid,));c.commit()
    if cur.rowcount: audit("delete","funding_opportunity",oid,None,role)
    return cur.rowcount>0


def list_projects() -> list[dict[str, Any]]:
    ensure_schema()
    with runtime_store._conn() as c:
        rows=[]
        for r in c.execute("SELECT * FROM wash_projects ORDER BY updated_at DESC,id DESC"):
            d=dict(r); d["funding_gap"]=max(0,float(d.get("total_budget") or 0)-float(d.get("existing_funding") or 0))
            d["linked_opportunities"]=[x[0] for x in c.execute("SELECT opportunity_id FROM project_funding_links WHERE project_id=?",(d["id"],))]
            rows.append(d)
        return rows


def create_project(payload: dict[str, Any], role: str="Administrator") -> dict[str, Any]:
    ensure_schema();now=_now()
    data={
        "title":payload.get("title"),"country":payload.get("country"),"community":payload.get("community"),
        "beneficiaries":int(payload.get("beneficiaries") or 0),"intervention":payload.get("intervention"),
        "total_budget":float(payload.get("total_budget") or 0),"existing_funding":float(payload.get("existing_funding") or 0),
        "implementation_period":payload.get("implementation_period"),"priority":payload.get("priority") or "Medium",
        "readiness":payload.get("readiness") or "Planning","trl":payload.get("trl"),"owner":payload.get("owner"),
        "milestones":payload.get("milestones"),"created_at":now,"updated_at":now
    }
    with runtime_store._conn() as c:
        cur=c.execute('''INSERT INTO wash_projects(title,country,community,beneficiaries,intervention,total_budget,existing_funding,
          implementation_period,priority,readiness,trl,owner,milestones,created_at,updated_at)
          VALUES(:title,:country,:community,:beneficiaries,:intervention,:total_budget,:existing_funding,:implementation_period,
          :priority,:readiness,:trl,:owner,:milestones,:created_at,:updated_at)''',data)
        pid=cur.lastrowid;c.commit()
    audit("create","wash_project",pid,{"title":data["title"]},role)
    return next(x for x in list_projects() if x["id"]==pid)


def patch_project(pid: int, changes: dict[str, Any], role: str="Administrator") -> dict[str, Any] | None:
    ensure_schema(); allowed={"title","country","community","beneficiaries","intervention","total_budget","existing_funding","implementation_period","priority","readiness","trl","owner","milestones"}
    valid={k:v for k,v in changes.items() if k in allowed and v is not None}
    if not valid:return None
    valid["updated_at"]=_now(); sets=",".join(f"{k}=?" for k in valid);vals=list(valid.values())+[pid]
    with runtime_store._conn() as c:
        c.execute(f"UPDATE wash_projects SET {sets} WHERE id=?",vals);c.commit()
    audit("update","wash_project",pid,valid,role)
    return next((x for x in list_projects() if x["id"]==pid),None)


def delete_project(pid: int, role: str="Administrator") -> bool:
    ensure_schema()
    with runtime_store._conn() as c:
        c.execute("DELETE FROM project_funding_links WHERE project_id=?",(pid,))
        cur=c.execute("DELETE FROM wash_projects WHERE id=?",(pid,));c.commit()
    if cur.rowcount:audit("delete","wash_project",pid,None,role)
    return cur.rowcount>0


def link_project(project_id: int, opportunity_id: int, role: str="Administrator") -> dict[str, Any]:
    ensure_schema()
    with runtime_store._conn() as c:
        c.execute("INSERT OR IGNORE INTO project_funding_links(project_id,opportunity_id,created_at) VALUES(?,?,?)",(project_id,opportunity_id,_now()));c.commit()
    audit("link","project_funding_link",f"{project_id}:{opportunity_id}",None,role)
    return {"project_id":project_id,"opportunity_id":opportunity_id,"linked":True}


def scenario(opportunity_ids: list[int], staff_hour_limit: float) -> dict[str, Any]:
    opps=[x for x in list_opportunities() if x["id"] in set(opportunity_ids)]
    hours=sum(float(x.get("expected_application_effort") or 0) for x in opps)
    requested=sum(float(x.get("funding_requirement") or 0) for x in opps)
    weighted=sum(float(x.get("funding_requirement") or 0)*(float(x.get("score") or 0)/100) for x in opps)
    return {"opportunity_count":len(opps),"total_requested_cad":requested,"staff_hours":hours,"staff_hour_limit":staff_hour_limit,
            "fits_staff_capacity":hours<=staff_hour_limit,"score_weighted_coverage_indicator_cad":round(weighted,2),
            "warning":"The score-weighted coverage indicator is a planning heuristic, not expected guaranteed funding or a validated probability."}


def executive_report(historical_analytics: dict[str, Any], public_opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    m=historical_analytics["metrics"]
    projects=list_projects(); useropps=list_opportunities()
    high=[x for x in useropps if x.get("priority")=="High"]
    pursue=[x for x in public_opportunities if x.get("decision") in ("PURSUE","PURSUE-QUEUE")]
    risks=[]
    if m.get("lost_application_effort_hours",0)>0:risks.append(f"{m['lost_application_effort_hours']:,.0f} fundraising hours were spent historically on Lost or Ineligible applications in the synthetic demonstration data.")
    if any(x.get("eligibility_status")=="Eligibility Unverified" for x in useropps):risks.append("One or more user-entered opportunities still have unverified eligibility evidence.")
    if not risks:risks.append("No major rule-based portfolio risk flagged; current donor eligibility and deadlines still require evidence verification.")
    return {
        "generated_at":_now(),"synthetic_notice":"Historical fundraising metrics use synthetic hackathon data, not WaterAid records.",
        "current_position":{
            "historical_applications":m.get("total_applications"),"historical_awarded_cad":m.get("total_awarded_cad"),
            "active_projects":len(projects),"user_scored_opportunities":len(useropps),"high_priority_user_opportunities":len(high),
            "verified_public_pursue_queue":len(pursue),
        },
        "historical_trends":{
            "stage_success_rate":m.get("stage_success_rate"),"cash_conversion_rate":m.get("funding_conversion_rate"),
            "awarded_per_hour":m.get("awarded_per_fundraising_hour"),"lost_effort_hours":m.get("lost_application_effort_hours"),
        },
        "best_supported_opportunities":[{"funder":x.get("funder_name"),"title":x.get("title"),"decision":x.get("decision"),"fit":x.get("fit_score")} for x in pursue[:5]],
        "risks":risks,
        "priority_recommendations":[
            "Verify hard eligibility and access before allocating proposal hours.",
            "Prioritize Canadian funders whose eligible geography overlaps active WaterAid countries.",
            "Use historical effort-efficiency evidence as context, not as a prediction of future awards.",
            "Protect staff capacity by scenario-testing high-effort proposals before pursuit.",
            "Keep evidence, retrieval dates, unknowns and human decisions attached to each brief."
        ],
        "action_plan":{
            "30_days":["Resolve REVIEW opportunities and verify open-call access.","Confirm country scope and planning assumptions."],
            "60_days":["Advance strongest verified prospects into cultivation/application stages.","Compare actual staff effort with planning assumptions."],
            "90_days":["Calibrate scoring using human decision logs and outcomes.","Review source freshness, duplicate funders and data quality issues."],
        }
    }


def audit_logs(limit: int=100) -> list[dict[str,Any]]:
    ensure_schema()
    with runtime_store._conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?",(limit,))]

def patch_opportunity(oid: int, changes: dict[str, Any], active_countries: set[str], role: str="Administrator") -> dict[str, Any] | None:
    ensure_schema()
    current = next((x for x in list_opportunities() if x["id"]==oid), None)
    if not current:
        return None
    allowed={"project_name","country","wash_theme","beneficiaries","project_description","funding_requirement","expected_application_effort","potential_donor","relationship_status","eligibility_requirements","submission_deadline","evidence_links","trl","funding_stage"}
    merged={k:current.get(k) for k in allowed}
    for k,v in changes.items():
        if k in allowed and v is not None:
            merged[k]=v
    scored=score_opportunity(merged,active_countries)
    valid={k:v for k,v in merged.items() if k in allowed}
    valid.update({
        "score":scored["score"],"priority":scored["priority"],"eligibility_status":scored["eligibility_status"],
        "score_json":json.dumps(scored["components"]),"unknown_json":json.dumps(scored["unknown"]),
        "risks_json":json.dumps(scored["risks"]),"recommendations_json":json.dumps(scored["recommendations"]),
        "updated_at":_now(),
    })
    sets=",".join(f"{k}=?" for k in valid)
    vals=list(valid.values())+[oid]
    with runtime_store._conn() as c:
        c.execute(f"UPDATE funding_opportunities_user SET {sets} WHERE id=?",vals);c.commit()
        row=c.execute("SELECT * FROM funding_opportunities_user WHERE id=?",(oid,)).fetchone()
    audit("update","funding_opportunity",oid,{"score":scored["score"]},role)
    return _row_to_opp(row) if row else None
