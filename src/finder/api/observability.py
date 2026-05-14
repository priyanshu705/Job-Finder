"""
src/finder/api/observability.py
------------------------------
TASK 13: OBSERVABILITY DASHBOARD
------------------------------
Provides real-time metrics and health monitoring via Socket.IO.

Metrics Tracked:
- Queue latency (avg time to apply)
- Task failures and retries
- AI token usage
- Scraper ban incidents
- Worker memory
- Redis health
- Socket.IO connection stats
- Provider failure rates

Updates via Socket.IO for real-time dashboard.
\"\"\"

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from finder.shared.db_abstraction import db_fetch_all, db_fetch_one, db_count
from finder.shared.redis_cache import get_cache
from finder.shared.worker_memory_safety import WorkerHealthCheck

log = logging.getLogger(__name__)


class ObservabilityMetrics:
    \"\"\"Collects and aggregates system metrics.\"\"\"
    
    @staticmethod
    def get_queue_metrics() -> Dict[str, Any]:
        \"\"\"Get queue latency and processing metrics.\"\"\"
        try:
            sql = \"\"\"
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(CAST((julianday('now') - julianday(queued_at)) * 24 * 60 AS FLOAT)) as avg_wait_minutes,
                    MIN(match_score_at_apply) as min_score,
                    MAX(match_score_at_apply) as max_score,
                    AVG(match_score_at_apply) as avg_score
                FROM apply_queue
                WHERE queued_at > datetime('now', '-7 days')
                GROUP BY status
            \"\"\"
            rows = db_fetch_all(sql, ())
            
            return {
                \"by_status\": [dict(r) for r in rows],
                \"timestamp\": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            log.warning(f\"Queue metrics failed: {e}\")
            return {}
    
    @staticmethod
    def get_task_metrics() -> Dict[str, Any]:
        \"\"\"Get task execution metrics.\"\"\"
        try:
            sql = \"\"\"
                SELECT 
                    status,
                    attempts,
                    COUNT(*) as count,
                    SUM(CASE WHEN attempts > 3 THEN 1 ELSE 0 END) as high_retry_count
                FROM apply_queue
                GROUP BY status, attempts
                ORDER BY attempts DESC
            \"\"\"
            rows = db_fetch_all(sql, ())
            
            # Count recent failures
            sql_failures = \"\"\"
                SELECT COUNT(*) as c FROM apply_queue
                WHERE status = 'failed'
                AND updated_at > datetime('now', '-24 hours')
            \"\"\"
            failures = db_count(sql_failures, ())
            
            return {
                \"by_attempt\": [dict(r) for r in rows],
                \"failed_24h\": failures,
                \"timestamp\": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            log.warning(f\"Task metrics failed: {e}\")
            return {}
    
    @staticmethod
    def get_ai_metrics() -> Dict[str, Any]:
        \"\"\"Get AI usage and token metrics.\"\"\"
        try:
            sql = \"\"\"
                SELECT
                    provider,
                    COUNT(*) as request_count,
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output,
                    SUM(estimated_cost) as total_cost,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                FROM ai_usage
                WHERE created_at > datetime('now', '-24 hours')
                GROUP BY provider
            \"\"\"
            rows = db_fetch_all(sql, ())
            
            return {
                \"by_provider\": [dict(r) for r in rows],
                \"timestamp\": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            log.warning(f\"AI metrics failed: {e}\")
            return {}
    
    @staticmethod
    def get_scraper_metrics() -> Dict[str, Any]:
        \"\"\"Get scraper health and incidents.\"\"\"
        try:
            sql = \"\"\"
                SELECT
                    domain,
                    reputation,
                    error_count_24h,
                    requests_today,
                    last_error
                FROM domain_rate_limits
                ORDER BY error_count_24h DESC LIMIT 10
            \"\"\"
            rows = db_fetch_all(sql, ())
            
            # Count ban incidents
            sql_bans = \"\"\"
                SELECT COUNT(*) as c FROM domain_rate_limits
                WHERE reputation = 'poor'
            \"\"\"
            bans = db_count(sql_bans, ())
            
            return {
                \"top_domains\": [dict(r) for r in rows],
                \"banned_domains\": bans,
                \"timestamp\": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            log.warning(f\"Scraper metrics failed: {e}\")
            return {}
    
    @staticmethod
    def get_worker_metrics() -> Dict[str, Any]:
        \"\"\"Get Celery worker health metrics.\"\"\"
        try:
            health = WorkerHealthCheck.get_health()
            
            return {
                \"memory_percent\": health.get(\"memory_percent\"),
                \"memory_mb\": health.get(\"memory_mb\"),
                \"status\": health.get(\"status\"),
                \"loaded_models\": health.get(\"loaded_models\", []),
                \"timestamp\": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            log.warning(f\"Worker metrics failed: {e}\")
            return {}
    
    @staticmethod
    def get_redis_metrics() -> Dict[str, Any]:
        \"\"\"Get Redis cache health.\"\"\"
        try:
            cache = get_cache()
            health = cache.health_check()
            
            return {
                \"status\": health.get(\"status\"),
                \"connected_clients\": health.get(\"connected_clients\"),
                \"used_memory_mb\": health.get(\"used_memory_mb\"),
                \"keyspace_size\": health.get(\"keyspace\"),
                \"timestamp\": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            log.warning(f\"Redis metrics failed: {e}\")
            return {}
    
    @staticmethod
    def get_provider_metrics() -> Dict[str, Any]:
        \"\"\"Get AI provider health tracking.\"\"\"
        try:
            sql = \"\"\"
                SELECT
                    provider,
                    status,
                    failures,
                    successes,
                    last_error,
                    circuit_open_at
                FROM provider_health
                ORDER BY updated_at DESC
            \"\"\"
            rows = db_fetch_all(sql, ())
            
            return {
                \"providers\": [dict(r) for r in rows],
                \"timestamp\": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            log.warning(f\"Provider metrics failed: {e}\")
            return {}


class DashboardAggregator:
    \"\"\"Aggregates all metrics into dashboard view.\"\"\"
    
    @staticmethod
    def get_full_dashboard() -> Dict[str, Any]:
        \"\"\"Get complete dashboard snapshot.\"\"\"
        return {
            \"timestamp\": datetime.now(timezone.utc).isoformat(),
            \"queue\": ObservabilityMetrics.get_queue_metrics(),
            \"tasks\": ObservabilityMetrics.get_task_metrics(),
            \"ai\": ObservabilityMetrics.get_ai_metrics(),
            \"scraper\": ObservabilityMetrics.get_scraper_metrics(),
            \"worker\": ObservabilityMetrics.get_worker_metrics(),
            \"redis\": ObservabilityMetrics.get_redis_metrics(),
            \"providers\": ObservabilityMetrics.get_provider_metrics(),
        }
    
    @staticmethod
    def get_health_summary() -> Dict[str, Any]:
        \"\"\"Get quick health summary for status indicator.\"\"\"
        metrics = DashboardAggregator.get_full_dashboard()
        
        issues = []
        
        # Check worker health
        worker = metrics.get(\"worker\", {})
        if worker.get(\"status\") == \"critical\":
            issues.append({\"type\": \"worker\", \"severity\": \"critical\", \"message\": \"Worker memory critical\"})}
        
        # Check scraper bans
        scraper = metrics.get(\"scraper\", {})
        if scraper.get(\"banned_domains\", 0) > 3:
            issues.append({\"type\": \"scraper\", \"severity\": \"warning\", \"message\": f\"{scraper['banned_domains']} domains banned\"})}
        
        # Check provider status
        providers = metrics.get(\"providers\", {})
        for p in providers.get(\"providers\", []):
            if p.get(\"status\") == \"circuit_open\":
                issues.append({\"type\": \"provider\", \"severity\": \"warning\", \"message\": f\"{p['provider']} circuit open\"})}
        
        # Check Redis
        redis = metrics.get(\"redis\", {})
        if redis.get(\"status\") != \"healthy\":
            issues.append({\"type\": \"redis\", \"severity\": \"error\", \"message\": \"Redis unavailable\"})}
        
        return {
            \"status\": \"critical\" if any(i[\"severity\"] == \"critical\" for i in issues) else \"warning\" if issues else \"healthy\",
            \"issues\": issues,
            \"timestamp\": datetime.now(timezone.utc).isoformat(),
        }


# Socket.IO emission helpers
def emit_dashboard_update(socketio, namespace=\"/api\"):
    \"\"\"Emit dashboard metrics to all connected clients.\"\"\"
    try:
        metrics = DashboardAggregator.get_full_dashboard()
        socketio.emit(\"dashboard:update\", metrics, namespace=namespace)
    except Exception as e:
        log.warning(f\"Dashboard emit failed: {e}\")


def emit_health_update(socketio, namespace=\"/api\"):
    \"\"\"Emit health summary to all connected clients.\"\"\"
    try:
        health = DashboardAggregator.get_health_summary()
        socketio.emit(\"dashboard:health\", health, namespace=namespace)
    except Exception as e:
        log.warning(f\"Health emit failed: {e}\")


class MetricsPoller:
    \"\"\"Background poller that emits metrics periodically.\"\"\"
    
    def __init__(self, socketio, interval_seconds: int = 5):
        self.socketio = socketio
        self.interval = interval_seconds
        self._running = False
    
    def start(self):
        \"\"\"Start background metrics polling.\"\"\"
        import threading
        
        self._running = True
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()
        log.info(f\"Metrics poller started (interval: {self.interval}s)\")
    
    def stop(self):
        \"\"\"Stop background polling.\"\"\"
        self._running = False
        log.info(\"Metrics poller stopped\")
    
    def _poll_loop(self):
        \"\"\"Background polling loop.\"\"\"
        while self._running:
            try:
                emit_dashboard_update(self.socketio)
                emit_health_update(self.socketio)
            except Exception as e:
                log.debug(f\"Polling error: {e}\")
            
            time.sleep(self.interval)
