"""
src/finder/shared/resume_parser.py
----------------------------------
Intelligent Resume Parser.
Extracts categorized skills, detects weighted roles, and generates targeted search queries.
"""

import os
import re
from typing import Dict, List, Any
from finder.shared.logging import get_logger

log = get_logger("resume_parser")

# Lazily import heavy parsers
pdfplumber = None
docx2txt = None

def _lazy_load_parsers():
    global pdfplumber, docx2txt
    if pdfplumber is None:
        try:
            import pdfplumber as _pdf
            pdfplumber = _pdf
        except ImportError:
            log.warning("pdfplumber not installed. PDF parsing will fail.")
    if docx2txt is None:
        try:
            import docx2txt as _docx
            docx2txt = _docx
        except ImportError:
            log.warning("docx2txt not installed. DOCX parsing will fail.")

# ── Categories & Aliases ────────────────────────────────────────────────────────

SKILL_CATEGORIES = {
    "languages": {
        "python": ["python", "python3"],
        "javascript": ["javascript", "js", "ecmascript"],
        "typescript": ["typescript", "ts"],
        "java": ["java", "java8", "java11", "java17"],
        "c++": ["c++", "cpp", "cxx"],
        "c#": ["c#", "csharp", ".net", "dotnet"],
        "go": ["go", "golang"],
        "ruby": ["ruby", "ruby on rails"],
        "php": ["php"],
        "rust": ["rust", "rustlang"],
        "sql": ["sql", "t-sql", "pl/sql"]
    },
    "frameworks": {
        "react": ["react", "react.js", "reactjs", "react native"],
        "angular": ["angular", "angular.js", "angularjs"],
        "vue": ["vue", "vue.js", "vuejs"],
        "django": ["django", "django rest framework", "drf"],
        "flask": ["flask"],
        "fastapi": ["fastapi"],
        "spring boot": ["spring boot", "springboot", "spring"],
        "express": ["express", "express.js", "expressjs"],
        "next.js": ["next.js", "nextjs", "next"],
        "laravel": ["laravel"]
    },
    "cloud": {
        "aws": ["aws", "amazon web services", "ec2", "s3", "lambda"],
        "gcp": ["gcp", "google cloud platform", "google cloud"],
        "azure": ["azure", "microsoft azure"],
        "docker": ["docker", "docker compose"],
        "kubernetes": ["kubernetes", "k8s"],
        "terraform": ["terraform", "tf"]
    },
    "databases": {
        "postgresql": ["postgres", "postgresql", "psql"],
        "mysql": ["mysql"],
        "mongodb": ["mongodb", "mongo"],
        "redis": ["redis"],
        "elasticsearch": ["elasticsearch", "elastic search", "es"],
        "cassandra": ["cassandra"],
        "oracle": ["oracle db", "oracle"]
    },
    "tools": {
        "git": ["git", "github", "gitlab", "bitbucket"],
        "linux": ["linux", "ubuntu", "centos", "bash", "shell"],
        "jenkins": ["jenkins"],
        "github actions": ["github actions", "gh actions"],
        "jira": ["jira"]
    }
}

