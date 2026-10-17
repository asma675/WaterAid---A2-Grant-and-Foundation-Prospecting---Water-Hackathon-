from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Literal

Decision = Literal["PURSUE", "PURSUE-QUEUE", "CULTIVATE", "REVIEW", "MONITOR", "DECLINE"]
GateResult = Literal["Pass", "Fail", "Uncertain"]
DateStatus = Literal["Confirmed", "Inferred", "Unknown"]


class SourceEvidence(BaseModel):
    url: str
    retrieved: str | None = None
    quote: str
    source_type: str | None = None


class FitCriterion(BaseModel):
    criterion_id: str
    name: str
    score: float | None = None
    weight: int | None = None
    explanation: str
    theme_or_country: str | None = None
    evidence_url: str | None = None
    retrieved: str | None = None


class GateCheck(BaseModel):
    gate_id: str
    name: str
    result: GateResult
    reason: str
    passport_ids: list[str] = []
    evidence_quote: str | None = None
    source_url: str | None = None
    retrieved: str | None = None


class KeyDate(BaseModel):
    label: str
    date: str | None = None
    status: DateStatus
    detail: str | None = None
    evidence_quote: str | None = None
    source_url: str | None = None
    retrieved: str | None = None


class MoneyEffort(BaseModel):
    grant_range: str | None = None
    likely_ask: str | None = None
    likely_ask_cad: float | None = None
    application_type: str | None = None
    fundraising_hours: float | None = None
    program_hours: float | None = None
    win_probability: float | None = None
    expected_value_cad: float | None = None
    expected_value_note: str | None = None
    capacity_remaining_hours: float | None = None
    fits_remaining_hours: bool | None = None
    planning_basis: str | None = None
    evidence_quote: str | None = None
    source_url: str | None = None
    retrieved: str | None = None


class RelationshipPath(BaseModel):
    status: str
    strength: str
    consent: str
    people_or_channel: str | None = None
    suggested_ask: str
    evidence_quote: str | None = None
    source_url: str | None = None
    retrieved: str | None = None


class NextStep(BaseModel):
    action: str
    owner: str
    due_date: str | None = None


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
    project_country: str = "Multiple WaterAid countries"
    target_countries: list[str] = []
    jurisdiction_verified: bool = True
    fit_criteria: list[FitCriterion] = []
    gates: list[GateCheck] = []
    key_dates: list[KeyDate] = []
    money_effort: MoneyEffort | None = None
    relationship_path: RelationshipPath | None = None
    risks_unknowns: list[str] = []
    next_step: NextStep | None = None
    briefing_complete: bool = False


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


class CountryCreate(BaseModel):
    country: str = Field(min_length=2, max_length=100)
    region: str = Field(default="Other", max_length=100)
    source: str = Field(default="User configured", max_length=200)
    source_url: str | None = None
    active: bool = True


class CountryPatch(BaseModel):
    country: str | None = Field(default=None, min_length=2, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=200)
    source_url: str | None = None
    active: bool | None = None


class PlanningSettingsPatch(BaseModel):
    remaining_fundraising_hours: float | None = Field(default=None, ge=0, le=10000)
    blended_fundraising_cost: float | None = Field(default=None, ge=0, le=10000)
    program_cost: float | None = Field(default=None, ge=0, le=10000)
    default_win_probability: float | None = Field(default=None, ge=0, le=1)
    default_owner: str | None = Field(default=None, max_length=120)
    default_due_days: int | None = Field(default=None, ge=0, le=365)
    weekly_review_limit: int | None = Field(default=None, ge=1, le=50)
    effort: dict[str, dict[str, float]] | None = None


class BriefOverridePatch(BaseModel):
    likely_ask_cad: float | None = Field(default=None, ge=0)
    application_type: str | None = Field(default=None, max_length=120)
    fundraising_hours: float | None = Field(default=None, ge=0)
    program_hours: float | None = Field(default=None, ge=0)
    win_probability: float | None = Field(default=None, ge=0, le=1)
    owner: str | None = Field(default=None, max_length=120)
    due_date: str | None = None
    relationship_strength: str | None = Field(default=None, max_length=120)
    relationship_consent: str | None = Field(default=None, max_length=120)
    relationship_note: str | None = Field(default=None, max_length=1000)


