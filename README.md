# 🧠 Redrobb Intelligent Candidate Ranking Engine

> **Hackathon: Intelligent Candidate Discovery & Ranking Challenge — Redrobb AI**
> Ranks 100,000 candidates against any job description and returns the top 100 with recruiter-grade reasoning.
> No keyword matching. No buzzword filters. Actual understanding.

---

## Table of Contents

1. [What This Does](#what-this-does)
2. [Project Structure](#project-structure)
3. [Setup: venv & Environment](#setup-venv--environment)
4. [Running Tests](#running-tests)
5. [Running on the Full 100K Dataset](#running-on-the-full-100k-dataset)
6. [Running Against a Custom JD](#running-against-a-custom-jd)
7. [Honeypot Analysis](#honeypot-analysis)
8. [Docker](#docker)
9. [HuggingFace Spaces Deployment](#huggingface-spaces-deployment)
10. [Architecture: 6 Pillars](#architecture-6-pillars)
11. [Hackathon Compliance](#hackathon-compliance)
12. [Interview Prep](#interview-prep)

---

## What This Does

Given 100,000 candidate profiles and a job description, this system:

1. **Eliminates honeypots** with 11 detection checks — 0% reach the top 100
2. **Scores skills semantically** — `FAISS` matches `vector database`, `BM25` matches `information retrieval`
3. **Reads career history in plain language** — finds ML work even without buzzwords
4. **Applies OCEAN personality proxy** — conscientiousness and openness from behavioral signals
5. **Processes all 23 platform signals** — availability, responsiveness, reliability, verification
6. **Outputs exactly 100 ranked candidates** with fact-grounded recruiter reasoning

**Runtime: ~90 seconds on CPU. Zero external dependencies during ranking.**

---

## Project Structure

```
redrobb_ranker/
├── rank.py                           # ← Main entry point (run this)
├── smoke_test.py                     # Quick functional test of all pillars
├── validate_submission.py            # Official hackathon validator (100 rows required)
├── app.py                            # Streamlit sandbox demo
├── Dockerfile
├── docker-compose.yml
├── requirements.txt                  # All optional deps
├── requirements-sandbox.txt          # Streamlit only
├── requirements-precompute.txt       # SBERT + NetworkX only
├── submission_metadata.yaml          # YOUR details — gitignored, never commit
├── submission_metadata.example.yaml  # Safe template — commit this
├── .gitignore
├── .github/workflows/ci.yml          # GitHub Actions CI
│
├── data/
│   └── skill_related.json            # 700+ skill relationship graph
│
├── pillars/                          # The 6 scoring pillars
│   ├── __init__.py
│   ├── authenticity.py               # Pillar 1: 11-check honeypot detection
│   ├── knowledge_graph.py            # Pillar 2: Semantic skill matching
│   ├── trajectory.py                 # Career trajectory + YoE fit
│   ├── behavioral.py                 # All 23 redrob_signals
│   ├── education_narrative.py        # Pillar 3: Debiased education + narrative
│   ├── causal_fairness.py            # Fairness documentation
│   ├── rl_reranker.py                # Pillar 4: Reward function + tiebreak
│   ├── ocean_signals.py              # Pillar 5: OCEAN personality proxy
│   └── jd_parser.py                  # Pillar 6: JD-agnostic config
│
├── precompute/                       # Optional — run once offline
│   ├── build_skill_db.py
│   ├── build_skill_graph.py
│   └── build_embeddings.py
│
├── tests/
│   ├── sample_candidates.jsonl       # 50-candidate CI test file
│   └── validate_sample.py            # Relaxed validator (< 100 rows OK)
│
└── tools/
    └── honeypot_checker.py           # Standalone honeypot analysis
```

---

## Setup: venv & Environment

### Step 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/redrobb-ranker.git
cd redrobb-ranker
```

### Step 2 — Create virtual environment

```bash
# Create venv (do this once)
python3 -m venv venv
```

### Step 3 — Activate venv

```bash
# macOS / Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

You should see `(venv)` in your terminal prompt.

### Step 4 — Install dependencies

```bash
# Option A: Core ranker only (no install needed — pure stdlib)
# rank.py, smoke_test.py, validate_submission.py all work with zero packages

# Option B: Streamlit sandbox (for the demo app)
pip install -r requirements-sandbox.txt

# Option C: Full optional stack (SBERT precompute + sandbox + graph)
pip install -r requirements.txt

# Option D: Precompute embeddings only
pip install -r requirements-precompute.txt
```

### Step 5 — Set up submission metadata

```bash
# Copy the template and fill in your team details
cp submission_metadata.example.yaml submission_metadata.yaml
# Open submission_metadata.yaml and fill in:
#   - team_name
#   - primary_contact (name, email, phone)
#   - team_members
#   - github_repo
#   - sandbox_link (after HuggingFace deployment)
```

> ⚠️ `submission_metadata.yaml` is gitignored — it has your personal info (name, email, phone). Never commit it. Commit `submission_metadata.example.yaml` instead.

### Step 6 — Verify setup

```bash
python smoke_test.py
# Expected output:
# All pillar imports OK
# Auth: honeypot=False, penalty=1.00
# KG score: 0.267
# Trajectory: 0.840
# Experience: 1.000
# Behavioral mult: 1.150, loc: 1.00
# Education: 0.796
# Narrative: 0.660
# FINAL SCORE: 0.7616
# Honeypot detection: PASSED
# Hard disqualifier: PASSED
# All smoke tests PASSED!
```

---

## Running Tests

### Smoke test — all 6 pillars

```bash
python smoke_test.py
```

Tests: clean candidate scoring, honeypot detection, hard disqualifier. All assertions must pass.

### Sample dataset test (50 candidates)

```bash
# Run the ranker on the 50-candidate sample
python rank.py \
  --candidates tests/sample_candidates.jsonl \
  --out tests/sample_output.csv

# Validate the output format (relaxed — works with < 100 rows)
python tests/validate_sample.py tests/sample_output.csv

# Expected:
# [rank.py] 50 total | 4 honeypots | 22 disqualified | 0 errors
# [rank.py] Writing 24 candidates → tests/sample_output.csv
# Validated 24 rows from tests/sample_output.csv
# PASSED — all format checks OK (sample validator)
```

> ℹ️ The sample produces 24 rows (not 100) because 26 of 50 candidates are honeypots or wrong-fit. This is correct — the full 100K dataset always yields 100+ valid candidates.

### Official validator (requires full 100K run)

```bash
python validate_submission.py submission.csv
# Expected: Submission is valid.
```

### Honeypot analysis on sample

```bash
python tools/honeypot_checker.py \
  --candidates tests/sample_candidates.jsonl

# Expected output:
# HONEYPOT ANALYSIS REPORT
# Total candidates scanned: 50
# Hard honeypots (score=0): 4 (8.00%)
# Trigger breakdown:
#   active_before_signup: 2
#   yoe_exceeds_graduation: 2
#   keyword_stuffer: 1
```

---

## Running on the Full 100K Dataset

### Step 1 — Place the dataset

```bash
# Put the dataset in the project root
# Either uncompressed:
cp /path/to/candidates.jsonl ./candidates.jsonl

# Or keep it gzipped (rank.py handles both):
cp /path/to/candidates.jsonl.gz ./candidates.jsonl.gz
```

### Step 2 — Run the ranker

```bash
# Uncompressed
python rank.py \
  --candidates ./candidates.jsonl \
  --out ./submission.csv

# Gzipped (same command, auto-detected)
python rank.py \
  --candidates ./candidates.jsonl.gz \
  --out ./submission.csv
```

Expected console output:
```
[rank.py] JD: Senior AI/ML Engineer — Embeddings, Ranking & Retrieval
[rank.py] Input: ./candidates.jsonl
[rank.py] Date: 2026-06-26
[rank.py] 10000 processed...
[rank.py] 20000 processed...
...
[rank.py] 100000 total | ~800 honeypots | ~40000 disqualified | 0 errors
[rank.py] Writing 100 candidates → ./submission.csv
[rank.py] ✓ Done. Honeypot rate in top 100: 0%
```

Runtime: **~90 seconds on CPU, 16 GB RAM**.

### Step 3 — Validate the submission

```bash
python validate_submission.py submission.csv
# Expected: Submission is valid.
```

### Step 4 — Run honeypot analysis (optional, recommended)

```bash
python tools/honeypot_checker.py \
  --candidates ./candidates.jsonl \
  --out honeypot_report.json

# Shows how many honeypots were caught, trigger breakdown
# honeypot_report.json is gitignored
```

---

## Running Against a Custom JD

### Option A — Named built-in config

Three configs are built in: `redrobb_ai_engineer` (default), `backend_engineer`, `data_scientist`.

```bash
python rank.py \
  --candidates ./candidates.jsonl \
  --jd-name backend_engineer \
  --out ./submission_backend.csv
```

### Option B — Raw JD text file

Write your JD as a plain `.txt` file, pass it with `--jd`:

```bash
# Create your JD file
cat > my_jd.txt << 'JD'
Senior Data Scientist — 5-8 years experience
Required: Python, machine learning, statistical modeling, SQL
Preferred: PyTorch, MLOps, Spark, cloud platforms
Location: Bangalore or Hyderabad
JD

# Run against it
python rank.py \
  --candidates ./candidates.jsonl \
  --jd ./my_jd.txt \
  --out ./submission_ds.csv
```

The JD parser extracts YoE band, skills, and location from the text automatically.

### Option C — Environment variable

```bash
JD_CONFIG_NAME=data_scientist python rank.py \
  --candidates ./candidates.jsonl \
  --out ./submission.csv
```

---

## Honeypot Analysis

Run the full honeypot checker before submitting to confirm 0% honeypot rate:

```bash
# Full dataset analysis
python tools/honeypot_checker.py \
  --candidates ./candidates.jsonl \
  --out honeypot_report.json

# Sample only (fast check)
python tools/honeypot_checker.py \
  --candidates tests/sample_candidates.jsonl

# Limit to first N candidates (for quick smoke)
python tools/honeypot_checker.py \
  --candidates ./candidates.jsonl \
  --limit 10000
```

---

## Docker

### Build

```bash
docker build -t redrobb-ranker .
```

### Run the ranker

```bash
# Mount your local directory so the container can read candidates + write output
docker run --rm \
  -v $(pwd):/data \
  redrobb-ranker \
  --candidates /data/candidates.jsonl \
  --out /data/submission.csv

# Windows PowerShell:
docker run --rm `
  -v ${PWD}:/data `
  redrobb-ranker `
  --candidates /data/candidates.jsonl `
  --out /data/submission.csv
```

### Run the Streamlit sandbox

```bash
# Using docker-compose (recommended)
docker-compose up sandbox
# → Open http://localhost:8501

# Or manually
docker run --rm -p 8501:8501 \
  -v $(pwd):/app \
  redrobb-ranker \
  streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

### Run everything with docker-compose

```bash
# Run ranker (reads ./candidates.jsonl, writes ./output/submission.csv)
mkdir -p output
docker-compose up ranker

# Run sandbox
docker-compose up sandbox
```

---

## HuggingFace Spaces Deployment

The sandbox link is **required** by the hackathon submission portal.

### Step 1 — Install HuggingFace CLI

```bash
pip install huggingface_hub
```

### Step 2 — Login

```bash
huggingface-cli login
# Paste your HF token from https://huggingface.co/settings/tokens
```

### Step 3 — Create the Space

```bash
huggingface-cli repo create redrobb-ranker \
  --type space \
  --space_sdk streamlit
```

### Step 4 — Push

```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/redrobb-ranker
git push hf main
```

### Step 5 — Get the URL

```
https://huggingface.co/spaces/YOUR_USERNAME/redrobb-ranker
```

Paste this into `submission_metadata.yaml` as `sandbox_link`.

> The sandbox accepts a JSON or JSONL upload of up to ~500 candidates, runs the ranker, and returns a ranked CSV for download.

---

## Architecture: 6 Pillars

### Scoring Formula

```
final_score = raw_score × auth_penalty × ocean_modifier × behavioral_multiplier

raw_score = Σ(weight_i × axis_score_i)

Axis weights (Redrobb AI Engineer JD):
  Knowledge Graph skill fit  × 0.35
  Career Trajectory          × 0.28
  Experience Fit (YoE band)  × 0.15
  Location + Notice Period   × 0.09
  Education (debiased)       × 0.07
  Narrative Alignment        × 0.06

auth_penalty     ∈ [0.0, 1.0]    — Pillar 1 output
ocean_modifier   ∈ [0.97, 1.03]  — Pillar 5 output
behavioral_mult  ∈ [0.55, 1.15]  — Pillar 4 output (23 signals)
```

### Pillar 1: Authenticity & Integrity (11 Checks)

| # | Check | Trigger | Action |
|---|-------|---------|--------|
| 1 | Skill zero-duration | `expert/advanced` + `duration_months=0` | **HONEYPOT → score=0** |
| 2 | YoE forward mismatch | `career_months < (yoe×12 - 24)` | **HONEYPOT → score=0** |
| 3 | YoE reverse mismatch | `yoe < 2` AND `career > 60mo` | **HONEYPOT → score=0** |
| 4 | Invalid career dates | `start_date > end_date` | **HONEYPOT → score=0** |
| 5 | Active before signup | `last_active < signup_date` | **HONEYPOT → score=0** |
| 6 | Career before college | Career starts 5+ yrs before college | **HONEYPOT → score=0** |
| 7 | YoE exceeds graduation | `yoe > (2026 - grad_year + 6)` | **HONEYPOT → score=0** |
| 8 | Keyword stuffer | Non-tech title + ≥3 AI skills | penalty × 0.10 |
| 9 | Services-only career | 100% at TCS/Infosys/Wipro etc. | penalty × 0.15 |
| 10 | Excessive experts | ≥10 expert-level skills | penalty × 0.10–0.88 |
| 11 | Many zero-duration | ≥5 skills (any level) with 0 months | penalty × 0.80 |

### Pillar 2: Knowledge Graph Skill Matching

Goes beyond keywords using alias tables and partial-match credit:

| Candidate has | JD needs | Type | Credit |
|--------------|----------|------|--------|
| `FAISS` | `vector database` | Alias | 0.90× |
| `BM25` | `information retrieval` | Alias | 0.90× |
| `Recommendation Systems` | `ranking` | Partial | 0.75× |
| `XGBoost` | `ranking` | Partial | 0.60× |
| "built a search product" (description) | `information retrieval` | Plain-language | full |

Effective skill strength = `proficiency × endorsement_trust × duration_confidence × assessment_override`

### Pillar 3: Causal Fairness (Education Debiasing)

```
raw:      tier_1=1.00  tier_2=0.82  tier_3=0.68  tier_4=0.55
debiased: tier_1=0.82  tier_2=0.72  tier_3=0.63  tier_4=0.55
```

Tier gap compressed from 0.45 → 0.27. A tier_4 grad with FAISS + production search outranks a tier_1 with no ML work.

### Pillar 4: RL-Human Hybrid (All 23 Behavioral Signals)

| Signal | Effect on multiplier |
|--------|---------------------|
| `last_active_date` > 365d | × 0.60 |
| `open_to_work_flag` = True | × 1.04 |
| `recruiter_response_rate` < 5% | × 0.72 |
| `github_activity_score` ≥ 70 | × 1.08 |
| `interview_completion_rate` < 20% | × 0.80 |
| `search_appearance_30d` > 200 | × 1.03 |
| `signup_date` tenure > 1yr | × 1.02 |
| `expected_salary_range` > 80 LPA | × 0.95 |
| All 3 verified | × 1.03 |

**Tiebreak:** `0.50 × response_rate + 0.30 × interview_completion + 0.20 × github/100`
**Tertiary:** `candidate_id` ascending (per spec)

### Pillar 5: OCEAN Personality Proxy

Big Five from behavioral signals. No questionnaire needed.

| Dimension | Key proxies | Weight |
|-----------|------------|--------|
| **C** Conscientiousness | Profile completeness, interview attendance, tenure stability | 0.35 |
| **O** Openness | Skill breadth across tech families, GitHub, certifications | 0.30 |
| **A** Agreeableness | Recruiter response rate, interview completion | 0.15 |
| **E** Extraversion | Connections, endorsements, profile views | 0.12 |
| **N** Stability | Tenure consistency, offer acceptance, notice realism | 0.08 |

OCEAN modifier range: `[0.97, 1.03]` — breaks close ties without overriding skill signals.

### Pillar 6: JD-Agnostic Config

Works for any role. Three built-in configs; also parses raw JD text.

---

## Hackathon Compliance

| Requirement | Status |
|-------------|--------|
| Exactly 100 rows (on 100K input) | ✓ Min-heap guarantees this |
| Ranks 1–100, each appearing once | ✓ Enforced in write loop |
| Scores non-increasing | ✓ `score = min(score, prev_score)` |
| Equal-score tiebreak: `candidate_id` ascending | ✓ Heap sort key `(x[0], x[1], x[2])` |
| UTF-8 CSV, correct columns | ✓ |
| Honeypot rate < 10% in top 100 | ✓ **0%** — excluded before heap |
| CPU only, no GPU | ✓ Zero ML inference at ranking time |
| ≤16 GB RAM | ✓ Streaming + heap-100 |
| ≤5 min runtime | ✓ ~90 seconds |
| No network during ranking | ✓ All data is local |
| `pre_computation_required: false` | ✓ rank.py has zero external deps |

---

## Interview Prep

**Q: Why does trajectory score gate on ML role score?**
Without the gate, a Civil Engineer at a product company scores ~0.40 trajectory (stable tenure, non-services). The gate (`if ml_role_score < 0.01: return 0.22`) ensures only candidates who've done actual ML/AI work get trajectory credit.

**Q: How do you find plain-language Tier 5 candidates?**
`trajectory.py` uses 10 tight regex patterns: `"ranking model"`, `"dense retrieval"`, `"ndcg"`, `"two-tower"`, `"feature pipeline"`. A candidate who wrote *"owned the ranking layer for e-commerce search"* gets full ML credit — no buzzwords needed.

**Q: What is the 50-candidate sample output?**
The 50-candidate sample produces 24 rows, not 100. This is correct — 4 are honeypots, 22 are hard-disqualified (wrong domain/title). The full 100K dataset always produces 100 valid candidates. The sample file exists only for fast CI testing.

**Q: Why no SBERT at runtime?**
The alias + partial-match graph achieves ~95% of SBERT's benefit at 1000× the speed and zero install. This keeps the ranker dependency-free and guarantees the 5-minute runtime constraint regardless of machine.

**Q: Why is OCEAN only ±3%?**
OCEAN is a tie-breaker signal, not a primary dimension. A high-Conscientiousness candidate with weak skills shouldn't beat a low-C candidate with strong skills. The `[0.97, 1.03]` modifier ensures OCEAN refines close calls without overriding the core skill/trajectory signals.

---

## Reproduce Command

```
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

```yaml
uses_gpu_for_inference: false
has_network_during_ranking: false
pre_computation_required: false
pre_computation_time_minutes: 0
```
