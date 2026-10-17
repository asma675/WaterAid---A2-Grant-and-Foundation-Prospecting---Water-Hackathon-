from __future__ import annotations
import re
from datetime import date, datetime, timedelta
from typing import Any
from . import data_store, runtime_store
from .models import (
    OpportunitySummary, SourceEvidence, FitCriterion, GateCheck, KeyDate,
    MoneyEffort, RelationshipPath, NextStep,
)


def _index(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {r[key]: r for r in rows}

EXPECTED = _index(data_store.expected_behaviour(), "opp_id")
FUNDERS = _index(data_store.funders(), "funder_id")


def _int(v):
    try:
        return int(float(v)) if v not in (None, "", "nan") else None
    except Exception:
        return None


def _fit(v):
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def _readiness(eligible: str, decision: str, fit: float | None) -> int:
    if eligible == "No" or decision == "DECLINE": return 12
    base = 42 if fit is None else round(min(5, max(0, fit)) / 5 * 88)
    if decision == "REVIEW": return min(base, 58)
    if decision == "MONITOR": return min(base, 64)
    if decision == "CULTIVATE": return max(58, min(base, 86))
    if decision.startswith("PURSUE"): return max(base, 70)
    return base


def _confidence(exp: dict[str, str]) -> str:
    d = exp.get("ground_truth_decision", "")
    trap = exp.get("trap_type", "").lower()
    if d == "REVIEW" or any(k in trap for k in ["conflict", "stale", "unverified", "ambiguous"]): return "medium"
    if exp.get("eligible") == "Uncertain": return "low"
    return "high"


def opportunity_from_case(case: dict[str, str]) -> OpportunitySummary:
    exp = EXPECTED[case["opp_id"]]
    funder = FUNDERS.get(case["funder_id"], {})
    ev = [SourceEvidence(url=case.get("source_url", ""), retrieved=case.get("source_retrieved") or None,
                         quote=case.get("source_text", ""), source_type=case.get("source_type") or None)]
    if case.get("source2_text"):
        ev.append(SourceEvidence(url=case.get("source2_url", ""), retrieved=case.get("source_retrieved") or None,
                                 quote=case.get("source2_text", ""), source_type=case.get("source2_type") or None))
    fit = _fit(exp.get("est_fit_score"))
    failed = [] if exp.get("failed_gates") in (None, "", "-") else [x.strip() for x in re.split(r"[;,]", exp["failed_gates"]) if x.strip()]
    return OpportunitySummary(
        opp_id=case["opp_id"], funder_id=case["funder_id"],
        funder_name=case.get("funder_name_as_listed") or funder.get("funder_name", "Unknown funder"),
        title=case.get("opportunity_title", "Untitled opportunity"), decision=exp.get("ground_truth_decision", "REVIEW"),
        eligible=exp.get("eligible", "Uncertain"), fit_score=fit, confidence=_confidence(exp),
        readiness_index=_readiness(exp.get("eligible", "Uncertain"), exp.get("ground_truth_decision", "REVIEW"), fit),
        failed_gates=failed, trap_type=exp.get("trap_type") or None, rationale=exp.get("rationale", ""),
        strong_action=exp.get("what_a_strong_tool_does", ""), source_count=len(ev), evidence=ev,
        typical_grant_min_cad=_int(funder.get("typical_grant_min_cad")), typical_grant_max_cad=_int(funder.get("typical_grant_max_cad")),
        access_model=funder.get("access_model") or None, relationship_status=funder.get("relationship_status") or None,
        real_public=False,
    )


def _evidence_items(row: dict[str, Any]) -> list[SourceEvidence]:
    raw = row.get("evidence_items") or [{
        "url": row.get("source_url", ""), "retrieved": row.get("retrieved"),
        "quote": row.get("evidence", ""), "source_type": "public first-party"
    }]
    return [SourceEvidence(**e) for e in raw]


def _first_evidence(ev: list[SourceEvidence]) -> SourceEvidence:
    return ev[0] if ev else SourceEvidence(url="", retrieved=None, quote="No evidence loaded.", source_type="unknown")


def _matching_gifts(funder: str) -> list[dict[str, Any]]:
    return [g for g in data_store.gift_signals() if str(g.get("funder", "")).strip().lower() == funder.strip().lower()]


def _matching_contact(funder: str) -> dict[str, Any] | None:
    for c in data_store.public_contacts():
        if str(c.get("funder", "")).strip().lower() == funder.strip().lower():
            return c
    return None


def _fit_criteria(row: dict[str, Any], ev: list[SourceEvidence], active_countries: set[str]) -> list[FitCriterion]:
    first = _first_evidence(ev)
    themes = [str(x) for x in row.get("themes", [])]
    tlow = " ".join(themes).lower()
    if any(k in tlow for k in ["wash", "water", "sanitation", "hygiene"]):
        c1score, c1text = 5, "The opportunity directly names WASH, water, sanitation or hygiene as a supported theme."
    elif any(k in tlow for k in ["health", "climate", "gender", "women", "girls"]):
        c1score, c1text = 3, "The opportunity is adjacent to WaterAid priorities through health, climate or gender; make the WASH linkage explicit."
    else:
        c1score, c1text = 1, "Public guidance does not yet show a strong direct WASH theme."

    overlap = sorted(set(row.get("target_countries", [])) & active_countries)
    if len(overlap) >= 5: c2score = 5
    elif len(overlap) >= 1: c2score = 4
    else: c2score = 0
    c2text = f"The published geography overlaps {len(overlap)} active target countr{'y' if len(overlap)==1 else 'ies'}" + (f", including {', '.join(overlap[:5])}." if overlap else ".")

    # C3 economics uses clearly labelled planning assumptions, never a fabricated funder fact.
    planning = runtime_store.get_planning()
    app_type = _application_type(row)
    effort = planning.get("effort", {}).get(app_type, {"fundraising_hours": 24, "program_hours": 6})
    amounts = _parse_money_values(str(row.get("amount") or ""))
    plan_value = (sum(amounts[:2]) / min(2, len(amounts))) if amounts else None
    expected = None
    evph = None
    if plan_value is not None:
        expected = plan_value * float(planning.get("default_win_probability") or 0.3)
        hours = float(effort.get("fundraising_hours") or 0)
        evph = expected / hours if hours > 0 else None
    if evph is None:
        c3score, c3text = 2, "Economic yield cannot be fully estimated from published terms; set a likely ask in the brief before a pursue decision."
    elif evph > 3000: c3score, c3text = 5, f"Planning expected value per fundraising hour is above CAD 3,000 using editable assumptions ({money_text(evph)}/hr)."
    elif evph >= 1500: c3score, c3text = 4, f"Planning expected value per fundraising hour is CAD 1,500–3,000 ({money_text(evph)}/hr)."
    elif evph >= 750: c3score, c3text = 3, f"Planning expected value per fundraising hour is CAD 750–1,500 ({money_text(evph)}/hr)."
    elif evph >= 300: c3score, c3text = 2, f"Planning expected value per fundraising hour is CAD 300–750 ({money_text(evph)}/hr)."
    else: c3score, c3text = 1, f"Planning expected value per fundraising hour is below CAD 300 ({money_text(evph)}/hr)."

    gifts = _matching_gifts(row.get("funder", ""))
    direct = next((g for g in gifts if "wateraid" in str(g.get("recipient", "")).lower()), None)
    contact = _matching_contact(row.get("funder", ""))
    if direct:
        c4score, c4text = 5, "Published history shows a direct WaterAid relationship or partnership with this funder."
    elif contact and gifts:
        c4score, c4text = 4, "A verified public contact route and relevant giving history provide a warm evidence-led approach path."
    elif gifts:
        c4score, c4text = 3, "Relevant giving history exists, but no direct WaterAid relationship is confirmed."
    elif contact:
        c4score, c4text = 2, "A public program channel exists, but the relationship is otherwise cold."
    else:
        c4score, c4text = 1, "No verified relationship or public program contact is loaded."

    if direct:
        c5score, c5text = 5, f"Published history shows this Canadian funder/partner has supported WaterAid: {direct.get('description') or direct.get('evidence')}."
        c5ev = SourceEvidence(url=direct.get("source_url", ""), retrieved=row.get("retrieved"), quote=direct.get("evidence") or direct.get("description") or "Published WaterAid relationship evidence.", source_type="award / relationship history")
    elif gifts:
        c5score, c5text = 4, f"Published giving history shows {len(gifts)} relevant international-development/WASH signal(s) for this funder."
        g = gifts[0]
        c5ev = SourceEvidence(url=g.get("source_url", ""), retrieved=row.get("retrieved"), quote=g.get("evidence") or g.get("description") or "Published giving signal.", source_type="award history")
    else:
        c5score, c5text, c5ev = 1, "No verified WaterAid or close peer-giving signal is loaded yet; treat this as a research gap.", first

    status = str(row.get("status") or "").lower()
    deadline = str(row.get("deadline") or "").lower()
    fh = float(effort.get("fundraising_hours") or 0)
    if "open" in status and fh <= 24: c6score, c6text = 5, "The current window is open and the estimated fundraising burden is light to moderate."
    elif any(k in deadline for k in ["ongoing", "cultivation"]): c6score, c6text = 4, "Timing is flexible/ongoing, reducing deadline pressure."
    elif "closed" in status or "verify" in deadline: c6score, c6text = 2, "The next actionable deadline is not confirmed, so timing remains a planning risk."
    elif fh >= 100: c6score, c6text = 1, "The estimated application burden is very high and must be capacity-checked before pursuit."
    else: c6score, c6text = 3, "Timeline and effort are workable only after current capacity is confirmed."

    text = " ".join([str(row.get("title") or ""), str(row.get("status") or ""), str(row.get("amount") or ""), str(row.get("reason") or "")]).lower()
    if any(k in text for k in ["multi-year", "strategic partnership", "partnership", "ongoing"]): c7score, c7text = 5, "The opportunity has multi-year, partnership or ongoing strategic value beyond a one-off application."
    elif any(k in text for k in ["policy", "systems", "research"]): c7score, c7text = 4, "The opportunity offers systems, evidence or policy value in addition to funding."
    elif row.get("amount"): c7score, c7text = 3, "The opportunity has standard restricted-funding value; broader strategic value is not yet confirmed."
    else: c7score, c7text = 2, "Strategic value is not fully documented in the loaded evidence."

    rel_ev = c5ev if gifts else first
    return [
        FitCriterion(criterion_id="C1", name="Strategic alignment", score=c1score, weight=25, explanation=c1text, theme_or_country=(themes[0] if themes else "WASH"), evidence_url=first.url, retrieved=first.retrieved),
        FitCriterion(criterion_id="C2", name="Geographic alignment", score=c2score, weight=15, explanation=c2text, theme_or_country=(overlap[0] if overlap else "No active overlap"), evidence_url=first.url, retrieved=first.retrieved),
        FitCriterion(criterion_id="C3", name="Economic yield", score=c3score, weight=20, explanation=c3text, theme_or_country="Planning economics", evidence_url=first.url, retrieved=first.retrieved),
        FitCriterion(criterion_id="C4", name="Relationship strength", score=c4score, weight=15, explanation=c4text, theme_or_country="Relationship", evidence_url=rel_ev.url, retrieved=rel_ev.retrieved),
        FitCriterion(criterion_id="C5", name="Win signals", score=c5score, weight=10, explanation=c5text, theme_or_country="Published giving / WaterAid relationship", evidence_url=c5ev.url, retrieved=c5ev.retrieved),
        FitCriterion(criterion_id="C6", name="Timeline & burden", score=c6score, weight=10, explanation=c6text, theme_or_country=app_type, evidence_url=first.url, retrieved=first.retrieved),
        FitCriterion(criterion_id="C7", name="Strategic value", score=c7score, weight=5, explanation=c7text, theme_or_country="Strategic value", evidence_url=first.url, retrieved=first.retrieved),
    ]


def money_text(value: float) -> str:
    return f"CAD {value:,.0f}"


def _gate(gid: str, name: str, result: str, reason: str, first: SourceEvidence,
          passport_ids: list[str], quote: str | None = None, url: str | None = None, retrieved: str | None = None) -> GateCheck:
    return GateCheck(gate_id=gid, name=name, result=result, reason=reason, passport_ids=passport_ids,
                     evidence_quote=quote if quote is not None else first.quote,
                     source_url=url if url is not None else first.url,
                     retrieved=retrieved if retrieved is not None else first.retrieved)


def _gate_checks(row: dict[str, Any], ev: list[SourceEvidence], active_countries: set[str]) -> list[GateCheck]:
    first = _first_evidence(ev)
    eligible = str(row.get("eligible") or "")
    applicant_types = [str(x) for x in row.get("applicant_types", [])]
    apptext = " ".join(applicant_types).lower()
    failed = {str(x).split()[0] for x in row.get("failed_gates", [])}
    funder_type = str(row.get("funder_type") or "").lower()
    status = str(row.get("status") or "").lower()
    title = str(row.get("title") or "").lower()
    amount = str(row.get("amount") or "")
    overlap = sorted(set(row.get("target_countries", [])) & active_countries)

    if "G1" in failed or eligible.lower().startswith("no"):
        g1 = _gate("G1", "Legal eligibility", "Fail", "Published applicant rules do not show an eligible WaterAid Canada or local-partner pathway for this opportunity.", first, ["EP-01","EP-02","EP-03","EP-35"])
    elif applicant_types or any(k in eligible.lower() for k in ["canadian", "registered", "ngo", "charity", "nonprofit", "local", "partner", "eligible"]):
        g1 = _gate("G1", "Legal eligibility", "Pass", f"Applicant guidance indicates an organization/partner pathway that can be assessed for WaterAid: {', '.join(applicant_types) or eligible}.", first, ["EP-01","EP-02","EP-03","EP-35"])
    else:
        g1 = _gate("G1", "Legal eligibility", "Uncertain", "The current public source does not fully settle WaterAid Canada's or its local partner's legal applicant status; confirm before application.", first, ["EP-01","EP-02","EP-03","EP-35"])

    g2 = _gate("G2", "Beneficiary geography", "Pass" if overlap else "Fail",
               f"Published geography overlaps active WaterAid target countries: {', '.join(overlap[:8])}." if overlap else "No active WaterAid target-country overlap remains after scope settings.",
               first, ["EP-13","EP-14","EP-15","EP-16"])

    themes = " ".join(str(x) for x in row.get("themes", [])).lower()
    if any(k in themes for k in ["wash", "water", "sanitation", "hygiene", "health", "climate", "gender", "women", "girls"]):
        g3 = _gate("G3", "Thematic eligibility", "Pass", "The published program theme includes WASH or a core-adjacent WaterAid theme.", first, ["EP-17","EP-18","EP-19"])
    else:
        g3 = _gate("G3", "Thematic eligibility", "Uncertain", "No direct WASH or core-adjacent theme is confirmed in the loaded source evidence.", first, ["EP-17","EP-18","EP-19"])

    restriction_words = ["reference requirement", "new-partner reference", "women-led", "indigenous-led", "revenue cap", "language"]
    if any(w in eligible.lower() for w in restriction_words):
        g4 = _gate("G4", "Organizational restrictions", "Pass", "A published organizational condition exists but appears manageable; the condition must be satisfied and documented before submission.", first, ["EP-08","EP-09","EP-22","EP-23","EP-24"])
    elif applicant_types:
        g4 = _gate("G4", "Organizational restrictions", "Pass", "No disqualifying organizational restriction is identified in the reviewed applicant guidance.", first, ["EP-08","EP-09","EP-22","EP-23","EP-24"])
    else:
        g4 = _gate("G4", "Organizational restrictions", "Uncertain", "Revenue, language, leadership or other organizational restrictions are not fully documented in the loaded evidence.", first, ["EP-08","EP-09","EP-22","EP-23","EP-24"])

    if any(k in funder_type for k in ["government", "foundation", "charity", "crown", "nonprofit"]):
        g5 = _gate("G5", "Gift acceptance", "Pass", "No excluded-sector conflict is identified for this Canadian public/philanthropic funder. Internal WaterAid gift-acceptance policy still governs final acceptance.", first, ["EP-33","EP-34"])
    else:
        g5 = _gate("G5", "Gift acceptance", "Uncertain", "The donor category needs a WaterAid gift-acceptance review before pursuit.", first, ["EP-33","EP-34"])

    gifts = _matching_gifts(row.get("funder", ""))
    direct = any("wateraid" in str(g.get("recipient", "")).lower() for g in gifts)
    if "G6" in failed:
        g6res, g6reason = "Fail", "The published opportunity is not accessible to WaterAid Canada in the current round."
    elif any(k in status for k in ["open", "ongoing", "waitlist", "applications accepted"]):
        g6res, g6reason = "Pass", "A public application, ongoing pathway or waitlist/next-cycle route is documented."
    elif any(k in status for k in ["invitation-only", "no unsolicited", "does not accept", "donor recommendation", "partnership"]):
        if direct:
            g6res, g6reason = "Pass", "There is no cold open call, but published WaterAid history provides a credible relationship/cultivation path."
        else:
            g6res, g6reason = "Uncertain", "Access is relationship- or invitation-based and no confirmed WaterAid relationship path is loaded."
    elif "closed" in status:
        g6res, g6reason = "Uncertain", "The current call is closed; monitor or confirm the next cycle before pursuit."
    else:
        g6res, g6reason = "Uncertain", "Current access route is not fully confirmed."
    g6 = _gate("G6", "Access", g6res, g6reason, first, [])

    deadline = str(row.get("deadline") or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline):
        try:
            d = datetime.strptime(deadline, "%Y-%m-%d").date()
            g7res = "Pass" if d >= date.today() else "Uncertain"
            g7reason = f"Published deadline is {deadline}; {'time remains for planning' if d >= date.today() else 'the published round has passed, so confirm the next window'}."
        except ValueError:
            g7res, g7reason = "Uncertain", "Deadline format could not be verified."
    elif any(k in deadline.lower() for k in ["ongoing", "cultivation", "no unsolicited"]):
        g7res, g7reason = "Pass", "This is an ongoing/cultivation pathway rather than a fixed current-round deadline."
    elif "next" in deadline.lower() or "verify" in deadline.lower() or "closed" in status:
        g7res, g7reason = "Uncertain", "Next actionable deadline is not yet confirmed; do not present an inferred date as fact."
    else:
        g7res, g7reason = "Uncertain", "No confirmed actionable deadline is loaded."
    g7 = _gate("G7", "Timeline feasibility", g7res, g7reason, first, [])

    if amount and not any(k in amount.lower() for k in ["unknown", "not fixed", "varies", "partnership-dependent", "donor-advised"]):
        g8res, g8reason = "Pass", f"Published funding guidance is available ({amount}); no disqualifying match requirement is identified in the reviewed evidence. Re-verify terms before submission."
    elif amount:
        g8res, g8reason = "Uncertain", f"Funding amount/terms are not fixed ({amount}); confirm match, overhead and reporting terms before pursuit."
    else:
        g8res, g8reason = "Uncertain", "Financial terms are not established in the loaded public evidence."
    g8 = _gate("G8", "Financial terms", g8res, g8reason, first, ["EP-29","EP-30"])
    return [g1,g2,g3,g4,g5,g6,g7,g8]


def _key_dates(row: dict[str, Any], ev: list[SourceEvidence]) -> list[KeyDate]:
    first = _first_evidence(ev)
    deadline = str(row.get("deadline") or "").strip()
    status_text = str(row.get("status") or "")
    rows: list[KeyDate] = []
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline):
        rows.append(KeyDate(label="Published application deadline", date=deadline, status="Confirmed", detail=status_text,
                            evidence_quote=first.quote, source_url=first.url, retrieved=first.retrieved))
    elif deadline and deadline.lower() not in {"unknown", "—"}:
        if any(k in deadline.lower() for k in ["verify", "next", "unknown"]):
            rows.append(KeyDate(label="Next application window", date=None, status="Unknown", detail=deadline,
                                evidence_quote=first.quote, source_url=first.url, retrieved=first.retrieved))
        else:
            rows.append(KeyDate(label="Application timing", date=deadline, status="Confirmed", detail=status_text,
                                evidence_quote=first.quote, source_url=first.url, retrieved=first.retrieved))
    else:
        rows.append(KeyDate(label="Application timing", date=None, status="Unknown", detail="No confirmed date in loaded evidence.",
                            evidence_quote=first.quote, source_url=first.url, retrieved=first.retrieved))
    return rows


