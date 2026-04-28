"""
src/finder/core/matcher/service.py
---------------------------------
Resume ↔ Job matcher — AutoApply AI.

Pure-Python implementation: no scikit-learn, no spaCy, no numpy.
Uses regex-based keyword extraction + TF-IDF cosine similarity
computed with only the standard library (math, collections, re).
"""

import os
import re
import json
import math
from collections import Counter
from typing import Optional

import pdfplumber
import docx2txt
from dotenv import load_dotenv

from finder.shared.logger import get_logger
from finder.shared.database import get_db
from finder.shared.metrics import record_metric

load_dotenv()

log = get_logger("matcher")

from finder.shared.config import RESUME_PATH
MIN_MATCH = float(os.getenv("MIN_MATCH", "70"))

# ── Keyword bank (covers QA / dev / automation roles) ────────────────────────
TECH_SKILLS = [
    "selenium", "playwright", "python", "java", "javascript", "typescript",
    "sql", "html", "css", "git", "docker", "aws", "azure", "gcp",
    "react", "angular", "vue", "django", "flask", "fastapi", "spring",
    "qa", "testing", "automation", "manual", "jira", "postman", "pytest",
    "testng", "junit", "robot", "appium", "cypress", "ci", "cd", "jenkins",
    "github", "gitlab", "bitbucket", "linux", "bash", "api", "rest",
    "graphql", "mongodb", "postgresql", "mysql", "redis", "kafka",
    "kubernetes", "terraform", "agile", "scrum", "devops", "sdet",
]

_SKILL_PATTERNS = {
    s: re.compile(r"\b" + re.escape(s) + r"\b", re.IGNORECASE)
    for s in TECH_SKILLS
}


# ── Resume parsing ────────────────────────────────────────────────────────────

def parse_resume(path: str = "") -> str:
    fpath = path or RESUME_PATH
    if not os.path.exists(fpath):
        return ""
    ext = os.path.splitext(fpath)[1].lower()
    try:
        if ext == ".pdf":
            with pdfplumber.open(fpath) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif ext in (".docx", ".doc"):
            return docx2txt.process(fpath)
    except Exception:
        pass
    return ""


# ── Skill extraction (pure regex — no spaCy) ─────────────────────────────────

def extract_skills(text: str) -> list[str]:
    """Extract known tech skills from text using regex patterns only."""
    if not text:
        return []
    return sorted({s for s, pat in _SKILL_PATTERNS.items() if pat.search(text)})


# ── Pure-Python TF-IDF cosine similarity ─────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Lowercase alphanum tokens, remove stop-words."""
    _STOP = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "should", "may", "might", "shall", "not", "no",
        "that", "this", "it", "its", "we", "you", "he", "she", "they",
        "from", "by", "as", "into", "about", "than", "more", "also",
    }
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP and len(t) > 1]


def _tfidf_cosine(doc_a: str, doc_b: str) -> float:
    """
    Compute cosine similarity between two documents using TF-IDF weights.
    Pure Python — no numpy, no sklearn.
    Returns a float in [0.0, 1.0].
    """
    corpus = [_tokenize(doc_a), _tokenize(doc_b)]

    # Build vocabulary
    vocab = sorted({tok for doc in corpus for tok in doc})
    if not vocab:
        return 0.0

    N = len(corpus)  # 2

    # Document frequency
    df = {
        term: sum(1 for doc in corpus if term in set(doc))
        for term in vocab
    }

    def _tfidf_vec(tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        total = len(tokens) or 1
        return {
            term: (tf.get(term, 0) / total) * math.log((N + 1) / (df[term] + 1))
            for term in vocab
        }

    vec_a = _tfidf_vec(corpus[0])
    vec_b = _tfidf_vec(corpus[1])

    dot   = sum(vec_a[t] * vec_b[t] for t in vocab)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Scoring ───────────────────────────────────────────────────────────────────

from finder.core.intelligence.profile import get_profile_summary


def score_job(resume_text: str, job: dict) -> float:
    job_text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("skills", ""),
    ]).lower()

    if not resume_text or not job_text.strip():
        return 0.0

    # User profile for intelligent alignment
    profile     = get_profile_summary()
    user_skills = set(profile["skills"])
    user_roles  = set(profile["suggested_roles"])
    is_fresher  = profile["experience_level"] == "fresher"

    r_skills = set(extract_skills(resume_text))
    j_skills = set(extract_skills(job_text))

    # 1. Skill overlap score (60% weight)
    overlap   = len(user_skills & j_skills)
    kw_score  = (overlap / len(j_skills) * 100) if j_skills else 0.0

    # 2. Semantic similarity via pure-Python TF-IDF (40% weight)
    try:
        cos_score = _tfidf_cosine(resume_text.lower(), job_text) * 100
    except Exception:
        cos_score = 0.0

    base_score = kw_score * 0.6 + cos_score * 0.4

    # 3. Intelligent boosts
    boost = 0
    title = job.get("title", "").lower()

    if any(role in title for role in user_roles):
        boost += 10                                          # role alignment

    if is_fresher and any(
        k in job_text for k in ["fresher", "entry level", "graduate", "0-1 year"]
    ):
        boost += 5                                           # fresher-friendly

    critical_matches = len(user_skills & j_skills)
    boost += min(critical_matches * 2, 10)                   # exact tech match

    return round(min(base_score + boost, 100.0), 2)


# ── Runner ────────────────────────────────────────────────────────────────────

def run_matcher(resume_path: str = "", min_match: float = 0.0) -> dict:
    threshold   = min_match or MIN_MATCH
    resume_text = parse_resume(resume_path)
    if not resume_text:
        return {"errors": 1}

    jobs = [
        dict(r) for r in get_db().execute(
            """SELECT q.id, q.job_url, j.title, j.description, j.skills
               FROM apply_queue q
               LEFT JOIN jobs j ON j.job_url = q.job_url
               WHERE q.status = 'pending' AND q.match_score_at_apply IS NULL"""
        ).fetchall()
    ]

    stats  = {"scored": 0, "passed": 0, "skipped": 0, "avg_score": 0.0, "top_jobs": []}
    scores = []

    with get_db() as conn:
        for job in jobs:
            score = score_job(resume_text, job)
            conn.execute(
                "UPDATE apply_queue SET match_score_at_apply = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (score, "pending" if score >= threshold else "skip", job["id"]),
            )
            stats["scored"] += 1
            scores.append(score)
            if score >= threshold:
                stats["passed"] += 1
                stats["top_jobs"].append({
                    "score":   score,
                    "title":   job["title"],
                    "company": job.get("company", ""),
                })
            else:
                stats["skipped"] += 1

    if scores:
        stats["avg_score"] = round(sum(scores) / len(scores), 2)

    record_metric("match_complete", "matcher", value=stats["scored"])
    return stats
