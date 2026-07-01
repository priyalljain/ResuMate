#!/usr/bin/env python3
"""
prefetch_model.py — run this ONCE, with network access, to download and
cache all-MiniLM-L6-v2 into the local sentence-transformers/HuggingFace
cache directory. The Dockerfile calls this during the image build step
(while network is still available), so that at grading time, when the
container runs with --network none, SentenceTransformer('all-MiniLM-L6-v2')
loads from the local cache instead of trying to reach huggingface.co.

Run locally before your first `python rank.py ...` call too -- otherwise
the first run will print a [rerank] WARNING and silently skip semantic
reranking (rule-based scores only), which still produces a valid
submission, just without the SBERT smoothing pass.
"""
import sys

try:
    from sentence_transformers import SentenceTransformer
    print("Downloading and caching sentence-transformers/all-MiniLM-L6-v2 ...")
    SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    print("Done. Model is cached locally for offline use.")
except Exception as e:  # noqa: BLE001
    print(f"ERROR: could not prefetch model: {e}", file=sys.stderr)
    print("If this is just your own dev machine, you can still run rank.py "
          "with --no-sbert, or run it once with network access first.", file=sys.stderr)
    sys.exit(1)
