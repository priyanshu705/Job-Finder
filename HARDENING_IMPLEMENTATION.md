# AutoApply AI Production Hardening - Complete Implementation Guide

## Executive Summary

This document provides complete guidance for implementing **14 production-grade hardening improvements** to the AutoApply AI platform. All improvements are:

- **Non-breaking**: Preserve existing API and architecture
- **Incremental**: Can be implemented and tested individually
- **Safe**: Idempotent, rollback-safe, transactional
- **Production-ready**: Fully tested patterns with structured logging

**Total estimated implementation time**: 2-3 weeks (phased approach)

---

## Part 1: Database Layer (Tasks 1-4)

### Task 1: Database Placeholder Abstraction
**File**: `src/finder/shared/db_abstraction.py`

**What**: Production-grade database abstraction that handles SQLite (?) and PostgreSQL (%s) placeholder conversion transparently.

**Core Functions**:
- `db_execute(sql, params)` - Execute INSERT/UPDATE/DELETE
- `db_fetch_one(sql, params)` - Get single row
- `db_fetch_all(sql, params)` - Get multiple rows
- `db_count(sql, params)` - Get COUNT value
- `db_upsert(table, conflict_col, data)` - Insert or replace

**Integration**:
```python
# OLD - mixed placeholders
with get_db() as conn:
    conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))

# NEW - abstraction layer
from finder.shared.db_abstraction import db_fetch_one
row = db_fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
```

**Testing**:
```bash
# Verify both SQLite and PostgreSQL work identically
pytest tests/test_db_abstraction.py
```

---

### Task 2: JWT Security Hardening
**File**: `src/finder/shared/jwt_security.py`

**What**: Production-grade JWT + CSRF security with HttpOnly cookies.

**Configuration**:
```python
# In environment or .env
JWT_SECRET=<generate-secure-key>
COOKIE_SECURE=true              # HTTPS only
COOKIE_SAMESITE=Strict          # Strict CSRF protection
COOKIE_HTTPONLY=true            # Never to JavaScript
```

**Integration in Flask**:
```python
from finder.shared.jwt_security import (
    JWTManager,
    CSRFTokenManager,
    require_jwt,
    require_csrf,
    set_access_token_cookie,
    set_refresh_token_cookie,
    set_csrf_token_cookie,
    clear_auth_cookies,
)

@app.route("/api/auth/login", methods=["POST"])
def login():
    user_id = authenticate_user(request.json)
    
    response = make_response({"status": "authenticated"})
    
    # Set tokens in HttpOnly cookies
    access_token = JWTManager.generate_access_token(user_id)
    refresh_token = JWTManager.generate_refresh_token(user_id)
    csrf_token = CSRFTokenManager.generate()
    
    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    set_csrf_token_cookie(response, csrf_token)
    
    return response

@app.route("/api/protected", methods=["GET"])
@require_jwt
def protected():
    # g.user_id is available - set by decorator
    return {"user": g.user_id}

@app.route("/api/resource", methods=["POST"])
@require_jwt
@require_csrf
def create_resource():
    # Both JWT and CSRF validated
    return {"created": True}

@app.route("/api/auth/logout", methods=["POST"])
@require_jwt
def logout():
    response = make_response({"status": "logged out"})
    clear_auth_cookies(response)
    return response
```

**Frontend Integration**:
```javascript
// src/api.js - Add CSRF token to requests
import axios from 'axios'

const api = axios.create({
  baseURL: process.env.VITE_API_URL || 'http://localhost:5000/api',
  withCredentials: true,  // Include cookies
})

// Add CSRF token from cookie
api.interceptors.request.use((config) => {
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1]
  
  if (csrfToken && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(config.method?.toUpperCase())) {
    config.headers['X-CSRF-Token'] = csrfToken
  }
  
  return config
})

export { api }
```

---

### Task 3: JWT Revocation System
**File**: `src/finder/shared/token_revocation.py`

**What**: Token blacklist for logout and session revocation.

**Database Schema**:
```sql
CREATE TABLE revoked_tokens (
    id        INTEGER PRIMARY KEY,
    jti       TEXT NOT NULL UNIQUE,      -- JWT ID
    user_id   TEXT,
    revoked_at DATETIME DEFAULT NOW(),
    expires_at DATETIME,
    reason    TEXT,                      -- logout, compromised, password_reset
    revoked_by TEXT
);
```

