"""
test_pipeline.py — sanity tests using the real sample_candidates.json bundle.

Run with: pytest tests/ -v
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src import integrity, scoring, domain_config  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_samples():
    with open(FIXTURES / "sample_candidates.json", encoding="utf-8") as f:
        return json.load(f)


def _by_id(samples, cid):
    return next(c for c in samples if c["candidate_id"] == cid)


# ---------------------------------------------------------------------------
# Integrity checks
# ---------------------------------------------------------------------------

def test_severe_career_before_college_is_flagged():
    samples = _load_samples()
    # CAND_0000017: graduated 2022, career started 2014 (8-year gap) -- a clean violation.
    c = _by_id(samples, "CAND_0000017")
    mult, flags = integrity.evaluate_integrity(c)
    assert mult <= integrity.HARD_FLOOR + 1e-9
    assert any("career_before_college" in f for f in flags)


def test_minor_career_before_college_is_not_flagged():
    samples = _load_samples()
    # CAND_0000049: graduated 2019, earliest role started 2017 -- only a 2-year
    # gap, well under the 5-year threshold. Should NOT be hard-flagged.
    c = _by_id(samples, "CAND_0000049")
    mult, flags = integrity.evaluate_integrity(c)
    assert not any("career_before_college" in f for f in flags)


def test_active_before_signup_is_flagged():
    samples = _load_samples()
    c = _by_id(samples, "CAND_0000006")
    mult, flags = integrity.evaluate_integrity(c)
    assert mult <= integrity.HARD_FLOOR + 1e-9
    assert "active_before_signup" in flags


def test_clean_profile_gets_full_integrity_score():
    samples = _load_samples()
    c = _by_id(samples, "CAND_0000031")  # the strong-fit candidate
    mult, flags = integrity.evaluate_integrity(c)
    assert mult == 1.0
    assert flags == []


# ---------------------------------------------------------------------------
# Scoring sanity: the JD's central anti-trap must hold.
# ---------------------------------------------------------------------------

def test_genuine_match_outranks_keyword_stuffer():
    samples = _load_samples()
    graphs = domain_config.load_domain_graphs()
    cfg = graphs["tech"]

    strong = _by_id(samples, "CAND_0000031")   # Recommendation Systems Engineer, real narrative
    stuffer = _by_id(samples, "CAND_0000001")  # Backend Engineer with 17 unrelated-to-narrative AI skills

    strong_mult, _ = integrity.evaluate_integrity(strong)
    stuffer_mult, _ = integrity.evaluate_integrity(stuffer)

    strong_components = scoring.score_candidate(strong, "tech", cfg, strong_mult)
    stuffer_components = scoring.score_candidate(stuffer, "tech", cfg, stuffer_mult)

    assert strong_components["final_score"] > stuffer_components["final_score"]
    # the stuffer's AI-sounding skills should show up as orphaned (unsubstantiated)
    assert len(stuffer_components["orphaned_skills"]) > 0


def test_domain_detection_picks_tech_for_released_jd():
    graphs = domain_config.load_domain_graphs()
    jd_text = (REPO_ROOT / "job_description.md").read_text(encoding="utf-8")
    assert domain_config.detect_domain(jd_text, graphs) == "tech"


# ---------------------------------------------------------------------------
# Full pipeline + official validator (integration test)
# ---------------------------------------------------------------------------

def test_end_to_end_matches_official_validator(tmp_path):
    # Build a >=100-row jsonl input by cycling the 50 real samples with unique
    # IDs -- purely so we exercise the --top-n 100 path the real grader uses.
    samples = _load_samples()
    jsonl_path = tmp_path / "candidates.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for i in range(120):
            c = dict(samples[i % len(samples)])
            c = json.loads(json.dumps(c))  # cheap deep copy
            c["candidate_id"] = f"CAND_{i+1:07d}"
            f.write(json.dumps(c) + "\n")

    out_csv = tmp_path / "submission.csv"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "rank.py"),
         "--candidates", str(jsonl_path),
         "--out", str(out_csv),
         "--no-sbert"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    validator = subprocess.run(
        [sys.executable, str(REPO_ROOT / "validate_submission.py"), str(out_csv)],
        capture_output=True, text=True,
    )
    assert validator.returncode == 0, validator.stdout + validator.stderr
    assert "Submission is valid." in validator.stdout
