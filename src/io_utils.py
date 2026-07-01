"""
io_utils.py — streaming ingestion of the candidate pool.

Handles both plain .jsonl and gzip-compressed .jsonl.gz (the format the
hackathon bundle ships candidates in: candidates.jsonl.gz, ~52MB compressed /
~465MB uncompressed for 100,000 rows). Reads line-by-line via a generator so
memory use stays bounded to "one record at a time" rather than loading the
whole pool into a list — this matters less on a 16GB box for ~500MB of JSON
than the hackathon docs make it sound, but streaming costs nothing and keeps
headroom for the SBERT stage's tensors later in the pipeline.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path
from typing import Iterator, Dict, Any


def iter_candidates(path: str) -> Iterator[Dict[str, Any]]:
    """Yield one parsed candidate dict per line. Transparently handles
    .jsonl and .jsonl.gz. Skips and logs (to stderr) any line that fails to
    parse as JSON, rather than crashing the whole run on one bad row."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Candidate file not found: {path}")

    opener = gzip.open if p.suffix == ".gz" else open
    mode = "rt"

    with opener(p, mode, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"[io_utils] WARNING: skipping malformed JSON at line "
                    f"{line_num}: {e}",
                    file=sys.stderr,
                )
                continue


def count_candidates(path: str) -> int:
    """Cheap line count for progress reporting / sanity checks."""
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    n = 0
    with opener(p, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n
