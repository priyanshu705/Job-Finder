"""
src/finder/core/intelligence/reasoning_engine.py
------------------------------------------------
Phase F: AI Reasoning Layer
LLM-powered reasoning for why a job is a good or bad match, going beyond simple semantic scoring.
Uses Gemini Free Tier, with PostgreSQL caching to minimize token usage.
"""

import os
import logging
from finder.shared.database import get_db

log = logging.getLogger("reasoning_engine")

def generate_reasoning(job_url: str, resume_skills: str, job_description: str, semantic_score: float) -> str:
    """
    Generate an explainable AI output for the job match.
    Returns the reasoning string.
    """
    
    # 0. Check Circuit Breaker & Memory Panic
    try:
        from finder.shared.redis_cache import get_cache
        from finder.shared.worker_memory_safety import WorkerHealthCheck
        
        # Proactively enforce panic check
        is_panic = WorkerHealthCheck.check_and_enforce_panic_mode()
        
        cache = get_cache()
        if cache.get("ai", "circuit_breaker_active") == "true":
            return f"Semantic Match: {semantic_score}% (AI reasoning temporarily disabled due to API limits)"
        if is_panic or cache.get("system", "memory_panic") == "true":
            return f"Semantic Match: {semantic_score}% (AI reasoning paused to stabilize system memory)"
    except:
        pass

    # 1. Check Cache
    try:
        with get_db() as conn:
            row = conn.execute("SELECT reasoning FROM reasoning_cache WHERE job_url = ?", (job_url,)).fetchone()
            if row:
                return row["reasoning"]
    except Exception as e:
        log.warning("Cache check failed: %s", e)
        
    # 2. Generate with Gemini
    try:
        from google.generativeai import configure, GenerativeModel
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return f"Semantic Match: {semantic_score}% (Detailed AI reasoning requires API key)"
            
        configure(api_key=api_key)
        model = GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        You are an expert career strategist. 
        Candidate Skills: {resume_skills}
        Job Description: {job_description[:1000]}...
        Semantic Match Score: {semantic_score}%
        
        Provide a concise, 2-sentence explanation of WHY this job is a good or bad match for the candidate. 
        Be specific about matching or missing skills. Do not use filler words like "Based on the description".
        """
        
        response = model.generate_content(prompt)
        reasoning = response.text.strip()
        
        # Reset circuit breaker on success
        try:
            from finder.shared.redis_cache import get_cache
            get_cache().delete("ai", "circuit_breaker_fails")
        except:
            pass
            
        # 3. Cache the Result
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO reasoning_cache (job_url, reasoning) VALUES (?, ?) ON CONFLICT DO NOTHING",
                    (job_url, reasoning)
                )
        except Exception as cache_err:
            log.warning("Could not cache reasoning: %s", cache_err)
            
        return reasoning
        
    except Exception as exc:
        log.error("Failed to generate AI reasoning: %s", exc)
        
        # Trip circuit breaker on failure
        try:
            from finder.shared.redis_cache import get_cache
            cache = get_cache()
            fails = cache.increment("ai", "circuit_breaker_fails")
            if fails >= 5:
                log.error("GEMINI CIRCUIT BREAKER TRIPPED. Disabling AI generation for 15 minutes.")
                cache.set("ai", "circuit_breaker_active", "true", ttl_seconds=900)
        except:
            pass
            
        return f"Semantic Match: {semantic_score}% (Reasoning generation failed)"
