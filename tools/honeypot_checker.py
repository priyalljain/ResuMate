#!/usr/bin/env python3
"""
tools/honeypot_checker.py — Standalone Honeypot Analysis Tool

Consolidates ALL logic from antigravity's 18 analysis scripts:
  analyze_honeypots.py, check_ratio.py, check_redrob.py,
  check_reverse_mismatch.py, check_zero_dur_skills.py,
  count_anomalies.py, count_low_ratio.py, find_all_honeypots.py,
  scan_all.py, scan_more.py, search_any_founded.py, search_founded.py

Usage:
  python tools/honeypot_checker.py --candidates ./candidates.jsonl
  python tools/honeypot_checker.py --candidates ./candidates.jsonl --limit 5000
  python tools/honeypot_checker.py --candidates ./candidates.jsonl --out honeypot_report.json
"""

import argparse
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pillars import authenticity


def parse_date(d_str):
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def analyze_candidate(c: dict) -> dict:
    """Run all 11 authenticity checks + additional statistical checks."""
    profile = c.get("profile", {})
    skills  = c.get("skills", [])
    career  = c.get("career_history", [])
    edu     = c.get("education", [])
    signals = c.get("redrob_signals", {})

    yoe = profile.get("years_of_experience", 0)
    total_career_months = sum(h.get("duration_months", 0) for h in career)

    # Run full authenticity evaluation (all 11 checks)
    auth_result = authenticity.evaluate(c)

    # Additional statistical checks (from antigravity scripts)
    extra_flags = []

    # check_ratio.py: low career/YoE ratio
    if yoe > 0:
        ratio = total_career_months / (yoe * 12)
        if ratio < 0.60:
            extra_flags.append(f"low_yoe_ratio_{ratio:.2f}")

    # check_zero_dur_skills.py: many zero-duration skills (any level)
    zero_dur_all = sum(1 for s in skills if s.get("duration_months", 1) == 0)
    if zero_dur_all >= 5:
        extra_flags.append(f"many_zero_dur_skills_{zero_dur_all}")

    # check_intermediate.py: intermediate with 0 duration
    inter_zero = [s for s in skills if s.get("proficiency") == "intermediate"
                  and s.get("duration_months", 1) == 0]
    if len(inter_zero) >= 3:
        extra_flags.append(f"intermediate_zero_dur_{len(inter_zero)}")

    # check_redrob.py: worked at Redrob before 2023 (company didn't exist)
    for role in career:
        co = role.get("company", "").lower()
        if "redrob" in co:
            sd = parse_date(role.get("start_date"))
            if sd and sd.year < 2023:
                extra_flags.append(f"worked_at_redrob_before_2023_{sd.year}")

    # search_founded.py: description mentions founding year inconsistency
    import re
    found_pattern = re.compile(
        r"(founded|established|started|launched|inception|incorporated)\s+(in|around|about|recently)?\s*\d{4}",
        re.IGNORECASE,
    )
    for role in career:
        desc = role.get("description", "")
        m = found_pattern.search(desc)
        if m:
            extra_flags.append(f"desc_has_founding_claim_{m.group(0)[:30]}")
            break

    return {
        "candidate_id": c.get("candidate_id"),
        "name": profile.get("anonymized_name"),
        "yoe": yoe,
        "career_months": total_career_months,
        "skill_count": len(skills),
        "is_honeypot": auth_result["is_honeypot"],
        "authenticity_score": round(auth_result["authenticity_score"], 3),
        "honeypot_reasons": auth_result["honeypot_reasons"],
        "extra_flags": extra_flags,
        "has_any_flag": auth_result["is_honeypot"] or bool(extra_flags),
    }


def run_analysis(candidates_path: str, limit: int | None = None, out_path: str | None = None):
    path = Path(candidates_path)
    opener = gzip.open if path.suffix == ".gz" else open

    results = []
    stats = {
        "total": 0, "hard_honeypots": 0, "soft_flagged": 0,
        "by_trigger": {},
    }

    with opener(path, mode="rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue

            stats["total"] += 1
            result = analyze_candidate(c)

            if result["is_honeypot"]:
                stats["hard_honeypots"] += 1
                results.append(result)
                for reason in result["honeypot_reasons"]:
                    trigger = reason.split(":")[0].lower().replace(" ", "_")
                    stats["by_trigger"][trigger] = stats["by_trigger"].get(trigger, 0) + 1

            elif result["extra_flags"]:
                stats["soft_flagged"] += 1
                for flag in result["extra_flags"]:
                    trigger = flag.split("_")[0]
                    stats["by_trigger"][trigger] = stats["by_trigger"].get(trigger, 0) + 1

            if limit and stats["total"] >= limit:
                break

            if stats["total"] % 10000 == 0:
                print(f"Scanned {stats['total']:,}...", file=sys.stderr)

    # Print summary
    print(f"\n{'='*60}")
    print(f"HONEYPOT ANALYSIS REPORT")
    print(f"{'='*60}")
    print(f"Total candidates scanned: {stats['total']:,}")
    print(f"Hard honeypots (score=0): {stats['hard_honeypots']:,} "
          f"({stats['hard_honeypots']/max(1,stats['total'])*100:.2f}%)")
    print(f"Soft-flagged (penalized): {stats['soft_flagged']:,}")
    print(f"\nTrigger breakdown:")
    for trigger, count in sorted(stats["by_trigger"].items(), key=lambda x: -x[1])[:15]:
        print(f"  {trigger}: {count:,}")

    if out_path:
        output = {"stats": stats, "flagged": results[:200]}
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nFull report saved to: {out_path}")

    return stats, results


def main():
    p = argparse.ArgumentParser(description="Honeypot detection analysis tool")
    p.add_argument("--candidates", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--out", default=None)
    args = p.parse_args()
    run_analysis(args.candidates, args.limit, args.out)


if __name__ == "__main__":
    main()
