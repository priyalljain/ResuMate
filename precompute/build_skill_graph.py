#!/usr/bin/env python3
"""
Precompute: Build NetworkX skill graph from skill_related.json.
Run once offline. Saves data/skill_graph.pkl.

Runtime: ~2 seconds.
"""

import json
import pickle
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def build():
    try:
        import networkx as nx
    except ImportError:
        print("networkx not installed — skipping graph build (optional component)")
        return

    skill_related_path = DATA_DIR / "skill_related.json"
    if not skill_related_path.exists():
        print("Run build_skill_db.py first to generate skill_related.json")
        return

    with open(skill_related_path) as f:
        skill_related = json.load(f)

    G = nx.Graph()

    for canonical, aliases in skill_related.items():
        G.add_node(canonical)
        for alias in aliases:
            G.add_node(alias)
            G.add_edge(canonical, alias, weight=1.0)

    # Also add edges between aliases of the same canonical (for traversal)
    for canonical, aliases in skill_related.items():
        all_terms = [canonical] + aliases
        for i, t1 in enumerate(all_terms):
            for t2 in all_terms[i + 1:]:
                if not G.has_edge(t1, t2):
                    G.add_edge(t1, t2, weight=1.5)  # Slightly higher cost

    out_path = DATA_DIR / "skill_graph.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(G, f)

    print(f"Built graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    build()
