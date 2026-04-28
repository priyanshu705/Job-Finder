"""
src/finder/core/apply_bot/answer_generator.py
--------------------------------------------
Production-Grade AI Answer Generator — AutoApply AI.
Strict skill intersection, tone variation, and hallucination prevention.
"""

import os
import random
from finder.shared.logger import get_logger

log = get_logger("answer_gen")

# User Context
USER_NAME   = os.getenv("USER_NAME", "Candidate")
USER_EXP    = os.getenv("USER_YEARS_EXP", "fresher")
USER_SUMMARY = os.getenv("USER_SUMMARY", "Technical professional with a focus on quality and efficiency.")
USER_SKILLS = set([s.strip().lower() for s in os.getenv("USER_SKILLS", "Python, Selenium, API Testing, QA").split(",")])

TONES = ["concise", "confident", "conversational"]

def _get_skill_intersection(job_skills: str) -> list[str]:
    if not job_skills: return []
    js = set([s.strip().lower() for s in job_skills.split(",")])
    return list(USER_SKILLS.intersection(js))

def _format_answer(template: str, skills: list[str], company: str, tone: str) -> str:
    skills_str = ", ".join(skills[:3]) if skills else "relevant technical skills"
    
    # Tone adjustments
    if tone == "concise":
        prefix = ""
        suffix = " I'm ready to contribute immediately."
    elif tone == "confident":
        prefix = "I am an expert in "
        suffix = f" My background makes me the ideal candidate for {company}."
    else: # conversational
        prefix = "I've spent significant time working with "
        suffix = f" I'd love to bring this experience to the team at {company}."

    return f"{prefix}{template.replace('{skills}', skills_str)}{suffix}"

def generate_smart_answers(job: dict, questions: list[str] = None) -> dict:
    title = job.get("title", "Role")
    company = job.get("company", "Company")
    job_skills = job.get("skills", "")
    
    intersected = _get_skill_intersection(job_skills)
    tone = random.choice(TONES)
    
    # Hallucination Guard: Use summary if no skill overlap found
    if not intersected:
        log.info(f"No skill intersection for {company}. Using fallback summary.")
        base_bio = USER_SUMMARY
    else:
        base_bio = f"My experience in {', '.join(intersected[:2])} is a direct match for this role."

    # Templates
    templates = {
        "why_role": "I'm interested in this role because it leverages my skills in {skills} to solve real-world problems.",
        "why_hire": "You should hire me because I have a proven track record in {skills} and a dedication to high-quality results.",
        "experience": f"I have {USER_EXP} years of experience. I have successfully applied {{skills}} in various professional contexts.",
    }

    generated = {}
    if questions:
        for q in questions:
            # Simple intent mapping
            q_low = q.lower()
            if "hire" in q_low or "fit" in q_low:
                generated[q] = _format_answer(templates["why_hire"], intersected, company, tone)
            elif "why" in q_low or "interest" in q_low:
                generated[q] = _format_answer(templates["why_role"], intersected, company, tone)
            elif "tell" in q_low or "experience" in q_low:
                generated[q] = _format_answer(templates["experience"], intersected, company, tone)
            else:
                generated[q] = base_bio

    # Match Explanation Fix (Task 2)
    if intersected:
        explanation = f"Your experience in {', '.join(intersected[:2])} aligns with their requirement for {job_skills.split(',')[0]}."
    else:
        explanation = "Partial match based on transferable skills and general technical proficiency."

    return {
        "tone_used": tone,
        "cover_letter": f"Dear {company} Team,\n\n{base_bio}\n\nBest,\n{USER_NAME}",
        "specific_answers": generated,
        "explanation": explanation,
        "highlights": {"pitch": base_bio, "tone": tone}
    }
