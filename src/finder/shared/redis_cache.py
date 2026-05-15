"""
src/finder/shared/redis_cache.py
--------------------------------
TASK 8: REDIS CACHE NAMESPACE HARDENING
--------------------------------
Provides production-grade Redis caching with:
- Consistent namespace strategy
- Multi-tenant safe keys
- TTL management
- Serialization handling
- Graceful degradation on connection failure

Namespace Strategy:
autoapply:ai:            AI generation cache
autoapply:emb:           Embeddings cache
autoapply:tasks:         Celery task state
autoapply:socket:        Socket.IO messages
autoapply:rate_limit:    Rate limiter state
autoapply:session:       User sessions
"""

import logging
import os
import json
from typing import Any, Optional, Dict

log = logging.getLogger(__name__)

# Try to import redis; gracefully handle if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    log.warning("redis-py not installed - caching disabled")


class RedisCache:
    """
    Production-grade Redis wrapper with namespace support.
    
    Automatically handles:
    - Connection pooling
    - Serialization (JSON)
    - Key namespacing
    - TTL management
    - Graceful fallback if Redis unavailable
    """
    
    # Namespace prefixes
    NAMESPACE = {
        "ai": "autoapply:ai:",           # AI generation results
        "embedding": "autoapply:emb:",   # Embeddings cache
        "task": "autoapply:tasks:",      # Celery tasks
        "socket": "autoapply:socket:",   # Socket.IO state
        "rate_limit": "autoapply:rate_limit:",  # Rate limiter
        "session": "autoapply:session:", # User sessions
        "queue": "autoapply:queue:",     # Queue state
    }
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._available = False
        
        if REDIS_AVAILABLE:
            try:
                self._connect()
            except Exception as e:
                log.warning(f"Redis connection failed: {e} - caching disabled")
                self._available = False
    
    def _connect(self):
        """Establish Redis connection with connection pooling."""
        try:
            # Parse Redis URL
            # Format: redis://[:password]@host:port/db
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,  # Auto-decode strings
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Test connection
            self._client.ping()
            self._available = True
            log.info("Redis connected successfully")
        except Exception as e:
            log.error(f"Redis connection failed: {e}")
            self._available = False
            raise
    
    def _make_key(self, namespace: str, identifier: str) -> str:
        """
        Create a namespaced Redis key.
        
        Args:
            namespace: One of NAMESPACE keys (ai, embedding, etc.)
            identifier: Unique identifier within namespace
            
        Returns:
            Full namespaced key
        """
        prefix = self.NAMESPACE.get(namespace, f"autoapply:{namespace}:")
        # Sanitize identifier to ensure valid Redis key
        sanitized = str(identifier).replace(" ", "_").replace("|", "_")
        return f"{prefix}{sanitized}"
    
    def get(
        self,
        namespace: str,
        identifier: str,
        default: Any = None
    ) -> Any:
        """
        Retrieve a cached value.
        
        Args:
            namespace: Cache namespace
            identifier: Key identifier
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        if not self._available:
            return default
        
        try:
            key = self._make_key(namespace, identifier)
            value = self._client.get(key)
            
            if value is None:
                return default
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Return as string if not JSON
                return value
        
        except Exception as e:
            log.warning(f"Cache get failed: {e}")
            return default
    
    def set(
        self,
        namespace: str,
        identifier: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Store a value in cache.
        
        Args:
            namespace: Cache namespace
            identifier: Key identifier
            value: Value to cache (auto-serialized)
            ttl_seconds: Time-to-live in seconds (None = no expiry)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._available:
            return False
        
        try:
            key = self._make_key(namespace, identifier)
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)
            
            # Set with optional TTL
            if ttl_seconds:
                self._client.setex(key, ttl_seconds, serialized)
            else:
                self._client.set(key, serialized)
            
            return True
        
        except Exception as e:
            log.warning(f"Cache set failed: {e}")
            return False
    
    def delete(self, namespace: str, identifier: str) -> bool:
        """Delete a cache entry."""
        if not self._available:
            return False
        
        try:
            key = self._make_key(namespace, identifier)
            self._client.delete(key)
            return True
        except Exception as e:
            log.warning(f"Cache delete failed: {e}")
            return False

    def acquire_lock(self, lock_name: str, timeout_seconds: int = 60) -> bool:
        """
        Phase G: Distributed task lock using SETNX.
        Prevents duplicate task execution on reconnects.
        """
        if not self._available:
            return True # Fail-open if redis is down
        try:
            key = f"autoapply:lock:{lock_name}"
            acquired = self._client.set(key, "locked", nx=True, ex=timeout_seconds)
            return bool(acquired)
        except Exception as e:
            log.warning("Failed to acquire lock: %s", e)
            return True
            
    def release_lock(self, lock_name: str) -> None:
        if not self._available:
            return
        try:
            key = f"autoapply:lock:{lock_name}"
            self._client.delete(key)
        except Exception as e:
            log.warning("Failed to release lock: %s", e)
    
    def delete_pattern(self, namespace: str, pattern: str) -> int:
        """
        Delete multiple entries matching a pattern.
        
        Args:
            namespace: Cache namespace
            pattern: Pattern to match (e.g., "user_*")
            
        Returns:
            Number of keys deleted
        """
        if not self._available:
            return 0
        
        try:
            prefix = self.NAMESPACE.get(namespace, f"autoapply:{namespace}:")
            full_pattern = f"{prefix}{pattern}"
            
            # Find matching keys
            keys = self._client.keys(full_pattern)
            
            if not keys:
                return 0
            
            # Delete all matching keys
            return self._client.delete(*keys)
        
        except Exception as e:
            log.warning(f"Pattern delete failed: {e}")
            return 0
    
    def exists(self, namespace: str, identifier: str) -> bool:
        """Check if a cache entry exists."""
        if not self._available:
            return False
        
        try:
            key = self._make_key(namespace, identifier)
            return self._client.exists(key) > 0
        except Exception as e:
            log.warning(f"Cache exists check failed: {e}")
            return False
    
    def increment(self, namespace: str, identifier: str, amount: int = 1) -> int:
        """Increment a numeric cache value."""
        if not self._available:
            return 0
        
        try:
            key = self._make_key(namespace, identifier)
            return self._client.incrby(key, amount)
        except Exception as e:
            log.warning(f"Cache increment failed: {e}")
            return 0
    
    def append(self, namespace: str, identifier: str, value: Any) -> bool:
        """Append to a list in cache."""
        if not self._available:
            return False
        
        try:
            key = self._make_key(namespace, identifier)
            
            if isinstance(value, dict):
                serialized = json.dumps(value)
            else:
                serialized = str(value)
            
            self._client.rpush(key, serialized)
            return True
        except Exception as e:
            log.warning(f"Cache append failed: {e}")
            return False
    
    def get_list(self, namespace: str, identifier: str) -> list:
        """Get all items from a list in cache."""
        if not self._available:
            return []
        
        try:
            key = self._make_key(namespace, identifier)
            items = self._client.lrange(key, 0, -1)
            
            # Deserialize JSON items
            result = []
            for item in items:
                try:
                    result.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    result.append(item)
            
            return result
        except Exception as e:
            log.warning(f"Cache get_list failed: {e}")
            return []
    
    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        if not self._available:
            return 0
        
        try:
            prefix = self.NAMESPACE.get(namespace, f"autoapply:{namespace}:")
            pattern = f"{prefix}*"
            
            keys = self._client.keys(pattern)
            if not keys:
                return 0
            
            return self._client.delete(*keys)
        except Exception as e:
            log.warning(f"Namespace clear failed: {e}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis health."""
        if not self._available:
            return {"status": "unavailable"}
        
        try:
            info = self._client.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": round(info.get("used_memory", 0) / 1_000_000, 2),
                "keyspace": len(info.get("keyspace", {})),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global cache instance
_cache = None


def get_cache() -> RedisCache:
    """Get or create global Redis cache instance."""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


# Convenience functions
def cache_get(namespace: str, identifier: str, default: Any = None) -> Any:
    """Convenience function to get from cache."""
    return get_cache().get(namespace, identifier, default)


def cache_set(namespace: str, identifier: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
    """Convenience function to set in cache."""
    return get_cache().set(namespace, identifier, value, ttl_seconds)


def cache_delete(namespace: str, identifier: str) -> bool:
    """Convenience function to delete from cache."""
    return get_cache().delete(namespace, identifier)

