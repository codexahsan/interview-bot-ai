# backend/app/shared/utils/domain_classifier.py

import json
from backend.app.core.logger import get_logger
from backend.app.shared.llm.client import get_llm

logger = get_logger(__name__)

DOMAIN_KEYWORDS = {
    "Technical_IT_Backend": ["node", "mongodb", "express", "django", "sql", "flask", "springboot", "java", "golang", "postgress"],
    "Technical_IT_Frontend": ["react", "vue", "angular", "css", "html", "sass", "frontend", "ui", "ux", "tailwind"],
    "Technical_IT_AI_ML": ["pytorch", "tensorflow", "pandas", "machine learning", "numpy", "ai", "deep learning", "sklearn"],
    "Education": ["teaching", "classroom", "student", "lesson", "education", "teacher", "curriculum"],
    "Business": ["marketing", "sales", "kpi", "roi", "business", "b2b", "management", "strategy", "finance"],
    "Design_Creative": ["design", "ui/ux", "figma", "adobe", "photoshop", "illustrator", "creative", "art"],
    "Healthcare": ["health", "medical", "doctor", "nurse", "patient", "clinical", "hospital"]
}

def classify_domain(raw_text: str) -> str:
    """
    Two-stage hybrid domain classifier.
    1. Keyword-based matching
    2. LLM fallback if keywords fail
    """
    text_lower = raw_text.lower()
    
    # Track matches
    matches = {domain: 0 for domain in DOMAIN_KEYWORDS}
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                matches[domain] += 1
                
    # Check if Technical_IT_Fullstack condition is met
    if matches["Technical_IT_Backend"] > 0 and matches["Technical_IT_Frontend"] > 0:
        logger.info("Deterministic domain match: Technical_IT_Fullstack")
        return "Technical_IT_Fullstack"
        
    # Find the domain with the max matches
    best_domain = max(matches, key=matches.get)
    best_score = matches[best_domain]
    
    # If we have a confident match (at least 2 keywords, or just any keyword depending on strictness)
    if best_score >= 1:
        logger.info(f"Deterministic domain match: {best_domain} (score: {best_score})")
        return best_domain
        
    # Fallback to LLM
    logger.info("No confident keyword match. Falling back to LLM classification.")
    prompt = f"""
    Categorize the following CV into one of these exact domains: 
    Technical_IT_Backend, Technical_IT_Frontend, Technical_IT_Fullstack, Technical_IT_AI_ML, Education, Business, Design_Creative, Healthcare, General.
    Return ONLY the category name. Do not include any other text.
    
    CV text: {raw_text[:2000]}
    """
    
    try:
        llm = get_llm()
        result = llm.invoke(prompt).content.strip()
        allowed_domains = ["Technical_IT_Backend", "Technical_IT_Frontend", "Technical_IT_Fullstack", 
                           "Technical_IT_AI_ML", "Education", "Business", "Design_Creative", "Healthcare", "General"]
        for domain in allowed_domains:
            if domain.lower() in result.lower():
                return domain
        return "General"
    except Exception as e:
        logger.error(f"LLM Domain Classification failed: {e}")
        return "General"
