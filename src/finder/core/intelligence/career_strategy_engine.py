"""
src/finder/core/intelligence/career_strategy_engine.py
------------------------------------------------------
Phase F: Career Strategy Intelligence
Generates skill gap analyses and career insights based on mismatch patterns.
"""

import os
import logging
from typing import List, Dict
from finder.shared.database import get_db

log = logging.getLogger("career_strategy")

def generate_skill_gap_analysis(user_id: int) -> str:
    """
    Analyzes historical rejections and mismatched jobs to identify skill gaps.
    """
    try:
        with get_db() as conn:
            # 1. Fetch missing skills from recently rejected or skipped jobs
            rows = conn.execute(
                "SELECT j.description FROM apply_queue q JOIN jobs j ON q.job_url = j.job_url WHERE q.status IN ('rejected', 'skip') ORDER BY q.updated_at DESC LIMIT 10"
            ).fetchall()
            
            resume = conn.execute("SELECT skills FROM resume_versions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,)).fetchone()
            
        if not rows or not resume:
            return "Not enough data to perform a skill gap analysis yet. Apply or skip more jobs."
            
        descriptions = "\n".join([r["description"][:500] for r in rows])
        skills = resume["skills"]
        
        # 2. Use Gemini to find the gaps
        from google.generativeai import configure, GenerativeModel
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Requires Gemini API Key for Skill Gap Analysis."
            
        configure(api_key=api_key)
        model = GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        You are an expert career strategist.
        The user has these skills: {skills}
        
        They recently missed out on jobs with these descriptions (snippets):
        {descriptions}
        
        Identify the top 3 missing skills or technologies the user should learn to improve their match rate for these types of roles.
        Keep it concise, actionable, and specific.
        """
        
        response = model.generate_content(prompt)
        insight = response.text.strip()
        
        # Save insight
        with get_db() as conn:
            conn.execute("INSERT INTO strategy_insights (user_id, insight_type, insight_text) VALUES (?, 'skill_gap', ?)", (user_id, insight))
            
        return insight
        
    except Exception as exc:
        log.error("Failed to generate skill gap analysis: %s", exc)
        return "Failed to analyze skill gaps due to an error."
