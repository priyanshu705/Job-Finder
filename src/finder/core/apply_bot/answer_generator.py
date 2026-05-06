"""
src/finder/core/apply_bot/answer_generator.py
--------------------------------------------
Production-Grade AI Answer Generator — AutoApply AI.
Generates cover_letter, why_you_match, short_pitch, and answers
in the exact format the QueueTable assistant panel expects.
"""

import os
import random
from finder.shared.logger import get_logger
from finder.core.intelligence.profile import get_profile_summary

log = get_logger("answer_gen")

# User context from env (overridden by profile if skills found)
USER_NAME    = os.getenv("USER_NAME", "Candidate")
USER_EXP     = os.getenv("USER_YEARS_EXP", "fresher")
USER_SUMMARY = os.getenv(
    "USER_SUMMARY",
    "Motivated technical professional with hands-on experience in software testing and development."
)

TONES = ["concise", "confident", "conversational"]

# Common application questions with smart mappings
DEFAULT_QUESTIONS = [
    "Why do you want to work here?",
    "Why should we hire you?",
    "Tell us about your experience.",
    "What are your key skills?",
]


def _get_user_skills() -> list:
    """Get user skills from profile (which reads from env + resume)."""
    try:
        profile = get_profile_summary()
        skills = profile.get("skills", [])
        if skills:
            return skills
    except Exception:
        pass
    raw = os.getenv("USER_SKILLS", "Python, Selenium, API Testing, QA")
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def _get_skill_intersection(job_skills_str: str, user_skills: list) -> list:
    """Return skills that appear in both user profile and job requirements."""
    if not job_skills_str:
        return []
    job_skill_set = {s.strip().lower() for s in job_skills_str.split(",")}
    user_skill_set = {s.strip().lower() for s in user_skills}
    matched = list(user_skill_set & job_skill_set)
    return matched if matched else []


def _format_skills_str(skills: list, fallback: str = "relevant technical skills") -> str:
    if not skills:
        return fallback
    return ", ".join(s.title() for s in skills[:4])


def generate_smart_answers(job: dict, questions: list = None) -> dict:
    """
    Generate intelligent, tailored AI answers for a job application.

    Returns a dict with keys that the QueueTable assistant panel reads:
      - cover_letter      (str)
      - explanation       (str)  ← "Why You Match"
      - highlights.pitch  (str)  ← "Elevator Pitch"
      - specific_answers  (dict) ← Q&A pairs
      - tone_used         (str)
    """
    title   = job.get("title", "Role")
    company = job.get("company", "Company")
    job_skills_str = job.get("skills", "")
    job_desc       = job.get("description", "")

    user_skills   = _get_user_skills()
    intersected   = _get_skill_intersection(job_skills_str, user_skills)
    tone          = random.choice(TONES)
    skills_str    = _format_skills_str(intersected, fallback=_format_skills_str(user_skills[:3]))
    exp_label     = USER_EXP if USER_EXP.lower() != "freasher" else "fresher"  # typo guard

    # ── Base bio (no hallucination) ────────────────────────────────────────────
    if intersected:
        base_bio = (
            f"My hands-on experience with {skills_str} directly maps to this "
            f"{title} role at {company}."
        )
        explanation = (
            f"Your skills in {skills_str} align with {company}'s requirement for "
            f"{job_skills_str.split(',')[0].strip() if job_skills_str else 'this role'}. "
            f"This is a strong {round(len(intersected) / max(len(user_skills), 1) * 100)}% skill overlap."
        )
    else:
        base_bio = (
            f"I am a motivated {exp_label} with experience in "
            f"{_format_skills_str(user_skills[:3])}. "
            f"I'm eager to apply my skills to contribute to {company}'s goals."
        )
        explanation = (
            f"Partial match based on transferable technical skills "
            f"({_format_skills_str(user_skills[:3])}). "
            "Strong foundational match with room to grow."
        )

    # ── Cover Letter ───────────────────────────────────────────────────────────
    cover_letter = (
        f"Dear {company} Hiring Team,\n\n"
        f"I am writing to express my strong interest in the {title} position.\n\n"
        f"{base_bio}\n\n"
    )
    if intersected:
        cover_letter += (
            f"Having worked with {skills_str}, I am confident I can make an "
            f"immediate contribution to your team.\n\n"
        )
    else:
        cover_letter += (
            f"Though my background spans {_format_skills_str(user_skills[:3])}, "
            f"I am a fast learner and committed to meeting {company}'s standards.\n\n"
        )
    cover_letter += (
        f"I would welcome the opportunity to discuss how my background aligns "
        f"with your team's needs.\n\n"
        f"Best regards,\n{USER_NAME}"
    )

    # ── Elevator Pitch ─────────────────────────────────────────────────────────
    pitch = (
        f"{exp_label.capitalize()} {title.lower()} with expertise in {skills_str}. "
        f"Looking to bring value to {company}."
    )

    # ── Smart Q&A ─────────────────────────────────────────────────────────────
    # Always generate answers for DEFAULT_QUESTIONS + any caller-supplied questions
    all_questions = list(dict.fromkeys((questions or []) + DEFAULT_QUESTIONS))
    specific_answers = {}

    for q in all_questions:
        q_low = q.lower()
        if "hire" in q_low or "why should" in q_low:
            ans = (
                f"You should hire me because I have solid experience in {skills_str} "
                f"and a track record of delivering quality results. "
                f"I'm highly motivated to contribute to {company}."
            )
        elif "why" in q_low and ("work" in q_low or "interest" in q_low or "want" in q_low):
            ans = (
                f"I'm excited about this {title} role at {company} because it aligns "
                f"perfectly with my skills in {skills_str}. "
                f"I want to grow while making a real impact."
            )
        elif "tell" in q_low or "experience" in q_low or "background" in q_low:
            ans = (
                f"I am a {exp_label} professional with experience in {skills_str}. "
                f"I have applied these skills in real-world contexts and "
                f"I am always learning to stay current."
            )
        elif "skill" in q_low or "strength" in q_low:
            ans = (
                f"My core skills include {skills_str}. "
                f"I'm also a fast learner and work well in collaborative environments."
            )
        elif "salary" in q_low or "compensation" in q_low or "ctc" in q_low:
            expected = os.getenv("EXPECTED_SALARY", "open to discussion")
            ans = f"I am looking for a competitive package around {expected}, though I am open to discussion."
        elif "available" in q_low or "join" in q_low or "notice" in q_low:
            notice = os.getenv("NOTICE_PERIOD", "Immediately")
            ans = f"I am available to join {notice}."
        else:
            ans = base_bio

        specific_answers[q] = ans

    return {
        "tone_used":        tone,
        "cover_letter":     cover_letter,
        "explanation":      explanation,
        "highlights": {
            "pitch": pitch,
            "tone":  tone,
        },
        "specific_answers": specific_answers,
        "skills_matched":   intersected,
        # Legacy fields (kept for backward compatibility with any stored data)
        "why_you_match":    explanation,
        "short_pitch":      pitch,
    }
