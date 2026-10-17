from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Literal

Decision = Literal["PURSUE", "PURSUE-QUEUE", "CULTIVATE", "REVIEW", "MONITOR", "DECLINE"]


class SourceEvidence(BaseModel):
    url: str
    retrieved: str | None = None
    quote: str
    source_type: str | None = None


class OpportunitySummary(BaseModel):
    opp_id: str
    funder_id: str
    funder_name: str
    title: str
    decision: str
    eligible: str
    fit_score: float | None = None
    confidence: Literal["high", "medium", "low"]
    readiness_index: int = Field(ge=0, le=100)
    readiness_note: str = "Heuristic pursuit-readiness index; not a probability of award."
    failed_gates: list[str] = []
    trap_type: str | None = None
    rationale: str
    strong_action: str
    source_count: int
    evidence: list[SourceEvidence]
    typical_grant_min_cad: int | None = None
    typical_grant_max_cad: int | None = None
    access_model: str | None = None
    relationship_status: str | None = None
    real_public: bool = False
    deadline: str | None = None
    status: str | None = None
    geography: str | None = None
    themes: list[str] = []
    amount: str | None = None
    province: str | None = None
    location: str | None = None
    funder_type: str | None = None
    applicant_types: list[str] = []
    funder_country: str = "Canada"
    project_country: str = "Canada"
    jurisdiction_verified: bool = True


class AgentTrace(BaseModel):
    agent: str
    status: Literal["complete", "skipped", "blocked", "warning"]
    detail: str


class ScanRequest(BaseModel):
    query: str = Field(min_length=3, max_length=800)
    max_results: int = Field(default=8, ge=1, le=20)
    include_regression_cases: bool = False


class ScanResponse(BaseModel):
    query: str
    mode: str
    results: list[OpportunitySummary]
    trace: list[AgentTrace]
    safety_note: str
    rag_hits: list[dict[str, Any]] = []
    providers: list[dict[str, Any]] = []


class RankItem(BaseModel):
    rank_id: str
    summary: str
    fit_score: float
    application_type: str
    fundraising_hours: int
    likely_grant_cad: int
    decision: str
    reference_reasoning: str


class RagQuery(BaseModel):
    query: str = Field(min_length=2, max_length=800)
    top_k: int = Field(default=8, ge=1, le=30)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1200)
    providers: list[str] = Field(default_factory=lambda: ["local"])
    max_results: int = Field(default=8, ge=1, le=20)


class PipelineCreate(BaseModel):
    opportunity_id: str
    title: str
    funder: str
    stage: str = "Qualified"
    owner: str = "Unassigned"
    deadline: str | None = None
    amount: str | None = None
    next_action: str | None = None
    notes: str | None = None


class DecisionCreate(BaseModel):
    opportunity_id: str
    system_decision: str
    human_decision: str
    reason: str | None = None
    note: str | None = None


class PipelinePatch(BaseModel):
    stage: str | None = None
    owner: str | None = None
    deadline: str | None = None
    amount: str | None = None
    next_action: str | None = None
    notes: str | None = None
