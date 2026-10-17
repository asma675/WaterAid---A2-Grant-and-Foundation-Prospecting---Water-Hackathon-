from __future__ import annotations
import json
from typing import Any
import httpx
from .config import settings
from .rag import build_context
from . import data_store, runtime_store

# Preferred high-authority sources. Discovery is intentionally broad so unknown Canadian funders can be found;
# candidates never enter the ranked queue until jurisdiction/evidence gates verify them.
PREFERRED_DOMAINS = [
    "international.gc.ca","canada.ca","open.canada.ca","search.open.canada.ca",
    "pfc.ca","imaginecanada.ca","wateraid.org"
]


def provider_status() -> list[dict[str, Any]]:
    return [
        {"id":"local","name":"Local WaterAid RAG","configured":True,"web_search":False,"note":"Always available; retrieves Canadian-funder opportunities, WaterAid target countries, peer gifts and source evidence."},
        {"id":"openai","name":"OpenAI Web Research","configured":bool(settings.openai_api_key),"web_search":True,"note":"Optional discovery worker for Canadian funders/donors supporting WaterAid countries. Candidates still require jurisdiction and evidence verification."},
        {"id":"gemini","name":"Gemini + Google Search","configured":bool(settings.gemini_api_key),"web_search":True,"note":"Optional discovery worker instructed to return Canadian funders for WaterAid target countries only. Candidates are not auto-ranked."},
        {"id":"microsoft","name":"Microsoft / Copilot-Bing gateway","configured":bool(settings.microsoft_research_url),"web_search":True,"note":"Optional Microsoft research gateway. Canadian-funder and WaterAid-country verification remain mandatory."},
    ]


def _system_prompt() -> str:
    countries=", ".join(sorted(runtime_store.active_country_names(data_store.wateraid_target_countries())))
    return (
        "You are a funding-discovery research worker for WaterAid Canada. "
        "Find ONLY funders, donors, foundations, corporations or public funding programs based in Canada. "
        "The funded project itself should be international and should map to one or more WaterAid target countries: " + countries + ". "
        "Do not return US, UK, EU or other non-Canadian funders. Do not default to Canadian domestic water projects. "
        "Prioritize WASH, water security/scarcity, sanitation, hygiene, climate-resilient WASH, health systems, women and girls, menstrual health, gender equality and systems strengthening. "
        "For every candidate state: Canadian funder name, target country/countries, status, deadline if confirmed, amount if confirmed, applicant eligibility, access model, and first-party source URL. "
        "Clearly distinguish open calls from relationship/cultivation prospects. Never invent eligibility, deadlines, amounts, invitation status or award probability. Unknown is valid. "
        "Do not request or expose donor, board, CRM or other private relationship data."
    )


async def local_research(query: str, max_results: int = 8) -> dict[str, Any]:
    context,hits=build_context(query,top_k=max_results,max_chars=settings.rag_max_context_chars)
    return {"provider":"local","configured":True,"summary":"Local RAG retrieved Canadian-funder evidence, WaterAid country context and peer-giving history. No external model call was required.","hits":hits,"context":context}


async def openai_research(query: str, max_results: int = 8) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {"provider":"openai","configured":False,"error":"OPENAI_API_KEY is not configured"}
    body={
        "model":settings.openai_research_model,
        "tools":[{"type":"web_search","context_size":"medium"}],
        "input":f"{_system_prompt()}\n\nResearch query: {query}\nReturn the best Canadian-funder leads for WaterAid target countries, plus exclusions, with source citations."
    }
    headers={"Authorization":f"Bearer {settings.openai_api_key}","Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        r=await client.post("https://api.openai.com/v1/responses",headers=headers,json=body)
        r.raise_for_status(); data=r.json()
    text=data.get("output_text") or ""
    urls=[]; parts=[]
    for item in data.get("output",[]):
        if item.get("type")!="message": continue
        for c in item.get("content",[]):
            if c.get("text"): parts.append(c.get("text"))
            for ann in c.get("annotations",[]):
                if ann.get("type")=="url_citation" and ann.get("url"):
                    urls.append({"url":ann.get("url"),"title":ann.get("title") or ann.get("url")})
    if not text: text="\n".join(parts)
    # De-duplicate citations while preserving order.
    seen=set(); dedup=[]
    for u in urls:
        if u["url"] not in seen: seen.add(u["url"]); dedup.append(u)
    return {"provider":"openai","configured":True,"summary":text,"sources":dedup[:20]}


async def gemini_research(query: str, max_results: int = 8) -> dict[str, Any]:
    if not settings.gemini_api_key:
        return {"provider":"gemini","configured":False,"error":"GEMINI_API_KEY is not configured"}
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_research_model}:generateContent?key={settings.gemini_api_key}"
    body={
        "contents":[{"parts":[{"text":f"{_system_prompt()}\n\nResearch query: {query}\nReturn Canadian-funder prospects for WaterAid target countries with first-party sources."}]}],
        "tools":[{"google_search":{}}],
        "generationConfig":{"temperature":0.1}
    }
    async with httpx.AsyncClient(timeout=45) as client:
        r=await client.post(url,json=body)
        r.raise_for_status(); data=r.json()
    parts=[]; sources=[]
    for cand in data.get("candidates",[]):
        for p in cand.get("content",{}).get("parts",[]):
            if p.get("text"): parts.append(p["text"])
        gm=cand.get("groundingMetadata",{})
        for ch in gm.get("groundingChunks",[]):
            web=ch.get("web",{})
            if web.get("uri"): sources.append({"url":web.get("uri"),"title":web.get("title")})
    return {"provider":"gemini","configured":True,"summary":"\n".join(parts),"sources":sources[:20]}


async def microsoft_research(query: str, max_results: int = 8) -> dict[str, Any]:
    if not settings.microsoft_research_url:
        return {"provider":"microsoft","configured":False,"error":"MICROSOFT_RESEARCH_URL is not configured"}
    headers={"Content-Type":"application/json"}
    if settings.microsoft_research_token:
        headers["Authorization"]=f"Bearer {settings.microsoft_research_token}"
    payload={"query":query,"allowed_domains":[],"preferred_domains":PREFERRED_DOMAINS,"max_results":max_results,"instruction":_system_prompt()}
    async with httpx.AsyncClient(timeout=45) as client:
        r=await client.post(settings.microsoft_research_url,headers=headers,json=payload)
        r.raise_for_status(); data=r.json()
    return {"provider":"microsoft","configured":True,"summary":data.get("summary") or data.get("answer") or json.dumps(data)[:8000],"sources":data.get("sources",[])}


async def run_provider(provider: str, query: str, max_results: int = 8) -> dict[str, Any]:
    p=provider.lower()
    if p=="local": return await local_research(query,max_results)
    if p=="openai": return await openai_research(query,max_results)
    if p=="gemini": return await gemini_research(query,max_results)
    if p in {"microsoft","copilot","bing"}: return await microsoft_research(query,max_results)
    return {"provider":provider,"configured":False,"error":"Unknown provider"}
