FROM python:3.11-slim

WORKDIR /app

# Install only what's needed for core ranker (zero deps) + optional SBERT
COPY requirements.txt .
RUN pip install --no-cache-dir streamlit>=1.28.0

# For optional SBERT precompute (commented out by default to keep image small)
# RUN pip install --no-cache-dir sentence-transformers numpy scikit-learn networkx

COPY . .

# Default: run the ranker
# Override with: docker run ... python rank.py --candidates /data/candidates.jsonl --out /data/submission.csv
ENTRYPOINT ["python", "rank.py"]
CMD ["--candidates", "./candidates.jsonl", "--out", "./submission.csv"]
