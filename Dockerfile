FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download and cache the SBERT weights into the image layer WHILE
# network is still available at build time. This is the step that makes
# offline grading (docker run --network none) work: at runtime,
# SentenceTransformer('all-MiniLM-L6-v2') resolves entirely from the local
# HuggingFace cache populated here, with zero outbound requests.
COPY scripts/prefetch_model.py .
RUN python prefetch_model.py

COPY . .

# Single command that reproduces the submission CSV from a candidates file,
# matching the "single command" requirement in submission_spec.md 10.3.
ENTRYPOINT ["python", "rank.py"]
CMD ["--candidates", "/data/candidates.jsonl.gz", "--out", "/data/submission.csv"]
