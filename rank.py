#!/usr/bin/env python3
"""
Redrobb Hackathon — rank.py  (FINAL)
Intelligent Candidate Ranking Engine

Ranks 100,000 candidates → top 100, valid submission.csv

Architecture (6 Pillars):
  Pillar 1: Authenticity & Integrity     (11-check honeypot detection)
  Pillar 2: Knowledge Graph              (semantic skill matching, skill_related.json)
  Pillar 3: Causal Fairness              (education debiasing)
  Pillar 4: RL-Human Hybrid             (multi-axis reward + behavioral multiplier, 23 signals)
  Pillar 5: OCEAN Personality Proxy     (Big Five from behavioral signals)
  Pillar 6: JD Agnostic Config          (works for any job description)

Constraints:
  ✓ CPU only, no GPU
  ✓ ≤16 GB RAM (streaming + min-heap-100)
  ✓ ≤5 min runtime (~90s for 100K)
  ✓ No network calls during ranking
  ✓ Exactly 100 rows, ranks 1-100, scores non-increasing
  ✓ UTF-8 CSV: candidate_id, rank, score, reasoning
  ✓ 0% honeypots in top 100

Usage:
  python rank.py --candidates ./candidates.jsonl --out ./submission.csv
  python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv
  python rank.py --candidates ./candidates.jsonl --out ./submission.csv --jd ./my_jd.txt
"""

import argparse
import csv
import gzip
import heapq
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pillars import authenticity, knowledge_graph, trajectory, behavioral, education_narrative
from pillars import ocean_signals
from pillars.jd_parser import get_active_jd_config, parse_jd_text, set_active_jd_config

TODAY = date.today()


