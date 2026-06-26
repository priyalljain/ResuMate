"""
Education & Narrative Scorer

Education: tier weight × field relevance × certifications
Narrative: profile text alignment with JD intent (positive signals vs negative)

The causal fairness principle (from implementation plan):
'Correct for institutional prestige bias — tier_1 vs tier_4 candidates
who are otherwise equal should not be penalized for where they studied.'

We implement this as a SOFT signal, not a gate. A tier_4 with perfect
skills and trajectory still ranks above a tier_1 with weak skills.
"""

from __future__ import annotations

import re

# ──────────────────────────────────────────────────────────────
# EDUCATION TIER WEIGHTS (counterfactual fairness applied)
# Raw tier → base score, then compressed toward center
# to reduce institutional bias
# ──────────────────────────────────────────────────────────────

TIER_BASE = {
    "tier_1": 1.00,
    "tier_2": 0.82,
    "tier_3": 0.68,
    "tier_4": 0.55,
    "unknown": 0.60,  # Give benefit of doubt
}

# After bias correction: compress tier gap
# Rationale: a tier_4 grad who built production ML systems
# outperforms a tier_1 grad who hasn't. Tier is a prior, not a gate.
TIER_DEBIASED = {k: 0.55 + (v - 0.55) * 0.60 for k, v in TIER_BASE.items()}

RELEVANT_FIELDS = {
    # Direct: full weight
    "computer science": 1.00,
    "software engineering": 1.00,
    "data science": 0.98,
    "artificial intelligence": 0.98,
    "machine learning": 0.98,
    "information technology": 0.90,
    "information science": 0.90,
    "mathematics": 0.85,
    "statistics": 0.85,
    "applied mathematics": 0.85,
    "computer engineering": 0.92,
    # Adjacent: partial weight
    "electronics": 0.70,
    "electrical engineering": 0.70,
    "electronics and communication": 0.65,
    "physics": 0.60,
    # Weak: minimal weight
    "mechanical engineering": 0.40,
    "civil engineering": 0.30,
    "business administration": 0.30,
    "management": 0.30,
    "commerce": 0.25,
}

RELEVANT_CERTS = {
    # High value
    "aws certified machine learning": 1.0,
    "google professional machine learning": 1.0,
    "tensorflow developer": 0.9,
    "pytorch": 0.9,
    "databricks certified ml": 0.9,
    "deep learning specialization": 0.9,
    "nlp specialization": 0.9,
    "mlops": 0.8,
    # Medium
    "aws certified": 0.6,
    "google cloud": 0.6,
    "azure": 0.5,
    "coursera": 0.4,
    "udacity nanodegree": 0.5,
    # Low
    "pmp": 0.1,
    "scrum": 0.1,
    "six sigma": 0.1,
}

DEGREE_WEIGHTS = {
    "phd": 1.05,  # PhD in CS/ML is a bonus
    "ph.d": 1.05,
    "doctor": 1.05,
    "m.tech": 1.00,
    "me ": 1.00,
    "m.e.": 1.00,
    "mtech": 1.00,
    "msc": 0.95,
    "m.sc": 0.95,
    "master": 0.95,
    "ms ": 0.95,
    "b.tech": 0.88,
    "btech": 0.88,
    "be ": 0.88,
    "b.e.": 0.88,
    "bsc": 0.82,
    "b.sc": 0.82,
    "bachelor": 0.82,
}


def _field_relevance(field_of_study: str) -> float:
    field = field_of_study.lower().strip()
    best = 0.50  # default for unrecognized fields
    for key, weight in RELEVANT_FIELDS.items():
        if key in field:
            best = max(best, weight)
    return best


def _degree_weight(degree: str) -> float:
    deg = degree.lower().strip()
    for key, weight in DEGREE_WEIGHTS.items():
        if key in deg:
            return weight
    return 0.80


