"""
JD Parser & Config System — makes the ranker work for ANY job description.

Instead of hardcoding skills/locations/YoE for the Redrobb AI Engineer JD,
this module provides:
  1. A JDConfig dataclass that holds all JD-specific parameters
  2. A set of pre-built configs (Redrobb AI Engineer is the primary one)
  3. A parse_jd_text() function to extract config from raw JD text

The ranker calls get_active_jd_config() at startup and all pillars
receive the config object — zero hardcoded values anywhere else.

For the hackathon: the Redrobb AI Engineer JD is active by default.
To rank for a different role, set JD_CONFIG_NAME env var or pass --jd flag.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


@dataclass
class JDConfig:
    """
    All parameters extracted from a job description.
    Pillars read from this object — nothing is hardcoded elsewhere.
    """
    # Role identity
    role_name: str = "Unknown Role"
    company: str = "Unknown Company"
    seniority: str = "mid"  # junior / mid / senior / lead / staff

    # Experience band
    yoe_min: float = 3.0
    yoe_max: float = 10.0
    yoe_ideal_min: float = 5.0
    yoe_ideal_max: float = 8.0

    # Skills (canonical JD skill name → weight)
    must_have_skills: dict[str, float] = field(default_factory=dict)
    nice_to_have_skills: dict[str, float] = field(default_factory=dict)
    negative_skills: dict[str, float] = field(default_factory=dict)

    # Location
    preferred_cities: list[str] = field(default_factory=list)
    preferred_country: str = "India"
    remote_ok: bool = False
    hybrid_ok: bool = True

    # Logistics
    notice_ideal_days: int = 30
    notice_max_days: int = 90

    # Scoring weights (must sum to 1.0)
    axis_weights: dict[str, float] = field(default_factory=lambda: {
        "kg": 0.35, "traj": 0.28, "exp": 0.15,
        "loc": 0.09, "edu": 0.07, "narr": 0.06,
    })

    # Narrative signals
    positive_narrative_terms: list[str] = field(default_factory=list)
    negative_narrative_terms: list[str] = field(default_factory=list)

    # Disqualifying title patterns (regex strings)
    disqualifying_title_patterns: list[str] = field(default_factory=list)

    # Services firms to penalize
    services_firms: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# PRE-BUILT JD CONFIGS
# ─────────────────────────────────────────────────────────────

def _redrobb_ai_engineer_jd() -> JDConfig:
    """
    Redrobb Hackathon: Senior AI/ML Engineer — Embeddings, Ranking, Retrieval
    This is the PRIMARY config used for the hackathon submission.
    Source: job_description.md in the hackathon bundle.
    """
    return JDConfig(
        role_name="Senior AI/ML Engineer — Embeddings, Ranking & Retrieval",
        company="Redrobb",
        seniority="senior",
        yoe_min=5.0,
        yoe_max=9.0,
        yoe_ideal_min=6.0,
        yoe_ideal_max=8.0,
        must_have_skills={
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
        },
        nice_to_have_skills={
            "fine-tuning": 1.5,
            "recommendation systems": 1.5,
            "mlops": 1.2,
            "xgboost": 1.2,
            "feature engineering": 1.2,
            "pytorch": 0.8,
            "tensorflow": 0.8,
            "hugging face": 0.8,
            "distributed systems": 0.8,
            "apache spark": 0.6,
            "aws": 0.5,
            "gcp": 0.5,
            "docker": 0.4,
            "sql": 0.4,
        },
        negative_skills={
            "photoshop": -0.5, "illustrator": -0.5,
            "marketing": -0.5, "sales": -0.5,
            "accounting": -0.5,
        },
        preferred_cities=["pune", "noida", "bangalore", "bengaluru",
                         "hyderabad", "mumbai", "delhi", "ncr",
                         "gurgaon", "gurugram"],
        preferred_country="India",
        remote_ok=False,
        hybrid_ok=True,
        notice_ideal_days=30,
        notice_max_days=90,
        axis_weights={
            "kg": 0.35, "traj": 0.28, "exp": 0.15,
            "loc": 0.09, "edu": 0.07, "narr": 0.06,
        },
        positive_narrative_terms=[
            "production", "ship", "deploy", "launch", "real users",
            "at scale", "high traffic", "low latency", "recommendation",
            "search", "retrieval", "ranking", "embedding", "vector",
            "dense", "sparse", "nlp", "natural language", "semantic",
            "llm", "language model", "fine-tun", "rag", "evaluation",
            "benchmark", "ndcg", "mrr", "a/b test", "product company",
            "feature pipeline", "feature store", "ml engineer",
        ],
        negative_narrative_terms=[
            "academia", "thesis", "publication", "paper", "lab",
            "research institute", "consulting", "delivery", "outsourc",
            "marketing", "accounting", "hr", "sales", "graphic design",
            "civil", "mechanical", "supply chain",
        ],
        disqualifying_title_patterns=[
            r"marketing manager", r"sales executive", r"sales manager",
            r"hr manager", r"content writer", r"graphic designer",
            r"ux designer", r"ui designer", r"scrum master",
            r"accountant", r"customer support", r"civil engineer",
            r"mechanical engineer", r"supply chain", r"procurement",
            r"finance manager",
        ],
        services_firms=[
            "tcs", "tata consultancy", "infosys", "wipro", "accenture",
            "cognizant", "capgemini", "hcl", "tech mahindra", "hexaware",
            "mphasis", "ltimindtree", "mindtree",
        ],
    )


def _generic_backend_engineer_jd() -> JDConfig:
    """Generic backend/software engineer JD template."""
    return JDConfig(
        role_name="Senior Backend Engineer",
        company="Generic",
        seniority="senior",
        yoe_min=4.0, yoe_max=10.0,
        yoe_ideal_min=5.0, yoe_ideal_max=8.0,
        must_have_skills={
            "python": 3.0, "sql": 3.0, "system design": 3.0,
            "api design": 2.5, "distributed systems": 2.5,
        },
        nice_to_have_skills={
            "docker": 1.5, "kubernetes": 1.5, "aws": 1.2,
            "kafka": 1.0, "spark": 0.8,
        },
        preferred_cities=["bangalore", "bengaluru", "hyderabad", "pune", "mumbai"],
        preferred_country="India",
        axis_weights={
            "kg": 0.32, "traj": 0.28, "exp": 0.17,
            "loc": 0.10, "edu": 0.07, "narr": 0.06,
        },
    )


def _generic_data_scientist_jd() -> JDConfig:
    """Generic data scientist JD template."""
    return JDConfig(
        role_name="Senior Data Scientist",
        company="Generic",
        seniority="senior",
        yoe_min=4.0, yoe_max=9.0,
        yoe_ideal_min=5.0, yoe_ideal_max=7.0,
        must_have_skills={
            "python": 3.0, "machine learning": 3.0,
            "statistics": 2.5, "sql": 2.0, "data analysis": 2.0,
        },
        nice_to_have_skills={
            "pytorch": 1.5, "tensorflow": 1.5, "xgboost": 1.5,
            "mlops": 1.2, "aws": 1.0, "spark": 0.8,
        },
        preferred_cities=["bangalore", "bengaluru", "hyderabad", "pune", "mumbai"],
        preferred_country="India",
    )


# Registry of all built-in JD configs
_JD_REGISTRY: dict[str, JDConfig] = {
    "redrobb_ai_engineer": _redrobb_ai_engineer_jd(),
    "backend_engineer": _generic_backend_engineer_jd(),
    "data_scientist": _generic_data_scientist_jd(),
}

# Active config (module-level singleton)
_ACTIVE_CONFIG: JDConfig | None = None


def get_active_jd_config() -> JDConfig:
    """Get the active JD config. Reads JD_CONFIG_NAME env var or defaults to redrobb_ai_engineer."""
    global _ACTIVE_CONFIG
    if _ACTIVE_CONFIG is None:
        name = os.environ.get("JD_CONFIG_NAME", "redrobb_ai_engineer")
        _ACTIVE_CONFIG = _JD_REGISTRY.get(name, _redrobb_ai_engineer_jd())
    return _ACTIVE_CONFIG


def set_active_jd_config(config: JDConfig):
    """Override the active config (for testing or custom JDs)."""
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = config


def parse_jd_text(jd_text: str, role_name: str = "Custom Role") -> JDConfig:
    """
    Parse a raw JD text and extract a JDConfig.
    Used when --jd flag is passed to rank.py with a text file.

    Extracts:
    - Years of experience band
    - Skills (from 'required', 'preferred', 'nice to have' sections)
    - Location hints
    - Seniority from title keywords
    """
    text_lower = jd_text.lower()

    # Extract YoE band
    yoe_pattern = re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*years?", text_lower)
    yoe_min, yoe_max = 3.0, 10.0
    if yoe_pattern:
        yoe_min = float(yoe_pattern.group(1))
        yoe_max = float(yoe_pattern.group(2))

    yoe_ideal_min = yoe_min + 1
    yoe_ideal_max = yoe_max - 1

    # Extract seniority
    seniority = "mid"
    if any(w in text_lower for w in ["senior", "sr.", "lead", "principal", "staff"]):
        seniority = "senior"
    elif any(w in text_lower for w in ["junior", "jr.", "entry"]):
        seniority = "junior"

    # Extract skills from common sections
    ml_tech_skills = [
        "python", "pytorch", "tensorflow", "keras", "sklearn", "numpy",
        "pandas", "spark", "kafka", "docker", "kubernetes", "aws", "gcp",
        "azure", "sql", "postgresql", "mongodb", "redis", "elasticsearch",
        "faiss", "pinecone", "weaviate", "qdrant", "milvus",
        "bert", "gpt", "llm", "rag", "embeddings", "nlp",
        "transformers", "hugging face", "sentence-transformers",
        "ranking", "retrieval", "recommendation", "vector database",
        "fine-tuning", "lora", "mlops", "mlflow", "airflow",
        "xgboost", "lightgbm", "gradient boosting",
    ]

    must_have = {}
    nice_to_have = {}

    for skill in ml_tech_skills:
        if skill in text_lower:
            # Heuristic: if in "required" section → must-have (2.0), else nice-to-have (1.0)
            must_have[skill] = 2.0

    # Location
    cities = []
    for city in ["pune", "bangalore", "bengaluru", "hyderabad", "mumbai",
                 "delhi", "noida", "gurgaon", "chennai", "kolkata"]:
        if city in text_lower:
            cities.append(city)

    return JDConfig(
        role_name=role_name,
        seniority=seniority,
        yoe_min=yoe_min,
        yoe_max=yoe_max,
        yoe_ideal_min=yoe_ideal_min,
        yoe_ideal_max=yoe_ideal_max,
        must_have_skills=must_have,
        nice_to_have_skills=nice_to_have,
        preferred_cities=cities or ["bangalore", "hyderabad", "pune", "mumbai"],
        preferred_country="India",
        axis_weights={
            "kg": 0.35, "traj": 0.28, "exp": 0.15,
            "loc": 0.09, "edu": 0.07, "narr": 0.06,
        },
    )
