"""Authenticity scoring for candidate profiles.

This pillar detects fake or inflated candidate profiles by measuring
semantic entropy across summary, skills, and experience sections,
then validating claimed years of experience against career history.
"""

import math
import re
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _normalize_text(text: str) -> str:
    return " ".join(str(text).split()).strip()


def _section_text(candidate: Dict, key: str, prefix: Optional[str] = None) -> str:
    value = candidate.get(key, "")
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item)
    if prefix and value:
        return f"{prefix}: {value}"
    return _normalize_text(value)


def _extract_experience_text(candidate: Dict) -> str:
    experiences = candidate.get("experience") or candidate.get("career_history") or []
    if isinstance(experiences, str):
        return _normalize_text(experiences)

    experience_texts: List[str] = []
    for item in experiences:
        if isinstance(item, str):
            experience_texts.append(item)
            continue

        if not isinstance(item, dict):
            continue

        if "description" in item and item["description"]:
            experience_texts.append(str(item["description"]))
            continue

        role_description = []
        for field in ("role", "title", "position", "company", "organization", "summary"):
            if item.get(field):
                role_description.append(str(item[field]))

        if role_description:
            experience_texts.append(" ".join(role_description))
            continue

        experience_texts.append(" ".join(str(value) for value in item.values() if value))

    return _normalize_text(" ".join(experience_texts))


def _load_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def _embed_sections(sections: List[str], model: SentenceTransformer) -> np.ndarray:
    return model.encode(sections, convert_to_numpy=True, show_progress_bar=False)


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    numerator = float(np.dot(a, b))
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    similarity = np.clip(numerator / denominator, -1.0, 1.0)
    return 1.0 - similarity


def _variance_of_pairwise_distances(embeddings: np.ndarray) -> float:
    distances: List[float] = []
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            distances.append(_cosine_distance(embeddings[i], embeddings[j]))
    return float(np.var(distances)) if distances else 0.0


def _sigmoid_entropy_score(variance: float) -> float:
    x = (variance - 0.2) * 20.0
    score = 1.0 / (1.0 + math.exp(-x))
    return float(np.clip(score, 0.0, 1.0))


def _parse_duration_to_months(value: object) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    text = _normalize_text(value)
    if not text:
        return None

    years = sum(int(match.group(1)) for match in re.finditer(r"(\d+)\s*(?:years?|yrs?)", text, re.I))
    months = sum(int(match.group(1)) for match in re.finditer(r"(\d+)\s*(?:months?|mos?)", text, re.I))
    if years or months:
        return years * 12 + months

    if text.isdigit():
        return int(text)

    return None


def _parse_date(value: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%m/%Y", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _duration_from_dates(start: str, end: str) -> Optional[int]:
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    if not start_date or not end_date:
        return None

    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    return max(months, 0)


def _career_history_months(candidate: Dict) -> Optional[int]:
    if candidate.get("career_months") is not None:
        try:
            return int(candidate["career_months"])
        except (TypeError, ValueError):
            pass

    total_months = 0
    seen_any = False

    history = candidate.get("career_history") or candidate.get("experience") or []
    if isinstance(history, dict):
        history = [history]

    for item in history:
        if isinstance(item, dict):
            months = _parse_duration_to_months(item.get("duration") or item.get("tenure") or item.get("time"))
            if months is None and item.get("years") is not None:
                try:
                    months = int(item["years"]) * 12
                except (TypeError, ValueError):
                    months = None
            if months is None and item.get("months") is not None:
                try:
                    months = int(item["months"])
                except (TypeError, ValueError):
                    months = None
            if months is None and item.get("start_date") and item.get("end_date"):
                months = _duration_from_dates(item["start_date"], item["end_date"])
            if months is None and item.get("from") and item.get("to"):
                months = _duration_from_dates(item["from"], item["to"])

            if months is not None:
                total_months += months
                seen_any = True
                continue

        if isinstance(item, str):
            months = _parse_duration_to_months(item)
            if months is not None:
                total_months += months
                seen_any = True

    return int(total_months) if seen_any else None


def _cross_reference_score(candidate: Dict) -> float:
    yoe = None
    for field in ("years_of_experience", "yoe", "experience_years", "total_experience"):
        if field in candidate and candidate[field] is not None:
            try:
                yoe = float(candidate[field])
                break
            except (TypeError, ValueError):
                continue

    career_months = _career_history_months(candidate)
    if yoe is None or career_months is None:
        return 1.0

    expected_months = yoe * 12.0
    if career_months >= expected_months - 12.0:
        return 1.0

    penalty = min(1.0, max(0.0, (expected_months - career_months) / max(expected_months, 1.0)))
    return float(np.clip(1.0 - penalty, 0.0, 1.0))


def score(candidate: Dict) -> float:
    summary = _normalize_text(candidate.get("summary", ""))
    skills = _section_text(candidate, "skills", prefix="Skills")
    experience = _extract_experience_text(candidate)

    sections = [summary or "Candidate summary not provided", skills or "Skills not provided", experience or "Experience not provided"]
    model = _load_model()
    embeddings = _embed_sections(sections, model)

    variance = _variance_of_pairwise_distances(embeddings)
    entropy_score = _sigmoid_entropy_score(variance)
    cross_ref_score = _cross_reference_score(candidate)

    score_value = 0.7 * entropy_score + 0.3 * cross_ref_score
    return float(np.clip(score_value, 0.0, 1.0))