**Integration**:
```python
from finder.shared.token_revocation import TokenRevocationManager

# On login - set up revocation checking
TokenRevocationManager.initialize()

# On logout - revoke the token
@app.route("/api/auth/logout", methods=["POST"])
@require_jwt
def logout():
    token = JWTManager.get_from_request()
    is_valid, payload, _ = JWTManager.verify_token(token)
    
    if is_valid:
        # Revoke both access and refresh tokens
        TokenRevocationManager.revoke(
            payload.get('jti'),
            user_id=g.user_id,
            reason='logout'
        )
    
    response = make_response({"status": "logged out"})
    clear_auth_cookies(response)
    return response

# Automatic revocation check in @require_jwt decorator
```

**Cleanup Task** (Celery):
```python
@celery_app.task(schedule=crontab(hour=2, minute=0))
def cleanup_expired_tokens():
    \"\"\"Run daily at 2 AM\"\"\"
    TokenRevocationManager.cleanup_expired()
```

---

### Task 4: Multi-Tenant Backfill Migration
**File**: `src/finder/shared/multi_tenant_migration.py`

**What**: Add user_id to all existing tables for multi-tenant safety.

**Tables Updated**:
- apply_queue
- resume_data  
- approval_queue
- company_intelligence
- application_outcomes
- user_goals
- query_weights

**Migration Process**:
```python
from finder.shared.multi_tenant_migration import MultiTenantMigration

# Run during deployment/startup
MultiTenantMigration.initialize()

# Verify all data has user_id
sql = "SELECT COUNT(*) as c FROM apply_queue WHERE user_id IS NULL"
orphaned = db_count(sql, ())
assert orphaned == 0, f"Found {orphaned} orphaned rows"
```

**Usage in Queries** (automatically scope to current user):
```python
from finder.shared.multi_tenant_migration import MultiTenantScopeHelper

# Get queue for current user only
user_id = g.user_id
queue_stats = MultiTenantScopeHelper.user_queue_count(user_id)

# Query is automatically scoped
sql = "SELECT * FROM apply_queue WHERE status = ?"
sql_scoped, _ = MultiTenantScopeHelper.scope_query(sql, user_id)
# Result: "SELECT * FROM apply_queue WHERE status = ? AND user_id = ?"
```

---

## Part 2: AI & Provider Layer (Tasks 5-7)

### Task 5: CSRF Flow Documentation
**File**: `src/finder/shared/jwt_security.py` (CSRFTokenManager)

**What**: X-CSRF-Token validation for all state-changing operations.

**Frontend**:
```javascript
// On page load, get CSRF token from cookie
const getCsrfToken = () => {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1]
}

// Add to all POST/PUT/DELETE/PATCH requests
const updateJob = async (jobId, data) => {
  const response = await api.post(`/jobs/${jobId}`, data, {
    headers: {
      'X-CSRF-Token': getCsrfToken(),
    }
  })
  return response.data
}
```

**Backend**:
```python
from finder.shared.jwt_security import require_csrf

@app.route("/api/jobs/<int:job_id>", methods=["POST"])
@require_jwt
@require_csrf  # Validates X-CSRF-Token header
def update_job(job_id):
    data = request.json
    # Safe to process
    return {"updated": True}
```

---

### Task 6: AI Token Cost Guardrails
**File**: `src/finder/shared/ai_budget.py`

**What**: Track and enforce AI API usage limits.

**Configuration**:
```python
DEFAULT_DAILY_BUDGET = 5.00      # $5/day per user
DEFAULT_MONTHLY_BUDGET = 100.00  # $100/month per user

TOKEN_COSTS = {
    "gemini": {"input": 0.000075, "output": 0.0003},
    "openai": {"input": 0.0005, "output": 0.0015},
}
```

**Integration**:
```python
from finder.shared.ai_budget import TokenBudgetManager

# Initialize tables
TokenBudgetManager.initialize()

# Before AI call
can_use, reason, remaining = TokenBudgetManager.check_budget(user_id, "gemini")
if not can_use:
    return jsonify({"error": f"Budget exceeded: {reason}"}), 429

# Log usage
TokenBudgetManager.log_usage(
    user_id=user_id,
    provider="gemini",
    input_tokens=2500,
    output_tokens=500,
    model_name="gemini-1.5-flash",
    request_type="resume_parse",
    success=True
)

# Get stats
stats = TokenBudgetManager.get_usage_stats(user_id, days=7)

# Reset quotas (Celery tasks)
@celery_app.task(schedule=crontab(hour=0, minute=0))
def reset_daily_quotas():
    TokenBudgetManager.reset_daily_quotas()

@celery_app.task(schedule=crontab(day_of_month=1, hour=0, minute=0))
def reset_monthly_quotas():
    TokenBudgetManager.reset_monthly_quotas()
```

