"""
Pillar 4: RL-Human Hybrid Reranker

Simulates a GRPO-style reward function:
  reward = weighted_sum(axis_scores) × behavioral_multiplier

The 'learned weights' are derived from the JD signal analysis:
  - Skills + trajectory are decisive (combined 63% weight)
  - Experience fit is important but not decisive (15%)
  - Location + education + narrative are supporting signals (22%)

Tie-breaking (novel behavioral signal composite):
  secondary_score = 0.50 × recruiter_response_rate
                  + 0.30 × interview_completion_rate
                  + 0.20 × github_activity_score (normalized 0-1)

  This approximates: "among equally skilled candidates, who is actually
  hireable and will show up?" — the core RL reward for a recruiting system.
"""

from __future__ import annotations

WEIGHTS = {
    "kg":   0.35,
    "traj": 0.28,
    "exp":  0.15,
    "loc":  0.09,
    "edu":  0.07,
    "narr": 0.06,
}


def compute_reward(axis_scores: dict, behavioral_multiplier: float, auth_penalty: float) -> float:
    """
    Compute the final reward score.

    Args:
        axis_scores: dict with keys matching WEIGHTS
        behavioral_multiplier: float in [0.55, 1.15]
        auth_penalty: float in [0.0, 1.0] from authenticity pillar

    Returns:
        final_score: float in [0.0, ~1.0]
    """
    raw = sum(WEIGHTS[k] * axis_scores.get(k, 0.0) for k in WEIGHTS)
    return raw * auth_penalty * behavioral_multiplier


def compute_secondary_score(candidate: dict) -> float:
    """
    Compute tiebreak score from behavioral signals.
    Higher = more hireable / responsive.
    """
    signals = candidate.get("redrob_signals", {})
    rr = signals.get("recruiter_response_rate", 0.0)
    icr = signals.get("interview_completion_rate", 0.5)
    gh = signals.get("github_activity_score", 0.0)
    gh_norm = max(0.0, gh) / 100.0
    return 0.50 * rr + 0.30 * icr + 0.20 * gh_norm


def tie_break(c1: dict, c2: dict) -> int:
    """
    Compare two candidates for tiebreak.
    Returns: -1 if c1 wins, +1 if c2 wins, 0 if equal.
    Tertiary tiebreak: candidate_id ascending (per spec).
    """
    s1 = compute_secondary_score(c1)
    s2 = compute_secondary_score(c2)
    if s1 > s2:
        return -1
    elif s2 > s1:
        return 1
    # Tertiary: candidate_id ascending
    id1 = c1.get("candidate_id", "")
    id2 = c2.get("candidate_id", "")
    if id1 < id2:
        return -1
    elif id2 < id1:
        return 1
    return 0
