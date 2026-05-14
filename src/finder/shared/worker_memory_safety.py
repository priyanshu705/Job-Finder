"""
src/finder/shared/worker_memory_safety.py
-----------------------------------------
TASK 12: WORKER MEMORY SAFETY
-----------------------------------------
Ensures embeddings and heavy models ONLY run in Celery workers,
never in the Flask web process.

Problem:
- sentence-transformers and torch are memory-heavy
- Loading them in Flask blocks requests
- Multiple processes cause memory bloat

Solution:
- Enforce model loading in workers only
- Lazy loading with guards
- Memory warnings and monitoring
- Graceful degradation
"""

import logging
import os
import psutil
import threading
from typing import Optional, Callable
from functools import wraps

log = logging.getLogger(__name__)

# Runtime detection
IS_CELERY_WORKER = os.environ.get("CELERY_WORKER_PROCESS") == "true"
IS_FLASK_PROCESS = not IS_CELERY_WORKER
MEMORY_WARNING_THRESHOLD_MB = 500  # Warn if model loading > 500MB

# Track loaded models to prevent reloading
_loaded_models = {}
_model_lock = threading.Lock()


class WorkerMemoryError(Exception):
    \"\"\"Exception for memory safety violations.\"\"\"
    pass


class ModelNotAvailable(WorkerMemoryError):
    \"\"\"Model unavailable in current process type.\"\"\"
    pass


