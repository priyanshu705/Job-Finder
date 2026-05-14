"""
src/finder/core/scraper/safety_layer.py
---------------------------------------
TASK 10: SCRAPER SAFETY LAYER
---------------------------------------
Advanced rate limiting, request budgeting, and health tracking.

Features:
- Domain reputation tracking
- Adaptive cooldowns
- Retry storm prevention
- Request budgeting per domain
- Scraper health metrics
- Automatic backoff strategies

Prevents:
- IP bans
- Rate limit hits
- Aggressive blocking
- Data corruption
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from enum import Enum

from finder.shared.db_abstraction import (
    db_execute,
    db_fetch_one,
    db_fetch_all,
    db_count,
)
from finder.shared.redis_cache import cache_get, cache_set, cache_increment

log = logging.getLogger(__name__)


class DomainReputation(Enum):
    \"\"\"Domain reputation levels.\"\"\"
    EXCELLENT = "excellent"  # Green light - full speed
    GOOD = "good"             # Yellow - normal speed
    FAIR = "fair"             # Orange - slow down
    POOR = "poor"             # Red - stop scraping


class RateLimiter:
    \"\"\"
    Implements per-domain rate limiting with adaptive backoff.
    \"\"\"
    
    SCHEMA = \"\"\"
        CREATE TABLE IF NOT EXISTS domain_rate_limits (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            domain          TEXT NOT NULL UNIQUE,
            requests_today  INTEGER DEFAULT 0,
            last_request    DATETIME,
            last_error      DATETIME,
            error_count_24h INTEGER DEFAULT 0,
            reputation      TEXT DEFAULT 'good',
            cooldown_until  DATETIME,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_domain_cooldown 
            ON domain_rate_limits(cooldown_until);
    \"\"\"
    
    # Rate limit config
    REQUESTS_PER_MINUTE = 2       # Max 2 requests per minute per domain
    REQUESTS_PER_HOUR = 30        # Max 30 per hour
    ERROR_THRESHOLD = 3           # 3 errors triggers slowdown
    
    @staticmethod
    def initialize():
        \"\"\"Create rate limit table.\"\"\"
        try:
            from finder.shared.database import _USE_POSTGRES
            
            if _USE_POSTGRES:
                schema_pg = \"\"\"
                    CREATE TABLE IF NOT EXISTS domain_rate_limits (
                        id              SERIAL PRIMARY KEY,
                        domain          TEXT NOT NULL UNIQUE,
                        requests_today  INTEGER DEFAULT 0,
                        last_request    TIMESTAMP,
                        last_error      TIMESTAMP,
                        error_count_24h INTEGER DEFAULT 0,
                        reputation      TEXT DEFAULT 'good',
                        cooldown_until  TIMESTAMP,
                        updated_at      TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_domain_cooldown 
                        ON domain_rate_limits(cooldown_until);
                \"\"\"
                for stmt in schema_pg.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception:
                            pass
            else:
                for stmt in RateLimiter.SCHEMA.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception:
                            pass
            
            log.info("Rate limiter initialized")
        except Exception as e:
            log.error(f"Rate limiter init failed: {e}")
    
    @staticmethod
    def can_request(domain: str) -> Tuple[bool, str, Optional[float]]:
        \"\"\"
        Check if a domain can be scraped right now.
        
        Args:
            domain: Domain name
            
        Returns:
            (can_request: bool, reason: str, wait_seconds: optional)
        \"\"\"
        try:
            # Check Redis cache first (fast path)
            cache_key = f\"rate:{domain}\"
            cooldown = cache_get("rate_limit", cache_key)
            
            if cooldown:
                wait = float(cooldown)
                return False, f"Domain on cooldown - wait {wait:.0f}s", wait
            
            # Check database
            sql = \"\"\"
                SELECT reputation, cooldown_until, last_request, error_count_24h
                FROM domain_rate_limits
                WHERE domain = ?
            \"\"\"
            row = db_fetch_one(sql, (domain,))
            
            if not row:
                # First request to domain
                RateLimiter._record_request(domain)
                return True, "First request to domain", None
            
            reputation = row.get("reputation", "good")
            cooldown_until = row.get("cooldown_until")
            last_request = row.get("last_request")
            error_count = row.get("error_count_24h", 0)
            
            # Check if in cooldown
            if cooldown_until:
                try:
                    cooldown_time = datetime.fromisoformat(cooldown_until)
                    if datetime.now(timezone.utc) < cooldown_time:
                        wait = (cooldown_time - datetime.now(timezone.utc)).total_seconds()
                        return False, f"Domain on cooldown", wait
                except Exception:
                    pass
            
            # Check reputation-based rate limiting
            if reputation == DomainReputation.POOR.value:
                return False, "Domain reputation POOR - stop scraping", 3600  # 1 hour
            
            if reputation == DomainReputation.FAIR.value:
                # Fair reputation - slow down significantly
                min_interval = 30  # 30 second minimum
            elif reputation == DomainReputation.GOOD.value:
                min_interval = 5   # 5 second minimum
            else:  # EXCELLENT
                min_interval = 1   # 1 second minimum
            
            # Check if enough time has passed since last request
            if last_request:
                try:
                    last = datetime.fromisoformat(last_request)
                    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
                    if elapsed < min_interval:
                        wait = min_interval - elapsed
                        return False, f"Rate limited - wait {wait:.0f}s", wait
                except Exception:
                    pass
            
            RateLimiter._record_request(domain)
            return True, "Request allowed", None
        
        except Exception as e:
            log.warning(f"Rate check failed: {e} - allowing request")
            return True, "Rate check unavailable", None
    
    @staticmethod
    def record_success(domain: str) -> None:
        \"\"\"Record a successful request.\"\"\"
        try:
            sql = \"\"\"
                UPDATE domain_rate_limits
                SET requests_today = requests_today + 1,
                    last_request = CURRENT_TIMESTAMP,
                    reputation = CASE
                        WHEN error_count_24h = 0 THEN 'excellent'
                        WHEN error_count_24h <= 1 THEN 'good'
                        WHEN error_count_24h <= 3 THEN 'fair'
                        ELSE 'poor'
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE domain = ?
            \"\"\"
            db_execute(sql, (domain,))
            
            # Clear cooldown from cache
            cache_set("rate_limit", f\"rate:{domain}\", None, 0)
        
        except Exception as e:
            log.warning(f"Failed to record success: {e}")
    
    @staticmethod
    def record_error(domain: str, wait_seconds: Optional[int] = None) -> None:
        \"\"\"Record a request error and implement adaptive backoff.\"\"\"
        try:
            backoff = wait_seconds or 10  # Default 10s backoff
            cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=backoff)
            
            sql = \"\"\"
                UPDATE domain_rate_limits
                SET error_count_24h = error_count_24h + 1,
                    last_error = CURRENT_TIMESTAMP,
                    cooldown_until = ?,
                    reputation = CASE
                        WHEN error_count_24h + 1 >= 5 THEN 'poor'
                        WHEN error_count_24h + 1 >= 3 THEN 'fair'
                        ELSE 'good'
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE domain = ?
            \"\"\"
            db_execute(sql, (cooldown_until.isoformat(), domain))
            
            # Set cache cooldown (fast path)
            cache_set("rate_limit", f\"rate:{domain}\", backoff, backoff)
            
            log.warning(f"{domain}: error recorded - cooldown for {backoff}s")
        
        except Exception as e:
            log.warning(f"Failed to record error: {e}")
    
    @staticmethod
    def _record_request(domain: str) -> None:
        \"\"\"Record a new request to domain.\"\"\"
        sql = \"\"\"
            INSERT INTO domain_rate_limits (domain, last_request)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(domain) DO UPDATE SET
                last_request = CURRENT_TIMESTAMP
        \"\"\"
        db_execute(sql, (domain,))


class RequestBudget:
    \"\"\"
    Per-user budget for total requests per day.
    Prevents abuse of scraper.
    \"\"\"
    
    # Budget config
    DEFAULT_DAILY_BUDGET = 100  # Max 100 requests per day
    
    @staticmethod
    def check_budget(user_id: str) -> Tuple[bool, str, int]:
        \"\"\"
        Check if user has requests remaining.
        
        Returns:
            (has_budget: bool, reason: str, requests_remaining: int)
        \"\"\"
        try:
            today = datetime.now().date().isoformat()
            cache_key = f\"{user_id}:{today}\"
            
            # Try cache first
            used = cache_get("rate_limit", cache_key, 0)
            used = int(used)
            
            remaining = RequestBudget.DEFAULT_DAILY_BUDGET - used
            
            if remaining <= 0:
                return False, \"Daily request budget exhausted\", 0
            
            return True, \"Budget available\", remaining
        
        except Exception as e:
            log.warning(f\"Budget check failed: {e}\")
            return True, \"Budget check unavailable\", RequestBudget.DEFAULT_DAILY_BUDGET
    
    @staticmethod
    def consume(user_id: str, count: int = 1) -> None:
        \"\"\"Record requests used.\"\"\"
        try:
            today = datetime.now().date().isoformat()
            cache_key = f\"{user_id}:{today}\"
            cache_increment("rate_limit", cache_key, count)
        except Exception as e:
            log.warning(f\"Budget consumption failed: {e}\")


class CooldownManager:
    \"\"\"
    Manages adaptive cooldowns between requests.
    \"\"\"
    
    @staticmethod
    def calculate_cooldown(
        error_count: int,
        reputation: str
    ) -> float:
        \"\"\"
        Calculate adaptive cooldown in seconds.
        
        Args:
            error_count: Number of errors in past 24h
            reputation: Domain reputation level
            
        Returns:
            Cooldown duration in seconds
        \"\"\"
        # Base cooldown
        base = {
            \"excellent\": 1,
            \"good\": 3,
            \"fair\": 10,
            \"poor\": 60,
        }.get(reputation, 5)
        
        # Exponential backoff for errors
        multiplier = min(2 ** error_count, 16)  # Cap at 16x
        
        return base * multiplier
    
    @staticmethod
    def should_retry(
        error_type: str,
        attempt: int,
        max_attempts: int = 3
    ) -> bool:
        \"\"\"
        Determine if a request should be retried.
        \"\"\"
        if attempt >= max_attempts:
            return False
        
        # Retry on transient errors
        retryable = {
            \"timeout\",
            \"connection_reset\",
            \"temporarily_unavailable\",
            \"rate_limit\",
        }
        
        return error_type.lower() in retryable


class ScraperHealth:
    \"\"\"Tracks scraper health metrics.\"\"\"
    
    SCHEMA = \"\"\"
        CREATE TABLE IF NOT EXISTS scraper_metrics (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            domain          TEXT,
            metric_type     TEXT,
            value           REAL,
            recorded_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_metrics_domain_type
            ON scraper_metrics(domain, metric_type);
    \"\"\"
    
    @staticmethod
    def record_metric(domain: str, metric_type: str, value: float) -> None:
        \"\"\"Record a scraper health metric.\"\"\"
        try:
            sql = \"\"\"
                INSERT INTO scraper_metrics (domain, metric_type, value)
                VALUES (?, ?, ?)
            \"\"\"
            db_execute(sql, (domain, metric_type, value))
        except Exception as e:
            log.debug(f\"Metric recording failed: {e}\")
    
    @staticmethod
    def get_health_report(domain: str) -> Dict[str, float]:
        \"\"\"Get health report for a domain.\"\"\"
        try:
            sql = \"\"\"
                SELECT metric_type, AVG(value) as avg_value
                FROM scraper_metrics
                WHERE domain = ?
                AND recorded_at > datetime('now', '-24 hours')
                GROUP BY metric_type
            \"\"\"
            rows = db_fetch_all(sql, (domain,))
            return {r.get(\"metric_type\"): r.get(\"avg_value\") for r in rows}
        except Exception as e:
            log.warning(f\"Health report failed: {e}\")
            return {}