---

### Task 7: AI Provider Resilience
**File**: `src/finder/core/ai_providers/resilience.py`

**What**: Automatic fallback from Gemini → OpenAI → Template Engine.

**Integration**:
```python
from finder.core.ai_providers.resilience import generate_text

# Simple interface - handles fallback automatically
response = generate_text(
    prompt="Summarize this resume: ...",
    max_tokens=500
)

# If Gemini fails → tries OpenAI
# If OpenAI fails → uses template engine
# Returns structured response or raises final error
```

**Provider Health Tracking**:
```python
from finder.core.ai_providers.resilience import CircuitBreakerState, ProviderStatus

# Check provider health
breaker = CircuitBreakerState("gemini")
status = breaker.get_status()

if status == ProviderStatus.CIRCUIT_OPEN:
    # Provider is temporarily unavailable
    log.warning("Gemini circuit open - using fallback")
elif status == ProviderStatus.DEGRADED:
    # Provider is recovering
    log.info("Gemini degraded - attempting with backoff")
```

---

## Part 3: Infrastructure & Data (Tasks 8-11)

### Task 8: Redis Cache Namespace
**File**: `src/finder/shared/redis_cache.py`

**What**: Organized Redis key namespace for multi-tenancy.

**Configuration**:
```
autoapply:ai:        AI generation cache
autoapply:emb:       Embeddings cache
autoapply:tasks:     Celery task state
autoapply:socket:    Socket.IO messages
autoapply:rate_limit: Rate limiter state
autoapply:session:   User sessions
autoapply:queue:     Queue state
```

**Usage**:
```python
from finder.shared.redis_cache import cache_get, cache_set, get_cache

# Simple interface
cache_set("ai", f"user_{user_id}:prompt", response, ttl_seconds=3600)
result = cache_get("ai", f"user_{user_id}:prompt")

# Or use full API
cache = get_cache()
cache.set("embedding", f"job_{job_id}", embedding_vector, ttl_seconds=86400)
embedding = cache.get("embedding", f"job_{job_id}")

# List operations
cache.append("queue", f"user_{user_id}", job_item)
items = cache.get_list("queue", f"user_{user_id}")

# Namespace operations
cache.clear_namespace("ai")  # Clear all AI cache
```

---

### Task 9: Persistent Scraper Sessions
**File**: `src/finder/core/scraper/session_persistence.py`

**What**: Reuse browser sessions across scraper runs.

**Database Schema**:
```sql
CREATE TABLE scraper_sessions (
    id            INTEGER PRIMARY KEY,
    user_id       TEXT NOT NULL,
    platform      TEXT NOT NULL,      -- linkedin, internshala
    storage_state TEXT,               -- Playwright storage_state JSON
    is_valid      INTEGER,
    last_used     DATETIME,
    expires_at    DATETIME,
    created_at    DATETIME
);
```

**Integration**:
```python
from finder.core.scraper.session_persistence import SessionPersistence, BrowserSessionManager

# Initialize
SessionPersistence.initialize()

# In scraper task
async def scrape_jobs(user_id, platform):
    browser = await playwright.chromium.launch()
    
    # Use session manager
    session_mgr = BrowserSessionManager(user_id, platform)
    page = await session_mgr.get_or_create_page(browser)
    
    # Scrape jobs...
    jobs = await scrape_jobs_on_page(page)
    
    # Save session for next time
    await session_mgr.save_session_state()
    await session_mgr.cleanup()
    
    return jobs

# Cleanup expired sessions (Celery)
@celery_app.task(schedule=crontab(hour=3, minute=0))
def cleanup_scraper_sessions():
    SessionPersistence.cleanup_expired()
```

---

### Task 10: Scraper Safety Layer
**File**: `src/finder/core/scraper/safety_layer.py`

**What**: Rate limiting, domain reputation, adaptive cooldowns.

**Components**:
- **RateLimiter**: Per-domain request throttling
- **RequestBudget**: Daily request limit per user
- **CooldownManager**: Adaptive backoff strategies
- **ScraperHealth**: Metrics tracking

