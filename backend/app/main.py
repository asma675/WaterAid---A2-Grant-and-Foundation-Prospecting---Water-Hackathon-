from __future__ import annotations
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .security import SecurityHeadersMiddleware, RateLimitMiddleware
from .models import (
    ScanRequest, ScanResponse, OpportunitySummary, RankItem,
    RagQuery, ResearchRequest, PipelineCreate, PipelinePatch, DecisionCreate,
)
from .agents import AGENTS, run_scan
from .engine import all_opportunities, public_opportunities
from .ranking import ranking_items
from .rag import search as rag_search
from .providers import provider_status, run_provider
from . import data_store, pipeline, decision_log

app=FastAPI(title="GrantCurrent API", version="0.3.0", docs_url="/docs" if settings.app_env!="production" else None)
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
    return {
        "status":"ok",
        "version":"0.3.0",
        "demo_mode":settings.demo_mode,
        "live_fetch_enabled":settings.live_fetch_enabled,
        "public_source_count":len(data_store.public_sources()),
        "public_opportunity_count":len(data_store.public_opportunities()),
        "public_funder_count":len(data_store.public_funders()),
        "gift_signal_count":len(data_store.gift_signals()),
        "public_contact_count":len(data_store.public_contacts()),
    }

@app.get("/api/v1/agents")
def agents():
    return {
        "agents":AGENTS,
        "provider_strategy":"Canada-only domestic funding workflow. Local RAG plus optional OpenAI, Gemini and Microsoft/Copilot research can discover candidates; only verified Canadian funders for projects in Canada enter the ranked queue.",
    }

@app.get("/api/v1/providers")
def providers():
    return {"providers":provider_status()}

@app.get("/api/v1/opportunities", response_model=list[OpportunitySummary])
def opportunities():
    # Live API is Canada-only. Synthetic challenge cases remain internal regression fixtures.
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
    # Public scan never mixes synthetic/international challenge fixtures into live results.
    return run_scan(req.query, req.max_results, include_regression_cases=False)

@app.post("/api/v1/rag/search")
def rag(req: RagQuery):
    return {"query":req.query,"hits":rag_search(req.query,top_k=req.top_k,include_synthetic=False)}

@app.post("/api/v1/research")
async def research(req: ResearchRequest):
    requested=[]
    seen=set()
    for p in ["local", *req.providers]:
        p=p.lower()
        if p not in seen:
            requested.append(p); seen.add(p)
    results=await asyncio.gather(*(run_provider(p,req.query,req.max_results) for p in requested), return_exceptions=True)
    normalized=[]
    for p,r in zip(requested,results):
        if isinstance(r,Exception):
            normalized.append({"provider":p,"configured":True,"error":str(r)})
        else:
            normalized.append(r)
    return {
        "query":req.query,
        "privacy":"Only public funding research text is sent to configured external research providers. Donor, board and CRM data is excluded by design.",
        "results":normalized,
    }

@app.get("/api/v1/ranking-scenario", response_model=list[RankItem])
def ranking():
    return ranking_items()

@app.get("/api/v1/sources")
def sources():
    return {"sources":data_store.sources()}

@app.get("/api/v1/public-sources")
def public_sources():
    return {"sources":data_store.public_sources()}

@app.get("/api/v1/funders")
def funders():
    return {"funders":data_store.public_funders()}

@app.get("/api/v1/gift-signals")
def gift_signals():
    return {"signals":data_store.gift_signals()}

@app.get("/api/v1/contacts")
def contacts():
    return {"contacts":data_store.public_contacts()}

@app.get("/api/v1/alerts")
def alerts():
    # Hackathon alert center: derives actionable watch items from the current public registry.
    rows=[]
    for o in data_store.public_opportunities():
        status=(o.get("status") or "").lower()
        if any(k in status for k in ("open","upcoming","ongoing")) or o.get("deadline") not in (None,"","Ongoing"):
            rows.append({
                "id":o.get("id"),"funder":o.get("funder"),"title":o.get("title"),
                "status":o.get("status"),"deadline":o.get("deadline"),"decision":o.get("decision"),
                "why":o.get("reason"),"source_url":o.get("source_url"),
            })
    return {"as_of":"2026-10-17","alerts":rows}

@app.get("/api/v1/controls")
def controls():
    return {"controls":data_store.controls()}

@app.get("/api/v1/metrics")
def metrics():
    return {"metrics":data_store.metrics()}

@app.get("/api/v1/live-evidence")
def live_evidence():
    return {
        "as_of":"2026-10-17",
        "items":data_store.real_public_demo(),
        "note":"Public Government of Canada evidence for the hackathon demo. Re-verify first-party pages before a real submission.",
    }


@app.get("/api/v1/decisions")
def decisions_list():
    return {"items":decision_log.list_items()}

@app.post("/api/v1/decisions")
def decisions_create(req: DecisionCreate):
    return decision_log.add(req.model_dump())

@app.get("/api/v1/pipeline")
def pipeline_list():
    return {"items":pipeline.list_items()}

@app.post("/api/v1/pipeline")
def pipeline_create(req: PipelineCreate):
    return pipeline.upsert(req.model_dump())

@app.patch("/api/v1/pipeline/{item_id}")
def pipeline_patch(item_id: int, req: PipelinePatch):
    row=pipeline.patch(item_id,req.model_dump())
    if not row:
        raise HTTPException(404,"Pipeline item not found or no changes supplied")
    return row

@app.delete("/api/v1/pipeline/{item_id}")
def pipeline_delete(item_id: int):
    if not pipeline.delete(item_id):
        raise HTTPException(404,"Pipeline item not found")
    return {"deleted":True,"id":item_id}
