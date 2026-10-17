from __future__ import annotations
from .engine import search_opportunities
from .models import AgentTrace, ScanResponse
from .rag import search as rag_search
from .providers import provider_status

AGENTS = [
    {"id":"scout","name":"Scout","job":"Find Canadian funders and programs for water problems in Canada only."},
    {"id":"verifier","name":"Verifier","job":"Cross-check Canadian jurisdiction, dates, amounts, access and source freshness; flag conflicts."},
    {"id":"gatekeeper","name":"Gatekeeper","job":"Block foreign funders, overseas projects and hard eligibility failures before scoring."},
    {"id":"strategist","name":"Strategist","job":"Rank strategic fit using issue, Canadian geography, award history and access."},
    {"id":"economist","name":"Economist","job":"Check effort, deadline feasibility, grant value and capacity before pursuit."},
    {"id":"auditor","name":"Evidence Auditor","job":"Require a public source and retrieval date; unknown stays unknown."},
]


def run_scan(query: str, max_results: int, include_regression_cases: bool=False) -> ScanResponse:
    results=search_opportunities(query,max_results,include_regression_cases=include_regression_cases)
    rag=rag_search(query,top_k=max_results,include_synthetic=include_regression_cases)
    trace=[
        AgentTrace(agent="Scout",status="complete",detail=f"Searched the curated Canada-only funding registry. {sum(1 for x in results if x.real_public)} verified domestic prospects returned."),
        AgentTrace(agent="Verifier",status="complete",detail="Checked first-party source links, dates and conflicting page states. Conflicts route to REVIEW."),
        AgentTrace(agent="Gatekeeper",status="complete",detail="Hard jurisdiction rule: funder/program must be Canadian and the funded project must take place in Canada."),
        AgentTrace(agent="Strategist",status="complete",detail="Ranked water/freshwater relevance, Canadian geography, public award history and practical access."),
        AgentTrace(agent="Economist",status="complete",detail="Prioritizes actionable calls and avoids spending proposal time on closed or poorly matched programs."),
        AgentTrace(agent="Evidence Auditor",status="complete",detail="No award probability is invented; evidence links and retrieval dates remain visible."),
    ]
    return ScanResponse(
        query=query, mode="canada-domestic-rag+regression" if include_regression_cases else "canada-domestic-rag",
        results=results, trace=trace,
        safety_note="Canada-only prospect gate is enforced for the live prospect queue. External AI can suggest candidates, but candidates are not trusted until verified against Canadian public sources.",
        rag_hits=rag, providers=provider_status()
    )