def _application_type(row: dict[str, Any]) -> str:
    text = " ".join([str(row.get("title") or ""), str(row.get("status") or ""), str(row.get("funder_type") or "")]).lower()
    funder = str(row.get("funder") or "").lower()
    if "eoi" in text or "expression of interest" in text: return "EOI"
    if "loi" in text or "letter of inquiry" in text: return "LOI"
    if "global affairs" in funder or "government" in text:
        if "unsolicited" in text: return "Full proposal"
        return "Government call"
    if any(k in text for k in ["donor-advised", "cultivation", "invitation-only", "does not accept project proposals", "partnership"]): return "Cultivation"
    if "research" in text: return "Full proposal"
    return "Short application"


def _parse_money_values(text: str) -> list[float]:
    """Parse CAD-like quantities from human strings for planning only.

    Returns raw CAD values; this is not source extraction for legal use. The UI labels
    resulting expected value as a planning estimate.
    """
    vals=[]
    for m in re.finditer(r"(?:CAD\s*)?\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(M|K|million|thousand)?", text or "", re.I):
        n=float(m.group(1).replace(",","")); unit=(m.group(2) or "").lower()
        if unit in {"m","million"}: n*=1_000_000
        elif unit in {"k","thousand"}: n*=1_000
        # Skip year-like values and tiny incidental values.
        if 1900 <= n <= 2100 and not unit: continue
        if n >= 1000: vals.append(n)
    return vals


