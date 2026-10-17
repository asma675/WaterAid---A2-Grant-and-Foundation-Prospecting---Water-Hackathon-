from __future__ import annotations
import math
import re
from dataclasses import dataclass
from typing import Any
from . import data_store, runtime_store

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.-]{1,}")
STOP = {
    "the","and","for","with","from","that","this","are","was","were","have","has","had","into","their","they","them","you","your","our","its","but","not","can","will","all","any","per","via","how","what","when","where","who","why","about","more","than","only","also","use","using"
}


def tokens(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall((text or "").lower()) if t not in STOP and len(t) > 2]


@dataclass
class Doc:
    id: str
    title: str
    text: str
    url: str | None
    kind: str
    metadata: dict[str, Any]


def corpus() -> list[Doc]:
    docs: list[Doc] = []
    profile=data_store.wateraid_live_profile()
    active_rows=runtime_store.list_countries(data_store.wateraid_target_countries(), include_inactive=False)
    active={x["country"] for x in active_rows}
    docs.append(Doc("WATERAID-PROFILE","WaterAid Canada prospecting profile", " ".join([
        profile.get("organization",""), profile.get("funder_constraint",""),
        "Configured active project countries: "+", ".join(sorted(active)),
        " ".join(profile.get("strategy_focus",[]))
    ]), "https://www.wateraid.org/ca/where-we-work", "organization_profile", profile))
    for c in active_rows:
        docs.append(Doc("COUNTRY-"+c.get("country","").upper().replace(" ","-"), c.get("country","")+" — active WaterAid target country",
                        " ".join([c.get("country",""),c.get("region",""),"WaterAid WASH target country"]), c.get("source_url") or "https://www.wateraid.org/ca/where-we-work", "target_country", c))
    for s in data_store.public_sources():
        text = " ".join([s.get("name", ""), s.get("category", ""), s.get("use_for", ""), s.get("notes", ""), " ".join(s.get("tags", [])), s.get("access", "")])
        docs.append(Doc(s["id"], s["name"], text, s.get("url"), "public_source", s))
    for o in data_store.public_opportunities():
        if o.get("funder_country","Canada")!="Canada" or not (set(o.get("target_countries",[])) & active):
            continue
        text = " ".join([o.get("funder", ""), o.get("title", ""), o.get("status", ""), o.get("deadline", ""), o.get("amount", ""), o.get("geography", ""), " ".join(o.get("target_countries", [])), " ".join(o.get("themes", [])), o.get("reason", ""), o.get("next_action", ""), o.get("evidence", "")])
        docs.append(Doc(o["id"], f'{o.get("funder")}: {o.get("title")}', text, o.get("source_url"), "public_opportunity", o))
    for f in data_store.public_funders():
        text = " ".join([f.get("name", ""), f.get("type", ""), f.get("status", ""), f.get("geography", ""), " ".join(f.get("themes", [])), f.get("access", ""), f.get("why", "")])
        docs.append(Doc(f["id"], f["name"], text, f.get("program_url") or f.get("website"), "funder_profile", f))
    for i, c in enumerate(data_store.public_contacts(), 1):
        text = " ".join([c.get("funder", ""), c.get("name", ""), c.get("role", ""), c.get("contact_type", ""), c.get("channel", ""), c.get("source_note", "")])
        docs.append(Doc(f"CONTACT-{i:03d}", f'{c.get("funder")} — {c.get("name")}', text, c.get("url"), "public_contact", c))
    for i, g in enumerate(data_store.gift_signals(), 1):
        # Keep Canadian-funder award history; country filtering happens at query/result use.
        text = " ".join([g.get("funder", ""), g.get("recipient", ""), g.get("year", ""), g.get("theme", ""), g.get("country", ""), g.get("evidence", "")])
        docs.append(Doc(f"GIFT-{i:03d}", f'{g.get("funder")} → {g.get("recipient")}', text, g.get("source_url"), "gift_signal", g))
    return docs


def _stats(docs: list[Doc]):
    dfs: dict[str, int] = {}; lengths=[]
    for d in docs:
        ts=tokens(d.text); lengths.append(len(ts))
        for t in set(ts): dfs[t]=dfs.get(t,0)+1
    return dfs, (sum(lengths)/max(1,len(lengths)))


def search(query: str, top_k: int = 8, include_synthetic: bool = True) -> list[dict[str, Any]]:
    q=tokens(query)
    if not q: return []
    docs=corpus(); dfs,avgdl=_stats(docs); N=len(docs); out=[]
    for d in docs:
        dt=tokens(d.text)
        if not dt: continue
        freqs={}
        for t in dt: freqs[t]=freqs.get(t,0)+1
        score=0.0
        for term in q:
            tf=freqs.get(term,0)
            if not tf: continue
            df=dfs.get(term,0); idf=math.log(1+(N-df+0.5)/(df+0.5)); k1,b=1.5,0.75
            score += idf*(tf*(k1+1))/(tf+k1*(1-b+b*len(dt)/max(1,avgdl)))
        if d.kind=="public_opportunity": score*=1.35
        elif d.kind=="gift_signal": score*=1.18
        elif d.kind=="funder_profile": score*=1.12
        if score>0: out.append((score,d))
    out.sort(key=lambda x:x[0], reverse=True)
    return [{"id":d.id,"title":d.title,"kind":d.kind,"url":d.url,"score":round(s,4),"snippet":d.text[:420],"metadata":d.metadata} for s,d in out[:top_k]]


def build_context(query: str, top_k: int = 8, max_chars: int = 16000) -> tuple[str,list[dict[str,Any]]]:
    hits=search(query,top_k=top_k,include_synthetic=False); parts=[]; used=0
    for h in hits:
        line=f"[{h['id']}] {h['title']}\nURL: {h.get('url') or 'n/a'}\n{h['snippet']}\n"
        if used+len(line)>max_chars: break
        parts.append(line); used+=len(line)
    return "\n---\n".join(parts), hits