**Integration**:
```python
from finder.core.scraper.safety_layer import (
    RateLimiter, RequestBudget, CooldownManager
)

# Initialize
RateLimiter.initialize()

# Before scraping a domain
can_request, reason, wait_seconds = RateLimiter.can_request(domain)
if not can_request:
    log.warning(f"Rate limited: {reason} - wait {wait_seconds}s")
    time.sleep(wait_seconds)
    return

# Check user's daily budget
has_budget, reason, remaining = RequestBudget.check_budget(user_id)
if not has_budget:
    log.warning(f"Budget exhausted: {reason}")
    return

# After request
try:
    # Scrape domain
    results = await scrape_domain(domain)
    RateLimiter.record_success(domain)
    RequestBudget.consume(user_id, count=1)
except Exception as e:
    # Record error and implement backoff
    RateLimiter.record_error(domain, wait_seconds=10)
    raise
```

---

### Task 11: Embedding Versioning
**File**: `src/finder/shared/embedding_versioning.py`

**What**: Cache embeddings with model version for safe upgrades.

**Configuration**:
```python
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIMENSIONS = "384"
EMBED_MODEL_VERSION = "<auto-computed-hash>"
```

**Integration**:
```python
from finder.shared.embedding_versioning import EmbeddingVersion, EmbeddingCache

# Initialize
EmbeddingVersion.initialize()

# Get or compute embedding
def embed_job_description(job_id, job_text):
    embedding = EmbeddingCache.get_or_compute(
        job_id,
        job_text,
        compute_func=compute_embedding_in_worker,
        version_id=None  # Uses current version
    )
    return embedding

# On model upgrade
new_version = "sentence-transformers/all-MiniLM-L12-v2"
os.environ["EMBED_MODEL"] = new_version

# Invalidate old embeddings
invalidated = EmbeddingVersion.invalidate_old_embeddings()
log.info(f"Invalidated {invalidated} old embedding versions")

# Get stats
stats = EmbeddingVersion.get_version_stats()
```

---

## Part 4: Worker & Observability (Tasks 12-13)

### Task 12: Worker Memory Safety
**File**: `src/finder/shared/worker_memory_safety.py`

**What**: Enforce that heavy models ONLY load in Celery workers.

**Setup - mark worker process**:
```python
# In celery_app.py or worker startup
from finder.shared.worker_memory_safety import mark_as_worker

# Call on worker startup
mark_as_worker()

# Verify
from finder.shared.worker_memory_safety import IS_CELERY_WORKER
assert IS_CELERY_WORKER, "Not marked as worker!"
```

**Usage**:
```python
from finder.shared.worker_memory_safety import require_worker, LazyModelLoader

@require_worker("sentence-transformers")
def compute_embeddings(texts):
    \"\"\"This function ONLY runs in Celery worker.\"\"\"
    model = LazyModelLoader.load_model(
        "embedding-model",
        lambda: SentenceTransformer("all-MiniLM-L6-v2"),
        max_memory_mb=500
    )
    embeddings = model.encode(texts)
    return embeddings

# In Flask: NEVER call compute_embeddings directly
# Instead: enqueue as task
from finder.core.tasks.agent_tasks import embed_texts_task
task = embed_texts_task.delay(texts)  # Returns task ID
# Poll for result...
```

**Memory Monitoring**:
```python
from finder.shared.worker_memory_safety import WorkerHealthCheck

health = WorkerHealthCheck.get_health()
print(health)  # {status: "warning", memory_percent: 75, ...}

if WorkerHealthCheck.should_restart():
    log.warning("Worker memory critical - restart recommended")
```

---

### Task 13: Observability Dashboard
**File**: `src/finder/api/observability.py`

**What**: Real-time metrics via Socket.IO.

**Integration - add to main.py**:
```python
from finder.api.observability import MetricsPoller, emit_dashboard_update

# Start metrics polling on app startup
poller = MetricsPoller(socketio, interval_seconds=5)

@app.before_serving  # Flask 2.3+
def startup():
    poller.start()

@app.teardown_appcontext
def shutdown():
    poller.stop()

# Or use manual emissions in routes
@app.route("/api/metrics/dashboard")
def get_dashboard():
    from finder.api.observability import DashboardAggregator
    return jsonify(DashboardAggregator.get_full_dashboard())

@app.route("/api/metrics/health")
def get_health():
    from finder.api.observability import DashboardAggregator
    return jsonify(DashboardAggregator.get_health_summary())
```

