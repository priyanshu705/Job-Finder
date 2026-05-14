"""
src/finder/shared/ai_budget.py
------------------------------
TASK 6: AI TOKEN COST GUARDRAILS
------------------------------
Tracks and enforces AI token usage limits across providers.

Features:
- Per-user daily/monthly quotas
- Provider-level tracking (Gemini, OpenAI, etc.)
- Token cost estimation
- Abuse prevention
- Graceful quota exceeded handling
- Structured logging
"""

import logging
import os
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Dict, Any

from finder.shared.db_abstraction import (
    db_execute,
    db_fetch_one,
    db_fetch_all,
    db_count,
    db_table_exists,
)
from finder.shared.database import _USE_POSTGRES

log = logging.getLogger(__name__)

# Token cost estimation (rough - refine based on actual usage)
TOKEN_COSTS = {
    "gemini": {
        "input": 0.000075,   # $0.075 per 1M input tokens
        "output": 0.0003,    # $0.3 per 1M output tokens
        "batch_discount": 0.5,  # 50% discount for batch processing
    },
    "openai": {
        "input": 0.0005,     # $0.50 per 1M input tokens
        "output": 0.0015,    # $1.50 per 1M output tokens  
        "batch_discount": 0.5,
    },
}

# Default quotas (adjust based on business model)
DEFAULT_DAILY_BUDGET = 5.00  # $5/day
DEFAULT_MONTHLY_BUDGET = 100.00  # $100/month