ROLE_DEFINITIONS = {
    "Backend Developer": {
        "keywords": ["backend", "api", "microservices", "server", "database"],
        "core_skills": ["python", "java", "go", "node", "django", "flask", "fastapi", "spring boot", "postgresql", "mysql", "mongodb"]
    },
    "Frontend Developer": {
        "keywords": ["frontend", "ui", "ux", "browser", "responsive", "web", "spa"],
        "core_skills": ["javascript", "typescript", "react", "angular", "vue", "html", "css", "next.js", "tailwind"]
    },
    "Full Stack Developer": {
        "keywords": ["full stack", "full-stack", "fullstack", "end-to-end"],
        "core_skills": ["javascript", "react", "node", "python", "django", "postgresql", "aws"]
    },
    "DevOps Engineer": {
        "keywords": ["devops", "ci/cd", "pipeline", "infrastructure", "automation", "deployment"],
        "core_skills": ["aws", "gcp", "azure", "docker", "kubernetes", "terraform", "jenkins", "linux"]
    },
    "Data Scientist": {
        "keywords": ["data", "machine learning", "ai", "model", "analytics", "prediction", "deep learning"],
        "core_skills": ["python", "sql", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch"]
    }
}

# ── Precompiled Regex Patterns ─────────────────────────────────────────────────

_COMPILED_SKILL_PATTERNS = []
for category, skill_map in SKILL_CATEGORIES.items():
    for canonical, aliases in skill_map.items():
        for alias in aliases:
            if not re.match(r'^\w+$', alias):
                pattern = r'(?:^|\s)' + re.escape(alias) + r'(?:\s|$|[.,;])'
            else:
                pattern = r'\b' + re.escape(alias) + r'\b'
            _COMPILED_SKILL_PATTERNS.append((category, canonical, re.compile(pattern)))

_COMPILED_ROLE_KEYWORDS = {}
for role, criteria in ROLE_DEFINITIONS.items():
    _COMPILED_ROLE_KEYWORDS[role] = [re.compile(r'\b' + re.escape(kw) + r'\b') for kw in criteria["keywords"]]

# ── Parsing Logic ──────────────────────────────────────────────────────────────

def parse_resume(file_path: str) -> str:
    """Extract raw text from a PDF or DOCX file."""
    _lazy_load_parsers()
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            if not pdfplumber:
                raise RuntimeError("pdfplumber is required for PDF parsing")
            with pdfplumber.open(file_path) as pdf:
                pages = [page.extract_text() for page in pdf.pages if page.extract_text()]
                text = "\n".join(pages)
        elif ext in (".docx", ".doc"):
            if not docx2txt:
                raise RuntimeError("docx2txt is required for DOCX parsing")
            text = docx2txt.process(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
    except Exception as e:
        log.error("Failed to parse resume: %s", e)
        from finder.shared.errors import ParsingError
        raise ParsingError(f"Could not extract text from {file_path}: {e}")
    return text

def extract_skills_categorized(text: str) -> Dict[str, List[str]]:
    """Extract skills and categorize them, handling aliases."""
    text_lower = text.lower()
    found_skills = {
        "languages": set(),
        "frameworks": set(),
        "cloud": set(),
        "databases": set(),
        "tools": set()
    }
    
    for category, canonical, compiled_pattern in _COMPILED_SKILL_PATTERNS:
        if canonical in found_skills[category]:
            continue
        if compiled_pattern.search(text_lower):
            found_skills[category].add(canonical)
            
    return {k: list(v) for k, v in found_skills.items()}

def detect_roles(text: str, extracted_skills: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """Score roles based on text keywords and extracted skills."""
    text_lower = text.lower()
    flat_skills = set()
    for skills in extracted_skills.values():
        flat_skills.update(skills)
        
    role_scores = []
    
    for role, criteria in ROLE_DEFINITIONS.items():
        score = 0
        matched_skills = []
        
        # Check keywords
        for compiled_kw in _COMPILED_ROLE_KEYWORDS[role]:
            if compiled_kw.search(text_lower):
                score += 10
                
        # Check core skills
        for skill in criteria["core_skills"]:
            if skill in flat_skills:
                score += 20
                matched_skills.append(skill)
                
        if score > 0:
            confidence = min(score * 1.5, 99)
            role_scores.append({
                "role": role,
                "confidence": int(confidence),
                "matched_skills": matched_skills
            })
            
    # Sort by confidence
    role_scores.sort(key=lambda x: x["confidence"], reverse=True)
    return role_scores[:3]

def generate_queries(roles: List[Dict[str, Any]]) -> List[str]:
    """Generate job search queries based on the top roles detected."""
    queries = []
    modifiers = ["", "Remote", "Intern", "Fresher", "Junior"]
    
    for role_data in roles:
        base_role = role_data["role"]
        # Add basic role
        queries.append(base_role)
        # Add modified roles
        for mod in modifiers:
            if mod:
                queries.append(f"{mod} {base_role}")
                
        # If they have specific skills, we can add skill-based queries
        skills = role_data["matched_skills"]
        if skills:
            top_skill = skills[0].title()
            queries.append(f"{top_skill} {base_role}")
            if "Remote" in modifiers:
                 queries.append(f"Remote {top_skill} {base_role}")
    
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            deduped.append(q)
            
    return deduped[:10]

def analyze_resume(file_path: str) -> Dict[str, Any]:
    """Master function to run the full parsing pipeline."""
    text = parse_resume(file_path)
    skills = extract_skills_categorized(text)
    roles = detect_roles(text, skills)
    queries = generate_queries(roles)
    
    return {
        "raw_text": text,
        "skills": skills,
        "roles": roles,
        "queries": queries
    }
