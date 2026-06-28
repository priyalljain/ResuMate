# Redrob-ai-hackathon
# Redrob Candidate Ranking Engine

## Team: Tech Vanguard Project (TVP)

### Overview
A production-ready, offline candidate ranking system that processes 100,000 candidates against any job description and outputs the top 100 ranked candidates with unique scores and reasoning.

### Architecture
- Pillar 1: Authenticity & Integrity (Semantic Entropy Detection)
- Pillar 2: Knowledge Graph (Semantic Skill Matching)
- Pillar 3: Causal & Counterfactual (Bias Correction)
- Pillar 4: RL-Human Hybrid (Multi-Component Scoring + Novel Tie-Breaking)

### Installation
```
pip install -r requirements.txt
```

### Pre-computation (Run once)
```
python precompute/build_skill_db.py
python precompute/build_skill_graph.py
python precompute/build_embeddings.py
```

### Run Ranking
```
python rank.py
```

### Validate
```
python validate_submission.py submission.csv
```

### Constraints Met
- CPU only (no GPU)
- < 16 GB RAM
- < 5 minutes runtime
- No network calls
- Exactly 100 candidates with unique ranks
- Scores monotonically non-increasing
- Tie-breaking using novel behavioral signals
```

---

## IMPLEMENTATION NOTES

### Performance Optimizations
1. **Heap Selection**: Use `heapq.nlargest` for O(N log 100) instead of O(N log N)
2. **Vectorized Operations**: Use NumPy for embeddings and similarity calculations
3. **Lazy Loading**: Load artifacts only when needed
4. **Batch Processing**: Process candidates in chunks if memory-constrained

### Edge Cases
1. **Candidate with no skills**: Skill score = 0, rely on other axes
2. **Candidate with no education**: Education score = 0.5
3. **Candidate with 0 YOE**: Experience fit = 1.0 if JD is entry-level
4. **Candidate with 20+ YOE**: Experience fit = 0.4 (over-qualified)
5. **Invalid JSON lines**: Skip and continue
6. **Missing signal values**: Use defaults (-1 → 0, missing dates → treat as inactive)

### Testing Strategy
1. Run validator on sample_submission.csv
2. Test with sample 50 candidates
3. Test with full 100,000 candidates (measure time)
4. Verify honeypot detection (<10% in top 100)

### Interview Preparation Points
1. Why semantic entropy detects AI-generated resumes
2. How knowledge graph enables conceptual matching
3. How causal fairness corrects for institutional bias
4. Why novel tie-breaking using behavioral signals is more predictive
5. How the system works for any JD (any role, any seniority)
6. Performance optimizations to meet constraints

---

## DEPLOYMENT INSTRUCTIONS

### Running in Competition Environment
```bash
# 1. Set up environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Run pre-computation (only once)
python precompute/build_skill_db.py
python precompute/build_skill_graph.py
python precompute/build_embeddings.py

# 3. Rank candidates
python rank.py

# 4. Validate submission
python validate_submission.py submission.csv
```

### Expected Runtime
- Pre-computation: 15-30 minutes (unlimited, run once)
- Ranking: < 2 minutes (within 5-minute constraint)

### Expected Output
- `submission.csv` with exactly 100 rows
- Each row: candidate_id, rank (1-100), score (4 decimal places), reasoning (1-2 sentences)
- Validator passes all checks

---

## KEY SUCCESS FACTORS

1. **Semantic Understanding**: Knowledge graph connects related skills
2. **Authenticity Check**: Semantic entropy catches fake resumes
3. **Fairness**: Bias correction for institutional prestige
4. **Novel Tie-Breaking**: Behavioral signals (response rate, interview rate, GitHub)
5. **Speed**: Optimized heap selection, pre-computed embeddings
6. **Explainability**: Reasoning strings from actual profile data
7. **Constraints Compliance**: CPU-only, <16GB, <5min, no network

---

This is the complete implementation guide for the Redrob Candidate Ranking Engine. All files are designed to work together, meet all constraints, and produce a validator-passing submission.