def score_education(candidate: dict) -> float:
    """
    Score education. Returns [0.0, 1.0].
    Missing education → 0.55 (self-taught; not a disqualifier).
    """
    education = candidate.get("education", [])
    certifications = candidate.get("certifications", [])

    if not education:
        base = 0.55
    else:
        best_edu_score = 0.0
        for edu in education:
            tier = edu.get("tier", "unknown")
            field = edu.get("field_of_study", "")
            degree = edu.get("degree", "")

            tier_score = TIER_DEBIASED.get(tier, TIER_DEBIASED["unknown"])
            field_score = _field_relevance(field)
            degree_mult = _degree_weight(degree)

            edu_score = (tier_score * 0.45 + field_score * 0.55) * degree_mult
            best_edu_score = max(best_edu_score, edu_score)

        base = best_edu_score

    # Certifications bonus (max +0.12)
    cert_bonus = 0.0
    for cert in certifications[:5]:
        cert_name = (cert.get("name") or "").lower()
        for key, val in RELEVANT_CERTS.items():
            if key in cert_name:
                cert_bonus = min(cert_bonus + val * 0.03, 0.12)
                break

    return min(1.0, base + cert_bonus)


# ──────────────────────────────────────────────────────────────
# NARRATIVE ALIGNMENT SCORER
# ──────────────────────────────────────────────────────────────

# Positive signals: production-oriented ML language (from JD)
POS_PATTERNS = [
    r"\b(production|production-ready|prod)\b",
    r"\b(ship(ped)?|deploy(ed)?|launch(ed)?)\b",
    r"\b(real users|at scale|high.traffic|low.latency)\b",
    r"\b(recommendation|search|retrieval|ranking)\b",
    r"\b(embedding|vector|dense|sparse)\b",
    r"\b(nlp|natural language|text|semantic)\b",
    r"\b(llm|language model|fine.tun|rag)\b",
    r"\b(evaluation|benchmark|ndcg|mrr|precision|recall|a/b|ab test)\b",
    r"\b(ml engineer|applied ml|machine learning engineer)\b",
    r"\b(feature engineering|feature pipeline|feature store)\b",
    r"\b(product company|startup|scale-up|tech company)\b",
]

# Negative signals: pure research / non-ML / operations language
NEG_PATTERNS = [
    r"\b(academia|academic|thesis|dissertation|publication|paper|lab|research institute)\b",
    r"\b(consulting|delivery|implementation|staffing|outsourc)\b",
    r"\b(marketing|seo|content|copywriting|social media)\b",
    r"\b(accounting|bookkeeping|finance|audit|tax)\b",
    r"\b(hr|human resources|talent|recruiting|payroll)\b",
    r"\b(sales|business development|cold calling|lead gen)\b",
    r"\b(graphic design|ux|ui design|figma|illustrator)\b",
    r"\b(civil|mechanical|electrical engineering)\b",
    r"\b(supply chain|logistics|operations management)\b",
]

POS_COMPILED = [re.compile(p, re.IGNORECASE) for p in POS_PATTERNS]
NEG_COMPILED = [re.compile(p, re.IGNORECASE) for p in NEG_PATTERNS]


def score_narrative(candidate: dict, jd_config=None) -> float:
    """
    Score profile narrative (headline + summary) for JD alignment.
    Returns [0.0, 1.0].
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])

    headline = profile.get("headline") or ""
    summary = profile.get("summary") or ""
    # Also include first 2 role descriptions (most recent)
    recent_descs = " ".join(r.get("description", "") for r in career[:2])

    full_text = f"{headline} {summary} {recent_descs}"

    pos_count = sum(1 for p in POS_COMPILED if p.search(full_text))
    neg_count = sum(1 for p in NEG_COMPILED if p.search(full_text))

    # Base 0.50, +0.04 per positive signal (up to +0.44), -0.05 per negative
    score = 0.50 + (0.04 * pos_count) - (0.05 * neg_count)
    return min(1.0, max(0.10, score))
