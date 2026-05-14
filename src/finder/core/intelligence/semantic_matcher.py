"""
src/finder/core/intelligence/semantic_matcher.py
------------------------------------------------
Phase I: Zero-Budget Production Semantic Matcher
Uses Google Gemini Embeddings API for ultra-lightweight RAM footprint.
"""

import json
import logging
import hashlib
from typing import Optional, List
import google.generativeai as genai
from finder.shared.database import get_db

log = logging.getLogger("semantic_matcher")

def _get_embedding_from_api(text: str) -> Optional[List[float]]:
    """Fetch embedding from Google Gemini API."""
    try:
        # Truncate text to Gemini's limit if necessary (approx 10k tokens)
        truncated_text = text[:30000] 
        result = genai.embed_content(
            model="models/embedding-001",
            content=truncated_text,
            task_type="clustering"
        )
        return result['embedding']
    except Exception as exc:
        log.error("Gemini embedding API failed: %s", exc)
        return None

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors using pure Python."""
    import math
    
    if len(vec1) != len(vec2):
        return 0.0
        
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)

def get_cached_embedding(source_type: str, source_id: str, version: str = "gemini-v1") -> Optional[List[float]]:
    """Retrieve an embedding from the cache."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT embedding FROM embedding_cache WHERE source_type = ? AND source_id = ? AND version = ?",
                (source_type, source_id, version)
            ).fetchone()
            if row and row["embedding"]:
                return json.loads(row["embedding"])
    except Exception as exc:
        log.warning("Cache fetch error: %s", exc)
    return None

def save_embedding(source_type: str, source_id: str, embedding: List[float], version: str = "gemini-v1"):
    """Save an embedding to the cache."""
    try:
        embedding_str = json.dumps(embedding)
        with get_db() as conn:
            conn.execute(
                "DELETE FROM embedding_cache WHERE source_type = ? AND source_id = ? AND version = ?",
                (source_type, source_id, version)
            )
            conn.execute(
                "INSERT INTO embedding_cache (source_type, source_id, embedding, version) VALUES (?, ?, ?, ?)",
                (source_type, source_id, embedding_str, version)
            )
    except Exception:
        pass

def compute_embedding(text: str, source_type: str, source_id: str, use_cache: bool = True) -> Optional[List[float]]:
    """Compute or retrieve embedding via Gemini API."""
    if not text: return None

    # We use a hash of the text to ensure cache hits for identical content across different job URLs
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    hash_id = f"h_{text_hash}"
    version = "gemini-v1"

    if use_cache:
        cached = get_cached_embedding(source_type, source_id, version)
        if cached: return cached
        
        cached_hash = get_cached_embedding(source_type, hash_id, version)
        if cached_hash:
            save_embedding(source_type, source_id, cached_hash, version)
            return cached_hash

    # Fetch from API
    log.info(f"Computing Gemini embedding for {source_type} {source_id}...")
    emb = _get_embedding_from_api(text)
    
    if emb and use_cache:
        save_embedding(source_type, source_id, emb, version)
        save_embedding(source_type, hash_id, emb, version)
        
    return emb

def calculate_semantic_similarity(resume_text: str, job_text: str, resume_id: str = "current_user", job_url: str = "") -> float:
    """Calculate cosine similarity using Gemini embeddings."""
    resume_emb = compute_embedding(resume_text, "resume", resume_id)
    job_emb = compute_embedding(job_text, "job", job_url)

    if not resume_emb or not job_emb:
        return 0.0

    score = _cosine_similarity(resume_emb, job_emb)
    return max(0.0, float(score))

