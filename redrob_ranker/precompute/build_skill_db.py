"""
Build Skill Relationship Database

Purpose: Create a JSON database of skill relationships (synonyms, related terms, 
broader/narrower concepts) for semantic skill matching.

Output: data/skill_related.json
"""

import json
import os
from pathlib import Path

# Comprehensive skill relationships database
SKILL_RELATIONSHIPS = {
    # PROGRAMMING LANGUAGES & FRAMEWORKS
    "python": ["programming", "scripting", "data science", "machine learning", "django", "flask", "pandas", "numpy"],
    "javascript": ["web development", "frontend", "nodejs", "typescript", "react", "angular", "vue"],
    "typescript": ["javascript", "programming", "web development", "angular", "react"],
    "java": ["programming", "object-oriented", "spring", "enterprise", "backend", "android"],
    "c++": ["programming", "systems programming", "low-level", "performance optimization"],
    "c#": ["programming", ".net", "unity", "windows development", "enterprise"],
    ".net": ["c#", "enterprise", "backend", "windows development"],
    "go": ["programming", "concurrency", "systems programming", "backend"],
    "rust": ["programming", "systems programming", "performance", "memory safety"],
    "php": ["programming", "web development", "backend", "wordpress"],
    "kotlin": ["programming", "android", "jvm"],
    "swift": ["programming", "ios", "macos", "apple development"],
    "r": ["programming", "statistical analysis", "data science", "visualization"],
    
    # WEB FRAMEWORKS & LIBRARIES
    "react": ["javascript", "web development", "frontend", "ui library", "component-based"],
    "angular": ["javascript", "web development", "frontend", "typescript", "spa"],
    "vue": ["javascript", "web development", "frontend", "progressive framework"],
    "nodejs": ["javascript", "backend", "server-side", "runtime"],
    "django": ["python", "web framework", "backend", "mvc"],
    "flask": ["python", "web framework", "backend", "microframework"],
    "spring": ["java", "web framework", "enterprise", "backend"],
    "fastapi": ["python", "web framework", "async", "backend"],
    "express": ["nodejs", "web framework", "backend"],
    
    # DATABASES & DATA STORAGE
    "sql": ["database", "relational", "querying", "data retrieval"],
    "mysql": ["database", "relational", "sql", "backend"],
    "postgresql": ["database", "relational", "sql", "advanced"],
    "mongodb": ["database", "nosql", "document-based", "scalable"],
    "redis": ["caching", "in-memory", "data store", "performance"],
    "elasticsearch": ["search", "data indexing", "analytics", "database"],
    "cassandra": ["database", "nosql", "distributed", "scalable"],
    "dynamodb": ["aws", "database", "nosql", "serverless"],
    "firestore": ["gcp", "database", "nosql", "realtime"],
    "oracle": ["database", "relational", "enterprise", "sql"],
    "sqlite": ["database", "relational", "embedded"],
    "neo4j": ["database", "graph", "relationships", "knowledge graph"],
    
    # CLOUD PLATFORMS
    "aws": ["cloud", "infrastructure", "ec2", "s3", "lambda", "rds"],
    "gcp": ["google cloud", "cloud", "infrastructure", "bigquery", "dataflow"],
    "azure": ["microsoft", "cloud", "infrastructure", "virtual machines"],
    "cloud": ["infrastructure", "deployment", "scalability", "aws", "gcp", "azure"],
    "ec2": ["aws", "virtual machines", "infrastructure"],
    "s3": ["aws", "storage", "object storage"],
    "lambda": ["aws", "serverless", "function-as-a-service"],
    "gke": ["gcp", "kubernetes", "orchestration", "containers"],
    "aks": ["azure", "kubernetes", "orchestration", "containers"],
    
    # CONTAINERIZATION & ORCHESTRATION
    "docker": ["containerization", "deployment", "infrastructure", "kubernetes"],
    "kubernetes": ["container orchestration", "k8s", "deployment", "scaling", "docker"],
    "k8s": ["kubernetes", "container orchestration"],
    "container orchestration": ["kubernetes", "docker swarm", "deployment", "scaling"],
    "helm": ["kubernetes", "package management", "deployment"],
    "docker swarm": ["container orchestration", "clustering"],
    
    # DATA ENGINEERING & BIG DATA
    "spark": ["big data", "data processing", "hadoop", "distributed computing", "python", "scala"],
    "hadoop": ["big data", "distributed computing", "mapreduce", "hdfs"],
    "hdfs": ["hadoop", "distributed storage", "file system"],
    "mapreduce": ["hadoop", "big data", "distributed computing"],
    "data engineering": ["big data", "etl", "pipelines", "spark", "hadoop"],
    "etl": ["data engineering", "data pipelines", "extract-transform-load"],
    "data pipelines": ["data engineering", "etl", "orchestration"],
    "apache airflow": ["orchestration", "workflows", "data pipelines"],
    "kafka": ["streaming", "event streaming", "message queue"],
    "event streaming": ["kafka", "real-time", "data pipelines"],
    
    # MACHINE LEARNING & AI
    "machine learning": ["ai", "data science", "algorithms", "python", "tensorflow", "pytorch"],
    "deep learning": ["machine learning", "neural networks", "tensorflow", "pytorch"],
    "neural networks": ["deep learning", "machine learning", "ai"],
    "tensorflow": ["machine learning", "deep learning", "python"],
    "pytorch": ["machine learning", "deep learning", "python"],
    "scikit-learn": ["machine learning", "python", "algorithms"],
    "nlp": ["natural language processing", "machine learning", "text analysis"],
    "natural language processing": ["nlp", "machine learning", "ai"],
    "computer vision": ["machine learning", "image processing", "ai"],
    "data science": ["machine learning", "analytics", "python", "statistics"],
    "analytics": ["data analysis", "data science", "insights"],
    
    # DEVOPS & INFRASTRUCTURE
    "devops": ["ci/cd", "automation", "deployment", "infrastructure"],
    "ci/cd": ["continuous integration", "continuous deployment", "devops", "automation"],
    "continuous integration": ["ci/cd", "devops", "automated testing"],
    "continuous deployment": ["ci/cd", "devops", "automation"],
    "gitlab ci": ["ci/cd", "devops", "automation"],
    "jenkins": ["ci/cd", "devops", "automation"],
    "github actions": ["ci/cd", "devops", "automation"],
    "terraform": ["infrastructure as code", "iac", "aws", "gcp", "azure"],
    "infrastructure as code": ["terraform", "devops", "automation"],
    "iac": ["infrastructure as code", "devops"],
    "monitoring": ["observability", "metrics", "devops", "prometheus"],
    "observability": ["monitoring", "logging", "tracing", "devops"],
    "logging": ["observability", "debugging", "monitoring"],
    "prometheus": ["monitoring", "metrics", "devops"],
    
    # TESTING & QA
    "testing": ["quality assurance", "qa", "pytest", "junit"],
    "unit testing": ["testing", "quality assurance"],
    "integration testing": ["testing", "quality assurance"],
    "selenium": ["testing", "automation", "web testing"],
    "pytest": ["testing", "python", "automation"],
    "junit": ["testing", "java", "automation"],
    "test automation": ["testing", "qa", "devops"],
    "quality assurance": ["testing", "qa"],
    
    # VERSION CONTROL & COLLABORATION
    "git": ["version control", "source code", "collaboration"],
    "github": ["git", "version control", "collaboration", "devops"],
    "gitlab": ["git", "version control", "collaboration", "devops"],
    "bitbucket": ["git", "version control", "collaboration"],
    "version control": ["git", "scm", "source code management"],
    
    # SOFT SKILLS
    "project management": ["leadership", "coordination", "planning", "agile", "scrum"],
    "leadership": ["project management", "management", "team management"],
    "team management": ["leadership", "management", "coordination"],
    "communication": ["soft skills", "presentation", "writing", "interpersonal"],
    "presentation": ["communication", "public speaking", "storytelling"],
    "writing": ["communication", "documentation", "content"],
    "problem solving": ["analytical skills", "critical thinking", "troubleshooting"],
    "analytical skills": ["problem solving", "data analysis", "critical thinking"],
    "critical thinking": ["analytical skills", "problem solving"],
    "collaboration": ["teamwork", "communication", "interpersonal"],
    "teamwork": ["collaboration", "communication", "team management"],
    "agile": ["scrum", "project management", "methodology"],
    "scrum": ["agile", "project management", "ceremonies"],
    "kaban": ["agile", "project management", "workflow"],
    
    # DOMAIN SKILLS - FINANCE
    "financial analysis": ["finance", "accounting", "modeling"],
    "accounting": ["finance", "bookkeeping", "reconciliation"],
    "auditing": ["accounting", "compliance", "internal controls"],
    "risk management": ["finance", "compliance", "security"],
    "compliance": ["risk management", "regulations", "audit"],
    
    # DOMAIN SKILLS - MARKETING & SALES
    "marketing": ["brand management", "digital marketing", "seo", "content marketing"],
    "digital marketing": ["marketing", "seo", "social media", "analytics"],
    "seo": ["digital marketing", "organic search", "optimization"],
    "seo": ["search engine optimization"],
    "content marketing": ["marketing", "writing", "strategy"],
    "social media": ["marketing", "digital marketing", "engagement"],
    "sales": ["business development", "customer management", "crm"],
    "crm": ["customer relationship management", "sales", "database"],
    "customer relationship management": ["crm", "sales", "customer management"],
    
    # DOMAIN SKILLS - OPERATIONS
    "supply chain": ["logistics", "operations", "inventory management"],
    "logistics": ["supply chain", "operations", "distribution"],
    "inventory management": ["supply chain", "operations", "warehouse"],
    "operations": ["process management", "optimization", "efficiency"],
    "process management": ["operations", "workflow", "optimization"],
    
    # DOMAIN SKILLS - HR
    "human resources": ["hr", "talent management", "recruitment"],
    "recruitment": ["human resources", "talent acquisition", "hiring"],
    "talent management": ["human resources", "employee development"],
    
    # SECURITY
    "cybersecurity": ["security", "network security", "information security"],
    "security": ["cybersecurity", "risk management", "compliance"],
    "network security": ["cybersecurity", "infrastructure", "firewalls"],
    "encryption": ["security", "cryptography", "data protection"],
    "authentication": ["security", "access control", "identity"],
    "authorization": ["security", "access control", "permissions"],
    
    # MOBILE DEVELOPMENT
    "mobile development": ["ios", "android", "app development"],
    "ios": ["mobile development", "swift", "apple"],
    "android": ["mobile development", "kotlin", "java"],
    "app development": ["mobile development", "software engineering"],
    
    # FRONTEND
    "frontend": ["web development", "ui", "ux", "react", "angular", "vue"],
    "ui": ["user interface", "frontend", "design"],
    "ux": ["user experience", "design", "frontend", "usability"],
    "html": ["frontend", "web development", "markup"],
    "css": ["frontend", "web development", "styling"],
    "responsive design": ["frontend", "ui", "mobile"],
    
    # BACKEND
    "backend": ["server-side", "api", "database"],
    "api": ["backend", "integration", "rest"],
    "rest": ["api", "web services"],
    "graphql": ["api", "query language", "backend"],
    "microservices": ["architecture", "backend", "scalability"],
    
    # ARCHITECTURE & DESIGN
    "software architecture": ["design patterns", "system design", "scalability"],
    "system design": ["architecture", "scalability", "performance"],
    "design patterns": ["software architecture", "oop", "best practices"],
    "object-oriented programming": ["oop", "software design"],
    "oop": ["object-oriented programming", "design patterns"],
    
    # ADDITIONAL TECH SKILLS
    "api development": ["backend", "rest", "graphql"],
    "integration": ["api", "middleware", "data synchronization"],
    "performance optimization": ["optimization", "tuning", "scalability"],
    "optimization": ["performance", "efficiency", "tuning"],
    "debugging": ["troubleshooting", "testing", "problem solving"],
    "troubleshooting": ["debugging", "problem solving", "support"],
    "refactoring": ["code quality", "best practices", "optimization"],
    "code review": ["quality assurance", "collaboration", "best practices"],
    "documentation": ["writing", "communication", "knowledge transfer"],
    "knowledge transfer": ["documentation", "training", "communication"],
    "training": ["knowledge transfer", "communication", "leadership"],
    
    # SYNONYMS & VARIANTS
    "machine learning engineer": ["machine learning", "data science", "ai engineer"],
    "data engineer": ["data engineering", "big data", "etl"],
    "devops engineer": ["devops", "infrastructure", "automation"],
    "frontend engineer": ["frontend", "web development", "ui development"],
    "backend engineer": ["backend", "server-side", "api development"],
    "full stack": ["frontend", "backend", "web development"],
    "software engineer": ["programming", "software development"],
    "system architect": ["software architecture", "system design"],
    "solutions architect": ["system design", "architecture", "consulting"],
    "technical lead": ["leadership", "technical management", "mentoring"],
    "engineering manager": ["management", "leadership", "team management"],
}

