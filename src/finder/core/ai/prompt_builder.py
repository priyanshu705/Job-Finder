"""
src/finder/core/ai/prompt_builder.py
--------------------------------------
Prompt builders for each AI generation type.
Prompts are kept under ~600 tokens (free-tier friendly).
"""

from typing import Dict, Any


# ---------------------------------------------------------------------------
# Individual prompt builders
# ---------------------------------------------------------------------------

def build_cover_letter(
    resume_skills: str = "",
    detected_role: str = "",
    job_description: str = "",
    company_name: str = "",
    match_explanation: str = "",
    **_,
) -> str:
    return (
        f"Write a concise, professional cover letter (max 200 words) for a "
        f"{detected_role or 'Software Engineer'} role at {company_name or 'the company'}.\n\n"
        f"Candidate's key skills: {resume_skills[:300]}\n\n"
        f"Job description excerpt: {job_description[:400]}\n\n"
        f"Why they are a good fit: {match_explanation[:200]}\n\n"
        f"Start with 'Dear Hiring Manager,' and end with 'Sincerely, [Your Name]'."
    )


def build_hire_me(
    resume_skills: str = "",
    detected_role: str = "",
    job_description: str = "",
    company_name: str = "",
    match_explanation: str = "",
    **_,
) -> str:
    return (
        f"Answer the interview question 'Why should we hire you?' for a "
        f"{detected_role} applying to {company_name}.\n\n"
        f"Candidate skills: {resume_skills[:300]}\n"
        f"Role context: {job_description[:300]}\n\n"
        f"Provide 4-5 concise bullet points. Be confident but genuine."
    )


def build_interview_prep(
    resume_skills: str = "",
    detected_role: str = "",
    job_description: str = "",
    company_name: str = "",
    **_,
) -> str:
    return (
        f"Generate 5 targeted interview preparation questions for a {detected_role} "
        f"role at {company_name}.\n\n"
        f"Job description: {job_description[:400]}\n"
        f"Candidate skills: {resume_skills[:200]}\n\n"
        f"Format: numbered list. Include both technical and behavioral questions."
    )


def build_candidate_pitch(
    resume_skills: str = "",
    detected_role: str = "",
    company_name: str = "",
    **_,
) -> str:
    return (
        f"Write a 2-sentence professional elevator pitch for a {detected_role} "
        f"applying to {company_name}.\n\n"
        f"Top skills to highlight: {resume_skills[:250]}\n\n"
        f"Make it memorable and specific."
    )


def build_resume_job_fit(
    resume_skills: str = "",
    detected_role: str = "",
    job_description: str = "",
    **_,
) -> str:
    return (
        f"Analyse how well this candidate fits the job (max 120 words).\n\n"
        f"Candidate skills: {resume_skills[:300]}\n"
        f"Target role: {detected_role}\n"
        f"Job description: {job_description[:400]}\n\n"
        f"Highlight top 3 matches and 1-2 gaps."
    )


def build_application_response(
    resume_skills: str = "",
    detected_role: str = "",
    job_description: str = "",
    company_name: str = "",
    **_,
) -> str:
    return (
        f"Write a brief, personalised application message (max 80 words) for a "
        f"{detected_role} role at {company_name}.\n\n"
        f"Skills: {resume_skills[:200]}\n"
        f"Role context: {job_description[:200]}\n\n"
        f"Sound enthusiastic but professional."
    )


def build_followup_email(
    company_name: str = "",
    job_title: str = "",
    followup_type: str = "recruiter",
    **_,
) -> str:
    type_context = {
        "interview": "thanking the interviewer and expressing continued interest",
        "recruiter": "following up on the job application status",
        "rejection": "gracefully acknowledging a rejection and keeping the door open",
        "networking": "connecting professionally on LinkedIn",
    }
    intent = type_context.get(followup_type, "following up on the application")
    return (
        f"Write a short, professional follow-up email (max 100 words) for a "
        f"{job_title} role at {company_name}.\n\n"
        f"Purpose: {intent}\n\n"
        f"Subject line + email body. Keep it warm, concise, and authentic."
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

PROMPT_BUILDERS: Dict[str, Any] = {
    "cover_letter":         build_cover_letter,
    "hire_me":              build_hire_me,
    "interview_prep":       build_interview_prep,
    "candidate_pitch":      build_candidate_pitch,
    "resume_job_fit":       build_resume_job_fit,
    "application_response": build_application_response,
    "followup_email":       build_followup_email,
}


def get_prompt(generation_type: str, context: Dict[str, Any]) -> str:
    """Return a built prompt string for the given generation_type.

    Args:
        generation_type: Key from PROMPT_BUILDERS.
        context: Dict with all the keyword args for the builder function.
    """
    builder = PROMPT_BUILDERS.get(generation_type)
    if not builder:
        raise ValueError(f"Unknown generation type: '{generation_type}'")
    return builder(**context)