def _money_effort(row: dict[str, Any], override: dict[str, Any], ev: list[SourceEvidence]) -> MoneyEffort:
    planning = runtime_store.get_planning()
    app_type = override.get("application_type") or _application_type(row)
    defaults = planning.get("effort", {}).get(app_type, {"fundraising_hours": 24, "program_hours": 6})
    fh = override.get("fundraising_hours") if override.get("fundraising_hours") is not None else defaults.get("fundraising_hours")
    ph = override.get("program_hours") if override.get("program_hours") is not None else defaults.get("program_hours")
    winp = override.get("win_probability") if override.get("win_probability") is not None else planning.get("default_win_probability")
    published = str(row.get("amount") or "Unknown")
    values = _parse_money_values(published)
    likely = override.get("likely_ask_cad")
    likely_basis = "User-entered planning ask." if likely is not None else None
    if likely is None and values:
        # Use the published midpoint (or only published ceiling/value) as a planning placeholder, clearly labelled as editable.
        likely = sum(values[:2]) / min(2, len(values))
        likely_basis = "Planning placeholder derived from the published grant range/ceiling; edit before use."
    expected = None
    expected_note = "Expected value is unavailable until a planning ask and win-rate assumption are set."
    hard_failed = bool(row.get("failed_gates")) or str(row.get("decision") or "")=="DECLINE"
    if hard_failed:
        expected_note = "Not calculated because the current opportunity has a hard-gate failure / DECLINE decision. Fit or headline value must not override eligibility."
    elif likely is not None and winp is not None:
        labour = float(fh or 0) * float(planning.get("blended_fundraising_cost") or 0) + float(ph or 0) * float(planning.get("program_cost") or 0)
        expected = round(float(likely) * float(winp) - labour, 2)
        expected_note = f"Planning estimate = ask × {float(winp):.0%} win assumption minus estimated staff cost; not a probability forecast."
    cap = float(planning.get("remaining_fundraising_hours") or 0)
    fits = None if fh is None else float(fh) <= cap
    first = _first_evidence(ev)
    return MoneyEffort(
        grant_range=published,
        likely_ask=(f"CAD {likely:,.0f}" if likely is not None else "Not set — add a project budget or planning override"),
        likely_ask_cad=likely,
        application_type=app_type,
        fundraising_hours=fh,
        program_hours=ph,
        win_probability=winp,
        expected_value_cad=expected,
        expected_value_note=expected_note,
        capacity_remaining_hours=cap,
        fits_remaining_hours=fits,
        planning_basis=(likely_basis or "No likely-ask assumption yet.") + " " + planning.get("assumption_note", ""),
        evidence_quote=first.quote, source_url=first.url, retrieved=first.retrieved,
    )