def normalize_skill(skill: str) -> str:
    """Normalize skill to lowercase and strip whitespace."""
    return skill.lower().strip()

def build_bidirectional_graph(relationships: dict) -> dict:
    """
    Convert unidirectional relationships to bidirectional.
    
    For each skill A → [B, C], also add B → A, C → A (if not already present).
    """
    graph = {}
    
    # Initialize with given relationships
    for skill, related in relationships.items():
        normalized_skill = normalize_skill(skill)
        graph[normalized_skill] = [normalize_skill(r) for r in related]
    
    # Add reverse relationships
    skills_to_add = list(graph.keys())
    for skill in skills_to_add:
        for related in graph.get(skill, []):
            if related not in graph:
                graph[related] = []
            if skill not in graph[related]:
                graph[related].append(skill)
    
    # Remove duplicates and sort for consistency
    for skill in graph:
        graph[skill] = sorted(list(set(graph[skill])))
    
    return graph

def main():
    """Build and save the skill database."""
    # Create data directory
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Build bidirectional graph
    skill_graph = build_bidirectional_graph(SKILL_RELATIONSHIPS)
    
    # Save to JSON
    output_path = data_dir / "skill_related.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(skill_graph, f, indent=2, ensure_ascii=False)
    
    # Print statistics
    total_skills = len(skill_graph)
    total_relationships = sum(len(v) for v in skill_graph.values())
    
    print(f"✓ Skill database built successfully")
    print(f"  - Total skills: {total_skills}")
    print(f"  - Total relationships: {total_relationships}")
    print(f"  - Output: {output_path}")
    
    # Sample output
    print(f"\n  Sample relationships:")
    sample_skills = ["python", "kubernetes", "machine learning", "project management"]
    for skill in sample_skills:
        if skill in skill_graph:
            print(f"    {skill} → {skill_graph[skill][:5]}")

if __name__ == "__main__":
    main()
