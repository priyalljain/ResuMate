"""
Streamlit Sandbox Demo — required by hackathon for sandbox_link submission.
Upload up to 500 candidates as JSON/JSONL, get ranked CSV back.
"""
import csv, io, json, sys, tempfile
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from rank import rank_candidates
from pillars.jd_parser import get_active_jd_config, _JD_REGISTRY

st.set_page_config(page_title="Redrobb Ranker", layout="wide")
st.title("🧠 Redrobb Intelligent Candidate Ranker")
st.markdown("Upload candidate JSON/JSONL → get ranked top-100 CSV with recruiter reasoning.")

col1, col2 = st.columns([2, 1])
with col1:
    uploaded = st.file_uploader("Candidates (JSON array or JSONL)", type=["json", "jsonl"])
with col2:
    jd_choice = st.selectbox("Job Description", list(_JD_REGISTRY.keys()),
                              index=0, help="Select which JD to rank against")

if uploaded:
    content = uploaded.read().decode("utf-8")
    candidates = []
    try:
        candidates = json.loads(content)
    except json.JSONDecodeError:
        for line in content.splitlines():
            if line.strip():
                try: candidates.append(json.loads(line))
                except: pass
    st.info(f"✓ Loaded {len(candidates):,} candidates")

    if st.button("🚀 Run Ranker", type="primary"):
        import os
        os.environ["JD_CONFIG_NAME"] = jd_choice
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tmp:
            for c in candidates:
                tmp.write(json.dumps(c) + "\n")
            tmp_in = tmp.name
        tmp_out = tmp_in.replace(".jsonl", "_out.csv")

        with st.spinner(f"Ranking {len(candidates):,} candidates..."):
            rank_candidates(tmp_in, tmp_out)

        with open(tmp_out, encoding="utf-8") as f:
            result_csv = f.read()

        st.success("✅ Ranking complete!")
        rows = list(csv.DictReader(io.StringIO(result_csv)))
        st.dataframe([{
            "Rank": r["rank"], "ID": r["candidate_id"],
            "Score": float(r["score"]),
            "Reasoning": r["reasoning"][:100] + "..."
        } for r in rows[:20]], use_container_width=True)

        st.download_button("⬇️ Download submission.csv",
                           data=result_csv, file_name="submission.csv",
                           mime="text/csv")
