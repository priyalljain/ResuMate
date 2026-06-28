"""
Build Skill Graph for Fast Relationship Traversal

Purpose: Create a NetworkX graph from skill relationships for efficient 
graph-based operations and skill relationship queries.

Input: data/skill_related.json
Output: data/skill_graph.pkl
"""

import json
import pickle
from pathlib import Path

import networkx as nx


def load_skill_relationships(json_path: Path) -> dict:
    """
    Load skill relationships from JSON file.
    
    Args:
        json_path: Path to skill_related.json
        
    Returns:
        Dictionary mapping skills to their related skills
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_skill_graph(relationships: dict) -> nx.Graph:
    """
    Build an undirected NetworkX graph from skill relationships.
    
    Args:
        relationships: Dictionary mapping skills to lists of related skills
        
    Returns:
        NetworkX undirected graph with skills as nodes and weighted edges
    """
    graph = nx.Graph()
    
    # Add nodes for all skills
    skills = set(relationships.keys())
    for skill in skills:
        graph.add_node(skill)
    
    # Add edges with weight=1.0
    # Use a set to avoid adding duplicate edges (since graph is undirected)
    edges_added = set()
    for skill, related_skills in relationships.items():
        for related_skill in related_skills:
            # Create canonical edge representation (sorted tuple)
            edge = tuple(sorted([skill, related_skill]))
            
            # Only add if not already added
            if edge not in edges_added:
                graph.add_edge(skill, related_skill, weight=1.0)
                edges_added.add(edge)
    
    return graph


def save_graph(graph: nx.Graph, pkl_path: Path) -> None:
    """
    Save NetworkX graph to pickle file.
    
    Args:
        graph: NetworkX graph to save
        pkl_path: Path where to save the pickled graph
    """
    with open(pkl_path, "wb") as f:
        pickle.dump(graph, f)


def main():
    """Build and save the skill graph."""
    # Define paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    json_path = data_dir / "skill_related.json"
    pkl_path = data_dir / "skill_graph.pkl"
    
    # Create data directory if it doesn't exist
    data_dir.mkdir(exist_ok=True)
    
    # Check if input file exists
    if not json_path.exists():
        raise FileNotFoundError(
            f"Skill relationships file not found: {json_path}\n"
            "Please run build_skill_db.py first."
        )
    
    # Load relationships
    print(f"Loading skill relationships from {json_path}...")
    relationships = load_skill_relationships(json_path)
    
    # Build graph
    print("Building skill graph...")
    graph = build_skill_graph(relationships)
    
    # Save graph
    print(f"Saving skill graph to {pkl_path}...")
    save_graph(graph, pkl_path)
    
    # Print statistics
    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()
    num_components = nx.number_connected_components(graph)
    avg_degree = 2 * num_edges / num_nodes if num_nodes > 0 else 0
    
    print(f"\n✓ Skill graph built successfully")
    print(f"  - Total nodes (skills): {num_nodes}")
    print(f"  - Total edges (relationships): {num_edges}")
    print(f"  - Connected components: {num_components}")
    print(f"  - Average degree: {avg_degree:.2f}")
    print(f"  - Output: {pkl_path}")
    
    # Sample graph properties
    if num_nodes > 0:
        print(f"\n  Sample skill properties:")
        sample_skills = list(graph.nodes())[:5]
        for skill in sample_skills:
            neighbors = list(graph.neighbors(skill))
            print(f"    {skill} → {len(neighbors)} connections, neighbors: {neighbors[:5]}")


if __name__ == "__main__":
    main()
