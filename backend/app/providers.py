from __future__ import annotations
import json
from typing import Any
import httpx
from .config import settings
from .rag import build_context

# Canada-only discovery sources. External AI can discover candidate leads, but candidates
# never enter the ranked queue until the app's jurisdiction/evidence gates verify them.
ALLOWED_DOMAINS = [
    "canada.ca","open.canada.ca","search.open.canada.ca","ontario.ca",
    "td.com","watershedsecurityfund.ca","fcm.ca","greenmunicipalfund.ca",
    "communityfoundations.ca","pfc.ca"
]


def provider_status() -> list[dict[str, Any]]:
    return [
        {"id":"local","name":"Local Canadian RAG","configured":True,"web_search":False,"note":"Always available; retrieves curated Canadian freshwater opportunities, award history and source evidence."},
        {"id":"openai","name":"OpenAI Web Research","configured":bool(settings.openai_api_key),"web_search":True,"note":"Optional discovery worker restricted to approved Canadian/public domains. Candidates still require GrantCurrent verification."},
        {"id":"gemini","name":"Gemini + Google Search","configured":bool(settings.gemini_api_key),"web_search":True,"note":"Optional discovery worker instructed to return Canadian funders for projects in Canada only. Candidates are not auto-ranked."},
        {"id":"microsoft","name":"Microsoft / Copilot-Bing gateway","configured":bool(settings.microsoft_research_url),"web_search":True,"note":"Optional Microsoft research gateway. Canada-only discovery instruction and verification gate remain mandatory."},
    ]


def _system_prompt() -> str:
    return (
        "You are a funding-discovery research worker for Canadian freshwater and water-related community projects. "
        "Find ONLY funders based in Canada or Canadian public funding programs, and ONLY opportunities for projects taking place in Canada. "
        "Do not return international-development, overseas, US, UK, EU, foreign-government, or non-Canadian donor prospects. "
        "Prefer first-party Canadian government, foundation, corporate-foundation and fund pages. "
        "For every candidate, state funder/program, Canadian geography, status, deadline if confirmed, amount if confirmed, eligible applicant types, and source URL. "
        "Never invent eligibility, deadlines, amounts, invitation status, or award probability. Treat unknown as unknown. "
        "Do not request or expose donor, board, CRM or other private relationship data."
    )


async def local_research(query: str, max_results: int = 8) -> dict[str, Any]:
    context,hits=build_context(query,top_k=max_results,max_chars=settings.rag_max_context_chars)
    return {"provider":"local","configured":True,"summary":"Local Canadian RAG retrieved curated domestic freshwater funding evidence. No external model call was required.","hits":hits,"context":context}


async def openai_research(query: str, max_results: int = 8) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {"provider":"openai","configured":False,"error":"OPENAI_API_KEY is not configured"}
    body={
        "model":settings.openai_research_model,
        "tools":[{"type":"web_search","filters":{"allowed_domains":ALLOWED_DOMAINS}}],
        "input":f"{_system_prompt()}\n\nResearch query: {query}\nReturn the best Canada-only funding leads and exclusions with source citations."
    }
    headers={"Authorization":f"Bearer {settings.openai_api_key}","Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=45) as client:
        r=await client.post("https://api.openai.com/v1/responses",headers=headers,json=body)
        r.raise_for_status(); data=r.json()
    text=data.get("output_text") or ""
    urls=[]
    for item in data.get("output",[]):
        if item.get("type")!="message": continue
        for c in item.get("content",[]):
            for ann in c.get("annotations",[]):
                if ann.get("type")=="url_citation": urls.append({"url":ann.get("url"),"title":ann.get("title")})
    return {"provider":"openai","configured":True,"summary":text,"sources":urls[:20]}


async def gemini_research(query: str, max_results: int = 8) -> dict[str, Any]:
    if not settings.gemini_api_key:
        return {"provider":"gemini","configured":False,"error":"GEMINI_API_KEY is not configured"}
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_research_model}:generateContent?key={settings.gemini_api_key}"
    body={
        "contents":[{"parts":[{"text":f"{_system_prompt()}\n\nResearch query: {query}\nReturn Canada-only domestic-water funding prospects with first-party sources."}]}],
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
    payload={"query":query,"allowed_domains":ALLOWED_DOMAINS,"max_results":max_results,"instruction":_system_prompt()}
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
