"""
domain_config.py — JD-agnostic track detection.

The released hackathon JD is single-domain (Senior AI Engineer -> "tech"),
but the engine stays domain-agnostic on the *job description* side so the
same pipeline works unmodified if Redrob points it at a Marketing, HR,
Legal, Medical, Design, or Creative role in the future, per how this project
was scoped. Detection is a simple weighted keyword vote over `title_signals`
in data/domain_graphs.json — good enough to route a JD to its track without
hardcoding "if tech: ...".
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "domain_graphs.json"


def load_domain_graphs() -> Dict[str, Any]:
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_domain(jd_text: str, graphs: Dict[str, Any]) -> str:
    jd_lower = jd_text.lower()
    scores = {}
    for domain, cfg in graphs.items():
        score = 0
        for sig in cfg.get("title_signals", []):
            if sig in jd_lower:
                score += 1
        # also count must_have hits as weak domain evidence
        for term in cfg.get("must_have", {}):
            if term in jd_lower:
                score += 0.5
        scores[domain] = score
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "tech"  # safe default for this engine's primary use case
    return best
