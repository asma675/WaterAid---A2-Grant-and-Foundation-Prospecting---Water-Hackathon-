from __future__ import annotations
import asyncio
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .security import SecurityHeadersMiddleware, RateLimitMiddleware
from .models import (
    ScanRequest, ScanResponse, OpportunitySummary, RankItem,
    RagQuery, ResearchRequest, PipelineCreate, PipelinePatch, DecisionCreate,
    CountryCreate, CountryPatch, PlanningSettingsPatch, BriefOverridePatch,
    DataIssueCreate, DataIssuePatch, HistoricalImportRequest, UserOpportunityCreate, ProjectCreate, ProjectPatch, ProjectLinkCreate, ScenarioRequest, ScoringConfigPatch, AdvisorRequest, UserOpportunityPatch,
)
from .agents import AGENTS, run_scan
from .engine import public_opportunities
from .ranking import ranking_items
from .rag import search as rag_search
from .providers import provider_status, run_provider
from . import data_store, pipeline, decision_log, runtime_store, historical, workspace

app=FastAPI(title="GrantCurrent API", version="0.7.0", docs_url="/docs" if settings.app_env!="production" else None)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET","POST","PATCH","DELETE"],
    allow_headers=["Content-Type","X-Request-ID"],
)

@app.get("/health")
def health():
    active=runtime_store.list_countries(data_store.wateraid_target_countries(), include_inactive=False)
    return {
        "status":"ok",
        "version":"0.7.0",
        "demo_mode":settings.demo_mode,
        "live_fetch_enabled":settings.live_fetch_enabled,
        "public_source_count":len(data_store.public_sources()),
        "public_opportunity_count":len(data_store.public_opportunities()),
        "public_funder_count":len(data_store.public_funders()),
        "gift_signal_count":len(data_store.gift_signals()),
        "public_contact_count":len(data_store.public_contacts()),
        "active_target_country_count":len(active),
        "historical_application_count":len(historical.all_rows()),
        "user_opportunity_count":len(workspace.list_opportunities()),
        "project_count":len(workspace.list_projects()),
    }

@app.get("/api/v1/agents")
def agents():
    return {
        "agents":AGENTS,
        "provider_strategy":"Canadian-funder-only workflow for configurable WaterAid target countries. Local RAG plus optional OpenAI, Gemini and Microsoft/Copilot research can discover candidates; only verified Canadian funders with active target-country overlap enter the ranked queue.",
    }

@app.get("/api/v1/providers")
def providers():
    return {"providers":provider_status()}

@app.get("/api/v1/target-countries")
def target_countries():
    all_rows=runtime_store.list_countries(data_store.wateraid_target_countries(), include_inactive=True)
    return {
        "countries":[x for x in all_rows if x.get("active")],
        "all_countries":all_rows,
        "profile":data_store.wateraid_live_profile(),
    }

