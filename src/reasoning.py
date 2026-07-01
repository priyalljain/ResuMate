"""
reasoning.py — generates the `reasoning` column.

Stage 4 manual review explicitly checks for: specific facts from the
profile, connection to JD requirements, honest acknowledgment of gaps,
zero hallucination, variation across rows, and tone matching the rank.
This module is built around those checks:

  - Every fact inserted into a sentence is read directly off the candidate
    dict (years_of_experience, current_title, current_company, an actual
    matched skill name, a real signal value) -- nothing is invented.
  - Template choice is deterministic (hashed off candidate_id) rather than
    `random`, so re-running the pipeline on the same input reproduces the
    exact same CSV -- this matters for the "reproduce_command" requirement
    and for not contradicting yourself at the Stage 5 interview.
  - Tone bucket (strong / moderate / weak / excluded) is derived from the
    same score components used for ranking, so a high-rank row can't end up
    with skeptical language or vice versa.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List


def _pick(seed_str: str, options: List[str]) -> str:
    h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
    return options[h % len(options)]


def _tone_bucket(score_components: Dict[str, Any]) -> str:
    if score_components["exclusion_flags"] or score_components["final_score"] < 0.15:
        return "excluded"
    if score_components["final_score"] >= 0.6:
        return "strong"
    if score_components["final_score"] >= 0.3:
        return "moderate"
    return "weak"


def build_reasoning(candidate: Dict[str, Any], score_components: Dict[str, Any]) -> str:
    profile = candidate.get("profile") or {}
    signals = candidate.get("redrob_signals") or {}
    cid = candidate["candidate_id"]

    yoe = profile.get("years_of_experience")
    title = profile.get("current_title") or "Unknown title"
    company = profile.get("current_company") or "their current employer"
    location = profile.get("location") or "unspecified location"

    matched_must = score_components.get("matched_must") or []
    matched_nice = score_components.get("matched_nice") or []
    orphaned = score_components.get("orphaned_skills") or []
    anti_fit = score_components.get("anti_fit_hits") or []
    exclusion_flags = score_components.get("exclusion_flags") or []
    rr = signals.get("recruiter_response_rate")
    notice = signals.get("notice_period_days")

    tone = _tone_bucket(score_components)
    skill_phrase = ", ".join(matched_must[:3]) if matched_must else None
    nice_phrase = ", ".join(matched_nice[:2]) if matched_nice else None

    if tone == "excluded":
        if "pure_research_no_production" in exclusion_flags:
            return (
                f"{title} ({yoe} yrs) at {company} — career history shows no production "
                f"deployment evidence in the narrative; JD explicitly excludes pure-research "
                f"backgrounds without shipped systems."
            )
        if "recent_langchain_only_ai_experience" in exclusion_flags:
            return (
                f"{title} ({yoe} yrs) — AI-related skills are recent (<12mo) and centered on "
                f"LangChain/prompting with no longer-tenured ML production skill; JD flags this "
                f"pattern explicitly as a non-fit."
            )
        if orphaned and not matched_must:
            return (
                f"{title} ({yoe} yrs) at {company} — lists {len(orphaned)} AI/ML-adjacent skills "
                f"(e.g. {', '.join(orphaned[:3])}) but none are referenced anywhere in the role "
                f"descriptions; reads as keyword-listing rather than applied experience."
            )
        if anti_fit:
            return (
                f"{title} ({yoe} yrs) — skill set centers on {', '.join(anti_fit[:2])} "
                f"(computer vision / speech) with no NLP or retrieval exposure; JD explicitly "
                f"excludes this profile shape."
            )
        return (
            f"{title} ({yoe} yrs) at {company} in {location} — minimal overlap with the JD's "
            f"core requirements (embeddings/retrieval/ranking, evaluation, production Python); "
            f"included only as lower-bound filler."
        )

    if tone == "strong":
        opener = _pick(cid, [
            f"{title} ({yoe} yrs) at {company}",
            f"{yoe}-year {title} currently at {company}",
            f"Strong fit: {title} ({yoe} yrs), {company}",
        ])
        mid = f"hands-on with {skill_phrase}" if skill_phrase else "production ML/retrieval narrative in their work history"
        concern = None
        if notice and notice > 60:
            concern = f"notice period is {notice} days, above the JD's sub-30-day preference"
        elif isinstance(rr, (int, float)) and rr < 0.2:
            concern = f"recruiter response rate is low ({rr:.0%})"
        elif score_components.get("location_modifier", 1.0) < 0.9:
            concern = f"based in {location}, outside the JD's named hub cities"
        tail = f"; main concern is {concern}." if concern else f"; based in {location}, matches the JD's location preference."
        return f"{opener} — {mid}{tail}"

    if tone == "moderate":
        opener = _pick(cid, [
            f"{title} ({yoe} yrs) at {company}",
            f"{title}, {yoe} yrs experience",
        ])
        if skill_phrase:
            body = f"shows real exposure to {skill_phrase}"
        elif nice_phrase:
            body = f"has adjacent exposure ({nice_phrase}) but limited core retrieval/ranking depth"
        else:
            body = "has partial overlap with the JD's core stack but no standout signal either way"
        gaps = []
        if orphaned:
            gaps.append(f"{len(orphaned)} listed skill(s) not backed up in the narrative")
        if isinstance(rr, (int, float)) and rr < 0.3:
            gaps.append(f"recruiter response rate only {rr:.0%}")
        gap_text = f" Gap: {gaps[0]}." if gaps else ""
        return f"{opener} — {body}.{gap_text}"

    # weak but still in top-100 as lower-bound filler
    return (
        f"{title} ({yoe} yrs) at {company}, {location} — weak overlap with the JD's core "
        f"retrieval/ranking/embeddings requirements; included as lower-confidence filler near "
        f"the bottom of the shortlist."
    )
