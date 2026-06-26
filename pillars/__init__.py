"""
Redrobb Ranking Engine — Pillars Package

Pillar 1: authenticity       — 11-check honeypot & integrity detection
Pillar 2: knowledge_graph    — semantic skill matching via alias + partial-match graph
Pillar 3: causal_fairness    — counterfactual education debiasing
         education_narrative — debiased education + narrative alignment
Pillar 4: behavioral         — all 23 redrob_signals multiplier
         rl_reranker         — reward function & tiebreak
         trajectory          — career trajectory + experience fit
Pillar 5: ocean_signals      — Big Five personality proxy from behavioral data
Pillar 6: jd_parser          — JD-agnostic config system (any role)
"""

from pillars import (
    authenticity,
    knowledge_graph,
    trajectory,
    behavioral,
    education_narrative,
    causal_fairness,
    rl_reranker,
    ocean_signals,
    jd_parser,
)

__all__ = [
    "authenticity", "knowledge_graph", "trajectory", "behavioral",
    "education_narrative", "causal_fairness", "rl_reranker",
    "ocean_signals", "jd_parser",
]
