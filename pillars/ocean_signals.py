"""
Pillar 5: OCEAN Personality Proxy

OCEAN (Big Five) personality dimensions inferred from platform behavioral signals.
Each dimension is approximated from observable proxy signals — no direct questionnaire.

Dimensions:
  O — Openness to Experience
  C — Conscientiousness
  E — Extraversion
  A — Agreeableness
  N — Neuroticism (inverse: stability is good)

Why OCEAN for hiring?
- Research (Barrick & Mount 1991, Tett et al 1991) shows:
  Conscientiousness predicts performance across ALL job types (r=0.22-0.31)
  Openness predicts learning speed and adaptability (critical for fast-moving ML roles)
  Extraversion predicts performance in collaborative/leadership roles
  Neuroticism (low) predicts reliability and interview completion

For a Senior ML Engineer building production systems:
  High C (conscientiousness) = ships reliably, documents well, stable tenure
  High O (openness) = learns new tools (FAISS→Qdrant), experiments
  Medium E (extraversion) = can communicate with stakeholders
  Low N (stability) = doesn't ghost interviews, completes tasks

Returns:
  ocean_score: float [0.0, 1.0] — weighted composite
  ocean_profile: dict of 5 dimension scores for reasoning
"""

from __future__ import annotations

from datetime import date

TODAY = date.today()


def _days_since(date_str: str | None) -> int:
    if not date_str:
        return 999
    try:
        d = date.fromisoformat(date_str)
        return (TODAY - d).days
    except (ValueError, TypeError):
        return 999


