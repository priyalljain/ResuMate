#!/usr/bin/env python3
"""
Precompute: Generate SBERT embeddings for all candidates (optional).

This is OPTIONAL for the main ranker — rank.py uses fast rule-based scoring
by default (zero external dependencies).

If you want to enable semantic embedding similarity (for Pillar 2 enhancement),
run this script ONCE offline:

  python precompute/build_embeddings.py --candidates ./candidates.jsonl.gz

This generates:
  data/candidate_embeddings.pkl  (~38 MB for 100K candidates at 384-dim)
  data/skill_embeddings.pkl       (~2 MB for unique skills)

Runtime: ~15-20 minutes on CPU (100K candidates × 384-dim SBERT).
rank.py detects if these files exist and uses them; otherwise falls back
to the rule-based knowledge graph (which is fast and accurate).

Constraints: All embedding work is OFFLINE. rank.py itself does NOT load
or run SBERT — this meets the no-network and <5-min runtime constraints.
"""

import argparse
import gzip
import json
import pickle
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def build_embeddings(candidates_path: str):
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        print("sentence-transformers or numpy not installed.")
        print("Run: pip install sentence-transformers numpy")
        return

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    print("Model loaded.")

    path = Path(candidates_path)
    opener = gzip.open if path.suffix == ".gz" else open
    open_mode = "rt"

    candidate_ids = []
    candidate_texts = []
    all_skills = set()

    print("Loading candidates...")
    with opener(path, open_mode, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue

            cid = c.get("candidate_id", "")
            if not cid:
                continue

            profile = c.get("profile", {})
            summary = profile.get("summary", "")
            headline = profile.get("headline", "")
            skill_names = " ".join(s.get("name", "") for s in c.get("skills", []))
            desc_text = " ".join(
                r.get("description", "")[:300] for r in c.get("career_history", [])[:3]
            )
            text = f"{headline}. {summary}. Skills: {skill_names}. {desc_text}"

            candidate_ids.append(cid)
            candidate_texts.append(text[:1000])  # Cap for memory
            all_skills.update(s.get("name", "").lower() for s in c.get("skills", []))

    print(f"Loaded {len(candidate_ids):,} candidates, {len(all_skills):,} unique skills")

    # Encode in batches
    print("Encoding candidates (batch size 256)...")
    import numpy as np
    all_embs = model.encode(
        candidate_texts,
        batch_size=256,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    out1 = DATA_DIR / "candidate_embeddings.pkl"
    with open(out1, "wb") as f:
        pickle.dump({"ids": candidate_ids, "embeddings": all_embs}, f, protocol=4)
    print(f"Saved candidate embeddings: {out1} ({all_embs.shape})")

    # Encode skills
    print("Encoding skills...")
    skill_list = sorted(all_skills)
    skill_embs = model.encode(
        skill_list,
        batch_size=512,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    skill_to_idx = {s: i for i, s in enumerate(skill_list)}

    out2 = DATA_DIR / "skill_embeddings.pkl"
    with open(out2, "wb") as f:
        pickle.dump({
            "skill_list": skill_list,
            "embeddings": skill_embs,
            "skill_to_idx": skill_to_idx,
        }, f, protocol=4)
    print(f"Saved skill embeddings: {out2} ({skill_embs.shape})")
    print("Done. rank.py will detect and use these automatically.")


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="./candidates.jsonl",
                        help="Path to candidates.jsonl or candidates.jsonl.gz")
    args = parser.parse_args()
    build_embeddings(args.candidates)
