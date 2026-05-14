"""
src/finder/core/intelligence/semantic_matcher.py
------------------------------------------------
Phase C: Semantic Matching Engine
Zero-budget, lightweight semantic similarity using sentence-transformers.
"""

import json
import logging
from typing import Optional, List
from finder.shared.database import get_db

log = logging.getLogger("semantic_matcher")

_model = None

def get_model():
    """Lazy load the sentence-transformer model to save memory."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            log.info("Loading semantic model (all-MiniLM-L6-v2)...")
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError as exc:
            log.error("Failed to load sentence-transformers: %s", exc)
            return None
    return _model


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors (fallback if sklearn is missing)."""
    import numpy as np
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


def get_cached_embedding(source_type: str, source_id: str, version: str = "all-MiniLM-L6-v2") -> Optional[List[float]]:
    """Retrieve an embedding from PostgreSQL."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT embedding FROM embedding_cache WHERE source_type = ? AND source_id = ? AND version = ?",
                (source_type, source_id, version)
            ).fetchone()
            if row and row["embedding"]:
                return json.loads(row["embedding"])
    except Exception as exc:
        log.warning("Cache fetch error for %s (%s): %s", source_type, source_id, exc)
    return None


def save_embedding(source_type: str, source_id: str, embedding: List[float], version: str = "all-MiniLM-L6-v2"):
    """Save an embedding to PostgreSQL."""
    try:
        embedding_str = json.dumps(embedding)
        with get_db() as conn:
            # We use an ON CONFLICT or REPLACE equivalent depending on PG/SQLite
            # Our DB wrapper doesn't abstract UPSERT fully, so we'll delete and insert
            conn.execute(
                "DELETE FROM embedding_cache WHERE source_type = ? AND source_id = ? AND version = ?",
                (source_type, source_id, version)
            )
            conn.execute(
                "INSERT INTO embedding_cache (source_type, source_id, embedding, version) VALUES (?, ?, ?, ?)",
                (source_type, source_id, embedding_str, version)
            )
    except Exception as exc:
        log.warning("Cache save error for %s (%s): %s", source_type, source_id, exc)


def compute_embedding(text: str, source_type: str, source_id: str, use_cache: bool = True) -> Optional[List[float]]:
    """Compute (or retrieve) the embedding for a given text."""
    if not text:
        return None

    import hashlib
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    hash_source_id = f"hash_{text_hash}"

    if use_cache:
        # First check if we have the embedding for this specific source_id
        cached = get_cached_embedding(source_type, source_id)
        if cached:
            return cached
            
        # Then check if we have the exact identical text hashed previously
        cached_hash = get_cached_embedding(source_type, hash_source_id)
        if cached_hash:
            log.info(f"Exact-match cache hit for {source_type} {source_id}")
            # Save it under the new source_id for future quick lookups
            save_embedding(source_type, source_id, cached_hash)
            return cached_hash

    model = get_model()
    if not model:
        return None

    # Generate embedding
    try:
        # Encode returns a numpy array, convert to list of floats
        embedding = model.encode(text).tolist()
        if use_cache:
            save_embedding(source_type, source_id, embedding)
            save_embedding(source_type, hash_source_id, embedding)
        return embedding
    except Exception as exc:
        log.error("Embedding generation failed: %s", exc)
        return None


def calculate_semantic_similarity(resume_text: str, job_text: str, resume_id: str = "current_user", job_url: str = "") -> float:
    """
    Calculate the semantic cosine similarity between a resume and a job description.
    Returns a score between 0.0 and 1.0.
    """
    resume_emb = compute_embedding(resume_text, "resume", resume_id)
    job_emb = compute_embedding(job_text, "job", job_url)

    if not resume_emb or not job_emb:
        log.warning("Could not compute semantic similarity (missing embeddings).")
        return 0.0

    try:
        # Use sklearn for fast cosine similarity if available
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        score = cosine_similarity(np.array(resume_emb).reshape(1, -1), np.array(job_emb).reshape(1, -1))[0][0]
        return max(0.0, float(score))
    except ImportError:
        # Fallback
        score = _cosine_similarity(resume_emb, job_emb)
        return max(0.0, float(score))
