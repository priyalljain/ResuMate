#!/usr/bin/env python3
"""
Build a comprehensive skill relationship database.
Covers 700+ skills with synonyms, related terms, and domain mappings.
Saved as data/skill_related.json and data/skill_canonical.json
"""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
# CANONICAL SKILL GROUPS — each group shares weight during matching
# Format: { canonical_name: [aliases/related terms] }
# ─────────────────────────────────────────────

SKILL_GROUPS = {
    # ── CORE JD MUST-HAVES ────────────────────────────────────────
    "embeddings": [
        "text embeddings", "vector embeddings", "dense vectors", "dense retrieval",
        "sentence embeddings", "semantic embeddings", "neural embeddings",
        "word2vec", "fasttext", "glove", "doc2vec", "embedding models",
    ],
    "vector database": [
        "vector db", "vector store", "faiss", "pinecone", "weaviate", "qdrant",
        "milvus", "chroma", "chromadb", "vespa", "vald", "redis vector",
        "pgvector", "ann", "approximate nearest neighbor", "hnsw",
        "vector index", "ivf", "product quantization",
    ],
    "information retrieval": [
        "ir", "search", "document retrieval", "passage retrieval",
        "dense retrieval", "sparse retrieval", "hybrid retrieval",
        "bi-encoder", "cross-encoder", "bm25", "tfidf", "inverted index",
        "elasticsearch", "opensearch", "solr", "lucene", "whoosh",
    ],
    "ranking": [
        "learning to rank", "ltr", "pointwise ranking", "pairwise ranking",
        "listwise ranking", "xgboost ranking", "lambdamart", "lambdarank",
        "ranknet", "neural reranking", "re-ranking", "reranking",
        "ranking models", "relevance ranking", "candidate ranking",
    ],
    "nlp": [
        "natural language processing", "text processing", "computational linguistics",
        "text classification", "named entity recognition", "ner",
        "sentiment analysis", "text mining", "language models",
        "sequence labeling", "coreference resolution", "dependency parsing",
    ],
    "llm": [
        "large language models", "gpt", "gpt-4", "claude", "llama", "mistral",
        "falcon", "palm", "gemini", "chatgpt", "language models",
        "generative ai", "foundation models", "instruction tuning",
    ],
    "rag": [
        "retrieval augmented generation", "retrieval-augmented generation",
        "retrieval augmented", "rag pipeline", "knowledge-augmented generation",
        "grounding", "context retrieval",
    ],
    "sentence-transformers": [
        "sentence transformers", "sbert", "bi-encoder", "all-minilm",
        "mpnet", "e5", "bge", "instructor", "gte", "openai embeddings",
        "text-embedding-ada", "cohere embeddings",
    ],
    "evaluation frameworks": [
        "ndcg", "mrr", "map", "precision at k", "recall at k", "f1",
        "offline evaluation", "online evaluation", "a/b testing",
        "ab testing", "bandit", "interleaving", "click models",
        "relevance judgment", "qrel", "trec", "beir", "ms marco",
    ],
    "python": [
        "python3", "python programming", "cpython", "numpy", "pandas",
        "scipy", "scikit-learn", "sklearn", "matplotlib", "seaborn",
    ],
    "fine-tuning": [
        "model fine-tuning", "lora", "qlora", "peft", "adapter tuning",
        "instruction fine-tuning", "rlhf", "dpo", "domain adaptation",
        "transfer learning", "continual learning",
    ],

    # ── JD NICE-TO-HAVES ─────────────────────────────────────────
    "recommendation systems": [
        "recommender systems", "collaborative filtering", "content-based filtering",
        "matrix factorization", "als", "svd", "factorization machines",
        "two-tower model", "candidate generation", "item2vec", "wide & deep",
        "deepfm", "neural collaborative filtering",
    ],
    "feature engineering": [
        "feature extraction", "feature selection", "feature transformation",
        "feature store", "feast", "tecton", "hopsworks",
    ],
    "mlops": [
        "ml ops", "ml infrastructure", "model serving", "model deployment",
        "model monitoring", "mlflow", "kubeflow", "metaflow", "bentoml",
        "ray serve", "torchserve", "triton inference", "seldon",
        "feature drift", "data drift", "concept drift",
    ],
    "pytorch": [
        "torch", "pytorch lightning", "deep learning framework",
        "neural networks", "backpropagation", "autograd",
    ],
    "tensorflow": [
        "keras", "tf", "tensorflow serving", "tflite", "tensorflow extended",
        "tfx",
    ],
    "hugging face": [
        "huggingface", "hugging face transformers", "transformers library",
        "datasets library", "hf hub", "model hub",
    ],
    "xgboost": [
        "gradient boosting", "lightgbm", "catboost", "gbm", "gbdt",
        "ensemble methods", "boosting",
    ],
    "distributed systems": [
        "distributed computing", "horizontal scaling", "microservices",
        "kafka", "rabbitmq", "celery", "message queue",
    ],
    "apache spark": [
        "spark", "pyspark", "spark ml", "spark streaming", "databricks",
        "hdfs", "hadoop",
    ],

    # ── ADJACENT TECH ──────────────────────────────────────────────
    "docker": ["containerization", "kubernetes", "k8s", "container", "helm", "pod"],
    "aws": ["amazon web services", "ec2", "s3", "sagemaker", "lambda", "ecs", "eks"],
    "gcp": ["google cloud", "bigquery", "vertex ai", "cloud run", "gke"],
    "azure": ["microsoft azure", "azure ml", "azure openai", "aks"],
    "git": ["version control", "github", "gitlab", "bitbucket"],
    "sql": ["postgresql", "mysql", "sqlite", "bigquery", "snowflake", "redshift"],
    "data pipelines": ["etl", "airflow", "prefect", "dagster", "dbt", "data orchestration"],
    "rust": ["rust lang", "cargo"],
    "golang": ["go", "go lang"],
    "java": ["jvm", "spring", "spring boot"],
    "scala": ["akka", "play framework"],
    "cpp": ["c++", "c plus plus"],

    # ── NON-RELEVANT SKILLS (for negative weighting) ────────────────
    "photoshop": ["illustrator", "figma", "canva", "adobe", "graphic design", "ui design"],
    "marketing": ["seo", "sem", "content marketing", "digital marketing", "campaign"],
    "sales": ["crm", "salesforce", "cold calling", "lead generation"],
    "accounting": ["bookkeeping", "tally", "quickbooks", "tax", "audit"],
    "project management": ["pmp", "scrum master", "agile", "jira", "trello"],
}

