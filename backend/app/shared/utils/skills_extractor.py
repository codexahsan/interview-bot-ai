# backend/app/shared/utils/skills_extractor.py

import re
from collections import defaultdict
from backend.app.shared.llm.client import get_llm

# -----------------------------
# SKILL DICTIONARY (expand later)
# -----------------------------
SKILL_DB = {
    "languages": ["python", "java", "c++", "javascript", "typescript", "go", "rust", "c#", "php", "ruby", "swift", "kotlin"],
    "frameworks": ["django", "flask", "fastapi", "react", "vue", "angular", "node", "express", "spring", "laravel", "rails", "next.js", "tailwindcss"],
    "databases": ["mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle", "cassandra", "dynamodb"],
    "devops": ["docker", "kubernetes", "aws", "azure", "gcp", "jenkins", "github actions", "terraform", "ansible", "linux"],
    "ai_ml": ["tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "opencv", "nlp", "llm", "langchain"],
    "tools": ["git", "github", "jira", "postman", "figma", "graphql", "rest", "websocket", "oauth", "jwt"],
}

# Alias normalization
ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "nodejs": "node",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "sklearn": "scikit-learn",
    "gcp": "google cloud platform",
}

# -----------------------------
# MAIN HYBRID FUNCTION
# -----------------------------
def hybrid_extract_skills(text: str, chunks: list = None) -> str:
    text_lower = text.lower()
    extracted = defaultdict(set)

    # 1. Rule-based extraction
    for category, skills in SKILL_DB.items():
        for skill in skills:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text_lower):
                extracted[category].add(skill)

    # 2. Alias normalization
    normalized = defaultdict(set)
    for category, skills in extracted.items():
        for skill in skills:
            normalized[category].add(ALIASES.get(skill, skill))

    # Calculate flat_skills ONCE
    flat_skills = [s for skills in normalized.values() for s in skills]

    # 3. LLM/RAG Fallback (only if weak extraction)
    if len(flat_skills) < 5:
        context = "\n".join(chunks[:3]) if chunks else text[:2000]
        if context.strip():
            llm_skills = _llm_infer_skills(context)
            for skill in llm_skills:
                normalized["inferred"].add(skill.lower())

    return _format_skills(normalized)


# -----------------------------
# LLM SKILL INFERENCE
# -----------------------------
def _llm_infer_skills(text: str) -> list:
    llm = get_llm()

    prompt = f"""
Extract technical skills from this resume.

Rules:
- Only return skills (no explanation)
- Max 10 skills
- Comma separated
- Focus on tools, languages, frameworks

TEXT:
{text[:1500]}
"""

    try:
        response = llm.invoke(prompt).content.strip()
        skills = [s.strip().lower() for s in response.split(",") if s.strip()]
        return skills
    except:
        return []


# -----------------------------
# FORMATTER
# -----------------------------
def _format_skills(skills_dict: dict) -> str:
    lines = []

    for category, skills in skills_dict.items():
        if not skills:
            continue

        clean_skills = sorted(set(skills))
        line = f"{category.upper()}: " + ", ".join(clean_skills)
        lines.append(line)

    if not lines:
        return "No skills detected."

    return "\n".join(lines)