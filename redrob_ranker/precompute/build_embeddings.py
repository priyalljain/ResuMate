"""
Build SBERT Embeddings for Candidates and Skills

Purpose: Generate sentence-transformer embeddings for candidates and skills
for semantic similarity matching and ranking.

Uses: sentence-transformers/all-MiniLM-L6-v2 (384-dim embeddings)
Input: candidates.jsonl.gz
Output: data/candidate_embeddings.pkl, data/skill_embeddings.pkl
"""

import gzip
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


# Configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32
EMBEDDING_DIM = 384


def load_candidates(candidates_path: Path) -> List[Dict]:
    """
    Load candidates from compressed JSONL file.
    
    Args:
        candidates_path: Path to candidates.jsonl.gz
        
    Returns:
        List of candidate dictionaries
    """
    candidates = []
    with gzip.open(candidates_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                candidates.append(json.loads(line))
    return candidates


def prepare_candidate_text(candidate: Dict) -> str:
    """
    Combine candidate summary, skills, and experience into a single text.
    
    Args:
        candidate: Candidate dictionary with summary, skills, experience
        
    Returns:
        Combined text representation of the candidate
    """
    parts = []
    
    # Add summary
    if "summary" in candidate and candidate["summary"]:
        parts.append(str(candidate["summary"]))
    
    # Add skills
    if "skills" in candidate and candidate["skills"]:
        skills_text = " ".join(
            [str(skill) for skill in candidate["skills"]]
            if isinstance(candidate["skills"], list)
            else [str(candidate["skills"])]
        )
        if skills_text:
            parts.append(f"Skills: {skills_text}")
    
    # Add experience descriptions
    if "experience" in candidate and candidate["experience"]:
        experiences = candidate["experience"]
        if isinstance(experiences, list):
            for exp in experiences:
                if isinstance(exp, dict) and "description" in exp:
                    parts.append(str(exp["description"]))
                elif isinstance(exp, str):
                    parts.append(str(exp))
        elif isinstance(experiences, str):
            parts.append(experiences)
    
    # Combine with spacing
    combined_text = " ".join(parts)
    
    # Fallback to candidate name/id if no content
    if not combined_text.strip():
        if "name" in candidate:
            combined_text = str(candidate["name"])
        elif "id" in candidate:
            combined_text = f"Candidate {candidate['id']}"
        else:
            combined_text = "Candidate"
    
    return combined_text.strip()


def generate_candidate_embeddings(
    candidates: List[Dict],
    model: SentenceTransformer,
    batch_size: int = BATCH_SIZE
) -> np.ndarray:
    """
    Generate embeddings for all candidates.
    
    Args:
        candidates: List of candidate dictionaries
        model: Loaded SentenceTransformer model
        batch_size: Batch size for processing
        
    Returns:
        NumPy array of shape (num_candidates, 384)
    """
    print(f"Preparing candidate texts ({len(candidates)} candidates)...")
    texts = [prepare_candidate_text(c) for c in candidates]
    
    print(f"Generating candidate embeddings (batch size: {batch_size})...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    return embeddings


def extract_unique_skills(candidates: List[Dict]) -> List[str]:
    """
    Extract all unique skills from candidates.
    
    Args:
        candidates: List of candidate dictionaries
        
    Returns:
        Sorted list of unique skills
    """
    skills_set = set()
    
    for candidate in candidates:
        if "skills" in candidate and candidate["skills"]:
            skills = candidate["skills"]
            if isinstance(skills, list):
                skills_set.update(str(s).lower().strip() for s in skills if s)
            else:
                skill_str = str(skills).lower().strip()
                if skill_str:
                    skills_set.add(skill_str)
    
    return sorted(list(skills_set))


def generate_skill_embeddings(
    skills: List[str],
    model: SentenceTransformer,
    batch_size: int = BATCH_SIZE
) -> Tuple[np.ndarray, Dict[str, int]]:
    """
    Generate embeddings for all unique skills.
    
    Args:
        skills: List of unique skills
        model: Loaded SentenceTransformer model
        batch_size: Batch size for processing
        
    Returns:
        Tuple of (embeddings array, skill_to_idx mapping)
    """
    print(f"Generating skill embeddings ({len(skills)} unique skills)...")
    embeddings = model.encode(
        skills,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    # Create skill to index mapping
    skill_to_idx = {skill: idx for idx, skill in enumerate(skills)}
    
    return embeddings, skill_to_idx


def main():
    """Generate and save embeddings for candidates and skills."""
    # Define paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    candidates_path = data_dir / "candidates.jsonl.gz"
    
    # Create data directory if it doesn't exist
    data_dir.mkdir(exist_ok=True)
    
    # Check if input file exists
    if not candidates_path.exists():
        raise FileNotFoundError(
            f"Candidates file not found: {candidates_path}\n"
            "Please ensure candidates.jsonl.gz is in the data directory."
        )
    
    # Load model
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print(f"Model loaded. Embedding dimension: {model.get_sentence_embedding_dimension()}")
    
    # Load candidates
    print(f"Loading candidates from {candidates_path}...")
    candidates = load_candidates(candidates_path)
    print(f"Loaded {len(candidates)} candidates")
    
    # Generate candidate embeddings
    candidate_embeddings = generate_candidate_embeddings(candidates, model)
    print(f"Generated candidate embeddings shape: {candidate_embeddings.shape}")
    
    # Save candidate embeddings
    candidate_emb_path = data_dir / "candidate_embeddings.pkl"
    print(f"Saving candidate embeddings to {candidate_emb_path}...")
    with open(candidate_emb_path, "wb") as f:
        pickle.dump(candidate_embeddings, f)
    print(f"✓ Saved candidate embeddings")
    
    # Extract unique skills
    print("Extracting unique skills from candidates...")
    skills = extract_unique_skills(candidates)
    print(f"Found {len(skills)} unique skills")
    
    # Generate skill embeddings
    skill_embeddings, skill_to_idx = generate_skill_embeddings(skills, model)
    print(f"Generated skill embeddings shape: {skill_embeddings.shape}")
    
    # Prepare skill embeddings package
    skill_emb_data = {
        "skills": skills,
        "embeddings": skill_embeddings,
        "skill_to_idx": skill_to_idx
    }
    
    # Save skill embeddings
    skill_emb_path = data_dir / "skill_embeddings.pkl"
    print(f"Saving skill embeddings to {skill_emb_path}...")
    with open(skill_emb_path, "wb") as f:
        pickle.dump(skill_emb_data, f)
    print(f"✓ Saved skill embeddings")
    
    # Print summary statistics
    print(f"\n✓ Embeddings generated successfully")
    print(f"  - Candidate embeddings: {candidate_embeddings.shape}")
    print(f"  - Skill embeddings: {skill_embeddings.shape}")
    print(f"  - Model: {MODEL_NAME}")
    print(f"  - Embedding dimension: {EMBEDDING_DIM}")
    print(f"  - Total candidates: {len(candidates)}")
    print(f"  - Total unique skills: {len(skills)}")
    print(f"  - Sample skills: {skills[:10]}")


if __name__ == "__main__":
    main()