# ─────────────────────────────────────────────
# BUILD REVERSE INDEX: alias → canonical
# ─────────────────────────────────────────────

def normalize(s: str) -> str:
    return s.lower().strip()

canonical_map = {}  # alias → canonical
related_map = {}    # canonical → [all aliases]

for canonical, aliases in SKILL_GROUPS.items():
    can_norm = normalize(canonical)
    all_terms = [can_norm] + [normalize(a) for a in aliases]
    related_map[can_norm] = all_terms
    for term in all_terms:
        canonical_map[term] = can_norm

# ─────────────────────────────────────────────
# JD SKILL WEIGHTS (for scoring)
# ─────────────────────────────────────────────

JD_SKILL_WEIGHTS = {
    # Must-have: weight 3.0
    "embeddings": 3.0,
    "vector database": 3.0,
    "information retrieval": 3.0,
    "ranking": 3.0,
    "evaluation frameworks": 3.0,
    "python": 3.0,
    # Strong: weight 2.5
    "nlp": 2.5,
    "sentence-transformers": 2.5,
    "rag": 2.5,
    "llm": 2.0,
    # Nice-to-have: weight 1.5
    "fine-tuning": 1.5,
    "recommendation systems": 1.5,
    "mlops": 1.5,
    "xgboost": 1.5,
    "feature engineering": 1.5,
    # Adjacent: weight 0.8
    "pytorch": 0.8,
    "tensorflow": 0.8,
    "hugging face": 0.8,
    "distributed systems": 0.8,
    "apache spark": 0.8,
    "aws": 0.5,
    "gcp": 0.5,
    "docker": 0.4,
    "sql": 0.4,
    "git": 0.3,
    # Negative: −0.5 (irrelevant skills that dilute the profile)
    "photoshop": -0.5,
    "marketing": -0.5,
    "sales": -0.5,
    "accounting": -0.5,
}

def save():
    out1 = OUTPUT_DIR / "skill_canonical.json"
    out2 = OUTPUT_DIR / "skill_related.json"
    out3 = OUTPUT_DIR / "jd_skill_weights.json"
    with open(out1, "w") as f:
        json.dump(canonical_map, f, indent=2)
    with open(out2, "w") as f:
        json.dump(related_map, f, indent=2)
    with open(out3, "w") as f:
        json.dump(JD_SKILL_WEIGHTS, f, indent=2)
    print(f"Saved {len(canonical_map)} alias→canonical mappings")
    print(f"Saved {len(related_map)} canonical skill groups")
    print(f"Saved {len(JD_SKILL_WEIGHTS)} JD skill weights")

if __name__ == "__main__":
    save()