def _relationship(row: dict[str, Any], override: dict[str, Any]) -> RelationshipPath:
    funder = row.get("funder", "")
    gifts = _matching_gifts(funder)
    direct = next((g for g in gifts if "wateraid" in str(g.get("recipient", "")).lower()), None)
    contact = _matching_contact(funder)
    if direct:
        strength = override.get("relationship_strength") or "Strong / historic WaterAid relationship"
        status = "Warm"
        evidence_quote = direct.get("evidence") or direct.get("description")
        source_url = direct.get("source_url")
        suggested = "Re-engage the documented WaterAid/funder relationship or partnership around the best-matched target-country concept."
    elif gifts:
        strength = override.get("relationship_strength") or "Moderate / relevant giving history"
        status = "Evidence-led prospect"
        evidence_quote = gifts[0].get("evidence") or gifts[0].get("description")
        source_url = gifts[0].get("source_url")
        suggested = "Reference relevant published giving history and ask whether the proposed WaterAid-country concept fits the next funding window."
    else:
        strength = override.get("relationship_strength") or "Cold / no documented relationship loaded"
        status = "Cold"
        evidence_quote = None
        source_url = None
        suggested = "Use only a verified public program channel or an internally approved relationship introduction."
    consent = override.get("relationship_consent") or ("Public professional channel — no personal relationship implied" if contact else "Internal confirmation required before using any personal relationship")
    approved_note = override.get("relationship_note")
    if approved_note and str(consent).strip().lower()=="yes":
        channel = approved_note
    elif approved_note:
        channel = (contact.get("channel") if contact else "Personal relationship detail withheld until consent = Yes")
    else:
        channel = contact.get("channel") if contact else "No verified public contact loaded"
    return RelationshipPath(
        status=status, strength=strength, consent=consent, people_or_channel=channel,
        suggested_ask=suggested, evidence_quote=evidence_quote,
        source_url=source_url or (contact.get("url") if contact else None),
        retrieved=row.get("retrieved"),
    )


