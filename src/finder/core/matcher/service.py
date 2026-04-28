"""
src/finder/core/matcher/service.py
---------------------------------
Resume ↔ Job matcher — AutoApply AI.
"""

import os
import re
import json
from typing import Optional

import pdfplumber
import docx2txt
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

from finder.shared.logger import get_logger
from finder.shared.database import get_db
from finder.shared.metrics import record_metric

load_dotenv()

log = get_logger("matcher")

from finder.shared.config import RESUME_PATH
MIN_MATCH   = float(os.getenv("MIN_MATCH", "70"))

try:
    NLP = spacy.load("en_core_web_sm")
except OSError:
    NLP = None
    log.warning("spaCy model not found.")

TECH_SKILLS = ["selenium", "playwright", "python", "java", "javascript", "sql", "html", "css", "git", "docker", "aws", "react", "django", "flask", "qa", "testing"]
_SKILL_PATTERNS = {s: re.compile(r"\b" + re.escape(s) + r"\b", re.IGNORECASE) for s in TECH_SKILLS}

def parse_resume(path: str = "") -> str:
    fpath = path or RESUME_PATH
    if not os.path.exists(fpath): return ""
    ext = os.path.splitext(fpath)[1].lower()
    try:
        if ext == ".pdf":
            with pdfplumber.open(fpath) as pdf: return "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif ext in (".docx", ".doc"): return docx2txt.process(fpath)
    except Exception: pass
    return ""

def extract_skills(text: str) -> list[str]:
    if not text: return []
    found = {s.lower() for s, p in _SKILL_PATTERNS.items() if p.search(text)}
    if NLP:
        for ent in NLP(text[:50000]).ents:
            if ent.label_ in ("ORG", "PRODUCT") and len(ent.text.split()) <= 2: found.add(ent.text.lower())
    return sorted(found)

from finder.core.intelligence.profile import get_profile_summary

def score_job(resume_text: str, job: dict) -> float:
    job_text = " ".join([job.get("title", ""), job.get("description", ""), job.get("skills", "")]).lower()
    if not resume_text or not job_text.strip(): return 0.0
    
    # Get user profile for intelligent alignment
    profile = get_profile_summary()
    user_skills = set(profile["skills"])
    user_roles  = set(profile["suggested_roles"])
    is_fresher  = profile["experience_level"] == "fresher"

    r_skills, j_skills = set(extract_skills(resume_text)), set(extract_skills(job_text))
    
    # 1. Skill Overlap (Base Score)
    overlap = len(user_skills & j_skills)
    kw_score = (overlap / len(j_skills) * 100) if j_skills else 0.0
    
    # 2. Semantic Similarity
    try:
        vec = TfidfVectorizer(stop_words="english")
        mtx = vec.fit_transform([resume_text.lower(), job_text.lower()])
        cos_score = float(cosine_similarity(mtx[0], mtx[1])[0][0]) * 100
    except Exception: cos_score = 0.0
    
    base_score = kw_score * 0.6 + cos_score * 0.4
    
    # 3. Intelligent Boosts
    boost = 0
    
    # Role alignment boost (+10%)
    title = job.get("title", "").lower()
    if any(role in title for role in user_roles):
        boost += 10
        
    # Fresher-friendly boost (+5%)
    if is_fresher and any(k in job_text for k in ["fresher", "entry level", "graduate", "0-1 year"]):
        boost += 5
        
    # Exact tech match boost (+2% per critical skill match)
    critical_matches = len(user_skills & j_skills)
    boost += min(critical_matches * 2, 10)
    
    final_score = min(base_score + boost, 100.0)
    return round(final_score, 2)

def run_matcher(resume_path: str = "", min_match: float = 0.0) -> dict:
    threshold = min_match or MIN_MATCH
    resume_text = parse_resume(resume_path)
    if not resume_text: return {"errors": 1}
    jobs = [dict(r) for r in get_db().execute("SELECT q.id, q.job_url, j.title, j.description, j.skills FROM apply_queue q LEFT JOIN jobs j ON j.job_url = q.job_url WHERE q.status = 'pending' AND q.match_score_at_apply IS NULL").fetchall()]
    stats = {"scored": 0, "passed": 0, "skipped": 0, "avg_score": 0.0, "top_jobs": []}
    scores = []
    with get_db() as conn:
        for job in jobs:
            score = score_job(resume_text, job)
            conn.execute("UPDATE apply_queue SET match_score_at_apply = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (score, "pending" if score >= threshold else "skip", job["id"]))
            stats["scored"] += 1
            scores.append(score)
            if score >= threshold:
                stats["passed"] += 1
                stats["top_jobs"].append({"score": score, "title": job["title"], "company": job.get("company", "")})
            else: stats["skipped"] += 1
    if scores: stats["avg_score"] = round(sum(scores) / len(scores), 2)
    record_metric("match_complete", "matcher", value=stats["scored"])
    return stats
