"""
Pillar 1: Authenticity & Integrity Engine — v3 FINAL

Incorporates ALL checks from:
  - Original system (v2): 6 checks
  - Antigravity analysis (find_all_honeypots.py, scan_more.py,
    check_redrob.py, count_anomalies.py, check_zero_dur_skills.py):
    5 additional checks

COMPLETE CHECK LIST (11 total):
  Hard honeypots (score = 0.0, excluded from heap):
    1. Expert/Advanced proficiency + duration_months == 0
    2. career_total_months < (yoe * 12 - 24)  [antigravity Rule 2]
    3. yoe < 2.0 AND career_total > 60 months  [reverse mismatch]
    4. Career start date > end date (invalid date)  [antigravity find_all]
    5. last_active_date < signup_date  [antigravity find_all]
    6. Career starts 5+ years before college start  [antigravity scan_more]
    7. yoe > (2026 - graduation_year + 4 + 2)  [antigravity scan_more]

  Soft penalties (penalty_multiplier reduction, score NOT zeroed):
    8. Keyword stuffer: non-tech title + ≥3 AI skills  → × 0.10
    9. Entire career at services firms  → × 0.15
   10. Excessive experts: ≥10 expert skills  → × 0.10–0.88
   11. ≥5 skills with zero duration (any level)  → × 0.80
       (antigravity: check_zero_dur_skills.py found this separately)

Returns AuthenticityResult TypedDict.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict

TODAY = date.today()
CURRENT_YEAR = TODAY.year   # 2026

SERVICES_FIRMS = frozenset({
    "tcs", "tata consultancy", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "tech mahindra", "hexaware",
    "mphasis", "ltimindtree", "mindtree",
})

AI_SKILL_NAMES = frozenset({
    "rag", "llm", "embeddings", "vector database", "faiss", "pinecone",
    "weaviate", "qdrant", "milvus", "sentence transformers", "sbert",
    "nlp", "natural language processing", "information retrieval",
    "fine-tuning", "bert", "gpt", "transformers", "hugging face transformers",
    "bge", "e5", "ranking", "learning to rank",
})

NON_TECH_TITLE_KW = frozenset({
    "marketing manager", "sales executive", "sales manager", "hr manager",
    "content writer", "graphic designer", "ux designer", "ui designer",
    "scrum master", "accountant", "customer support", "civil engineer",
    "mechanical engineer", "supply chain", "procurement", "finance manager",
    "operations manager", "project manager", "business analyst",
    "customer success", "business development",
})

TECH_TITLE_KW = frozenset({
    "engineer", "developer", "scientist", "architect", "researcher",
    "analyst", "data", "ml", "ai", "nlp", "backend", "software",
    "sre", "devops", "platform", "infrastructure", "lead",
})


class AuthenticityResult(TypedDict):
    is_honeypot: bool
    honeypot_reasons: list
    authenticity_score: float
    penalty_multiplier: float


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _is_services(company: str) -> bool:
    co = company.lower().strip()
    return any(sf in co for sf in SERVICES_FIRMS)


def _parse_date(d_str: str | None) -> datetime | None:
    """Parse YYYY-MM-DD date string. Returns None on failure."""
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────
# HARD HONEYPOT CHECKS  (penalty = 0.0 → excluded from heap)
# ─────────────────────────────────────────────────────────────

def _check1_skill_zero_duration(skills: list) -> tuple[list, float]:
    """
    CHECK 1 (antigravity Rule 1 + implementation plan):
    Expert/Advanced proficiency with duration_months == 0.
    Impossible: you cannot be expert in something you've never used.
    """
    bad = [
        s["name"] for s in skills
        if s.get("proficiency") in ("expert", "advanced")
        and s.get("duration_months", 1) == 0
    ]
    if bad:
        return [f"Expert/Advanced + 0 duration_months: {bad[:4]}"], 0.0
    return [], 1.0


def _check2_yoe_career_mismatch(profile: dict, career: list) -> tuple[list, float]:
    """
    CHECK 2 (antigravity Rule 2 / count_anomalies.py):
    total career months < (yoe * 12 - 24). Hard honeypot.
    """
    yoe = profile.get("years_of_experience", 0)
    total_months = sum(r.get("duration_months", 0) for r in career)
    if yoe > 2 and total_months < (yoe * 12 - 24):
        ratio = total_months / max(1, yoe * 12)
        return [
            f"Career total ({total_months}mo) << YoE ({yoe}yr={yoe*12:.0f}mo), ratio={ratio:.2f}"
        ], 0.0
    return [], 1.0


def _check3_reverse_mismatch(profile: dict, career: list) -> tuple[list, float]:
    """
    CHECK 3 (antigravity check_reverse_mismatch.py):
    yoe < 2.0 but career history > 60 months. Impossible.
    """
    yoe = profile.get("years_of_experience", 0)
    total_months = sum(r.get("duration_months", 0) for r in career)
    if yoe < 2.0 and total_months > 60:
        return [f"Reverse: YoE={yoe}yr but career={total_months}mo"], 0.0
    return [], 1.0


def _check4_invalid_career_dates(career: list) -> tuple[list, float]:
    """
    CHECK 4 (antigravity find_all_honeypots.py — Rule 5):
    Any role where start_date > end_date. Chronologically impossible.
    """
    for role in career:
        sd = _parse_date(role.get("start_date"))
        ed = _parse_date(role.get("end_date"))
        if sd and ed and sd > ed:
            return [
                f"Invalid dates at {role.get('company','?')}: "
                f"start={role.get('start_date')} > end={role.get('end_date')}"
            ], 0.0
    return [], 1.0


def _check5_active_before_signup(signals: dict) -> tuple[list, float]:
    """
    CHECK 5 (antigravity find_all_honeypots.py — Rule 6):
    last_active_date < signup_date. Impossible on Redrob platform.
    """
    signup = _parse_date(signals.get("signup_date"))
    active = _parse_date(signals.get("last_active_date"))
    if signup and active and active < signup:
        return [
            f"last_active ({signals.get('last_active_date')}) "
            f"< signup ({signals.get('signup_date')})"
        ], 0.0
    return [], 1.0


def _check6_career_before_college(career: list, education: list) -> tuple[list, float]:
    """
    CHECK 6 (antigravity scan_more.py — Rule 3):
    Career starts 5+ years before college started. Impossible.
    """
    if not career or not education:
        return [], 1.0

    earliest_career_year = min(
        (int(r["start_date"].split("-")[0])
         for r in career if r.get("start_date")),
        default=9999,
    )
    earliest_edu_year = min(
        (e["start_year"] for e in education if e.get("start_year")),
        default=9999,
    )

    if (earliest_career_year != 9999 and earliest_edu_year != 9999
            and earliest_career_year < earliest_edu_year - 5):
        return [
            f"Career started {earliest_career_year} but "
            f"college started {earliest_edu_year} (gap >5yr)"
        ], 0.0
    return [], 1.0


def _check7_yoe_exceeds_graduation(
    profile: dict, education: list
) -> tuple[list, float]:
    """
    CHECK 7 (antigravity scan_more.py — Rule 4):
    yoe > (CURRENT_YEAR - graduation_year + 4). Impossible given graduation date.
    Buffer of 4 years for working during college; extra 2yr tolerance.
    """
    if not education:
        return [], 1.0

    yoe = profile.get("years_of_experience", 0)
    latest_grad_year = max(
        (e["end_year"] for e in education if e.get("end_year")),
        default=-1,
    )
    if latest_grad_year == -1:
        return [], 1.0

    max_possible_yoe = CURRENT_YEAR - latest_grad_year + 4
    if yoe > max_possible_yoe + 2:
        return [
            f"YoE={yoe} > max_possible={max_possible_yoe} "
            f"(graduated {latest_grad_year})"
        ], 0.0
    return [], 1.0


# ─────────────────────────────────────────────────────────────
# SOFT PENALTY CHECKS  (penalty < 1.0 but not 0.0)
# ─────────────────────────────────────────────────────────────

def _check8_keyword_stuffer(profile: dict, skills: list) -> tuple[list, float]:
    """
    CHECK 8: Non-technical current title + ≥3 AI skills.
    Spec-defined primary disqualifier pattern.
    """
    current_title = (profile.get("current_title") or "").lower()
    is_nontech = any(nt in current_title for nt in NON_TECH_TITLE_KW)
    is_tech = any(tw in current_title for tw in TECH_TITLE_KW)

    if is_nontech and not is_tech:
        skill_names_lower = {s.get("name", "").lower() for s in skills}
        ai_claimed = skill_names_lower & AI_SKILL_NAMES
        if len(ai_claimed) >= 3:
            return [
                f"Keyword stuffer: '{current_title}' + "
                f"{len(ai_claimed)} AI skills: {list(ai_claimed)[:4]}"
            ], 0.10
    return [], 1.0


def _check9_services_only(career: list) -> tuple[bool, float]:
    """
    CHECK 9: Entire career at TCS/Infosys/Wipro etc.
    JD explicit disqualifier. Returns (is_services_only, penalty).
    """
    if not career:
        return False, 1.0
    total_months = sum(r.get("duration_months", 0) for r in career)
    services_months = sum(
        r.get("duration_months", 0) for r in career
        if _is_services(r.get("company", ""))
    )
    if total_months == 0:
        return False, 1.0

    ratio = services_months / total_months
    if ratio >= 0.98:
        return True, 0.15
    elif ratio >= 0.85:
        return False, 0.45
    elif ratio >= 0.70:
        return False, 0.70
    elif ratio >= 0.50:
        return False, 0.85
    return False, 1.0


def _check10_excessive_experts(skills: list, yoe: float) -> tuple[list, float]:
    """
    CHECK 10: ≥10 expert-level skills (implausible breadth).
    Also: yoe ≤ 1.0 with >3 experts.
    """
    experts = [s for s in skills if s.get("proficiency") == "expert"]
    n = len(experts)
    flags = []
    penalty = 1.0

    if n >= 10:
        flags.append(f"Implausible: {n} expert-level skills")
        penalty *= max(0.10, 1.0 - (n - 9) * 0.12)
    if yoe <= 1.0 and n > 3:
        flags.append(f"YoE={yoe}yr but {n} expert skills")
        penalty *= 0.30

    return flags, penalty


def _check11_many_zero_duration(skills: list) -> tuple[list, float]:
    """
    CHECK 11 (antigravity check_zero_dur_skills.py):
    ≥5 skills (any proficiency level) with duration_months == 0.
    Suggests mass-padding of skills without actual usage.
    Soft penalty only (not a hard honeypot — could be data entry error).
    """
    zero_count = sum(1 for s in skills if s.get("duration_months", 1) == 0)
    if zero_count >= 5:
        return [f"{zero_count} skills with zero duration (any level)"], 0.80
    return [], 1.0


# ─────────────────────────────────────────────────────────────
# MAIN PUBLIC API
# ─────────────────────────────────────────────────────────────

def evaluate(candidate: dict) -> AuthenticityResult:
    """
    Full 11-check authenticity evaluation.

    Hard honeypots: any check returning penalty=0.0 → is_honeypot=True
    Soft flags: reduce penalty_multiplier multiplicatively.

    Returns AuthenticityResult dict.
    """
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    education = candidate.get("education", [])
    signals = candidate.get("redrob_signals", {})
    yoe = profile.get("years_of_experience", 0)

    honeypot_reasons: list[str] = []
    penalty = 1.0
    is_honeypot = False

    # ── HARD CHECKS ──────────────────────────────────────────────
    for check_fn, args in [
        (_check1_skill_zero_duration, (skills,)),
        (_check2_yoe_career_mismatch, (profile, career)),
        (_check3_reverse_mismatch, (profile, career)),
        (_check4_invalid_career_dates, (career,)),
        (_check5_active_before_signup, (signals,)),
        (_check6_career_before_college, (career, education)),
        (_check7_yoe_exceeds_graduation, (profile, education)),
    ]:
        flags, p = check_fn(*args)
        honeypot_reasons.extend(flags)
        if p == 0.0:
            is_honeypot = True
        penalty = min(penalty, p)   # One hard check zeros everything

    # ── SOFT CHECKS (only apply if not already a hard honeypot) ──
    # Still run them so penalty_multiplier reflects all issues
    flags8, p8 = _check8_keyword_stuffer(profile, skills)
    honeypot_reasons.extend(flags8)
    penalty *= p8

    _, services_only_flag, p9 = (*_check9_services_only(career), None)[:3]  # unpack (bool, float)
    # Redo properly:
    _svc_flag, p9 = _check9_services_only(career)[0], _check9_services_only(career)[1]
    if _svc_flag:
        honeypot_reasons.append("Entire career at IT services firms")
    penalty *= p9

    flags10, p10 = _check10_excessive_experts(skills, yoe)
    honeypot_reasons.extend(flags10)
    penalty *= p10

    flags11, p11 = _check11_many_zero_duration(skills)
    honeypot_reasons.extend(flags11)
    penalty *= p11

    # ── Verification bonus (small boost for clean, verified profiles) ──
    verify_bonus = 0.02 * sum([
        signals.get("verified_email", False),
        signals.get("verified_phone", False),
        signals.get("linkedin_connected", False),
    ])

    auth_score = min(1.0, max(0.0, penalty) + verify_bonus)

    return AuthenticityResult(
        is_honeypot=is_honeypot,
        honeypot_reasons=honeypot_reasons,
        authenticity_score=auth_score,
        penalty_multiplier=min(1.0, max(0.0, penalty)),
    )