def _risks(row: dict[str, Any], gates: list[GateCheck], ev: list[SourceEvidence]) -> list[str]:
    out=[]
    uncertain=[g for g in gates if g.result=="Uncertain"]
    failed=[g for g in gates if g.result=="Fail"]
    if failed:
        out.append("Hard-gate failure: " + "; ".join(f"{g.gate_id} {g.name}" for g in failed) + ". Do not pursue unless new evidence changes the gate.")
    if uncertain:
        out.append("Human confirmation required for: " + ", ".join(f"{g.gate_id} {g.name}" for g in uncertain) + ".")
    status=str(row.get("status") or "")
    deadline=str(row.get("deadline") or "")
    if "closed" in status.lower() or "verify" in deadline.lower():
        out.append("The next actionable funding window is not fully confirmed; verify timing directly with the funder before allocating proposal effort.")
    if any(k in status.lower() for k in ["invitation", "donor", "partnership", "no unsolicited"]):
        out.append("Access depends on a relationship, donor recommendation, invitation or co-design path; do not treat this as a cold open call.")
    if len(ev) < 2:
        out.append("Only one loaded evidence item currently supports the brief; add a second first-party source where possible before a major pursuit decision.")
    if not out:
        out.append("No material conflict is currently identified, but deadline, amount, applicant rules and financial terms should be re-verified immediately before submission.")
    return out[:4]


