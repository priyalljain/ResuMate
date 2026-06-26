"""
Behavioral Signals Processor — ALL 23 redrob_signals

Signal index (from candidate_schema.json):
  1.  profile_completeness_score
  2.  signup_date                    ← WAS MISSING (now CHECK5 in auth + recency here)
  3.  last_active_date
  4.  open_to_work_flag
  5.  profile_views_received_30d
  6.  applications_submitted_30d
  7.  recruiter_response_rate
  8.  avg_response_time_hours
  9.  skill_assessment_scores
  10. connection_count
  11. endorsements_received
  12. notice_period_days
  13. expected_salary_range_inr_lpa  ← WAS MISSING (salary fit check)
  14. preferred_work_mode
  15. willing_to_relocate
  16. github_activity_score
  17. search_appearance_30d          ← WAS MISSING (market demand signal)
  18. saved_by_recruiters_30d
  19. interview_completion_rate
  20. offer_acceptance_rate
  21. verified_email
  22. verified_phone
  23. linkedin_connected

Returns dict with:
  multiplier: float [0.55, 1.15]
  location_score: float [0, 1]
  notice_score: float [0, 1]
  is_hireable: bool
  key_signals: dict for reasoning
"""

from __future__ import annotations
from datetime import date

TODAY = date.today()

PREFERRED_CITIES = frozenset({
    "pune", "noida", "bangalore", "bengaluru", "hyderabad",
    "mumbai", "delhi", "ncr", "gurgaon", "gurugram",
})
RELOCATION_CITIES = frozenset({
    "chennai", "kolkata", "ahmedabad", "jaipur", "indore",
    "coimbatore", "bhopal", "chandigarh", "vizag", "visakhapatnam",
})


def _days_since(date_str: str | None) -> int:
    if not date_str:
        return 999
    try:
        return (TODAY - date.fromisoformat(date_str)).days
    except (ValueError, TypeError):
        return 999


