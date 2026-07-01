"""
integrity.py — authenticity / honeypot-resistance checks.

IMPORTANT CALIBRATION NOTE (read before changing thresholds):
candidate_schema.json does NOT include some fields that an earlier draft
architecture assumed (e.g. a company "founding date" for WHOIS-style company
age checks). Every check below only uses fields that actually exist in the
real schema, and thresholds were calibrated against the 50-row
sample_candidates.json bundle to avoid false-positiving ordinary, plausible
profiles (e.g. someone whose part-time job started ~2 years before their
delayed graduation is normal and should NOT be penalized the same as someone
whose "career" started 8 years before they graduated).

We deliberately do NOT hard-delete candidates from the ranking pool over
integrity concerns (the submission spec requires exactly 100 output rows
every time; nuking too aggressively risks an under-filled pool). Instead we
compute a multiplicative `integrity_multiplier` in (0, 1] that collapses
toward ~0.02 for profiles with clear, unambiguous logical impossibilities,
and applies smaller, stacking discounts for softer red flags. A profile that
is merely a weak fit on skills will already rank low on relevance; this
module's job is narrowly to make sure profiles that are *internally
contradictory* never outrank profiles that are merely less impressive.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Tuple

HARD_FLOOR = 0.02
CAREER_BEFORE_COLLEGE_YEARS = 5  # >= this many years before graduation = hard flag
ZERO_DURATION_EXPERT_COUNT_HARD = 5  # matches spec's own honeypot example ("expert in 10 skills, 0 months")
ZERO_DURATION_EXPERT_COUNT_SOFT = 2
YOE_MONTHS_MISMATCH_HARD = 48  # 4 years off between claimed YoE and summed career months
YOE_MONTHS_MISMATCH_SOFT = 24


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def evaluate_integrity(candidate: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Returns (integrity_multiplier, list_of_flag_strings) for logging/reasoning."""
    flags: List[str] = []
    multiplier = 1.0

    career = candidate.get("career_history") or []
    education = candidate.get("education") or []
    skills = candidate.get("skills") or []
    signals = candidate.get("redrob_signals") or {}
    profile = candidate.get("profile") or {}

    # --- Hard checks: unambiguous logical impossibilities ---------------

    # 1. Employment chronology: start after end.
    for ch in career:
        sd, ed = _parse_date(ch.get("start_date")), _parse_date(ch.get("end_date"))
        if sd and ed and sd > ed:
            flags.append("invalid_chronology")
            multiplier = min(multiplier, HARD_FLOOR)
            break

    # 2. Education timeline: end before start.
    for e in education:
        sy, ey = e.get("start_year"), e.get("end_year")
        if isinstance(sy, int) and isinstance(ey, int) and ey < sy:
            flags.append("invalid_education_timeline")
            multiplier = min(multiplier, HARD_FLOOR)
            break

    # 3. Platform activity before signup — logically impossible.
    signup = _parse_date(signals.get("signup_date"))
    last_active = _parse_date(signals.get("last_active_date"))
    if signup and last_active and last_active < signup:
        flags.append("active_before_signup")
        multiplier = min(multiplier, HARD_FLOOR)

    # 4. Career started well before graduation (>= 5 years), with no
    #    part-time/intern signal in that role's description — i.e. not
    #    explainable as a normal pre-graduation internship.
    if education and career:
        grad_years = [e.get("end_year") for e in education if isinstance(e.get("end_year"), int)]
        if grad_years:
            earliest_grad = min(grad_years)
            for ch in career:
                sd = _parse_date(ch.get("start_date"))
                if sd is None:
                    continue
                gap = earliest_grad - sd.year
                if gap >= CAREER_BEFORE_COLLEGE_YEARS:
                    desc = (ch.get("description") or "").lower()
                    title = (ch.get("title") or "").lower()
                    explainable = any(
                        tok in desc or tok in title
                        for tok in ("intern", "part-time", "part time", "apprentice", "trainee")
                    )
                    if not explainable:
                        flags.append(f"career_before_college(gap={gap}y)")
                        multiplier = min(multiplier, HARD_FLOOR)
                        break

    # 5. Massive zero-duration expert/advanced skill stuffing.
    zero_dur_expert = [
        s.get("name") for s in skills
        if s.get("proficiency") in ("advanced", "expert") and (s.get("duration_months") or 0) == 0
    ]
    if len(zero_dur_expert) >= ZERO_DURATION_EXPERT_COUNT_HARD:
        flags.append(f"massive_zero_duration_stuffing({len(zero_dur_expert)})")
        multiplier = min(multiplier, HARD_FLOOR)
    elif len(zero_dur_expert) >= ZERO_DURATION_EXPERT_COUNT_SOFT:
        flags.append(f"zero_duration_expert_skills({len(zero_dur_expert)})")
        multiplier *= 0.6

    # --- Soft checks: plausibility discounts, not hard kills -------------

    # YoE vs. summed career_history duration_months.
    yoe = profile.get("years_of_experience")
    total_months = sum((ch.get("duration_months") or 0) for ch in career)
    if isinstance(yoe, (int, float)):
        claimed_months = yoe * 12
        diff = abs(claimed_months - total_months)
        if diff >= YOE_MONTHS_MISMATCH_HARD:
            flags.append(f"yoe_career_mismatch(diff_months={diff:.0f})")
            multiplier *= 0.25
        elif diff >= YOE_MONTHS_MISMATCH_SOFT:
            flags.append(f"yoe_career_minor_mismatch(diff_months={diff:.0f})")
            multiplier *= 0.8

    # Excessive expert inflation: 10+ skills all "expert".
    expert_count = sum(1 for s in skills if s.get("proficiency") == "expert")
    if expert_count >= 10:
        flags.append(f"excessive_expert_inflation({expert_count})")
        multiplier *= 0.7

    # Overlapping full-time concurrent roles beyond a normal handover window,
    # unless one side is explicitly freelance/self-employed.
    dated = [
        (_parse_date(ch.get("start_date")), _parse_date(ch.get("end_date")) or date.today(), ch)
        for ch in career
    ]
    dated = [d for d in dated if d[0] is not None]
    dated.sort(key=lambda x: x[0])
    for i in range(len(dated) - 1):
        s1, e1, c1 = dated[i]
        s2, e2, c2 = dated[i + 1]
        overlap_days = (e1 - s2).days
        if overlap_days > 90:
            names = f"{c1.get('company','')}/{c2.get('company','')}".lower()
            if "freelance" not in names and "self-employed" not in names and "independent" not in names:
                flags.append(f"overlapping_employment({overlap_days}d)")
                multiplier *= 0.85

    multiplier = max(HARD_FLOOR, min(1.0, multiplier))
    return multiplier, flags
