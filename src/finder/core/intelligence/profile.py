import os
import re
from finder.shared.logger import get_logger

log = get_logger("profile_analyzer")

CATEGORIES = {
    "backend": ["python", "django", "flask", "node", "java", "spring", "golang", "ruby", "c#", ".net"],
    "frontend": ["react", "vue", "angular", "javascript", "typescript", "html", "css", "tailwind"],
    "testing": ["selenium", "playwright", "automation", "qa", "cypress", "testing", "manual testing"],
    "data": ["sql", "mysql", "postgresql", "mongodb", "data analysis", "machine learning", "ml", "ai", "pandas"],
    "devops": ["docker", "kubernetes", "aws", "azure", "ci/cd", "jenkins", "linux"]
}

def get_user_skills():
    """Extract skills from environment variables or a resume profile."""
    # In a real app, this would parse a PDF. Here we use the .env config.
    raw_skills = os.getenv("USER_SKILLS", "")
    if not raw_skills:
        # Fallback to some common defaults if not set
        return ["python", "javascript", "sql"]
    
    return [s.strip().lower() for s in raw_skills.split(",") if s.strip()]

def categorize_skills(skills):
    """Categorize skills into backend, frontend, testing, etc."""
    stats = {cat: [] for cat in CATEGORIES}
    stats["other"] = []

    for skill in skills:
        found = False
        for cat, keywords in CATEGORIES.items():
            if any(k in skill for k in keywords):
                stats[cat].append(skill)
                found = True
        if not found:
            stats["other"].append(skill)
    
    return stats

def detect_roles(skills):
    """Dynamically generate job roles based on skills."""
    roles = set()
    
    cats = categorize_skills(skills)
    
    if cats["backend"]: roles.add("backend developer")
    if cats["frontend"]: roles.add("frontend developer")
    if "react" in skills: roles.add("react developer")
    if cats["testing"]: roles.add("automation tester")
    if "python" in skills: roles.add("python developer")
    if cats["data"]: roles.add("data analyst")
    
    # Generic fallback if nothing detected
    if not roles:
        roles.add("software engineer")
        
    return list(roles)

def get_profile_summary():
    """Get a full intelligence summary of the user's profile."""
    skills = get_user_skills()
    return {
        "skills": skills,
        "categories": categorize_skills(skills),
        "suggested_roles": detect_roles(skills),
        "experience_level": os.getenv("USER_EXP_LEVEL", "fresher")
    }