def require_worker(model_name: str = ""):
    \"\"\"
    Decorator to enforce that function runs ONLY in Celery worker.
    
    Usage:
        @require_worker(\"sentence-transformers\")
        def embed_text(text):
            ...
    \"\"\"
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if IS_FLASK_PROCESS:
                raise ModelNotAvailable(
                    f\"Model '{model_name}' unavailable in Flask process. \"
                    f\"This operation requires Celery worker. \"
                    f\"Use task queue instead.\"
                )
            return func(*args, **kwargs)
        return wrapper
    
    return decorator


class LazyModelLoader:
    \"\"\"
    Safely loads heavy models with memory tracking.
    
    Guarantees:
    - Only loads in workers
    - Tracks memory usage
    - Warns on excessive consumption
    - Supports multiple model types
    \"\"\"
    
    @staticmethod
    def load_model(
        model_name: str,
        loader_func: Callable,
        max_memory_mb: int = 1000
    ):
        \"\"\"
        Load a model with memory safety checks.
        
        Args:
            model_name: Unique model identifier
            loader_func: Function that loads the model
            max_memory_mb: Max acceptable memory usage
            
        Returns:
            Loaded model
            
        Raises:
            ModelNotAvailable: Not in worker process
            WorkerMemoryError: Memory threshold exceeded
        \"\"\"
        if IS_FLASK_PROCESS:
            raise ModelNotAvailable(
                f\"Cannot load model '{model_name}' in Flask process. \"
                f\"Use Celery worker task instead.\"
            )
        
        # Check if already loaded
        with _model_lock:
            if model_name in _loaded_models:
                log.debug(f\"Model '{model_name}' already loaded\")
                return _loaded_models[model_name]
            
            # Measure memory before loading
            mem_before = LazyModelLoader._get_memory_mb()
            
            try:
                log.info(f\"Loading model '{model_name}'...\")
                model = loader_func()
                
                # Measure memory after loading
                mem_after = LazyModelLoader._get_memory_mb()
                mem_delta = mem_after - mem_before
                
                # Check memory threshold
                if mem_delta > max_memory_mb:
                    log.warning(
                        f\"Model '{model_name}' used {mem_delta}MB \"
                        f\"(threshold: {max_memory_mb}MB)\"
                    )
                
                # Cache model
                _loaded_models[model_name] = model
                log.info(f\"Model '{model_name}' loaded successfully (+{mem_delta}MB)\")
                
                return model
            
            except Exception as e:
                log.error(f\"Failed to load model '{model_name}': {e}\")
                raise
    
    @staticmethod
    def _get_memory_mb() -> float:
        \"\"\"Get current process memory usage in MB.\"\"\"
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception as e:
            log.debug(f\"Memory check failed: {e}\")
            return 0
    
    @staticmethod
    def get_memory_stats() -> dict:
        \"\"\"Get memory statistics for monitoring.\"\"\"
        try:
            process = psutil.Process()
            info = process.memory_info()
            
            return {
                \"rss_mb\": info.rss / 1024 / 1024,
                \"vms_mb\": info.vms / 1024 / 1024,
                \"percent\": process.memory_percent(),
                \"available_mb\": psutil.virtual_memory().available / 1024 / 1024,
                \"is_worker\": IS_CELERY_WORKER,
            }
        except Exception as e:
            log.warning(f\"Memory stats failed: {e}\")
            return {}


class EmbeddingWorkerProxy:
    \"\"\"
    Proxy for embedding operations - routes to worker if needed.
    
    Ensures embeddings never compute in Flask process.
    \"\"\"
    
    @staticmethod
    def embed(text: str) -> Optional[list]:
        \"\"\"
        Get embedding for text.
        
        In Flask: Enqueues task, returns None (must poll result)
        In Worker: Computes embedding directly
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if queued
        \"\"\"
        if IS_CELERY_WORKER:
            # We're in worker - compute directly
            return EmbeddingWorkerProxy._compute_embedding(text)
        else:
            # We're in Flask - enqueue task
            from finder.core.tasks.agent_tasks import compute_embedding_task
            
            task = compute_embedding_task.delay(text)
            log.debug(f\"Enqueued embedding task {task.id}\")
            return None  # Caller must poll task result
    
    @staticmethod
    @require_worker(\"sentence-transformers\")
    def _compute_embedding(text: str) -> list:
        \"\"\"Actually compute embedding (worker only).\"\"\"
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = \"all-MiniLM-L6-v2\"
            model = LazyModelLoader.load_model(
                model_name,
                lambda: SentenceTransformer(model_name)
            )
            
            embeddings = model.encode([text], convert_to_tensor=False)
            return embeddings[0].tolist()
        
        except Exception as e:
            log.error(f\"Embedding computation failed: {e}\")
            raise


def memory_guard(func):
    \"\"\"
    Decorator to warn if function loads heavy models in wrong process.
    
    Usage:
        @memory_guard
        def my_embedding_function():
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(...)
    \"\"\"
    @wraps(func)
    def wrapper(*args, **kwargs):
        mem_before = LazyModelLoader._get_memory_mb()
        result = func(*args, **kwargs)
        mem_after = LazyModelLoader._get_memory_mb()
        mem_delta = mem_after - mem_before
        
        if mem_delta > MEMORY_WARNING_THRESHOLD_MB:
            process_type = \"WORKER\" if IS_CELERY_WORKER else \"FLASK\"
            log.warning(
                f\"{process_type}: {func.__name__} used {mem_delta}MB. \"
                f\"Consider moving to worker if in Flask.\"
            )
        
        return result
    
    return wrapper


class WorkerHealthCheck:
    \"\"\"Monitor worker memory and health.\"\"\"
    
    @staticmethod
    def get_health() -> dict:
        \"\"\"Get worker health metrics.\"\"\"
        stats = LazyModelLoader.get_memory_stats()
        
        # Determine health status
        memory_percent = stats.get(\"percent\", 0)
        health_status = \"healthy\"
        
        if memory_percent > 90:
            health_status = \"critical\"
        elif memory_percent > 75:
            health_status = \"warning\"
        elif memory_percent > 50:
            health_status = \"elevated\"
        
        return {
            **stats,
            \"status\": health_status,
            \"loaded_models\": list(_loaded_models.keys()),
        }
    
    @staticmethod
    def should_restart() -> bool:
        \"\"\"Check if worker should restart due to memory pressure.\"\"\"
        stats = LazyModelLoader.get_memory_stats()
        memory_percent = stats.get(\"percent\", 0)
        
        # Restart if using > 90% memory
        should_restart = memory_percent > 90
        
        if should_restart:
            log.warning(f"Worker memory critical ({memory_percent}%) - restart recommended")
        
        return should_restart

    @staticmethod
    def check_and_enforce_panic_mode() -> bool:
        """
        Phase G: Auto Memory Panic Mode
        If RSS memory exceeds threshold (e.g. 400MB), trip the panic flag in Redis
        to gracefully degrade AI and Scraper execution until memory stabilizes.
        """
        stats = LazyModelLoader.get_memory_stats()
        rss_mb = stats.get("rss_mb", 0)
        
        try:
            from finder.shared.redis_cache import get_cache
            cache = get_cache()
            
            if rss_mb > 400:
                log.error("CRITICAL MEMORY: %s MB. Entering Panic Mode.", rss_mb)
                cache.set("system", "memory_panic", "true", ttl_seconds=300)
                return True
            else:
                cache.delete("system", "memory_panic")
                return False
        except:
            return False


# Initialization: Set environment variable for worker processes
def mark_as_worker():
    \"\"\"
    Call this from Celery worker initialization.
    Should be in worker startup code.
    \"\"\"
    os.environ[\"CELERY_WORKER_PROCESS\"] = \"true\"
    log.info(\"Marked as Celery worker process\")


# Validation: Assert process type is correct
def assert_worker():
    \"\"\"Assert that code is running in worker context.\"\"\"
    if not IS_CELERY_WORKER:
        raise WorkerMemoryError(
            \"This operation requires Celery worker context. \"
            \"Check WorkerMemoryError - this should never happen in Flask.\"
        )


def assert_flask():
    \"\"\"Assert that code is running in Flask context.\"\"\"
    if IS_CELERY_WORKER:
        raise WorkerMemoryError(
            \"This operation should only run in Flask. \"
            \"Worker detected when Flask expected.\"
        )