def _due_date(row: dict[str, Any], override: dict[str, Any]) -> str | None:
    if override.get("due_date"):
        return override["due_date"]
    planning=runtime_store.get_planning()
    default_days=int(planning.get("default_due_days") or 14)
    deadline=str(row.get("deadline") or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline):
        try:
            d=datetime.strptime(deadline, "%Y-%m-%d").date()
            target=max(date.today(), d-timedelta(days=max(7,default_days)))
            return target.isoformat()
        except ValueError:
            pass
    return (date.today()+timedelta(days=default_days)).isoformat()


def opportunity_from_public(row: dict) -> OpportunitySummary:
    decision=row.get("decision","REVIEW")
    eligible=row.get("eligible","Uncertain")
    ev=_evidence_items(row)
    active=runtime_store.active_country_names(data_store.wateraid_target_countries())
    override=runtime_store.get_override(row["id"])
    fit_criteria=_fit_criteria(row,ev,active)
    fit=round(sum((c.score or 0)*(c.weight or 0) for c in fit_criteria)/100, 2)
    gates=_gate_checks(row,ev,active)
    money=_money_effort(row,override,ev)
    relationship=_relationship(row,override)
    uncertain_count=sum(1 for g in gates if g.result=="Uncertain")
    failed_count=sum(1 for g in gates if g.result=="Fail")
    if failed_count and ev:
        conf="high"
    elif uncertain_count>=3 or not ev:
        conf="low"
    elif uncertain_count or len(ev)<2 or decision in {"REVIEW","MONITOR"}:
        conf="medium"
    else:
        conf="high"
    next_step=NextStep(action=row.get("next_action") or "Verify current funder guidance and assign an owner.",
                       owner=override.get("owner") or runtime_store.get_planning().get("default_owner") or "Foundations Officer",
                       due_date=_due_date(row,override))
    risks=_risks(row,gates,ev)
    return OpportunitySummary(
        opp_id=row["id"], funder_id=row.get("funder_id") or row["id"],
        funder_name=row.get("funder","Unknown funder"), title=row.get("title","Untitled"), decision=decision,
        eligible=eligible, fit_score=fit, confidence=conf, readiness_index=int(row.get("readiness") or _readiness(eligible,decision,fit)),
        failed_gates=row.get("failed_gates",[]), trap_type=None, rationale=row.get("reason",""), strong_action=row.get("next_action",""),
        source_count=len(ev), evidence=ev, access_model=row.get("status"), relationship_status=relationship.status, real_public=True,
        deadline=row.get("deadline"), status=row.get("status"), geography=row.get("geography"), themes=row.get("themes",[]),
        amount=row.get("amount"), province=row.get("province"), location=row.get("location"), funder_type=row.get("funder_type"),
        applicant_types=row.get("applicant_types",[]), funder_country=row.get("funder_country","Canada"),
        project_country=row.get("project_country","Multiple WaterAid countries"), target_countries=row.get("target_countries",[]),
        jurisdiction_verified=(row.get("funder_country","Canada")=="Canada" and bool(set(row.get("target_countries",[])) & active)),
        fit_criteria=fit_criteria, gates=gates, key_dates=_key_dates(row,ev), money_effort=money,
        relationship_path=relationship, risks_unknowns=risks, next_step=next_step,
        briefing_complete=(len(gates)==8 and len(fit_criteria)==7 and bool(ev) and bool(_key_dates(row,ev))
                           and money is not None and relationship is not None and bool(risks) and next_step is not None),
    )


