"""
rerank.py — Stage 2 of the funnel: fine-grained semantic similarity on a
shortlist only (not the full 100K pool).

Why a shortlist and not the full pool: encoding 100,000 candidate narrative
blocks on CPU is the single most likely way to blow the 5-minute budget.
Encoding ~1,500 shortlisted candidates' text plus the JD is comfortably fast
(seconds, not minutes) on CPU with all-MiniLM-L6-v2 -- it's also more than
generous in practice, well past the spec's "no GPU" constraint.

Network discipline: SentenceTransformer('all-MiniLM-L6-v2') will try to hit
huggingface.co on first use if the model isn't already cached locally. Since
ranking must run with --network none, the model MUST be pre-downloaded
before the ranking run (see Dockerfile / scripts/prefetch_model.py). This
module fails soft: if the model can't be loaded (not cached, or
sentence-transformers isn't installed), it logs a warning and the pipeline
falls back to rule-based scores only rather than crashing the run.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Tuple

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None
_load_attempted = False


def _get_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
    except Exception as e:  # noqa: BLE001 - deliberately broad: any failure here must not crash ranking
        print(f"[rerank] WARNING: SBERT model unavailable ({e}); "
              f"continuing with rule-based scores only.", file=sys.stderr)
        _model = None
    return _model


def semantic_rerank(jd_text: str, shortlist: List[Tuple[Dict[str, Any], str]]) -> Dict[str, float]:
    """shortlist: list of (candidate_dict, narrative_text) tuples.
    Returns {candidate_id: cosine_similarity_0_to_1}. Empty dict if the
    model is unavailable (caller should treat missing entries as 0 weight,
    i.e. fall back to rule-based score alone)."""
    model = _get_model()
    if model is None or not shortlist:
        return {}

    from sentence_transformers import util

    texts = [narrative for _, narrative in shortlist]
    ids = [c["candidate_id"] for c, _ in shortlist]

    jd_emb = model.encode(jd_text, convert_to_tensor=True, show_progress_bar=False)
    cand_embs = model.encode(texts, convert_to_tensor=True, show_progress_bar=False, batch_size=64)

    sims = util.cos_sim(jd_emb, cand_embs)[0].tolist()
    # cosine similarity is in [-1, 1]; rescale to [0, 1] for blending with our other 0-1 scores.
    return {cid: max(0.0, (s + 1.0) / 2.0) for cid, s in zip(ids, sims)}
