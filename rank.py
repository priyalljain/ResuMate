#!/usr/bin/env python3
"""
rank.py — Redrob Hackathon candidate ranker. Single-command entrypoint:

    python rank.py --candidates ./candidates.jsonl.gz --jd ./job_description.md --out ./submission.csv

Pipeline (the "cascading funnel"):
  1. Stream candidates.jsonl(.gz) line-by-line (io_utils) -- bounded memory.
  2. Per candidate: integrity check (integrity.py) -> rule-based JD-fit score
     (scoring.py). O(1) work per candidate, no model inference -- this pass
     covers the full 100K pool and is fast (pure Python/dict logic).
  3. Maintain a bounded min-heap of the top SHORTLIST_SIZE candidates by
     rule-based score (default 2000) -- this is the "Stage 3 -> top 500-2000"
     funnel narrowing from the architecture discussion.
  4. Run SBERT semantic similarity (rerank.py) ONLY on the shortlist, blend
     it lightly (15%) into the final score. This is the only part of the
     pipeline that touches a neural model, and it never sees more than
     SHORTLIST_SIZE candidates, keeping it well inside the 5-minute budget.
  5. Sort by (-score rounded to 4dp, candidate_id ascending) -- this single
     sort key simultaneously guarantees the "non-increasing score" rule AND
     the "ties broken by candidate_id ascending" rule from
     validate_submission.py.
  6. Take exactly the top 100, assign rank 1..100, generate grounded
     reasoning text (reasoning.py), write the CSV in the exact required
     format (candidate_id,rank,score,reasoning).

Compute constraints this script is written against (submission_spec.md
section 3): <=5 min wall-clock, <=16GB RAM, CPU only, no network during
ranking, <=5GB intermediate disk. No GPU code path exists in this script.
"""
from __future__ import annotations

import argparse
import csv
import heapq
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import io_utils, integrity, domain_config, scoring, rerank, reasoning  # noqa: E402

REQUIRED_HEADER = ["candidate_id", "rank", "score", "reasoning"]
DEFAULT_SHORTLIST_SIZE = 2000
DEFAULT_TOP_N = 100


def main():
    parser = argparse.ArgumentParser(description="Redrob Hackathon candidate ranker")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl or candidates.jsonl.gz")
    parser.add_argument("--jd", default=str(Path(__file__).resolve().parent / "job_description.md"),
                         help="Path to the job description text/markdown file")
    parser.add_argument("--out", required=True, help="Output submission CSV path")
    parser.add_argument("--shortlist-size", type=int, default=DEFAULT_SHORTLIST_SIZE,
                         help="How many top candidates (by rule-based score) advance to the SBERT rerank stage")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="How many ranked rows to output")
    parser.add_argument("--no-sbert", action="store_true", help="Skip the SBERT semantic rerank stage entirely")
    parser.add_argument("--allow-short-pool", action="store_true",
                         help="Allow output with fewer than --top-n rows (TESTING ONLY -- "
                              "the real validator requires exactly 100 rows; use this only "
                              "against small sample files like sample_candidates.json)")
    args = parser.parse_args()

    t0 = time.time()

    jd_text = Path(args.jd).read_text(encoding="utf-8")
    graphs = domain_config.load_domain_graphs()
    domain = domain_config.detect_domain(jd_text, graphs)
    cfg = graphs[domain]
    print(f"[rank] Detected JD domain: {domain}", file=sys.stderr)

    heap = []  # min-heap of (rule_score, counter, candidate, narrative_text, components)
    counter = 0
    n_seen = 0
    n_integrity_flagged = 0

    for candidate in io_utils.iter_candidates(args.candidates):
        n_seen += 1
        integrity_mult, integrity_flags = integrity.evaluate_integrity(candidate)
        if integrity_flags:
            n_integrity_flagged += 1
        components = scoring.score_candidate(candidate, domain, cfg, integrity_mult)
        components["integrity_flags"] = integrity_flags
        rule_score = components["final_score"]
        _, narrative_text = scoring.build_text_blobs(candidate)

        counter += 1
        item = (rule_score, counter, candidate, narrative_text, components)
        if len(heap) < args.shortlist_size:
            heapq.heappush(heap, item)
        elif rule_score > heap[0][0]:
            heapq.heapreplace(heap, item)

        if n_seen % 20000 == 0:
            print(f"[rank] ...scored {n_seen} candidates ({time.time()-t0:.1f}s elapsed)", file=sys.stderr)

    print(f"[rank] Streamed {n_seen} candidates total "
          f"({n_integrity_flagged} flagged by integrity checks). "
          f"Shortlist size: {len(heap)}. Elapsed: {time.time()-t0:.1f}s", file=sys.stderr)

    if n_seen == 0:
        raise SystemExit(f"No candidates parsed from {args.candidates} -- check the file path/format.")

    sbert_map = {}
    if not args.no_sbert:
        shortlist_pairs = [(c, narrative) for (_, _, c, narrative, _) in heap]
        sbert_map = rerank.semantic_rerank(jd_text, shortlist_pairs)
        print(f"[rank] SBERT rerank produced {len(sbert_map)} scores. "
              f"Elapsed: {time.time()-t0:.1f}s", file=sys.stderr)

    results = []
    for rule_score, _, candidate, narrative_text, components in heap:
        sbert_sim = sbert_map.get(candidate["candidate_id"])
        if sbert_sim is not None:
            blended = 0.85 * rule_score + 0.15 * sbert_sim
        else:
            blended = rule_score
        components["final_score"] = blended
        components["sbert_similarity"] = sbert_sim
        results.append((blended, candidate, components))

    # Single sort key that simultaneously satisfies "score non-increasing by
    # rank" and "ties broken by candidate_id ascending":
    results.sort(key=lambda r: (-round(r[0], 4), r[1]["candidate_id"]))

    top_n = args.top_n
    if len(results) < top_n:
        msg = (f"Only {len(results)} candidates available but --top-n={top_n} was requested. "
               f"The real hackathon submission REQUIRES exactly 100 rows -- this is expected "
               f"only when testing against a small sample file.")
        if args.allow_short_pool:
            print(f"[rank] WARNING: {msg}", file=sys.stderr)
            top_n = len(results)
        else:
            raise SystemExit(f"[rank] ERROR: {msg} Pass --allow-short-pool to proceed anyway for local testing.")

    rows = []
    for rank, (score, candidate, components) in enumerate(results[:top_n], start=1):
        reasoning_text = reasoning.build_reasoning(candidate, components)
        rows.append([candidate["candidate_id"], rank, f"{round(score, 4):.4f}", reasoning_text])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(REQUIRED_HEADER)
        writer.writerows(rows)

    print(f"[rank] Wrote {len(rows)} rows to {out_path}. Total elapsed: {time.time()-t0:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
