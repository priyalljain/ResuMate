"""
Pillar 2: Knowledge Graph — Semantic Skill Matching

Goes beyond exact keyword matching to find:
- "FAISS" == "approximate nearest neighbor"
- "Recommendation System" → related to "Ranking" → related to "Search"
- "XGBoost" → implies "Learning to Rank"
- "BM25" → implies "Information Retrieval"

Implements:
- Alias resolution (normalizes skill names to canonical forms)
- Neighbor traversal (skills related to JD skills score partial credit)
- Proficiency-weighted matching
- Endorsement-trust weighting

No external models needed — pure rule-based graph traversal.
Runs in O(skills per candidate × JD_skills) — very fast.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# ──────────────────────────────────────────────────────────────
# INLINE SKILL DEFINITIONS (no file I/O required at init)
# Mirrors build_skill_db.py but self-contained for speed
# ──────────────────────────────────────────────────────────────

PROFICIENCY_SCORES = {
    "beginner": 0.35,
    "intermediate": 0.65,
    "advanced": 0.85,
    "expert": 1.00,
}

# Each key is a canonical JD skill; values are aliases that count as a FULL match
# Aliases score 0.85x to avoid penalizing different naming conventions
FULL_MATCH_ALIASES: dict[str, set[str]] = {
    "embeddings": {
        "text embeddings", "vector embeddings", "dense vectors",
        "semantic embeddings", "neural embeddings", "word2vec", "doc2vec",
        "embedding models", "sentence embeddings",
    },
    "vector database": {
        "vector db", "vector store", "faiss", "pinecone", "weaviate", "qdrant",
        "milvus", "chroma", "chromadb", "vespa", "ann",
        "approximate nearest neighbor", "hnsw", "vector index", "pgvector",
    },
    "information retrieval": {
        "ir", "search", "document retrieval", "passage retrieval",
        "dense retrieval", "sparse retrieval", "hybrid retrieval",
        "bi-encoder", "cross-encoder", "bm25", "tfidf", "elasticsearch",
        "opensearch", "solr", "lucene",
    },
    "ranking": {
        "learning to rank", "ltr", "lambdamart", "lambdarank", "ranknet",
        "neural reranking", "re-ranking", "reranking", "relevance ranking",
        "xgboost ranking", "listwise ranking", "pairwise ranking",
    },
    "nlp": {
        "natural language processing", "text processing", "text classification",
        "named entity recognition", "ner", "sentiment analysis", "text mining",
        "sequence labeling",
    },
    "llm": {
        "large language models", "gpt", "gpt-4", "claude", "llama", "mistral",
        "palm", "gemini", "chatgpt", "foundation models", "instruction tuning",
        "generative ai",
    },
    "rag": {
        "retrieval augmented generation", "retrieval-augmented generation",
        "rag pipeline", "knowledge-augmented generation", "grounding",
    },
    "sentence-transformers": {
        "sentence transformers", "sbert", "all-minilm", "mpnet", "e5", "bge",
        "instructor", "gte", "openai embeddings", "text-embedding-ada",
        "cohere embeddings",
    },
    "evaluation frameworks": {
        "ndcg", "mrr", "map", "precision at k", "recall at k", "a/b testing",
        "ab testing", "offline evaluation", "online evaluation", "bandit",
        "interleaving", "click models", "relevance judgment",
    },
    "python": {
        "python3", "python programming", "numpy", "pandas", "scikit-learn",
        "sklearn",
    },
    "fine-tuning": {
        "model fine-tuning", "lora", "qlora", "peft", "adapter tuning",
        "instruction fine-tuning", "rlhf", "dpo", "domain adaptation",
        "transfer learning",
    },
    "recommendation systems": {
        "recommender systems", "collaborative filtering", "matrix factorization",
        "als", "svd", "factorization machines", "two-tower model",
        "candidate generation", "item2vec", "wide & deep", "deepfm",
        "neural collaborative filtering",
    },
}

# PARTIAL_MATCH: these skills give 0.6x credit (related but not the same)
# Format: jd_skill → {candidate_skill → partial_weight}
PARTIAL_MATCH: dict[str, dict[str, float]] = {
    "embeddings": {
        "hugging face transformers": 0.7, "bert": 0.7, "roberta": 0.7,
        "machine learning": 0.4, "deep learning": 0.4,
    },
    "vector database": {
        "elasticsearch": 0.8, "opensearch": 0.8, "solr": 0.6,
        "redis": 0.5, "postgresql": 0.4,
    },
    "information retrieval": {
        "recommendation systems": 0.7, "search": 0.9,
        "elasticsearch": 0.75, "whoosh": 0.6,
    },
    "ranking": {
        "recommendation systems": 0.75, "xgboost": 0.6, "lightgbm": 0.6,
        "gradient boosting": 0.6, "feature engineering": 0.4,
    },
    "nlp": {
        "bert": 0.8, "hugging face transformers": 0.8, "spacy": 0.7,
        "nltk": 0.6, "text mining": 0.7, "sequence to sequence": 0.6,
    },
    "llm": {
        "gpt": 1.0, "bert": 0.7, "hugging face transformers": 0.8,
        "fine-tuning": 0.7, "prompt engineering": 0.6,
    },
    "rag": {
        "llm": 0.7, "langchain": 0.6, "llamaindex": 0.7,
        "embeddings": 0.6, "vector database": 0.6,
    },
    "evaluation frameworks": {
        "a/b testing": 1.0, "statistics": 0.5, "data analysis": 0.4,
        "experimentation": 0.6,
    },
    "fine-tuning": {
        "pytorch": 0.6, "tensorflow": 0.6, "hugging face transformers": 0.8,
        "deep learning": 0.5,
    },
    "recommendation systems": {
        "ranking": 0.75, "collaborative filtering": 1.0,
        "matrix factorization": 0.9, "xgboost": 0.5,
    },
    "python": {
        "jupyter": 0.6, "colab": 0.5, "data science": 0.4,
    },
}

# JD skill weights
JD_WEIGHTS = {
    "embeddings": 3.0,
    "vector database": 3.0,
    "information retrieval": 3.0,
    "ranking": 3.0,
    "evaluation frameworks": 3.0,
    "python": 3.0,
    "nlp": 2.5,
    "sentence-transformers": 2.5,
    "rag": 2.5,
    "llm": 2.0,
    "fine-tuning": 1.5,
    "recommendation systems": 1.5,
}

MAX_JD_WEIGHT = sum(JD_WEIGHTS.values())


def _normalize(s: str) -> str:
    """Lowercase and strip for matching."""
    return s.lower().strip()


def _endorsement_trust(endorsements: int) -> float:
    """
    Sigmoid trust multiplier based on endorsement count.
    0 endorsements → 0.80x (not validated)
    10+ endorsements → 1.00x
    50+ endorsements → 1.10x (strong social proof)
    """
    if endorsements <= 0:
        return 0.80
    return min(1.10, 0.80 + 0.30 * (1 / (1 + math.exp(-0.15 * (endorsements - 10)))))


def _duration_confidence(duration_months: int) -> float:
    """
    Confidence multiplier from time using the skill.
    0 months → suspicious (0.5x) — can't be expert with 0 use
    6 months → 0.75x
    24+ months → 1.0x
    48+ months → 1.05x
    """
    if duration_months == 0:
        return 0.50  # Impossible to be competent with 0 usage
    elif duration_months < 6:
        return 0.70
    elif duration_months < 12:
        return 0.82
    elif duration_months < 24:
        return 0.92
    elif duration_months < 48:
        return 1.00
    else:
        return 1.05


def _assessment_override(
    proficiency_score: float,
    assessment_score: float | None,
) -> float:
    """
    Platform assessment overrides self-reported proficiency.
    If candidate claimed 'expert' but scored 30% on test → cap at 0.50.
    If candidate claimed 'intermediate' but scored 90% → boost.
    """
    if assessment_score is None or assessment_score < 0:
        return proficiency_score
    # Assessment score is 0-100
    test_score = assessment_score / 100
    # Blend: 0.4 * self_report + 0.6 * test (test is more objective)
    return 0.4 * proficiency_score + 0.6 * test_score


def match_score(candidate: dict, jd_config=None) -> float:
    """
    Compute how well candidate skills match JD requirements.
    Uses knowledge graph traversal (full match, partial match, alias match).
    Returns normalized score in [0.0, 1.0].
    """
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})
    assessment_scores = signals.get("skill_assessment_scores", {})

    # Build candidate skill lookup: normalized_name → best effective score
    candidate_skills: dict[str, float] = {}

    for skill_obj in skills:
        name_raw = skill_obj.get("name", "")
        name = _normalize(name_raw)
        proficiency = PROFICIENCY_SCORES.get(
            skill_obj.get("proficiency", "beginner"), 0.35
        )
        endorsements = skill_obj.get("endorsements", 0)
        duration_months = skill_obj.get("duration_months", 0)

        # Get platform assessment if available
        assess = assessment_scores.get(name_raw, None)
        if assess is None:
            # Try case-insensitive lookup
            for k, v in assessment_scores.items():
                if k.lower() == name:
                    assess = v
                    break

        # Compute effective skill strength
        effective = (
            _assessment_override(proficiency, assess)
            * _endorsement_trust(endorsements)
            * _duration_confidence(duration_months)
        )

        # Keep the best score for this skill name
        candidate_skills[name] = max(candidate_skills.get(name, 0.0), effective)

    # ── Score each JD skill ──────────────────────────────────────
    total_weighted_score = 0.0

    for jd_skill, jd_weight in JD_WEIGHTS.items():
        jd_norm = _normalize(jd_skill)
        best_match = 0.0

        # Check 1: Exact or alias match (full credit × 0.85-1.0)
        if jd_norm in candidate_skills:
            best_match = max(best_match, candidate_skills[jd_norm] * 1.00)

        # Check 2: Alias matches (full credit × 0.90)
        for alias in FULL_MATCH_ALIASES.get(jd_skill, set()):
            alias_norm = _normalize(alias)
            if alias_norm in candidate_skills:
                best_match = max(best_match, candidate_skills[alias_norm] * 0.90)

        # Check 3: Partial match (partial credit)
        for partial_skill, partial_weight in PARTIAL_MATCH.get(jd_skill, {}).items():
            partial_norm = _normalize(partial_skill)
            if partial_norm in candidate_skills:
                best_match = max(
                    best_match,
                    candidate_skills[partial_norm] * partial_weight * 0.80
                )

        total_weighted_score += jd_weight * best_match

    # Normalize to [0, 1] — divide by theoretical max
    # Max is achieved when all JD skills are at 1.10 effective strength
    theoretical_max = MAX_JD_WEIGHT * 1.10
    normalized = total_weighted_score / theoretical_max

    return min(1.0, normalized)


def get_matched_skills(candidate: dict, jd_config=None) -> list[str]:
    """Return list of JD-relevant skill names this candidate has (for reasoning)."""
    skills = candidate.get("skills", [])
    matched = []

    for skill_obj in skills:
        name_raw = skill_obj.get("name", "")
        name = _normalize(name_raw)

        for jd_skill, aliases in FULL_MATCH_ALIASES.items():
            aliases_normalized = {_normalize(a) for a in aliases}
            if name == _normalize(jd_skill) or name in aliases_normalized:
                matched.append(name_raw)
                break

    # Deduplicate preserving order
    seen = set()
    return [s for s in matched if not (s.lower() in seen or seen.add(s.lower()))]
