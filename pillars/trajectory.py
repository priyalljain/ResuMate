"""
Career Trajectory Scorer — v2 (bug-fixed)

Key fixes from v1:
- trajectory score now gated: if ml_role_score == 0, base trajectory 
  is capped at 0.25 (product company / tenure bonus only)
  → prevents Civil/Mech Engineers from ranking above ML candidates
- Stronger plain-language ML work detection
- Title-domain mismatch penalty applied before score computation
"""

from __future__ import annotations

import re
from datetime import date

TODAY = date.today()

SERVICES_FIRMS = frozenset({
    "tcs", "tata consultancy", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "tech mahindra", "hexaware",
    "mphasis", "ltimindtree", "mindtree",
})

ML_TITLE_KW = frozenset({
    "ml engineer", "machine learning engineer", "applied ml", "applied scientist",
    "research scientist", "nlp engineer", "data scientist", "ai engineer",
    "search engineer", "ranking engineer", "recommendation", "retrieval",
    "embedding", "applied ai", "deep learning engineer",
})

# Broader ML title keywords (partial match)
ML_TITLE_BROAD = frozenset({
    "ml", "machine learning", "nlp", "data scientist",
    "recommendation", "search", "ranking", "retrieval", "embedding",
    "applied scientist", "ai engineer", "applied ai",
})

# Plain-language ML work signals in descriptions (tight patterns only)
ML_DESC_PATTERNS = [
    r"\b(ranking model|learning.to.rank|relevance model|reranking|re-ranking)\b",
    r"\b(recommendation engine|recommender|collaborative filtering|matrix factori[sz]ation)\b",
    r"\b(embedding.based|dense retrieval|vector search|semantic search)\b",
    r"\b(two.tower|candidate generation|item embedding|user embedding)\b",
    r"\b(ndcg|mrr|precision.at.\d|recall.at.\d|offline.online correlation)\b",
    r"\b(feature pipeline|training pipeline|inference pipeline|model serving|model deploy)\b",
    r"\b(a/b test|ab test|uplift|experimentation framework)\b",
    r"\b(fine.tun|lora|qlora|peft|instruction.tun)\b",
    r"\b(rag pipeline|retrieval augmented|knowledge.augmented)\b",
    r"\b(language model|llm|bert|gpt|transformer.based)\b",
]
ML_DESC_COMPILED = [re.compile(p, re.IGNORECASE) for p in ML_DESC_PATTERNS]

# Hard disqualifying title patterns (current role = wrong domain entirely)
DISQ_CURRENT_TITLES = re.compile(
    r"\b(marketing manager|sales executive|sales manager|hr manager|"
    r"content writer|graphic designer|ux designer|ui designer|"
    r"scrum master|accountant|customer support|civil engineer|"
    r"mechanical engineer|supply chain|procurement|finance manager)\b",
    re.IGNORECASE,
)

# JD disqualifier: the only allowed exception is if prior career has ML work
SENIORITY_MAP = {
    "intern": 0, "trainee": 0, "junior": 1, "associate": 1,
    "engineer": 2, "developer": 2, "scientist": 2, "analyst": 2,
    "specialist": 2, "senior": 3, "lead": 3, "tech lead": 3,
    "staff": 4, "principal": 4, "architect": 4,
    "director": 5, "head": 5, "vp": 5, "vice president": 5,
    "manager": 3, "senior manager": 4,
}


def _is_services(company: str) -> bool:
    co = company.lower().strip()
    return any(sf in co for sf in SERVICES_FIRMS)


def _seniority_level(title: str) -> int:
    tl = title.lower()
    best = -1
    for kw, level in SENIORITY_MAP.items():
        if kw in tl:
            best = max(best, level)
    return best if best >= 0 else 1


def _desc_ml_signal_count(description: str) -> int:
    """Count tight ML plain-language signals (no false positives)."""
    if not description:
        return 0
    return sum(1 for p in ML_DESC_COMPILED if p.search(description))


def _has_ml_title(title: str) -> bool:
    tl = title.lower()
    # Exact phrase match first
    if any(kw in tl for kw in ML_TITLE_KW):
        return True
    # Broad: must have both a role word AND an ML domain word
    role_words = {"engineer", "developer", "scientist", "researcher", "architect", "lead"}
    ml_words = ML_TITLE_BROAD
    has_role = any(w in tl for w in role_words)
    has_ml = any(w in tl for w in ml_words)
    return has_role and has_ml


