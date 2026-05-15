"""
src/finder/core/ai/providers/gemini_provider.py
------------------------------------------------
Gemini Free-Tier AI provider (synchronous, Celery-compatible).
Uses google-generativeai SDK with request caching via Redis,
daily quota enforcement, retry with exponential backoff, and
graceful template fallback.
"""

import os
import hashlib
import time
import logging
from typing import Optional

log = logging.getLogger("gemini_provider")

GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL      = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")   # free-tier model
DAILY_QUOTA       = int(os.getenv("GEMINI_DAILY_QUOTA", "50"))      # safe free-tier limit
REDIS_URL         = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL         = 60 * 60 * 24   # 24 h

# ---------------------------------------------------------------------------
# Optional Redis cache – degrades gracefully when Redis is unavailable
# ---------------------------------------------------------------------------
_redis = None
def _get_redis():
    global _redis
    if _redis is None:
        try:
            import redis as redis_lib
            _redis = redis_lib.StrictRedis.from_url(REDIS_URL, socket_connect_timeout=2)
            _redis.ping()
        except Exception as exc:
            log.warning("Redis not available – caching disabled: %s", exc)
            _redis = False
    return _redis if _redis else None


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:32]


def _cache_get(key: str) -> Optional[str]:
    r = _get_redis()
    if r is None:
        return None
    try:
        val = r.get(f"ai:{key}")
        return val.decode() if val else None
    except Exception:
        return None


def _cache_set(key: str, value: str):
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(f"ai:{key}", CACHE_TTL, value)
    except Exception as exc:
        log.debug("Cache set failed: %s", exc)


# ---------------------------------------------------------------------------
# Fallback template engine (pure Python, no dependencies)
# ---------------------------------------------------------------------------
def _fallback_template(generation_type: str, context: dict) -> str:
    """Return a static template-filled string when Gemini is unavailable."""
    role     = context.get("detected_role", "the position")
    company  = context.get("company_name", "the company")
    skills   = context.get("resume_skills", "relevant skills")

    templates = {
        "cover_letter": (
            f"Dear Hiring Manager,\n\nI am excited to apply for the {role} role at {company}. "
            f"My key skills include {skills}, which align well with your requirements. "
            f"I would love to contribute to your team.\n\nBest regards"
        ),
        "hire_me": (
            f"You should hire me because:\n"
            f"• I bring hands-on experience in {skills}\n"
            f"• I am a strong fit for the {role} role\n"
            f"• I am passionate about contributing to {company}'s mission\n"
            f"• I learn quickly and thrive in dynamic environments"
        ),
        "interview_prep": (
            f"Interview preparation questions for {role} at {company}:\n"
            f"1. Describe your experience with {skills}.\n"
            f"2. How do you handle tight deadlines?\n"
            f"3. What interests you most about {company}?\n"
            f"4. How do you approach problem solving?\n"
            f"5. Describe a challenging project and how you handled it."
        ),
        "candidate_pitch": (
            f"I'm a {role} with expertise in {skills}, "
            f"looking to bring my skills to {company} and drive meaningful impact."
        ),
        "resume_job_fit": (
            f"Strong match: Your skills ({skills}) align well with the {role} requirements. "
            f"Consider highlighting your most relevant experience."
        ),
        "application_response": (
            f"Thank you for the opportunity. My background in {skills} makes me a great fit "
            f"for the {role} role at {company}. I look forward to discussing further."
        ),
    }
    return templates.get(generation_type, "Content generation is temporarily unavailable. Please try again later.")


# ---------------------------------------------------------------------------
# Quota check (DB-based)
# ---------------------------------------------------------------------------
def _daily_usage() -> int:
    try:
        from finder.shared.database import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM ai_generations WHERE date(created_at) = date('now')"
            ).fetchone()
            return (row["cnt"] if row else 0)
    except Exception:
        return 0


def _record_generation(generation_type: str, prompt_hash: str, response: str, provider: str = "gemini", cached: bool = False):
    try:
        from finder.shared.database import get_db
        with get_db() as conn:
            conn.execute(
                "INSERT INTO ai_generations (generation_type, prompt_hash, provider, response, cached) VALUES (?,?,?,?,?)",
                (generation_type, prompt_hash, provider, response[:4000], cached)
            )
    except Exception as exc:
        log.warning("Failed to record AI generation: %s", exc)


# ---------------------------------------------------------------------------
# Core generate function
# ---------------------------------------------------------------------------
def generate(prompt: str, generation_type: str = "generic", context: dict = None,
             max_retries: int = 3, timeout: int = 30, temperature: float = 0.7) -> str:
    """
    Synchronous Gemini generation with:
      - Redis response caching (24 h)
      - Daily quota enforcement (defaults to 50 calls/day free tier)
      - Retry with exponential backoff (max 3 attempts)
      - Graceful fallback to template on failure or quota exhaustion
    """
    context = context or {}
    prompt_hash = _hash_prompt(prompt)

    # 1. Cache check
    cached = _cache_get(prompt_hash)
    if cached:
        log.debug("AI cache hit: %s", prompt_hash)
        _record_generation(generation_type, prompt_hash, cached, "gemini", cached=True)
        return cached

    # 2. Quota check
    if _daily_usage() >= DAILY_QUOTA:
        log.warning("Gemini daily quota exhausted – using fallback template")
        fallback = _fallback_template(generation_type, context)
        _record_generation(generation_type, prompt_hash, fallback, "fallback")
        return fallback

    # 3. API key required
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not set – using fallback template")
        return _fallback_template(generation_type, context)

    # 4. Gemini SDK call with retries
    response_text = None
    for attempt in range(1, max_retries + 1):
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(GEMINI_MODEL)
            resp = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=1024,
                )
            )
            response_text = resp.text
            break
        except Exception as exc:
            log.warning("Gemini attempt %d/%d failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)   # exponential backoff

    if response_text is None:
        log.error("All Gemini attempts failed – using fallback template")
        fallback = _fallback_template(generation_type, context)
        _record_generation(generation_type, prompt_hash, fallback, "fallback")
        return fallback

    # 5. Cache and record successful response
    _cache_set(prompt_hash, response_text)
    _record_generation(generation_type, prompt_hash, response_text, "gemini")
    return response_text
