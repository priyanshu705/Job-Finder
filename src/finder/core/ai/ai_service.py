"""
src/finder/core/ai/ai_service.py
---------------------------------
Synchronous AI orchestration layer.
Called from Celery tasks – must NOT use async/await.
"""

import logging
from finder.api.sockets import emit_event
from .prompt_builder import get_prompt
from .providers.gemini_provider import generate as gemini_generate

log = logging.getLogger("ai_service")


def generate_content(generation_type: str, context: dict) -> str:
    """
    Build the prompt, call Gemini (with cache/quota/fallback), emit
    Socket.IO events, and return the generated text.

    Args:
        generation_type: One of cover_letter | hire_me | interview_prep |
                         candidate_pitch | resume_job_fit | application_response
        context: Dict of kwargs forwarded to the prompt builder.
    Returns:
        Generated (or fallback) text string.
    """
    try:
        prompt = get_prompt(generation_type, context)
    except ValueError as exc:
        log.error("Prompt build failed: %s", exc)
        return f"[Prompt error: {exc}]"

    emit_event("ai:generation_started", {"type": generation_type})

    try:
        result = gemini_generate(
            prompt=prompt,
            generation_type=generation_type,
            context=context,
        )
        emit_event("ai:generation_completed", {"type": generation_type, "success": True})
        return result
    except Exception as exc:
        log.error("AI generation error for %s: %s", generation_type, exc)
        emit_event("ai:generation_completed", {"type": generation_type, "success": False, "error": str(exc)})
        return f"[Generation error: {exc}]"