class DataIssueCreate(BaseModel):
    opportunity_id: str | None = None
    page: str | None = None
    description: str = Field(min_length=3, max_length=2000)
    source_url: str | None = None
    status: str = "Open"


class DataIssuePatch(BaseModel):
    description: str | None = Field(default=None, min_length=3, max_length=2000)
    source_url: str | None = None
    status: str | None = Field(default=None, max_length=50)

class HistoricalImportRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=5_000_000)

class UserOpportunityCreate(BaseModel):
    project_name: str = Field(min_length=2, max_length=200)
    country: str = Field(min_length=2, max_length=100)
    wash_theme: str = Field(min_length=2, max_length=120)
    beneficiaries: str | None = Field(default=None, max_length=500)
    project_description: str | None = Field(default=None, max_length=4000)
    funding_requirement: float = Field(default=0, ge=0)
    expected_application_effort: float = Field(default=0, ge=0, le=5000)
    potential_donor: str | None = Field(default=None, max_length=200)
    relationship_status: str | None = Field(default="Unknown", max_length=120)
    eligibility_requirements: str | None = Field(default=None, max_length=4000)
    submission_deadline: str | None = None
    evidence_links: str | None = Field(default=None, max_length=4000)
    trl: int | None = Field(default=None, ge=1, le=9)
    funding_stage: str = Field(default="Prospecting", max_length=120)

class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    country: str = Field(min_length=2, max_length=100)
    community: str | None = Field(default=None, max_length=300)
    beneficiaries: int | None = Field(default=0, ge=0)
    intervention: str | None = Field(default=None, max_length=1500)
    total_budget: float = Field(default=0, ge=0)
    existing_funding: float = Field(default=0, ge=0)
    implementation_period: str | None = Field(default=None, max_length=200)
    priority: str = Field(default="Medium", max_length=50)
    readiness: str = Field(default="Planning", max_length=80)
    trl: int | None = Field(default=None, ge=1, le=9)
    owner: str | None = Field(default=None, max_length=120)
    milestones: str | None = Field(default=None, max_length=2000)

class ProjectPatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    community: str | None = Field(default=None, max_length=300)
    beneficiaries: int | None = Field(default=None, ge=0)
    intervention: str | None = Field(default=None, max_length=1500)
    total_budget: float | None = Field(default=None, ge=0)
    existing_funding: float | None = Field(default=None, ge=0)
    implementation_period: str | None = Field(default=None, max_length=200)
    priority: str | None = Field(default=None, max_length=50)
    readiness: str | None = Field(default=None, max_length=80)
    trl: int | None = Field(default=None, ge=1, le=9)
    owner: str | None = Field(default=None, max_length=120)
    milestones: str | None = Field(default=None, max_length=2000)

class ProjectLinkCreate(BaseModel):
    project_id: int = Field(ge=1)
    opportunity_id: int = Field(ge=1)

class ScenarioRequest(BaseModel):
    opportunity_ids: list[int] = []
    staff_hour_limit: float = Field(default=150, ge=0, le=10000)

class ScoringConfigPatch(BaseModel):
    weights: dict[str, float]

class AdvisorRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1200)
    exclude_largest_award: bool = False

class UserOpportunityPatch(BaseModel):
    project_name: str | None = Field(default=None, min_length=2, max_length=200)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    wash_theme: str | None = Field(default=None, min_length=2, max_length=120)
    beneficiaries: str | None = Field(default=None, max_length=500)
    project_description: str | None = Field(default=None, max_length=4000)
    funding_requirement: float | None = Field(default=None, ge=0)
    expected_application_effort: float | None = Field(default=None, ge=0, le=5000)
    potential_donor: str | None = Field(default=None, max_length=200)
    relationship_status: str | None = Field(default=None, max_length=120)
    eligibility_requirements: str | None = Field(default=None, max_length=4000)
    submission_deadline: str | None = None
    evidence_links: str | None = Field(default=None, max_length=4000)
    trl: int | None = Field(default=None, ge=1, le=9)
    funding_stage: str | None = Field(default=None, max_length=120)
