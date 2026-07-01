# Redrob AI Talent Intelligence Ranker

An optimized, production-grade candidate ranking engine developed for the Redrob AI Hackathon challenge. This pipeline implements a highly memory-efficient, deterministic **Cascading Funnel Architecture** capable of processing 100,000+ candidate records completely offline within strict compute thresholds.

## 📁 Repository Structure
Per the architectural design layout, the engine is structured as follows:
- `rank.py`: Main entrypoint for execution.
- `job_description.md`: The released frozen Job Description file.
- `requirements.txt`: Project package dependencies.
- `Dockerfile`: Multi-layer Docker build to support network-isolated testing.
- `validate_submission.py`: The official hackathon validator script.
- `candidate_schema.json`: Complete dataset profile schema definitions.
- `submission_metadata_template.yaml`: Template tracking portal info.
- `data/domain_graphs.json`: Embedded domain-specific knowledge mappings.
- `src/`: Core logic modules (Ingestion, Integrity, Scoring, SBERT, Reasoning).
- `scripts/prefetch_model.py`: Air-gapped neural weight downloader.
- `tests/`: Automated pipeline validation test suite.

## 🚀 Key Architectural Features
- **Cascading Funnel Processing:** Streams the massive candidate pool line-by-line (`O(1)` memory overhead), filters out structural anomalies, maintains a bounded min-heap, and runs SBERT semantic similarity exclusively on the top-ranked shortlists.
- **Honeypot & Anti-Trap Resistance:** Implements strict logical validations checking for impossible profiles, timeline inversions, and keyword-stuffer signals.
- **Network Isolation Discipline:** Pre-downloads sentence-transformer weights during the container build stage to guarantee flawless operational stability under `docker run --network none` grading parameters.
- **Deterministic Explanations:** Utilizes deterministic seed hashing tied directly to `candidate_id` tags to output robust, fact-grounded justification text with organic phrasing variations.

## 🛠️ Performance Metrics
- **Dataset Scale:** 100,000 Candidates
- **Processing Window:** ~27 seconds (CPU-only execution)
- **Peak Memory Bound:** ~145 MB RAM

## 📦 Execution & Verification

### Run the Ranking Pipeline
To process a candidate collection data file and compile the final sorted matrix output, execute:
```bash
python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv

### Validate Submission Format
Confirm compliance against the official competition requirements using the validator harness:

python validate_submission.py ./submission.csv



Developed with care by Pranjal Vishwakarma © 2026. All Rights Reserved.