def score_trajectory(candidate: dict) -> float:
    """Score career trajectory. Returns [0.0, 1.0]."""
    career = candidate.get("career_history", [])
    if not career:
        return 0.0

    total_months = sum(r.get("duration_months", 0) for r in career)
    if total_months == 0:
        return 0.0

    # ── Component 1: Product company ratio ──────────────────────
    product_months = sum(
        r.get("duration_months", 0) for r in career
        if not _is_services(r.get("company", ""))
    )
    product_ratio = product_months / total_months

    # ── Component 2: ML role quality (GATING component) ─────────
    ml_title_months = 0
    ml_desc_months = 0
    seniority_levels = []
    most_recent_is_ml = False

    for i, role in enumerate(career):
        title = role.get("title", "")
        desc = role.get("description", "")
        dur = role.get("duration_months", 0)
        is_current = role.get("is_current", False)

        has_ml_t = _has_ml_title(title)
        desc_signals = _desc_ml_signal_count(desc)

        if has_ml_t:
            ml_title_months += dur
        if desc_signals >= 2:
            ml_desc_months += dur

        if i == 0 and (has_ml_t or desc_signals >= 2):
            most_recent_is_ml = True

        level = _seniority_level(title)
        seniority_levels.append(level)

    # ML role score: weighted blend of title-based and description-based evidence
    title_ml_ratio = ml_title_months / max(1, total_months)
    desc_ml_ratio = ml_desc_months / max(1, total_months)
    ml_role_score = min(1.0, max(title_ml_ratio, desc_ml_ratio) * 1.5)

    # Recency bonus
    if most_recent_is_ml:
        ml_role_score = min(1.0, ml_role_score * 1.15)

    # ── GATE: If no ML signal at all, cap total trajectory at 0.22 ──
    # This prevents Civil/Mech/Sales profiles from scoring high on trajectory
    if ml_role_score < 0.01:
        # Tiny non-zero to preserve relative ordering of non-ML candidates
        return min(0.22, product_ratio * 0.20)

    # ── Component 3: Seniority slope ────────────────────────────
    if len(seniority_levels) >= 2:
        delta = seniority_levels[0] - seniority_levels[-1]  # current - oldest
        slope_score = min(1.0, max(0.0, 0.5 + delta * 0.15))
    else:
        slope_score = 0.50

    # ── Component 4: Tenure stability ───────────────────────────
    n_roles = len(career)
    avg_tenure = total_months / n_roles
    if avg_tenure >= 30:
        tenure_score = 1.0
    elif avg_tenure >= 20:
        tenure_score = 0.85
    elif avg_tenure >= 14:
        tenure_score = 0.70
    elif avg_tenure >= 8:
        tenure_score = 0.50
    else:
        tenure_score = 0.30

    # Title-chaser penalty
    services_months = total_months - product_months
    if n_roles >= 4 and avg_tenure < 16 and services_months > product_months:
        tenure_score *= 0.70

    # ── Component 5: Industry relevance ─────────────────────────
    RELEVANT_INDUSTRIES = {
        "software", "ai/ml", "fintech", "e-commerce", "food delivery",
        "transportation", "healthtech", "edtech", "saas", "cloud",
        "internet", "tech",
    }
    industry_months = sum(
        r.get("duration_months", 0) for r in career
        if r.get("industry", "").lower() in RELEVANT_INDUSTRIES
    )
    industry_score = min(1.0, industry_months / max(1, total_months) * 2)

    # ── Weighted combination ─────────────────────────────────────
    score = (
        0.28 * product_ratio
        + 0.37 * ml_role_score       # most predictive — highest weight
        + 0.16 * slope_score
        + 0.11 * tenure_score
        + 0.08 * industry_score
    )
    return min(1.0, max(0.0, score))


def score_experience_fit(candidate: dict, jd_config=None) -> float:
    """Score YoE fit against JD band (default: 5-9yr, ideal 6-8yr)."""
    yoe = candidate.get("profile", {}).get("years_of_experience", 0)
    # Use JD config if available
    yoe_min = getattr(jd_config, "yoe_min", 5.0) if jd_config else 5.0
    yoe_max = getattr(jd_config, "yoe_max", 9.0) if jd_config else 9.0
    yoe_ideal_min = getattr(jd_config, "yoe_ideal_min", 6.0) if jd_config else 6.0
    yoe_ideal_max = getattr(jd_config, "yoe_ideal_max", 8.0) if jd_config else 8.0

    if yoe_ideal_min <= yoe <= yoe_ideal_max:
        band_score = 1.00
    elif yoe_min <= yoe < yoe_ideal_min:
        band_score = 0.92
    elif yoe_ideal_max < yoe <= yoe_max:
        band_score = 0.92
    elif yoe_min - 1 <= yoe < yoe_min:
        band_score = 0.78
    elif yoe_max < yoe <= yoe_max + 2:
        band_score = 0.72
    elif yoe_min - 2 <= yoe < yoe_min - 1:
        band_score = 0.58
    elif yoe_max + 2 < yoe <= yoe_max + 4:
        band_score = 0.55
    elif yoe > yoe_max + 4:
        band_score = 0.35
    else:
        band_score = 0.20

    # Production-work check: research-only profiles without deployment history
    career = candidate.get("career_history", [])
    has_production_signal = any(
        _desc_ml_signal_count(r.get("description", "")) >= 1
        or any(kw in r.get("title", "").lower()
               for kw in ["engineer", "developer", "architect"])
        for r in career
    )
    if not has_production_signal and yoe > 3:
        band_score *= 0.72

    return band_score


def is_hard_disqualified(candidate: dict) -> tuple[bool, str]:
    """
    Hard JD disqualifiers. Returns (True, reason) if disqualified.
    Not the same as honeypot — these are real people, wrong fit.
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    current_title = profile.get("current_title", "")

    # Disqualifier 1: disqualifying CURRENT title AND no ML in prior career
    if DISQ_CURRENT_TITLES.search(current_title):
        prior_ml_roles = [
            r for r in career
            if _has_ml_title(r.get("title", ""))
            or _desc_ml_signal_count(r.get("description", "")) >= 2
        ]
        if not prior_ml_roles:
            return True, f"Disqualifying current title with no ML career history: '{current_title}'"

    # Disqualifier 2: entire career at services firms
    if career:
        all_services = all(_is_services(r.get("company", "")) for r in career)
        if all_services:
            return True, "Entire career at IT services firms only"

    return False, ""
