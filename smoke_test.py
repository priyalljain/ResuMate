"""smoke_test.py — quick functional test of all pillars"""
import sys
sys.path.insert(0, '.')

from pillars import authenticity, knowledge_graph, trajectory, behavioral, education_narrative, causal_fairness, rl_reranker
print("All pillar imports OK")

c = {
    "candidate_id": "TEST_001",
    "profile": {
        "anonymized_name": "Test Candidate",
        "years_of_experience": 7,
        "current_title": "ML Engineer",
        "current_company": "Swiggy",
        "location": "Bangalore",
        "country": "India",
        "headline": "ML Engineer focused on ranking and embeddings",
        "summary": "Building production ranking models with LTR and FAISS",
    },
    "skills": [
        {"name": "FAISS", "proficiency": "advanced", "duration_months": 24, "endorsements": 15},
        {"name": "Python", "proficiency": "expert", "duration_months": 60, "endorsements": 40},
        {"name": "Sentence Transformers", "proficiency": "intermediate", "duration_months": 12, "endorsements": 5},
        {"name": "BM25", "proficiency": "advanced", "duration_months": 18, "endorsements": 10},
    ],
    "career_history": [
        {"title": "ML Engineer", "company": "Swiggy", "duration_months": 36, "is_current": True,
         "description": "Built ranking model using learning to rank and NDCG evaluation"},
        {"title": "Data Scientist", "company": "Flipkart", "duration_months": 24, "is_current": False,
         "description": "Recommendation engine with collaborative filtering"},
    ],
    "education": [{"tier": "tier_2", "field_of_study": "Computer Science", "degree": "B.Tech"}],
    "certifications": [{"name": "AWS Certified Machine Learning"}],
    "redrob_signals": {
        "open_to_work_flag": True,
        "recruiter_response_rate": 0.75,
        "interview_completion_rate": 0.85,
        "github_activity_score": 65,
        "last_active_date": "2026-06-01",
        "notice_period_days": 30,
        "verified_email": True,
        "verified_phone": True,
        "linkedin_connected": True,
        "profile_completeness_score": 92,
    }
}

auth = authenticity.evaluate(c)
print(f"Auth: honeypot={auth['is_honeypot']}, penalty={auth['penalty_multiplier']:.2f}")

kg = knowledge_graph.match_score(c)
print(f"KG score: {kg:.3f}")

traj = trajectory.score_trajectory(c)
print(f"Trajectory: {traj:.3f}")

exp = trajectory.score_experience_fit(c)
print(f"Experience: {exp:.3f}")

beh = behavioral.compute_behavioral_multiplier(c)
print(f"Behavioral mult: {beh['multiplier']:.3f}, loc: {beh['location_score']:.2f}")

edu = education_narrative.score_education(c)
print(f"Education: {edu:.3f}")

narr = education_narrative.score_narrative(c)
print(f"Narrative: {narr:.3f}")

WEIGHTS = {"kg": 0.35, "traj": 0.28, "exp": 0.15, "loc": 0.09, "edu": 0.07, "narr": 0.06}
loc_score = beh["location_score"] * 0.60 + beh["notice_score"] * 0.40
raw = (WEIGHTS["kg"] * kg + WEIGHTS["traj"] * traj + WEIGHTS["exp"] * exp +
       WEIGHTS["loc"] * loc_score + WEIGHTS["edu"] * edu + WEIGHTS["narr"] * narr)
final = raw * auth["penalty_multiplier"] * beh["multiplier"]
print(f"FINAL SCORE: {final:.4f}")

# Test honeypot detection
honeypot = {
    "candidate_id": "HONEYPOT_001",
    "profile": {"years_of_experience": 15, "current_title": "ML Engineer"},
    "skills": [{"name": "LLM", "proficiency": "expert", "duration_months": 0}],
    "career_history": [{"title": "ML Engineer", "company": "Google", "duration_months": 6}],
    "redrob_signals": {}
}
hp_auth = authenticity.evaluate(honeypot)
assert hp_auth["is_honeypot"], "Honeypot should be detected!"
print(f"Honeypot detection: PASSED (reason: {hp_auth['honeypot_reasons'][0]})")

# Test hard disqualifier
dq_cand = {
    "candidate_id": "DQ_001",
    "profile": {"years_of_experience": 5, "current_title": "Marketing Manager"},
    "career_history": [{"title": "Marketing Manager", "company": "Some Co", "duration_months": 60}],
    "skills": [],
    "redrob_signals": {}
}
dq, reason = trajectory.is_hard_disqualified(dq_cand)
assert dq, "Marketing Manager with no ML history should be disqualified!"
print(f"Hard disqualifier: PASSED (reason: {reason})")

print("\nAll smoke tests PASSED!")