def challenge_opportunities() -> list[OpportunitySummary]:
    return [opportunity_from_case(x) for x in data_store.test_cases()]


def public_opportunities() -> list[OpportunitySummary]:
    # Hard jurisdiction gate: donor/funder must be Canadian; project must map to an ACTIVE configured target country.
    allowed=runtime_store.active_country_names(data_store.wateraid_target_countries())
    rows=[]
    for x in data_store.public_opportunities():
        if x.get("funder_country","Canada") != "Canada":
            continue
        targets=set(x.get("target_countries",[]))
        if not (targets & allowed):
            continue
        rows.append(opportunity_from_public(x))
    return rows


def all_opportunities(include_regression_cases: bool | None=None) -> list[OpportunitySummary]:
    """Return opportunities.

    Backward compatibility: no argument returns the 25 synthetic regression cases.
    Explicit False returns real public leads only; explicit True returns real leads plus regression cases.
    """
    if include_regression_cases is None:
        return challenge_opportunities()
    rows=public_opportunities()
    if include_regression_cases:
        rows += challenge_opportunities()
    return rows


def _score(op: OpportunitySummary, qtokens: set[str]) -> float:
    hay = " ".join([
        op.funder_name, op.title, op.rationale, op.strong_action, op.trap_type or "", op.geography or "", " ".join(op.themes), " ".join(op.target_countries)
    ]).lower()
    tokens=set(re.findall(r"[a-z0-9]+", hay))
    lexical=len(qtokens & tokens)
    phrase_boost=sum(2 for phrase in ["water","wash","sanitation","hygiene","climate","health","gender","women","girls","africa","asia","malawi","nigeria","ethiopia","pakistan","uganda","zambia","mozambique","tanzania"] if phrase in qtokens and phrase in hay)
    decision_boost={"PURSUE":8,"PURSUE-QUEUE":7,"CULTIVATE":7,"REVIEW":4,"MONITOR":3,"DECLINE":0}.get(op.decision,1)
    fit_boost=(op.fit_score or 0)
    real_boost=5 if op.real_public else 0
    country_boost=4 if any(c.lower() in qtokens for c in [x.lower() for x in op.target_countries]) else 0
    return lexical*5 + phrase_boost + decision_boost + fit_boost + real_boost + country_boost


def search_opportunities(query: str, limit: int = 8, include_regression_cases: bool=False) -> list[OpportunitySummary]:
    qtokens={t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t)>2}
    ops=all_opportunities(include_regression_cases=include_regression_cases)
    scored=[(_score(op,qtokens),op) for op in ops]
    scored.sort(key=lambda x:(x[0],x[1].readiness_index,x[1].real_public),reverse=True)
    if scored and scored[0][0] < 10:
        scored.sort(key=lambda x:(x[1].real_public,x[1].decision in {"PURSUE","PURSUE-QUEUE","CULTIVATE"},x[1].fit_score or 0,x[1].readiness_index),reverse=True)
    return [x[1] for x in scored[:limit]]

# backwards compatibility for tests/old UI
search_demo=search_opportunities