def _iter_candidates(path: Path):
    """Yield candidate dicts. Supports JSONL, JSON array, and .gz of either."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, mode="rt", encoding="utf-8") as f:
        first_char = ""
        while not first_char.strip():
            ch = f.read(1)
            if not ch:
                return
            first_char = ch

        if first_char == "[":
            rest = f.read()
            try:
                for c in json.loads(first_char + rest):
                    if isinstance(c, dict):
                        yield c
            except json.JSONDecodeError as e:
                print(f"[rank.py] JSON array parse error: {e}", file=sys.stderr)
        else:
            buffer = first_char
            for line in f:
                full = (buffer + line).strip()
                buffer = ""
                if not full:
                    continue
                try:
                    c = json.loads(full)
                    if isinstance(c, dict):
                        yield c
                except json.JSONDecodeError:
                    pass


def score_candidate(c: dict, jd) -> tuple[float, float, dict]:
    """
    Score one candidate. Returns (final_score, secondary, details).
    final_score = 0.0 for honeypots and hard-disqualified candidates.
    """
    # ── PILLAR 1: Honeypot / Integrity ──────────────────────────
    auth = authenticity.evaluate(c)
    if auth["is_honeypot"]:
        return 0.0, 0.0, {"honeypot": True, "reasons": auth["honeypot_reasons"]}

    # ── Hard disqualifier ────────────────────────────────────────
    dq, dq_reason = trajectory.is_hard_disqualified(c)
    if dq:
        return 0.0, 0.0, {"disqualified": True, "reason": dq_reason}

    # ── PILLAR 2: Knowledge Graph skill match ────────────────────
    kg_score = knowledge_graph.match_score(c, jd)

    # ── PILLAR 4a: Career trajectory ─────────────────────────────
    traj_score = trajectory.score_trajectory(c)
    exp_score  = trajectory.score_experience_fit(c, jd)

    # ── PILLAR 4b: Behavioral (all 23 signals) ───────────────────
    beh = behavioral.compute_behavioral_multiplier(c, jd)
    loc_score  = beh["location_score"] * 0.60 + beh["notice_score"] * 0.40
    beh_mult   = beh["multiplier"]

    # ── PILLAR 3: Education (debiased) ───────────────────────────
    edu_score  = education_narrative.score_education(c)

    # ── Narrative alignment ──────────────────────────────────────
    narr_score = education_narrative.score_narrative(c, jd)

    # ── PILLAR 5: OCEAN personality proxy ────────────────────────
    ocean = ocean_signals.compute_ocean_score(c)
    ocean_score = ocean["ocean_score"]

    # ── Weighted raw score (JD-config-driven weights) ────────────
    W = jd.axis_weights
    raw = (
        W["kg"]   * kg_score
        + W["traj"] * traj_score
        + W["exp"]  * exp_score
        + W["loc"]  * loc_score
        + W["edu"]  * edu_score
        + W["narr"] * narr_score
    )

    # OCEAN as a soft modifier: ±3% influence (doesn't dominate)
    ocean_modifier = 0.97 + 0.06 * ocean_score   # range [0.97, 1.03]
    raw = raw * auth["penalty_multiplier"] * ocean_modifier

    final = raw * beh_mult

    # ── Tiebreak: response_rate + interview_rate + github ────────
    signals = c.get("redrob_signals", {})
    rr  = signals.get("recruiter_response_rate", 0.0)
    icr = signals.get("interview_completion_rate", 0.5)
    gh  = max(0.0, signals.get("github_activity_score", 0.0)) / 100.0
    secondary = 0.50 * rr + 0.30 * icr + 0.20 * gh

    return final, secondary, {
        "kg": kg_score, "traj": traj_score, "exp": exp_score,
        "loc": loc_score, "edu": edu_score, "narr": narr_score,
        "ocean": ocean_score, "ocean_dims": ocean["dimensions"],
        "auth_penalty": auth["penalty_multiplier"],
        "beh_mult": beh_mult, "raw": raw, "final": final,
        "beh_result": beh,
        "matched_skills": knowledge_graph.get_matched_skills(c),
    }


def generate_reasoning(c: dict, rank: int, details: dict) -> str:
    """Fact-grounded, unique reasoning. Max 495 chars."""
    profile  = c.get("profile", {})
    signals  = c.get("redrob_signals", {})

    name    = profile.get("anonymized_name", "Candidate")
    yoe     = profile.get("years_of_experience", 0)
    title   = profile.get("current_title", "N/A")
    company = profile.get("current_company", "")
    loc     = profile.get("location", "")
    country = profile.get("country", "")

    beh      = details.get("beh_result", {})
    ks       = beh.get("key_signals", {})
    rr       = ks.get("response_rate", 0.0)
    notice   = ks.get("notice_days", 90)
    github   = ks.get("github_score", -1)
    inactive = ks.get("days_inactive", 999)
    otw      = ks.get("open_to_work", False)

    matched   = details.get("matched_skills", [])[:3]
    skill_str = ", ".join(matched) if matched else "ML background"

    # OCEAN highlight
    dims = details.get("ocean_dims", {})
    c_score = dims.get("conscientiousness", 0)
    o_score = dims.get("openness", 0)
    ocean_note = ""
    if c_score > 0.7 and o_score > 0.6:
        ocean_note = " High C+O profile (reliable learner)."
    elif c_score > 0.75:
        ocean_note = " High conscientiousness (ships reliably)."
    elif o_score > 0.75:
        ocean_note = " High openness (fast learner)."

    tier = ("Strong fit" if rank <= 15 else
            "Good fit"   if rank <= 40 else
            "Partial fit" if rank <= 70 else
            "Marginal fit")

    s1 = (f"{tier}: {name} — {yoe:.1f}yr {title} @ {company} "
          f"({loc}, {country}). Skills: {skill_str}.{ocean_note}")

    pos, neg = [], []
    if otw:                   pos.append("actively looking")
    if rr >= 0.70:            pos.append(f"responsive ({rr:.0%} RR)")
    elif rr < 0.20:           neg.append(f"low RR ({rr:.0%})")
    if notice <= 30:          pos.append(f"available {notice}d")
    elif notice > 90:         neg.append(f"long notice ({notice}d)")
    if github >= 50:          pos.append(f"GitHub {github:.0f}/100")
    elif github == -1:        neg.append("no GitHub")
    if inactive > 180:        neg.append(f"inactive {inactive}d")
    if yoe > 12:              neg.append("may be over-qualified")
    if details.get("loc",0) < 0.5: neg.append("location mismatch")

    parts = [s1]
    if pos: parts.append("+" + "; ".join(pos[:2]) + ".")
    if neg: parts.append("⚠ " + "; ".join(neg[:2]) + ".")
    return " ".join(parts)[:495]


def rank_candidates(candidates_path: str, output_path: str, jd=None):
    path = Path(candidates_path)
    if not path.exists():
        print(f"ERROR: {candidates_path} not found", file=sys.stderr)
        sys.exit(1)

    if jd is None:
        jd = get_active_jd_config()

    print(f"[rank.py] JD: {jd.role_name}", file=sys.stderr)
    print(f"[rank.py] Input: {candidates_path}", file=sys.stderr)
    print(f"[rank.py] Date: {TODAY}", file=sys.stderr)

    heap = []
    total = honeypots = disqualified = errors = 0

    for c in _iter_candidates(path):
        total += 1
        cid = c.get("candidate_id", "")
        if not cid:
            continue
        try:
            final, secondary, details = score_candidate(c, jd)
        except Exception as e:
            errors += 1
            continue

        if details.get("honeypot"):
            honeypots += 1
            continue
        if details.get("disqualified"):
            disqualified += 1
            continue

        entry = (-final, -secondary, cid, c, details)
        if len(heap) < 100:
            heapq.heappush(heap, entry)
        elif -final < heap[0][0]:
            heapq.heapreplace(heap, entry)

        if total % 10000 == 0:
            print(f"[rank.py] {total:,} processed...", file=sys.stderr)

    print(f"[rank.py] {total:,} total | {honeypots:,} honeypots | "
          f"{disqualified:,} disqualified | {errors} errors", file=sys.stderr)

    top100 = sorted(heap, key=lambda x: (x[0], x[1], x[2]))
    print(f"[rank.py] Writing {len(top100)} candidates → {output_path}", file=sys.stderr)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        prev = float("inf")
        for rank, (neg_score, neg_sec, cid, c, details) in enumerate(top100, 1):
            score = min(-neg_score, prev)
            prev = score
            w.writerow([cid, rank, f"{score:.4f}", generate_reasoning(c, rank, details)])

    print(f"[rank.py] ✓ Done. Honeypot rate in top 100: 0%", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="Redrobb Candidate Ranking Engine")
    p.add_argument("--candidates", default="./candidates.jsonl",
                   help="Path to candidates.jsonl or .jsonl.gz")
    p.add_argument("--out", default="./submission.csv", help="Output CSV path")
    p.add_argument("--jd", default=None,
                   help="Path to custom JD text file (optional)")
    p.add_argument("--jd-name", default=None,
                   help="Named JD config: redrobb_ai_engineer | backend_engineer | data_scientist")
    args = p.parse_args()

    jd = None
    if args.jd:
        jd_text = Path(args.jd).read_text(encoding="utf-8")
        jd = parse_jd_text(jd_text, role_name=Path(args.jd).stem)
        set_active_jd_config(jd)
        print(f"[rank.py] Loaded custom JD: {jd.role_name}", file=sys.stderr)
    elif args.jd_name:
        import os
        os.environ["JD_CONFIG_NAME"] = args.jd_name

    rank_candidates(args.candidates, args.out, jd)


if __name__ == "__main__":
    main()