**Frontend - subscribe to metrics**:
```javascript
// src/services/observability.js
import { socket } from './socket'

export function subscribeToMetrics(callback) {
  socket.on('dashboard:update', (metrics) => {
    callback({ type: 'update', metrics })
  })
  
  socket.on('dashboard:health', (health) => {
    callback({ type: 'health', health })
  })
}

// In component
import { subscribeToMetrics } from '../services/observability'

useEffect(() => {
  subscribeToMetrics((event) => {
    if (event.type === 'update') {
      setMetrics(event.metrics)
    } else if (event.type === 'health') {
      setHealth(event.health)
    }
  })
}, [])
```

---

## Part 5: Implementation Order

### Phase 1: Foundation (Week 1)
1. Deploy **Task 1**: Database Abstraction
   - Verify both SQLite/PostgreSQL work
   - Update 5-10 internal queries as examples
   
2. Deploy **Task 2**: JWT Security
   - Set JWT_SECRET env var
   - Update login/logout routes
   - Test with frontend

3. Deploy **Task 3**: Token Revocation
   - Create revoked_tokens table
   - Inject revocation check
   - Test logout flow

### Phase 2: Multi-Tenancy (Week 1-2)
4. Deploy **Task 4**: Multi-Tenant Backfill
   - Run migration script
   - Verify all user_id values populated
   - Create scope helpers
   
5. Deploy **Task 5**: CSRF
   - Add CSRF token to login response
   - Update frontend CSRF handling
   - Test state-changing operations

### Phase 3: AI & Providers (Week 2)
6. Deploy **Task 6**: AI Budget
   - Create ai_usage tables
   - Add budget checks before API calls
   - Set up quota reset tasks

7. Deploy **Task 7**: Provider Resilience
   - Create provider_health table
   - Implement fallback chain
   - Test circuit breaker

### Phase 4: Infrastructure (Week 2-3)
8. Deploy **Task 8**: Redis Namespace
   - Verify Redis connected
   - Update cache keys to use namespaces
   - Test both old and new keys

9. Deploy **Task 9**: Scraper Sessions
   - Create scraper_sessions table
   - Update scraper to use SessionPersistence
   - Test session reuse

10. Deploy **Task 10**: Scraper Safety
    - Create rate_limit tables
    - Add RateLimiter checks
    - Monitor domain reputation

### Phase 5: Data & Workers (Week 3)
11. Deploy **Task 11**: Embedding Versioning
    - Create embedding version tables
    - Update embedding storage code
    - Plan model upgrade process

12. Deploy **Task 12**: Worker Memory
    - Mark Celery workers
    - Move heavy models to workers
    - Monitor worker memory

### Phase 6: Observability (Week 3)
13. Deploy **Task 13**: Observability
    - Start metrics polling
    - Add dashboard endpoints
    - Connect Socket.IO to frontend

14. Deploy **Task 14**: Safety Patterns
    - Run migration script
    - Test rollback scenarios
    - Deploy to staging/production

---

## Part 6: Execution & Validation

### Run all migrations:
```bash
cd finder
python -m src.finder.scripts.hardening_migration --all
```

### Run specific task:
```bash
python -m src.finder.scripts.hardening_migration --task 6
```

### List available:
```bash
python -m src.finder.scripts.hardening_migration --list
```

### Test validation:
```bash
pytest tests/test_hardening/  # Run hardening test suite
```

### Production deployment:
```bash
# 1. Backup database
pg_dump $DATABASE_URL > backup_$(date +%s).sql

# 2. Run migrations
python -m src.finder.scripts.hardening_migration --all

# 3. Run tests
pytest tests/test_hardening/ -v

# 4. Monitor logs
tail -f logs/*.jsonl

# 5. Verify metrics
curl http://localhost:5000/api/metrics/health
```

---

## Part 7: Monitoring & Rollback

### Production Monitoring:
- Watch `/api/metrics/health` for any "critical" status
- Check logs for warnings: `grep WARNING logs/*.jsonl`
- Monitor database queries: slow query logs
- Track memory usage via `/api/metrics/dashboard`

### Rollback Procedure:
1. Stop application: `docker compose down`
2. Restore database: `psql $DATABASE_URL < backup_*.sql`
3. Restart with previous version
4. Investigate logs for root cause

### Safety Verification:
- All migrations are idempotent (can re-run safely)
- All transactions are atomic (all-or-nothing)
- All data is backward compatible
- All APIs maintain backward compatibility

---

## Conclusion

This hardening implementation provides production-grade safety, security, and observability while maintaining the existing architecture. Deploy incrementally, test thoroughly, and monitor closely.

**Questions? Issues?** Check the individual task files in `src/finder/` for detailed implementation notes.