def _openness(candidate: dict) -> float:
    """
    Openness — curiosity, breadth, learning new things.

    Proxies:
    + Diverse skill portfolio (breadth across different tech families)
    + Active GitHub (experimentation signal)
    + Certifications (intentional learning)
    + Multiple industries across career
    + Recent platform activity (staying current)
    """
    signals = candidate.get("redrob_signals", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    certs = candidate.get("certifications", [])

    score = 0.0

    # Skill breadth: distinct tech families
    tech_families = {
        "ml": {"pytorch", "tensorflow", "sklearn", "xgboost", "lightgbm"},
        "nlp": {"bert", "nlp", "transformers", "hugging face", "spacy"},
        "retrieval": {"faiss", "elasticsearch", "qdrant", "pinecone", "weaviate"},
        "cloud": {"aws", "gcp", "azure", "docker", "kubernetes"},
        "data": {"spark", "kafka", "sql", "airflow", "dbt"},
        "generative": {"llm", "gpt", "rag", "fine-tuning", "embeddings"},
    }
    skill_names_lower = {s.get("name", "").lower() for s in skills}
    families_present = sum(
        1 for family, fskills in tech_families.items()
        if skill_names_lower & fskills
    )
    score += min(0.35, families_present * 0.07)

    # GitHub activity (experimentation)
    gh = signals.get("github_activity_score", -1)
    if gh >= 60:
        score += 0.25
    elif gh >= 30:
        score += 0.15
    elif gh >= 10:
        score += 0.08
    elif gh == -1:
        score += 0.0

    # Certifications (intentional upskilling)
    score += min(0.20, len(certs) * 0.06)

    # Industry diversity across career
    industries = {r.get("industry", "").lower() for r in career}
    score += min(0.15, (len(industries) - 1) * 0.05)

    # Recent activity (staying current)
    days_inactive = _days_since(signals.get("last_active_date"))
    if days_inactive <= 30:
        score += 0.05

    return min(1.0, score)


def _conscientiousness(candidate: dict) -> float:
    """
    Conscientiousness — reliability, thoroughness, follow-through.

    Proxies:
    + Profile completeness (takes care of presentation)
    + Interview completion rate (shows up when committed)
    + Low average response time (organized, responsive)
    + Long average tenure (finishes what they start)
    + Verified email + phone (attention to detail)
    + Offer acceptance rate (doesn't accept and renege)
    """
    signals = candidate.get("redrob_signals", {})
    career = candidate.get("career_history", [])

    score = 0.0

    # Profile completeness
    completeness = signals.get("profile_completeness_score", 50)
    score += (completeness / 100) * 0.20

    # Interview completion rate
    icr = signals.get("interview_completion_rate", 0.5)
    score += icr * 0.25

    # Response time (organized people respond faster)
    avg_rt = signals.get("avg_response_time_hours", 48)
    if avg_rt <= 4:
        score += 0.15
    elif avg_rt <= 24:
        score += 0.10
    elif avg_rt <= 72:
        score += 0.05

    # Tenure stability
    if career:
        avg_tenure = sum(r.get("duration_months", 0) for r in career) / len(career)
        score += min(0.20, avg_tenure / 36 * 0.20)

    # Verification
    verify = sum([
        signals.get("verified_email", False),
        signals.get("verified_phone", False),
        signals.get("linkedin_connected", False),
    ])
    score += verify * 0.04

    # Offer acceptance rate (doesn't waste recruiter time)
    oar = signals.get("offer_acceptance_rate", -1)
    if oar >= 0.70:
        score += 0.06
    elif 0 <= oar < 0.20:
        score -= 0.05

    return min(1.0, max(0.0, score))


def _extraversion(candidate: dict) -> float:
    """
    Extraversion — engagement, network, visibility.
    Moderate is ideal for ML engineers (not fully introverted, not fully sales-y).

    Proxies:
    + Connection count (network size)
    + Endorsements received (others invest in them)
    + Profile views (others seek them out)
    + Applications submitted (proactive outreach)
    """
    signals = candidate.get("redrob_signals", {})

    score = 0.0

    # Connection count
    connections = signals.get("connection_count", 0)
    score += min(0.30, connections / 500 * 0.30)

    # Endorsements (others validate them)
    endorsements = signals.get("endorsements_received", 0)
    score += min(0.25, endorsements / 100 * 0.25)

    # Profile views (market interest)
    views = signals.get("profile_views_received_30d", 0)
    score += min(0.25, views / 200 * 0.25)

    # Proactive applications
    apps = signals.get("applications_submitted_30d", 0)
    score += min(0.20, apps / 10 * 0.20)

    return min(1.0, score)


def _agreeableness(candidate: dict) -> float:
    """
    Agreeableness — cooperation, responsiveness, non-toxic behavior.

    Proxies:
    + Recruiter response rate (cooperative with process)
    + No ghost signals (doesn't waste others' time)
    + Endorsements given vs received ratio (reciprocal behavior)

    For senior ML roles: medium-high agreeableness is ideal.
    Very low = difficult to work with. Very high = no pushback.
    """
    signals = candidate.get("redrob_signals", {})

    score = 0.0

    # Recruiter response rate (most direct proxy for agreeableness in hiring context)
    rr = signals.get("recruiter_response_rate", 0.5)
    score += rr * 0.50

    # Interview completion (doesn't ghost)
    icr = signals.get("interview_completion_rate", 0.5)
    score += icr * 0.30

    # Response time (considerate of others' time)
    avg_rt = signals.get("avg_response_time_hours", 48)
    if avg_rt <= 12:
        score += 0.20
    elif avg_rt <= 48:
        score += 0.10
    else:
        score += 0.0

    return min(1.0, score)


def _stability(candidate: dict) -> float:
    """
    Emotional Stability (inverse of Neuroticism).
    High stability = predictable, consistent, reliable under pressure.

    Proxies:
    + Consistent tenure (not fleeing jobs)
    + Consistent platform activity (not erratic)
    + No offer renege pattern
    + Notice period alignment (realistic expectations)
    """
    signals = candidate.get("redrob_signals", {})
    career = candidate.get("career_history", [])

    score = 0.5  # Neutral baseline

    # Tenure consistency (low std dev in role durations = stable)
    if career:
        durations = [r.get("duration_months", 0) for r in career]
        avg = sum(durations) / len(durations)
        variance = sum((d - avg) ** 2 for d in durations) / len(durations)
        std_dev = variance ** 0.5

        if std_dev < 6:
            score += 0.20  # Very consistent
        elif std_dev < 12:
            score += 0.10
        elif std_dev > 24:
            score -= 0.10  # Erratic

    # No offer-renege pattern
    oar = signals.get("offer_acceptance_rate", -1)
    if oar >= 0.80:
        score += 0.15
    elif 0 <= oar < 0.30:
        score -= 0.10

    # Notice period realism (knows their constraints)
    notice = signals.get("notice_period_days", 60)
    if 15 <= notice <= 60:
        score += 0.10  # Realistic expectations
    elif notice > 120:
        score -= 0.05  # May indicate unclear situation

    # Active but not frantic (too many applications = anxiety signal)
    apps = signals.get("applications_submitted_30d", 0)
    if 1 <= apps <= 8:
        score += 0.05
    elif apps > 20:
        score -= 0.05

    return min(1.0, max(0.0, score))


def compute_ocean_score(candidate: dict) -> dict:
    """
    Compute all 5 OCEAN dimensions and return composite.

    For Senior ML Engineer role weights:
      C (conscientiousness) = 0.35 — most predictive of job performance
      O (openness)          = 0.30 — fast-moving ML field needs learners
      A (agreeableness)     = 0.15 — team player, not a lone wolf
      E (extraversion)      = 0.12 — visible, but not sales-y
      N (stability)         = 0.08 — reliable, predictable

    Returns dict with:
      ocean_score: float [0.0, 1.0]
      dimensions: dict of 5 scores
    """
    O = _openness(candidate)
    C = _conscientiousness(candidate)
    E = _extraversion(candidate)
    A = _agreeableness(candidate)
    N = _stability(candidate)

    # Role-specific weights for Senior ML Engineer
    composite = (
        0.35 * C
        + 0.30 * O
        + 0.15 * A
        + 0.12 * E
        + 0.08 * N
    )

    return {
        "ocean_score": min(1.0, max(0.0, composite)),
        "dimensions": {
            "openness": round(O, 3),
            "conscientiousness": round(C, 3),
            "extraversion": round(E, 3),
            "agreeableness": round(A, 3),
            "stability": round(N, 3),
        },
    }