@app.post("/api/v1/target-countries")
def target_country_create(req: CountryCreate, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_admin")
    try:
        return runtime_store.add_country(data_store.wateraid_target_countries(), req.model_dump())
    except ValueError as e:
        raise HTTPException(400,str(e))

@app.patch("/api/v1/target-countries/{country_id}")
def target_country_patch(country_id: int, req: CountryPatch, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_admin")
    row=runtime_store.patch_country(country_id, req.model_dump())
    if not row: raise HTTPException(404,"Target country not found or no changes supplied")
    return row

@app.delete("/api/v1/target-countries/{country_id}")
def target_country_delete(country_id: int, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_admin")
    if not runtime_store.delete_country(country_id): raise HTTPException(404,"Target country not found")
    return {"deleted":True,"id":country_id}

@app.get("/api/v1/planning-settings")
def planning_settings():
    return runtime_store.get_planning()

@app.patch("/api/v1/planning-settings")
def planning_settings_patch(req: PlanningSettingsPatch, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role)
    if "write_settings" not in workspace.permissions(role) and "write_admin" not in workspace.permissions(role):
        raise HTTPException(403, f"Role '{role}' cannot edit planning settings.")
    return runtime_store.patch_planning(req.model_dump())

@app.get("/api/v1/brief-overrides/{opp_id}")
def brief_override_get(opp_id: str):
    return runtime_store.get_override(opp_id)

@app.patch("/api/v1/brief-overrides/{opp_id}")
def brief_override_patch(opp_id: str, req: BriefOverridePatch, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_opportunities")
    runtime_store.set_override(opp_id, req.model_dump())
    # Return the fully recalculated brief so the UI can update immediately.
    for x in public_opportunities():
        if x.opp_id.lower()==opp_id.lower(): return x
    raise HTTPException(404,"Opportunity not found")

@app.get("/api/v1/opportunities", response_model=list[OpportunitySummary])
def opportunities():
    return public_opportunities()

@app.get("/api/v1/public-opportunities", response_model=list[OpportunitySummary])
def real_opportunities():
    return public_opportunities()

@app.get("/api/v1/opportunities/{opp_id}", response_model=OpportunitySummary)
def opportunity(opp_id: str):
    for x in public_opportunities():
        if x.opp_id.lower()==opp_id.lower():
            return x
    raise HTTPException(404,"Opportunity not found")

@app.post("/api/v1/scan", response_model=ScanResponse)
def scan(req: ScanRequest):
    return run_scan(req.query, req.max_results, include_regression_cases=False)

@app.post("/api/v1/rag/search")
def rag(req: RagQuery):
    return {"query":req.query,"hits":rag_search(req.query,top_k=req.top_k,include_synthetic=False)}

@app.post("/api/v1/research")
async def research(req: ResearchRequest):
    requested=[]; seen=set()
    for p in ["local", *req.providers]:
        p=p.lower()
        if p not in seen:
            requested.append(p); seen.add(p)
    results=await asyncio.gather(*(run_provider(p,req.query,req.max_results) for p in requested), return_exceptions=True)
    normalized=[]
    for p,r in zip(requested,results):
        if isinstance(r,Exception): normalized.append({"provider":p,"configured":True,"error":str(r)})
        else: normalized.append(r)
    return {
        "query":req.query,
        "privacy":"Only public funding research text is sent to configured external research providers. Donor, board and CRM data is excluded by design.",
        "results":normalized,
    }

@app.get("/api/v1/ranking-scenario", response_model=list[RankItem])
def ranking():
    return ranking_items()

@app.get("/api/v1/sources")
def sources(): return {"sources":data_store.sources()}

@app.get("/api/v1/public-sources")
def public_sources(): return {"sources":data_store.public_sources()}

@app.get("/api/v1/funders")
def funders(): return {"funders":data_store.public_funders()}

@app.get("/api/v1/gift-signals")
def gift_signals(): return {"signals":data_store.gift_signals()}

@app.get("/api/v1/contacts")
def contacts(): return {"contacts":data_store.public_contacts()}

@app.get("/api/v1/alerts")
def alerts():
    rows=[]
    active={x["country"] for x in runtime_store.list_countries(data_store.wateraid_target_countries(), include_inactive=False)}
    for o in data_store.public_opportunities():
        if o.get("funder_country","Canada")!="Canada" or not (set(o.get("target_countries",[])) & active): continue
        status=(o.get("status") or "").lower()
        if any(k in status for k in ("open","upcoming","ongoing")) or o.get("deadline") not in (None,"","Ongoing"):
            rows.append({
                "id":o.get("id"),"funder":o.get("funder"),"title":o.get("title"),
                "status":o.get("status"),"deadline":o.get("deadline"),"decision":o.get("decision"),
                "why":o.get("reason"),"source_url":o.get("source_url"),
            })
    return {"as_of":"2026-10-17","alerts":rows}

@app.get("/api/v1/controls")
def controls(): return {"controls":data_store.controls()}

@app.get("/api/v1/metrics")
def metrics(): return {"metrics":data_store.metrics()}

@app.get("/api/v1/live-evidence")
def live_evidence():
    return {"as_of":"2026-10-17","items":data_store.real_public_demo(),"note":"Public evidence for the hackathon demo. Re-verify first-party pages before a real submission."}

@app.get("/api/v1/decisions")
def decisions_list(): return {"items":decision_log.list_items()}

@app.post("/api/v1/decisions")
def decisions_create(req: DecisionCreate, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_decisions")
    return decision_log.add(req.model_dump())

@app.get("/api/v1/pipeline")
def pipeline_list(): return {"items":pipeline.list_items()}

@app.post("/api/v1/pipeline")
def pipeline_create(req: PipelineCreate, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_pipeline")
    return pipeline.upsert(req.model_dump())

@app.patch("/api/v1/pipeline/{item_id}")
def pipeline_patch(item_id: int, req: PipelinePatch, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_pipeline")
    row=pipeline.patch(item_id,req.model_dump())
    if not row: raise HTTPException(404,"Pipeline item not found or no changes supplied")
    return row

@app.delete("/api/v1/pipeline/{item_id}")
def pipeline_delete(item_id: int, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_pipeline")
    if not pipeline.delete(item_id): raise HTTPException(404,"Pipeline item not found")
    return {"deleted":True,"id":item_id}

@app.get("/api/v1/data-issues")
def data_issues_list(): return {"items":runtime_store.list_issues()}

@app.post("/api/v1/data-issues")
def data_issues_create(req: DataIssueCreate):
    try: return runtime_store.add_issue(req.model_dump())
    except ValueError as e: raise HTTPException(400,str(e))

@app.patch("/api/v1/data-issues/{issue_id}")
def data_issues_patch(issue_id: int, req: DataIssuePatch, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role)
    if "write_settings" not in workspace.permissions(role) and "write_admin" not in workspace.permissions(role):
        raise HTTPException(403, f"Role '{role}' cannot resolve data issues.")
    row=runtime_store.patch_issue(issue_id,req.model_dump())
    if not row: raise HTTPException(404,"Issue not found or no changes supplied")
    return row

# ---------------- v0.7 historical intelligence, opportunity planning and project workspace ----------------

def _role(x_grantcurrent_role: str | None) -> str:
    return x_grantcurrent_role or "Administrator"

def _require(role: str, permission: str) -> None:
    if permission not in workspace.permissions(role):
        raise HTTPException(403, f"Role '{role}' does not have permission '{permission}'.")

@app.get("/api/v1/roles")
def roles():
    return workspace.role_info()

@app.get("/api/v1/trl")
def trl():
    return {
        "source":"Innovation Canada / ISED",
        "source_url":workspace.TRL_SOURCE,
        "nasa_source_url":workspace.TRL_NASA_SOURCE,
        "origin_note":"NASA conceived the TRL approach in the 1970s; the widely used modern scale runs from TRL 1 to TRL 9.",
        "note":"TRL describes technology maturity, not grant probability or the administrative stage of a funding application. Use it only when a project contains a technology component or a funder explicitly specifies a TRL range.",
        "levels":workspace.TRL_LEVELS,
    }

@app.get("/api/v1/history")
def history(
    year: str | None = None, country: str | None = None, theme: str | None = None,
    funder_type: str | None = None, relationship: str | None = None, outcome: str | None = None,
    application_type: str | None = None, funder: str | None = None, q: str | None = None,
):
    filters={"year":year,"country":country,"theme":theme,"funder_type":funder_type,"relationship":relationship,
             "outcome":outcome,"application_type":application_type,"funder":funder,"q":q}
    return {"synthetic":True,"notice":historical.SYNTHETIC_NOTICE,"items":historical.filtered_rows(filters),"filter_options":historical.filter_options()}

@app.post("/api/v1/history/import")
def history_import(req: HistoricalImportRequest, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"import_history")
    result=historical.import_text(req.csv_text)
    workspace.audit("import","historical_applications",None,result,role)
    return result

@app.get("/api/v1/history/benchmarks")
def history_benchmarks():
    return historical.benchmark_check()

@app.get("/api/v1/history/analytics")
def history_analytics(
    year: str | None = None, country: str | None = None, theme: str | None = None,
    funder_type: str | None = None, relationship: str | None = None, outcome: str | None = None,
    application_type: str | None = None, funder: str | None = None, q: str | None = None,
    exclude_largest_award: bool = False,
):
    filters={"year":year,"country":country,"theme":theme,"funder_type":funder_type,"relationship":relationship,
             "outcome":outcome,"application_type":application_type,"funder":funder,"q":q}
    return historical.analytics(filters,exclude_largest_award)

@app.get("/api/v1/history/export.csv")
def history_export(
    year: str | None = None, country: str | None = None, theme: str | None = None,
    funder_type: str | None = None, relationship: str | None = None, outcome: str | None = None,
    application_type: str | None = None, funder: str | None = None, q: str | None = None,
):
    from fastapi.responses import PlainTextResponse
    filters={"year":year,"country":country,"theme":theme,"funder_type":funder_type,"relationship":relationship,
             "outcome":outcome,"application_type":application_type,"funder":funder,"q":q}
    return PlainTextResponse(historical.csv_export(filters),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=grantcurrent_history.csv"})

@app.get("/api/v1/funder-intelligence")
def funder_intelligence():
    return {"synthetic_history":True,"notice":historical.SYNTHETIC_NOTICE,"funders":historical.funder_profiles()}

@app.post("/api/v1/advisor")
def advisor(req: AdvisorRequest):
    return historical.advisor(req.question, req.exclude_largest_award)

@app.get("/api/v1/scoring-config")
def scoring_config():
    return workspace.get_scoring()

@app.patch("/api/v1/scoring-config")
def scoring_config_patch(req: ScoringConfigPatch, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_admin")
    try: return workspace.set_scoring(req.weights,role)
    except ValueError as e: raise HTTPException(400,str(e))

@app.get("/api/v1/user-opportunities")
def user_opportunities():
    return {"items":workspace.list_opportunities()}

@app.post("/api/v1/user-opportunities")
def user_opportunity_create(req: UserOpportunityCreate, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_opportunities")
    active=runtime_store.active_country_names(data_store.wateraid_target_countries())
    return workspace.create_opportunity(req.model_dump(),active,role)

@app.patch("/api/v1/user-opportunities/{opportunity_id}")
def user_opportunity_patch(opportunity_id: int, req: UserOpportunityPatch, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_opportunities")
    active=runtime_store.active_country_names(data_store.wateraid_target_countries())
    row=workspace.patch_opportunity(opportunity_id,req.model_dump(),active,role)
    if not row: raise HTTPException(404,"Opportunity not found or no changes supplied")
    return row

@app.delete("/api/v1/user-opportunities/{opportunity_id}")
def user_opportunity_delete(opportunity_id: int, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_opportunities")
    if not workspace.delete_opportunity(opportunity_id,role): raise HTTPException(404,"Opportunity not found")
    return {"deleted":True,"id":opportunity_id}

@app.get("/api/v1/projects")
def projects():
    return {"items":workspace.list_projects()}

@app.post("/api/v1/projects")
def projects_create(req: ProjectCreate, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_projects")
    return workspace.create_project(req.model_dump(),role)

@app.patch("/api/v1/projects/{project_id}")
def projects_patch(project_id: int, req: ProjectPatch, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_projects")
    row=workspace.patch_project(project_id,req.model_dump(),role)
    if not row: raise HTTPException(404,"Project not found or no changes supplied")
    return row

@app.delete("/api/v1/projects/{project_id}")
def projects_delete(project_id: int, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_projects")
    if not workspace.delete_project(project_id,role): raise HTTPException(404,"Project not found")
    return {"deleted":True,"id":project_id}

@app.post("/api/v1/project-funding-links")
def project_link(req: ProjectLinkCreate, x_grantcurrent_role: str | None = Header(default=None)):
    role=_role(x_grantcurrent_role); _require(role,"write_projects")
    return workspace.link_project(req.project_id,req.opportunity_id,role)

@app.post("/api/v1/scenario")
def scenario(req: ScenarioRequest):
    return workspace.scenario(req.opportunity_ids,req.staff_hour_limit)

@app.get("/api/v1/executive-report")
def executive_report():
    hist=historical.analytics()
    pubs=[x.model_dump() for x in public_opportunities()]
    return workspace.executive_report(hist,pubs)

@app.get("/api/v1/audit-logs")
def audit_logs(limit: int = Query(default=100,ge=1,le=500)):
    return {"items":workspace.audit_logs(limit)}
