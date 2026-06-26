#!/usr/bin/env python3
"""
tests/validate_sample.py
Relaxed validator for sample/test files with < 100 candidates.

For the full 100K dataset, use validate_submission.py (official hackathon validator).
This script is for CI testing only.

Usage:
  python tests/validate_sample.py /tmp/test_out.csv
"""
import csv, re, sys
from pathlib import Path

REQUIRED_HEADER = ["candidate_id", "rank", "score", "reasoning"]
CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")

def validate(csv_path: str) -> list[str]:
    errors = []
    path = Path(csv_path)
    if not path.exists():
        return [f"File not found: {csv_path}"]

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header != REQUIRED_HEADER:
            errors.append(f"Header mismatch. Got: {header}")
        rows = [r for r in reader if any(c.strip() for c in r)]

    if not rows:
        return errors + ["No data rows found."]

    seen_ids, seen_ranks = set(), set()
    scores = []

    for i, row in enumerate(rows):
        row_num = i + 2
        if len(row) != 4:
            errors.append(f"Row {row_num}: expected 4 cols, got {len(row)}")
            continue
        cid, rank_s, score_s, reasoning = row
        cid = cid.strip()

        if not CANDIDATE_ID_PATTERN.match(cid):
            errors.append(f"Row {row_num}: invalid candidate_id {cid!r}")
        elif cid in seen_ids:
            errors.append(f"Row {row_num}: duplicate candidate_id {cid!r}")
        else:
            seen_ids.add(cid)

        try:
            rank = int(rank_s.strip())
            if rank in seen_ranks:
                errors.append(f"Row {row_num}: duplicate rank {rank}")
            seen_ranks.add(rank)
        except ValueError:
            errors.append(f"Row {row_num}: rank not integer: {rank_s!r}")

        try:
            scores.append(float(score_s.strip()))
        except ValueError:
            errors.append(f"Row {row_num}: score not float: {score_s!r}")

        if not reasoning.strip():
            errors.append(f"Row {row_num}: empty reasoning")

    # Check scores non-increasing
    for i in range(len(scores) - 1):
        if scores[i] < scores[i + 1]:
            errors.append(f"Score increasing at row {i+2}: {scores[i]:.4f} < {scores[i+1]:.4f}")

    print(f"Validated {len(rows)} rows from {csv_path}")
    return errors

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "submission.csv"
    errors = validate(path)
    if errors:
        print(f"FAILED ({len(errors)} issue(s)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("PASSED — all format checks OK (sample validator)")

if __name__ == "__main__":
    main()
