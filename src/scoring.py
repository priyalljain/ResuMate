"""
scoring.py — the core ranking formula.

Design note: every penalty/bonus in this file is traceable to a specific
sentence in job_description.md (the actual released JD), not to an
unverified weight constant. Where I had to make a judgment call not spelled
out numerically in the JD (e.g. exactly how much to discount a 45-day notice
period), I picked a smooth, defensible curve and documented it inline rather
than inventing a precise-looking but arbitrary constant.

Pipeline per candidate:
  1. Build searchable text blobs (title text vs. narrative text) — kept
     SEPARATE on purpose. The JD's central anti-trap warning is "a candidate
     who has all the AI keywords listed as skills but whose title is
     'Marketing Manager' is not a fit" — so title coherence and skill
     presence are scored independently and only travel together if the
     narrative actually backs the skill up (orphan-skill discount).
  2. Score skill match against the domain's must_have / nice_to_have /
     anti_fit vocabulary, discounting any skill that's listed in the skills[]
     array but never mentioned in the candidate's own narrative text
     (headline/summary/career descriptions) — this is the direct fix for the
     keyword-stuffing trap demonstrated by sample_submission.csv ranking an
     "HR Manager with 9 AI core skills" #1.
  3. Apply the JD's explicit exclusion/penalty rules (pure research, recent
     LangChain-only AI experience, stale architects, title-chasers,
     services-only career, CV/speech-without-NLP, closed-source-only).
  4. Apply experience-band, education, location, and notice-period fit.
  5. Multiply by the integrity multiplier (integrity.py) and the behavioral
     availability multiplier built from redrob_signals.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

WEIGHTS = {
    "skill_match": 0.45,
    "title_coherence": 0.20,
    "production_evidence": 0.20,
    "experience_band": 0.15,
}


def _now():
    return datetime.now().date()


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def build_text_blobs(candidate: Dict[str, Any]) -> Tuple[str, str]:
    """Returns (title_text, narrative_text), both lowercased."""
    profile = candidate.get("profile") or {}
    career = candidate.get("career_history") or []

    title_parts = [profile.get("current_title") or ""] + [c.get("title") or "" for c in career]
    title_text = " | ".join(title_parts).lower()

    narrative_parts = [
        profile.get("headline") or "",
        profile.get("summary") or "",
    ] + [c.get("description") or "" for c in career]
    narrative_text = " ".join(narrative_parts).lower()

    return title_text, narrative_text


def score_skills(candidate: Dict[str, Any], cfg: Dict[str, Any], narrative_text: str) -> Dict[str, Any]:
    skills = candidate.get("skills") or []
    must_have = cfg.get("must_have", {})
    nice_have = cfg.get("nice_to_have", {})
    anti_fit = cfg.get("anti_fit_cv_speech_robotics", {})
    nlp_rescue = cfg.get("nlp_ir_rescue_terms", {})

    matched_must, matched_nice, orphaned, anti_hits, nlp_hits = [], [], [], [], []
    must_score, nice_score, anti_score = 0.0, 0.0, 0.0

    for s in skills:
        name = (s.get("name") or "").lower().strip()
        if not name:
            continue
        mentioned_in_narrative = name in narrative_text
        if name in must_have:
            credit = must_have[name] if mentioned_in_narrative else must_have[name] * 0.3
            must_score += credit
            (matched_must if mentioned_in_narrative else orphaned).append(s.get("name"))
        if name in nice_have:
            credit = nice_have[name] if mentioned_in_narrative else nice_have[name] * 0.3
            nice_score += credit
            if mentioned_in_narrative:
                matched_nice.append(s.get("name"))
        if name in anti_fit:
            anti_score += anti_fit[name]
            anti_hits.append(s.get("name"))
        if name in nlp_rescue:
            nlp_hits.append(s.get("name"))

    # normalize: cap contributions so one candidate can't blow past 1.0 just
    # by having many skills — we care about coverage of the *important*
    # terms, not raw count.
    must_norm = min(1.0, must_score / 3.0)   # ~3 strong must-have hits = full credit
    nice_norm = min(0.3, nice_score / 6.0)   # nice-to-haves cap their contribution at 0.3
    skill_score = min(1.0, must_norm + nice_norm)

    # CV/speech/robotics-without-NLP penalty (explicit JD exclusion).
    cv_speech_penalty = 1.0
    if anti_hits and not nlp_hits and must_score < 0.5:
        cv_speech_penalty = 0.5

    return {
        "skill_score": skill_score,
        "matched_must": matched_must,
        "matched_nice": matched_nice,
        "orphaned_skills": orphaned,
        "anti_fit_hits": anti_hits,
        "cv_speech_penalty": cv_speech_penalty,
    }


def score_title_coherence(title_text: str, cfg: Dict[str, Any]) -> float:
    sigs = cfg.get("title_signals", [])
    return 1.0 if any(sig in title_text for sig in sigs) else 0.25


def score_production_evidence(narrative_text: str, cfg: Dict[str, Any]) -> float:
    terms = cfg.get("production_evidence_terms", [])
    hits = sum(1 for t in terms if t in narrative_text)
    return min(1.0, 0.25 + 0.15 * hits)  # baseline 0.25, +0.15 per distinct evidence term, capped at 1.0


def score_experience_band(yoe) -> float:
    """Smooth curve centered on the JD's 5-9yr soft band -- the JD is
    explicit that this is a range, not a hard requirement."""
    if not isinstance(yoe, (int, float)):
        return 0.5
    if 5 <= yoe <= 9:
        return 1.0
    if yoe < 5:
        if yoe >= 3:
            return 0.7 + 0.3 * (yoe - 3) / 2.0
        return max(0.25, 0.7 * (yoe / 3.0))
    if yoe <= 12:
        return 1.0 - 0.2 * (yoe - 9) / 3.0
    return max(0.45, 0.8 - 0.04 * (yoe - 12))


def score_education(education: List[Dict[str, Any]]) -> float:
    """The JD is explicitly anti-pedigree ('skills are teachable; the rest
    mostly isn't'), so this carries a small weight and a gentle curve -- not
    the steep institutional bias a naive ranker might apply."""
    if not education:
        return 0.85
    tier_map = {"tier_1": 1.0, "tier_2": 0.95, "tier_3": 0.9, "tier_4": 0.85, "unknown": 0.85}
    tiers = [tier_map.get(e.get("tier"), 0.85) for e in education]
    return max(tiers) if tiers else 0.85


def score_location(profile: Dict[str, Any], signals: Dict[str, Any], cfg: Dict[str, Any]) -> float:
    required_country = cfg.get("country_required")
    if not required_country:
        return 1.0
    loc = (profile.get("location") or "").lower()
    country = (profile.get("country") or "").lower()
    willing = bool(signals.get("willing_to_relocate"))
    preferred = cfg.get("preferred_locations", [])
    welcome = cfg.get("welcome_locations", [])

    if any(p in loc for p in preferred):
        return 1.0
    if any(w in loc for w in welcome):
        return 0.95
    if country == required_country:
        return 0.85  # in-country but not a named hub city
    return 0.55 if willing else 0.35  # outside India: no visa sponsorship, case-by-case


def score_notice_period(signals: Dict[str, Any]) -> float:
    days = signals.get("notice_period_days")
    if days is None:
        return 0.9
    if days <= 30:
        return 1.0
    if days <= 60:
        return 0.92
    if days <= 90:
        return 0.82
    return 0.7


def score_behavioral_multiplier(signals: Dict[str, Any]) -> float:
    m = 1.0
    last_active = _parse_date(signals.get("last_active_date"))
    if last_active:
        days_since = (_now() - last_active).days
        if days_since > 365:
            m *= 0.55
        elif days_since > 180:
            m *= 0.75
        elif days_since > 90:
            m *= 0.92

    if signals.get("open_to_work_flag"):
        m *= 1.05

    rr = signals.get("recruiter_response_rate")
    if isinstance(rr, (int, float)):
        if rr < 0.05:
            m *= 0.75
        elif rr < 0.15:
            m *= 0.9
        elif rr > 0.6:
            m *= 1.05

    icr = signals.get("interview_completion_rate")
    if isinstance(icr, (int, float)) and icr < 0.2:
        m *= 0.85

    gh = signals.get("github_activity_score")
    if isinstance(gh, (int, float)) and gh >= 70:
        m *= 1.08

    verified = sum([
        bool(signals.get("verified_email")),
        bool(signals.get("verified_phone")),
        bool(signals.get("linkedin_connected")),
    ])
    if verified == 3:
        m *= 1.02

    return max(0.45, min(1.2, m))


def apply_jd_exclusions(candidate: Dict[str, Any], cfg: Dict[str, Any], title_text: str,
                          narrative_text: str) -> Tuple[float, List[str]]:
    """The explicit 'things we explicitly do NOT want' section of the JD,
    translated into multiplicative penalty factors. Returns (penalty, flags)."""
    penalty = 1.0
    flags: List[str] = []
    career = candidate.get("career_history") or []
    profile = candidate.get("profile") or {}

    # Pure research-only, no production deployment.
    research_cfg = cfg.get("research_only_signals", {})
    research_industries = research_cfg.get("industries", [])
    research_titles = research_cfg.get("titles", [])
    industries = [(c.get("industry") or "").lower() for c in career] + [
        (profile.get("current_industry") or "").lower()
    ]
    titles_all = [(c.get("title") or "").lower() for c in career] + [
        (profile.get("current_title") or "").lower()
    ]
    if career and research_industries:
        all_research = all(any(ri in ind for ri in research_industries) for ind in industries if ind)
        any_research_title = any(any(rt in t for rt in research_titles) for t in titles_all)
        if all_research or (any_research_title and not any(
            t in narrative_text for t in cfg.get("production_evidence_terms", [])
        )):
            penalty *= 0.15
            flags.append("pure_research_no_production")

    # Recent LangChain/OpenAI-only "AI experience" without older ML production skills.
    skills = candidate.get("skills") or []
    ai_skill_names = {(s.get("name") or "").lower(): s for s in skills}
    has_langchain_or_promptonly = any(
        k in ai_skill_names for k in ("langchain", "prompt engineering")
    )
    deep_ml_terms = set(cfg.get("must_have", {})) - {"langchain", "prompt engineering", "llm", "llms", "python"}
    has_older_deep_ml = any(
        name in deep_ml_terms and (s.get("duration_months") or 0) >= 18
        for name, s in ai_skill_names.items()
    )
    if has_langchain_or_promptonly and not has_older_deep_ml:
        all_ai_recent = all(
            (s.get("duration_months") or 0) < 12
            for name, s in ai_skill_names.items()
            if name in cfg.get("must_have", {}) or name in cfg.get("nice_to_have", {})
        ) if ai_skill_names else False
        if all_ai_recent:
            penalty *= 0.5
            flags.append("recent_langchain_only_ai_experience")

    # Stale architect: long-tenured pure architecture/lead/management title
    # with no recent hands-on production evidence in the narrative.
    current_title = (profile.get("current_title") or "").lower()
    architect_words = ("architect", "tech lead", "engineering manager", "director", "head of engineering")
    if any(w in current_title for w in architect_words):
        if not any(t in narrative_text for t in cfg.get("production_evidence_terms", [])):
            penalty *= 0.8
            flags.append("possible_stale_architect")

    # Title-chasers: 3+ short stints (<18mo) with escalating seniority words.
    seniority_words = cfg.get("title_chaser_seniority_words", [])
    short_stints = [c for c in career if (c.get("duration_months") or 0) < 18]
    seniority_titles = [c for c in career if any(w in (c.get("title") or "").lower() for w in seniority_words)]
    if len(career) >= 3 and len(short_stints) >= 3 and len(seniority_titles) >= 2:
        penalty *= 0.85
        flags.append("possible_title_chaser")

    # Services-only career with no narrative evidence of building the kind
    # of system this JD needs (JD forgives services background IF there's
    # other strong signal).
    service_industries = set(cfg.get("service_firm_industries", []))
    service_names = set(cfg.get("service_firm_names", []))
    if career and service_industries:
        def is_service(c):
            ind = (c.get("industry") or "").lower()
            comp = (c.get("company") or "").lower()
            return any(si in ind for si in service_industries) or any(sn in comp for sn in service_names)

        if all(is_service(c) for c in career):
            has_evidence = any(t in narrative_text for t in cfg.get("production_evidence_terms", []))
            if not has_evidence:
                penalty *= 0.6
                flags.append("services_only_no_evidence")

    # Closed-source-only 5+ years, no external validation signal.
    yoe = profile.get("years_of_experience")
    certs = candidate.get("certifications") or []
    gh_score = (candidate.get("redrob_signals") or {}).get("github_activity_score")
    if isinstance(yoe, (int, float)) and yoe >= 5 and not certs and (gh_score is None or gh_score <= 0):
        penalty *= 0.85
        flags.append("closed_source_no_external_validation")

    return penalty, flags


def score_candidate(candidate: Dict[str, Any], domain: str, cfg: Dict[str, Any],
                     integrity_multiplier: float) -> Dict[str, Any]:
    title_text, narrative_text = build_text_blobs(candidate)
    profile = candidate.get("profile") or {}
    signals = candidate.get("redrob_signals") or {}
    education = candidate.get("education") or []

    skill_res = score_skills(candidate, cfg, narrative_text)
    title_coh = score_title_coherence(title_text, cfg)
    prod_evid = score_production_evidence(narrative_text, cfg)
    exp_band = score_experience_band(profile.get("years_of_experience"))
    edu_score = score_education(education)
    loc_mod = score_location(profile, signals, cfg)
    notice_mod = score_notice_period(signals)
    behavioral_mult = score_behavioral_multiplier(signals)
    exclusion_penalty, exclusion_flags = apply_jd_exclusions(candidate, cfg, title_text, narrative_text)

    domain_fit = (
        WEIGHTS["skill_match"] * skill_res["skill_score"]
        + WEIGHTS["title_coherence"] * title_coh
        + WEIGHTS["production_evidence"] * prod_evid
        + WEIGHTS["experience_band"] * exp_band
    )
    # education is a light additive nudge, not a primary axis (anti-pedigree JD).
    domain_fit = min(1.0, domain_fit * (0.92 + 0.08 * edu_score))

    final_score = (
        domain_fit
        * exclusion_penalty
        * skill_res["cv_speech_penalty"]
        * loc_mod
        * notice_mod
        * behavioral_mult
        * integrity_multiplier
    )

    return {
        "final_score": max(0.0, min(1.0, final_score)),
        "domain_fit": domain_fit,
        "skill_score": skill_res["skill_score"],
        "matched_must": skill_res["matched_must"],
        "matched_nice": skill_res["matched_nice"],
        "orphaned_skills": skill_res["orphaned_skills"],
        "anti_fit_hits": skill_res["anti_fit_hits"],
        "title_coherence": title_coh,
        "production_evidence": prod_evid,
        "experience_band_fit": exp_band,
        "education_score": edu_score,
        "location_modifier": loc_mod,
        "notice_modifier": notice_mod,
        "behavioral_multiplier": behavioral_mult,
        "exclusion_penalty": exclusion_penalty,
        "exclusion_flags": exclusion_flags,
    }
