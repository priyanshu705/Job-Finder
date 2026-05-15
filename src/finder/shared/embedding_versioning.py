"""
src/finder/shared/embedding_versioning.py
-----------------------------------------
TASK 11: EMBEDDING VERSIONING
-----------------------------------------
Manages embedding model versioning for cache invalidation.

Problem:
When embedding model changes, cached embeddings become invalid.
This layer ensures backward compatibility and safe migrations.

Solution:
- Tag embeddings with model version
- Auto-detect model changes
- Invalidate old embeddings
- Support side-by-side versions
"""

import logging
import os
import hashlib
from typing import Optional, Dict, Any

from finder.shared.db_abstraction import (
    db_execute,
    db_fetch_one,
    db_fetch_all,
)
from finder.shared.redis_cache import cache_get, cache_set, cache_delete_pattern

log = logging.getLogger(__name__)


class EmbeddingVersion:
    """Manages embedding model versioning."""
    
    # Current embedding model
    CURRENT_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Version computed from model name + config
    @staticmethod
    def get_current_version() -> str:
        """
        Compute current embedding model version.
        
        Returns:
            Version string (hash-based)
        """
        # Include model name and any config parameters
        version_string = f"{EmbeddingVersion.CURRENT_MODEL}"
        
        # Also include dimension if available
        try:
            dims = os.getenv("EMBED_DIMENSIONS", "384")
            version_string += f"|dim:{dims}"
        except Exception:
            pass
        
        # Hash for compact representation
        version_hash = hashlib.sha256(version_string.encode()).hexdigest()[:8]
        return version_hash
    
    SCHEMA = """
        CREATE TABLE IF NOT EXISTS embedding_versions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id      TEXT NOT NULL UNIQUE,
            model_name      TEXT NOT NULL,
            dimensions      INTEGER,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            deprecated_at   DATETIME,
            notes           TEXT
        );
        
        CREATE TABLE IF NOT EXISTS job_embeddings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id          INTEGER,
            job_url         TEXT,
            version_id      TEXT,
            embedding       BLOB,
            embedding_json  TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_embedding_job 
            ON job_embeddings(job_id, version_id);
        CREATE INDEX IF NOT EXISTS idx_embedding_url 
            ON job_embeddings(job_url, version_id);
    """
    
    @staticmethod
    def initialize():
        """Create embedding versioning tables."""
        try:
            from finder.shared.database import _USE_POSTGRES
            
            if _USE_POSTGRES:
                # PostgreSQL version
                schema_pg = """
                    CREATE TABLE IF NOT EXISTS embedding_versions (
                        id              SERIAL PRIMARY KEY,
                        version_id      TEXT NOT NULL UNIQUE,
                        model_name      TEXT NOT NULL,
                        dimensions      INTEGER,
                        created_at      TIMESTAMP DEFAULT NOW(),
                        deprecated_at   TIMESTAMP,
                        notes           TEXT
                    );
                    
                    CREATE TABLE IF NOT EXISTS job_embeddings (
                        id              SERIAL PRIMARY KEY,
                        job_id          INTEGER,
                        job_url         TEXT,
                        version_id      TEXT,
                        embedding       BYTEA,
                        embedding_json  TEXT,
                        created_at      TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_embedding_job 
                        ON job_embeddings(job_id, version_id);
                    CREATE INDEX IF NOT EXISTS idx_embedding_url 
                        ON job_embeddings(job_url, version_id);
                """
                for stmt in schema_pg.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception:
                            pass
            else:
                # SQLite version
                for stmt in EmbeddingVersion.SCHEMA.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception:
                            pass
            
            # Register current version
            EmbeddingVersion._register_version()
            
            log.info("Embedding versioning initialized")
        except Exception as e:
            log.error(f"Embedding versioning init failed: {e}")
    
    @staticmethod
    def _register_version():
        """Register current embedding model version."""
        try:
            version_id = EmbeddingVersion.get_current_version()
            model_name = EmbeddingVersion.CURRENT_MODEL
            
            # Check if version already exists
            sql = "SELECT id FROM embedding_versions WHERE version_id = ?"
            if db_fetch_one(sql, (version_id,)):
                return  # Already registered
            
            # Register new version
            sql = """
                INSERT INTO embedding_versions (version_id, model_name, dimensions)
                VALUES (?, ?, ?)
            """
            dims = int(os.getenv("EMBED_DIMENSIONS", "384"))
            db_execute(sql, (version_id, model_name, dims))
            
            log.info(f"Registered embedding version {version_id}: {model_name}")
        except Exception as e:
            log.warning(f"Version registration failed: {e}")
    
    @staticmethod
    def save_embedding(
        job_id: Optional[int],
        job_url: str,
        embedding: Any  # list or numpy array
    ) -> bool:
        """
        Save an embedding with current model version.
        
        Args:
            job_id: Job database ID
            job_url: Job URL
            embedding: Embedding vector
            
        Returns:
            True if successful
        """
        try:
            import json
            import numpy as np
            
            version_id = EmbeddingVersion.get_current_version()
            
            # Convert to list if numpy array
            if isinstance(embedding, np.ndarray):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)
            
            embedding_json = json.dumps(embedding_list)
            
            sql = """
                INSERT INTO job_embeddings
                (job_id, job_url, version_id, embedding_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id, version_id) DO UPDATE SET
                    embedding_json = ?, created_at = CURRENT_TIMESTAMP
            """
            db_execute(sql, (
                job_id, job_url, version_id, embedding_json,
                embedding_json
            ))
            
            return True
        except Exception as e:
            log.error(f"Failed to save embedding: {e}")
            return False
    
    @staticmethod
    def get_embedding(
        job_id: int,
        version_id: Optional[str] = None
    ) -> Optional[list]:
        """
        Get embedding for a job.
        
        Args:
            job_id: Job database ID
            version_id: Model version (current if None)
            
        Returns:
            Embedding list or None
        """
        try:
            import json
            
            if not version_id:
                version_id = EmbeddingVersion.get_current_version()
            
            # Try cache first
            cache_key = f"{job_id}:{version_id}"
            cached = cache_get("embedding", cache_key)
            if cached:
                return cached
            
            # Get from database
            sql = """
                SELECT embedding_json FROM job_embeddings
                WHERE job_id = ? AND version_id = ?
                LIMIT 1
            """
            row = db_fetch_one(sql, (job_id, version_id))
            
            if not row:
                return None
            
            embedding = json.loads(row.get("embedding_json"))
            
            # Cache for 24 hours
            cache_set("embedding", cache_key, embedding, ttl_seconds=86400)
            
            return embedding
        
        except Exception as e:
            log.debug(f"Failed to get embedding: {e}")
            return None
    
    @staticmethod
    def invalidate_old_embeddings() -> int:
        """
        Invalidate embeddings from old model versions.
        Should be called after model update.
        
        Returns:
            Number of invalidated embeddings
        """
        try:
            # Get current version
            current_version = EmbeddingVersion.get_current_version()
            
            # Find old versions
            sql = """
                SELECT version_id FROM embedding_versions
                WHERE version_id != ?
                AND deprecated_at IS NULL
            """
            old_versions = db_fetch_all(sql, (current_version,))
            
            count = 0
            for version_row in old_versions:
                old_version = version_row.get("version_id")
                
                # Mark as deprecated
                sql_mark = """
                    UPDATE embedding_versions
                    SET deprecated_at = CURRENT_TIMESTAMP
                    WHERE version_id = ?
                """
                db_execute(sql_mark, (old_version,))
                
                # Delete old embeddings
                sql_delete = """
                    DELETE FROM job_embeddings
                    WHERE version_id = ?
                """
                db_execute(sql_delete, (old_version,))
                
                # Clear cache
                cache_delete_pattern("embedding", f"*:{old_version}")
                
                count += 1
            
            log.info(f"Invalidated {count} old embedding versions")
            return count
        
        except Exception as e:
            log.warning(f"Invalidation failed: {e}")
            return 0
    
    @staticmethod
    def get_version_stats() -> Dict[str, Any]:
        """Get statistics about embedding versions."""
        try:
            sql = """
                SELECT ev.version_id, ev.model_name, COUNT(je.id) as embedding_count
                FROM embedding_versions ev
                LEFT JOIN job_embeddings je ON ev.version_id = je.version_id
                WHERE ev.deprecated_at IS NULL
                GROUP BY ev.version_id
            """
            rows = db_fetch_all(sql, ())
            
            current = EmbeddingVersion.get_current_version()
            
            return {
                "current_version": current,
                "versions": [dict(r) for r in rows],
            }
        except Exception as e:
            log.warning(f"Stats retrieval failed: {e}")
            return {}


class EmbeddingCache:
    """Wrapper for embedding caching with versioning."""
    
    @staticmethod
    def get_or_compute(
        job_id: int,
        job_text: str,
        compute_func: callable,
        version_id: Optional[str] = None
    ) -> Optional[list]:
        """
        Get embedding from cache or compute if missing.
        
        Args:
            job_id: Job database ID
            job_text: Text to embed
            compute_func: Function to compute embedding
            version_id: Model version (current if None)
            
        Returns:
            Embedding vector
        """
        try:
            # Try to get from DB (version-aware)
            embedding = EmbeddingVersion.get_embedding(job_id, version_id)
            if embedding:
                log.debug(f"Cache hit for job {job_id}")
                return embedding
            
            # Compute if missing
            log.debug(f"Computing embedding for job {job_id}")
            embedding = compute_func(job_text)
            
            # Save with version
            EmbeddingVersion.save_embedding(job_id, "", embedding)
            
            return embedding
        
        except Exception as e:
            log.error(f"Embedding cache failed: {e}")
            return None