class TokenBudgetManager:
    """
    Manages AI token usage and cost tracking.
    
    Tables:
    - ai_usage: Tracks each API call
    - ai_quotas: User-specific quota settings
    
    Queries are scoped per user (multi-tenant safe).
    """
    
    SCHEMA = """
        CREATE TABLE IF NOT EXISTS ai_usage (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            provider        TEXT NOT NULL,
            model_name      TEXT,
            input_tokens    INTEGER DEFAULT 0,
            output_tokens   INTEGER DEFAULT 0,
            estimated_cost  REAL DEFAULT 0.0,
            request_type    TEXT,
            success         INTEGER DEFAULT 1,
            error_message   TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS ai_quotas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL UNIQUE,
            provider        TEXT,
            daily_budget    REAL DEFAULT 5.0,
            monthly_budget  REAL DEFAULT 100.0,
            daily_used      REAL DEFAULT 0.0,
            monthly_used    REAL DEFAULT 0.0,
            daily_reset_at  DATE DEFAULT CURRENT_DATE,
            monthly_reset_at DATE DEFAULT CURRENT_DATE,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_usage_user ON ai_usage(user_id);
        CREATE INDEX IF NOT EXISTS idx_usage_provider ON ai_usage(provider);
        CREATE INDEX IF NOT EXISTS idx_usage_date ON ai_usage(created_at);
        CREATE INDEX IF NOT EXISTS idx_usage_success ON ai_usage(success);
    """
    
    @staticmethod
    def initialize():
        """Create AI usage tables if they don't exist."""
        try:
            if _USE_POSTGRES:
                # PostgreSQL version
                schema_pg = """
                    CREATE TABLE IF NOT EXISTS ai_usage (
                        id              SERIAL PRIMARY KEY,
                        user_id         TEXT NOT NULL,
                        provider        TEXT NOT NULL,
                        model_name      TEXT,
                        input_tokens    INTEGER DEFAULT 0,
                        output_tokens   INTEGER DEFAULT 0,
                        estimated_cost  REAL DEFAULT 0.0,
                        request_type    TEXT,
                        success         INTEGER DEFAULT 1,
                        error_message   TEXT,
                        created_at      TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE IF NOT EXISTS ai_quotas (
                        id              SERIAL PRIMARY KEY,
                        user_id         TEXT NOT NULL UNIQUE,
                        provider        TEXT,
                        daily_budget    REAL DEFAULT 5.0,
                        monthly_budget  REAL DEFAULT 100.0,
                        daily_used      REAL DEFAULT 0.0,
                        monthly_used    REAL DEFAULT 0.0,
                        daily_reset_at  DATE DEFAULT CURRENT_DATE,
                        monthly_reset_at DATE DEFAULT CURRENT_DATE,
                        updated_at      TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_usage_user ON ai_usage(user_id);
                    CREATE INDEX IF NOT EXISTS idx_usage_provider ON ai_usage(provider);
                    CREATE INDEX IF NOT EXISTS idx_usage_date ON ai_usage(created_at);
                    CREATE INDEX IF NOT EXISTS idx_usage_success ON ai_usage(success);
                """
                for stmt in schema_pg.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception as e:
                            log.debug(f"DDL skipped: {e}")
            else:
                # SQLite version
                for stmt in TokenBudgetManager.SCHEMA.split(";"):
                    if stmt.strip():
                        try:
                            db_execute(stmt.strip(), ())
                        except Exception as e:
                            log.debug(f"DDL skipped: {e}")
            
            log.info("AI budget tracking tables initialized")
        except Exception as e:
            log.error(f"Failed to initialize AI budget tables: {e}")
            raise
    
    @staticmethod
    def estimate_cost(
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> float:
        """
        Estimate API call cost based on token counts.
        
        Args:
            provider: "gemini" or "openai"
            input_tokens: Tokens sent to API
            output_tokens: Tokens returned from API
            
        Returns:
            Estimated cost in USD
        """
        try:
            costs = TOKEN_COSTS.get(provider.lower(), {})
            if not costs:
                log.warning(f"Unknown provider: {provider}")
                return 0.0
            
            input_cost = (input_tokens / 1_000_000) * costs.get("input", 0)
            output_cost = (output_tokens / 1_000_000) * costs.get("output", 0)
            
            total = input_cost + output_cost
            return round(total, 6)
        except Exception as e:
            log.error(f"Cost estimation failed: {e}")
            return 0.0
    
    @staticmethod
    def log_usage(
        user_id: str,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model_name: Optional[str] = None,
        request_type: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log AI API usage for a user.
        
        Args:
            user_id: User making the request
            provider: API provider (gemini, openai)
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            model_name: Model name used
            request_type: Type of request (resume_parse, match_score, etc.)
            success: Whether request succeeded
            error_message: Error details if failed
        """
        try:
            # Estimate cost
            estimated_cost = TokenBudgetManager.estimate_cost(
                provider, input_tokens, output_tokens
            )
            
            # Insert usage record
            sql = """
                INSERT INTO ai_usage
                (user_id, provider, input_tokens, output_tokens, estimated_cost,
                 model_name, request_type, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            db_execute(sql, (
                user_id, provider, input_tokens, output_tokens, estimated_cost,
                model_name, request_type, int(success), error_message
            ))
            
            # Update user quota
            TokenBudgetManager._update_quota(user_id, provider, estimated_cost)
            
            log.debug(
                f"Logged {provider} usage for user {user_id}: "
                f"{input_tokens} in, {output_tokens} out, ${estimated_cost:.4f}"
            )
        except Exception as e:
            log.error(f"Failed to log AI usage: {e}")
    
    @staticmethod
    def _update_quota(user_id: str, provider: str, cost: float) -> None:
        """Update user's daily/monthly quota consumption."""
        try:
            today = date.today().isoformat()
            month_start = date(date.today().year, date.today().month, 1).isoformat()
            
            # Ensure quota record exists
            sql = "SELECT id FROM ai_quotas WHERE user_id = ?"
            if not db_fetch_one(sql, (user_id,)):
                sql = """
                    INSERT INTO ai_quotas
                    (user_id, provider, daily_budget, monthly_budget)
                    VALUES (?, ?, ?, ?)
                """
                db_execute(sql, (
                    user_id, provider,
                    DEFAULT_DAILY_BUDGET,
                    DEFAULT_MONTHLY_BUDGET
                ))
            
            # Update daily/monthly usage
            sql = """
                UPDATE ai_quotas
                SET daily_used = daily_used + ?,
                    monthly_used = monthly_used + ?,
                    daily_reset_at = ?,
                    monthly_reset_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """
            db_execute(sql, (cost, cost, today, month_start, user_id))
        
        except Exception as e:
            log.warning(f"Failed to update quota: {e}")
    
    @staticmethod
    def check_budget(user_id: str, provider: str) -> tuple:
        """
        Check if user has budget remaining.
        
        Args:
            user_id: User ID
            provider: Provider (gemini, openai)
            
        Returns:
            (can_proceed: bool, reason: str)
        """
        try:
            # Get or create quota record
            sql = "SELECT * FROM ai_quotas WHERE user_id = ?"
            quota = db_fetch_one(sql, (user_id,))
            
            if not quota:
                # First time user - grant full budget
                return True, "First use - budget granted"
            
            # Check daily budget
            daily_used = float(quota.get("daily_used", 0))
            daily_budget = float(quota.get("daily_budget", DEFAULT_DAILY_BUDGET))
            
            if daily_used >= daily_budget:
                return False, f"Daily budget exceeded: ${daily_used:.2f}/${daily_budget:.2f}"
            
            # Check monthly budget
            monthly_used = float(quota.get("monthly_used", 0))
            monthly_budget = float(quota.get("monthly_budget", DEFAULT_MONTHLY_BUDGET))
            
            if monthly_used >= monthly_budget:
                return False, f"Monthly budget exceeded: ${monthly_used:.2f}/${monthly_budget:.2f}"
            
            return True, "Within budget"
        
        except Exception as e:
            log.error(f"Budget check failed: {e}")
            # Fail open on error
            return True, "Budget check unavailable (proceeding safely)"
    
    @staticmethod
    def get_usage_stats(user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get AI usage statistics for a user."""
        try:
            # Last N days usage
            sql = f"""
                SELECT provider, COUNT(*) as requests, 
                       SUM(input_tokens) as total_input,
                       SUM(output_tokens) as total_output,
                       SUM(estimated_cost) as total_cost,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                FROM ai_usage
                WHERE user_id = ?
                AND created_at > datetime('now', '-{days} days')
                GROUP BY provider
            """
            rows = db_fetch_all(sql, (user_id,))
            
            # Current quota
            sql = "SELECT * FROM ai_quotas WHERE user_id = ?"
            quota = db_fetch_one(sql, (user_id,))
            
            return {
                "user_id": user_id,
                "period_days": days,
                "by_provider": [dict(r) for r in rows],
                "quota": dict(quota) if quota else None,
            }
        except Exception as e:
            log.error(f"Failed to get usage stats: {e}")
            return {}
    
    @staticmethod
    def reset_daily_quotas() -> int:
        """
        Reset daily quotas at start of day.
        Should be called via Celery task daily.
        
        Returns:
            Number of quotas reset
        """
        try:
            today = date.today().isoformat()
            sql = """
                UPDATE ai_quotas
                SET daily_used = 0.0, daily_reset_at = ?
                WHERE daily_reset_at < ?
            """
            db_execute(sql, (today, today))
            
            count = db_count("SELECT COUNT(*) as c FROM ai_quotas WHERE daily_reset_at = ?", (today,))
            log.info(f"Reset {count} daily quotas")
            return count
        except Exception as e:
            log.warning(f"Failed to reset daily quotas: {e}")
            return 0
    
    @staticmethod
    def reset_monthly_quotas() -> int:
        """
        Reset monthly quotas at start of month.
        Should be called via Celery task on 1st of month.
        
        Returns:
            Number of quotas reset
        """
        try:
            month_start = date(date.today().year, date.today().month, 1).isoformat()
            sql = """
                UPDATE ai_quotas
                SET monthly_used = 0.0, monthly_reset_at = ?
                WHERE monthly_reset_at < ?
            """
            db_execute(sql, (month_start, month_start))
            
            count = db_count(
                "SELECT COUNT(*) as c FROM ai_quotas WHERE monthly_reset_at = ?",
                (month_start,)
            )
            log.info(f"Reset {count} monthly quotas")
            return count
        except Exception as e:
            log.warning(f"Failed to reset monthly quotas: {e}")
            return 0