def compute_behavioral_multiplier(candidate: dict, jd_config=None) -> dict:
    """
    All 23 signals → composite multiplier [0.55, 1.15].
    jd_config: optional JDConfig for salary/location checks.
    """
    signals = candidate.get("redrob_signals", {})
    profile = candidate.get("profile", {})
    mult = 1.0

    # ── SIGNAL 3: last_active_date ────────────────────────────────
    days_inactive = _days_since(signals.get("last_active_date"))
    if days_inactive > 365:
        mult *= 0.60
    elif days_inactive > 180:
        mult *= 0.72
    elif days_inactive > 90:
        mult *= 0.85
    elif days_inactive > 30:
        mult *= 0.95

    # ── SIGNAL 2: signup_date (platform tenure = trust signal) ────
    days_since_signup = _days_since(signals.get("signup_date"))
    if days_since_signup > 365:
        mult *= 1.02   # Long-term platform user = committed
    elif days_since_signup < 7:
        mult *= 0.97   # Brand new — may be low quality profile

    # ── SIGNAL 4: open_to_work_flag ──────────────────────────────
    open_to_work = signals.get("open_to_work_flag", False)
    mult *= 1.04 if open_to_work else 0.96

    # ── SIGNAL 1: profile_completeness_score ─────────────────────
    completeness = signals.get("profile_completeness_score", 50.0)
    if completeness >= 90:
        mult *= 1.02
    elif completeness < 50:
        mult *= 0.92

    # ── SIGNAL 7: recruiter_response_rate ────────────────────────
    rr = signals.get("recruiter_response_rate", 0.5)
    if rr < 0.05:
        mult *= 0.72
    elif rr < 0.15:
        mult *= 0.82
    elif rr < 0.30:
        mult *= 0.92
    elif rr >= 0.70:
        mult *= 1.05
    elif rr >= 0.50:
        mult *= 1.02

    # ── SIGNAL 8: avg_response_time_hours ────────────────────────
    avg_rt = signals.get("avg_response_time_hours", 48)
    if avg_rt < 4:
        mult *= 1.02
    elif avg_rt > 168:
        mult *= 0.94

    # ── SIGNAL 5: profile_views_received_30d ─────────────────────
    views_30d = signals.get("profile_views_received_30d", 0)
    if views_30d > 100:
        mult *= 1.02   # High market demand

    # ── SIGNAL 17: search_appearance_30d (WAS MISSING) ───────────
    search_30d = signals.get("search_appearance_30d", 0)
    if search_30d > 200:
        mult *= 1.03   # Recruiters are actively finding this person
    elif search_30d > 50:
        mult *= 1.01

    # ── SIGNAL 18: saved_by_recruiters_30d ───────────────────────
    saved_30d = signals.get("saved_by_recruiters_30d", 0)
    if saved_30d > 5:
        mult *= 1.03   # Multiple recruiters saved = market validation

    # ── SIGNAL 6: applications_submitted_30d ─────────────────────
    apps_30d = signals.get("applications_submitted_30d", 0)
    if apps_30d > 5:
        mult *= 1.01

    # ── SIGNAL 9: skill_assessment_scores ────────────────────────
    assessment_count = len(signals.get("skill_assessment_scores", {}))
    if assessment_count >= 3:
        mult *= 1.02

    # ── SIGNAL 10-11: Social validation ──────────────────────────
    endorsements = signals.get("endorsements_received", 0)
    if endorsements > 100:
        mult *= 1.03
    elif endorsements > 50:
        mult *= 1.01

    # ── SIGNAL 16: github_activity_score ─────────────────────────
    github_score = signals.get("github_activity_score", -1)
    if github_score == -1:
        mult *= 0.95
    elif github_score >= 70:
        mult *= 1.08
    elif github_score >= 40:
        mult *= 1.04
    elif github_score >= 15:
        mult *= 1.01
    else:
        mult *= 0.97

    # ── SIGNAL 19: interview_completion_rate ─────────────────────
    icr = signals.get("interview_completion_rate", 0.5)
    if icr < 0.20:
        mult *= 0.80
    elif icr < 0.40:
        mult *= 0.90
    elif icr >= 0.80:
        mult *= 1.03

    # ── SIGNAL 20: offer_acceptance_rate ─────────────────────────
    oar = signals.get("offer_acceptance_rate", -1)
    if oar != -1:
        if oar < 0.10:
            mult *= 0.92
        elif oar >= 0.70:
            mult *= 1.02

    # ── SIGNAL 21-23: Verification ───────────────────────────────
    verify_count = sum([
        signals.get("verified_email", False),
        signals.get("verified_phone", False),
        signals.get("linkedin_connected", False),
    ])
    if verify_count == 0:
        mult *= 0.88
    elif verify_count == 1:
        mult *= 0.95
    elif verify_count == 3:
        mult *= 1.03

    # ── SIGNAL 13: expected_salary_range_inr_lpa (WAS MISSING) ───
    # Salary fit: if expected salary is way above market for 5-9yr ML role,
    # it signals misaligned expectations (harder to close)
    salary = signals.get("expected_salary_range_inr_lpa", {})
    sal_min = salary.get("min", 0) if isinstance(salary, dict) else 0
    sal_max = salary.get("max", 0) if isinstance(salary, dict) else 0
    if sal_min > 0:
        # Market rate for Senior ML Engineer in India: 25-55 LPA
        # Below 15 LPA = candidate undervalued (red flag in seniority)
        # Above 80 LPA = very expensive, may not get offer
        if sal_max > 80:
            mult *= 0.95  # High salary bar — harder to close
        elif sal_min < 15:
            mult *= 0.97  # Suspiciously low — may indicate mismatch

    # ── SIGNAL 14-15: Work mode & location (used for loc_score) ──
    work_mode = signals.get("preferred_work_mode", "flexible")
    willing_to_relocate = signals.get("willing_to_relocate", False)

    # Location score (separate axis, not in multiplier)
    location = (profile.get("location") or "").lower()
    country = (profile.get("country") or "").lower()

    # Use JD config if available, else defaults
    preferred_cities = PREFERRED_CITIES
    if jd_config and jd_config.preferred_cities:
        preferred_cities = frozenset(c.lower() for c in jd_config.preferred_cities)

    in_preferred = any(city in location for city in preferred_cities)
    in_india = (country == "india" or
                any(city in location for city in preferred_cities | RELOCATION_CITIES))

    if in_preferred:
        location_score = 1.00
    elif in_india and willing_to_relocate:
        location_score = 0.85
    elif in_india:
        location_score = 0.75
    elif willing_to_relocate:
        location_score = 0.45
    else:
        location_score = 0.20

    if work_mode == "remote":
        location_score *= 0.90

    # Notice period score
    notice_days = signals.get("notice_period_days", 90)
    ideal = getattr(jd_config, "notice_ideal_days", 30) if jd_config else 30
    if notice_days <= 15:
        notice_score = 1.00
    elif notice_days <= ideal:
        notice_score = 0.95
    elif notice_days <= 60:
        notice_score = 0.80
    elif notice_days <= 90:
        notice_score = 0.60
    elif notice_days <= 120:
        notice_score = 0.40
    else:
        notice_score = 0.25

    is_hireable = not (days_inactive > 180 and rr < 0.10)
    mult = max(0.55, min(1.15, mult))

    return {
        "multiplier": mult,
        "is_hireable": is_hireable,
        "location_score": location_score,
        "notice_score": notice_score,
        "active_days_ago": days_inactive,
        "key_signals": {
            "response_rate": rr,
            "notice_days": notice_days,
            "github_score": github_score,
            "days_inactive": days_inactive,
            "open_to_work": open_to_work,
            "interview_completion": icr,
            "verified_count": verify_count,
            "search_appearance_30d": search_30d,
            "salary_max_lpa": sal_max,
        },
    }
