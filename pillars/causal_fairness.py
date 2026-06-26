"""
Pillar 3: Causal Fairness

This module is conceptually separate but its logic is directly embedded in
education_narrative.py (the TIER_DEBIASED compression toward center).

This file documents the counterfactual fairness design and provides a
standalone debias() function for use in ablation studies or as a wrapper.

Design rationale:
  Raw institutional tier creates a bias: a tier_4 candidate who built
  production ML systems at Swiggy is penalized relative to a tier_1
  candidate who hasn't shipped anything.

  We apply a SOFT bias correction:
    debiased_score = compressed toward center (not eliminated)
    Specifically: debiased = 0.55 + (raw - 0.55) * 0.60

  This means:
    tier_1 raw=1.00 → debiased=0.82 (loses 0.18)
    tier_4 raw=0.55 → debiased=0.55 (no change — it's the floor)

  The gap between tier_1 and tier_4 shrinks from 0.45 to 0.27.
  Tier remains a prior — never a gate.

  Counterfactual interpretation:
    "If this candidate had attended a different institution but had the
     same skills and career history, their score should be nearly equal."
"""

from __future__ import annotations


TIER_RAW = {
    "tier_1": 1.00,
    "tier_2": 0.82,
    "tier_3": 0.68,
    "tier_4": 0.55,
    "unknown": 0.60,
}

FLOOR = 0.55
COMPRESSION = 0.60  # How much we compress toward floor (1.0 = no correction, 0.0 = full correction)


def debiased_tier_score(tier: str) -> float:
    """
    Apply counterfactual fairness correction to education tier.
    Returns debiased score in [0.55, 0.82].
    """
    raw = TIER_RAW.get(tier, TIER_RAW["unknown"])
    return FLOOR + (raw - FLOOR) * COMPRESSION


def debias(raw_score: float, candidate: dict) -> float:
    """
    Apply causal fairness correction to a raw composite score.
    This adjusts for institutional prestige bias embedded in the education axis.

    Note: In our pipeline, debiasing is already applied per-axis in score_education().
    This function can be used as a post-hoc correction on the full raw_score.

    Currently: identity function (debiasing is axis-level, not score-level).
    """
    # Post-hoc score-level debiasing is not applied in the main pipeline.
    # Debiasing happens inside score_education() via TIER_DEBIASED mapping.
    # This function is a hook for future ablation experiments.
    return raw_score


def location_correction(raw_score: float, candidate: dict) -> float:
    """
    Mild location-based correction.
    India-based candidates competing against international candidates
    should not be penalized for salary expectations or time zone.
    (This is already handled in behavioral.py via location_score.)
    No additional correction applied here.
    """
    return raw_score
