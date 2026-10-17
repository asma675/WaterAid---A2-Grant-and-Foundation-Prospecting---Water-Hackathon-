from __future__ import annotations
from .engine import search_opportunities
from .models import AgentTrace, ScanResponse
from .rag import search as rag_search
from .providers import provider_status

AGENTS = [
    {"id":"scout","name":"Scout","job":"Find Canadian funders and donor programs that can support WaterAid projects in target countries."},
    {"id":"verifier","name":"Verifier","job":"Verify the funder is Canadian, confirm source dates/amounts/access, and map geographic eligibility to WaterAid countries."},
    {"id":"gatekeeper","name":"Gatekeeper","job":"Block non-Canadian funders and projects outside the WaterAid target-country list before scoring."},
    {"id":"strategist","name":"Strategist","job":"Rank fit across WASH, climate resilience, health systems, gender equality, country overlap and peer-giving history."},
    {"id":"economist","name":"Economist","job":"Check grant value, deadline feasibility, effort and team capacity before pursuit."},
    {"id":"auditor","name":"Evidence Auditor","job":"Require source-linked evidence; unknown stays unknown and invitation-only calls fail access."},
]


def run_scan(query: str, max_results: int, include_regression_cases: bool=False) -> ScanResponse:
    results=search_opportunities(query,max_results,include_regression_cases=include_regression_cases)
    rag=rag_search(query,top_k=max_results,include_synthetic=include_regression_cases)
    trace=[
        AgentTrace(agent="Scout",status="complete",detail=f"Searched Canadian funders against WaterAid target countries. {sum(1 for x in results if x.real_public)} verified international-development prospects returned."),
        AgentTrace(agent="Verifier",status="complete",detail="Checked first-party source links, dates, Canadian funder jurisdiction and country eligibility. Conflicts route to REVIEW."),
        AgentTrace(agent="Gatekeeper",status="complete",detail="Hard jurisdiction rule: funder/program must be Canadian and project geography must overlap the WaterAid target-country list."),
        AgentTrace(agent="Strategist",status="complete",detail="Ranked WASH, climate, health and gender fit, target-country overlap, peer-giving history and practical access."),
        AgentTrace(agent="Economist",status="complete",detail="Prioritizes actionable funding and avoids spending proposal time on closed, invitation-only or weakly aligned programs."),
        AgentTrace(agent="Evidence Auditor",status="complete",detail="No award probability is invented; evidence links and retrieval dates remain visible."),
    ]
    return ScanResponse(
        query=query, mode="canadian-funders-wateraid-countries+regression" if include_regression_cases else "canadian-funders-wateraid-countries",
        results=results, trace=trace,
        safety_note="Canadian-funder-only gate is enforced. Project geography must overlap WaterAid target countries. External AI may discover leads, but candidates are not trusted until funder jurisdiction, project-country fit and first-party evidence are verified.",
        rag_hits=rag, providers=provider_status()
    )
