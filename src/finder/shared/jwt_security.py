"""
src/finder/shared/jwt_security.py
---------------------------------
TASK 2: JWT SECURITY HARDENING + TASK 5: CSRF FLOW
---------------------------------
Production-grade JWT and CSRF security layer.

Features:
- HttpOnly + Secure cookies (NO localStorage JWT)
- Configurable SameSite policy (Strict for production)
- CSRF token generation + validation
- JWT refresh + access token pattern
- Session revocation support (Task 3)
- Structured logging
- Production-safe defaults
"""

import os
import logging
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

import jwt
from flask import request
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production-with-environment-variable")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)
JWT_REFRESH_TOKEN_EXPIRY = timedelta(days=7)

# Cookie Configuration  
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
COOKIE_HTTPONLY = True  # ALWAYS True - never send JWT to JavaScript
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Strict")  # Strict for production
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", None)
COOKIE_PATH = "/"

# CSRF Configuration
CSRF_TOKEN_EXPIRY = timedelta(hours=1)
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "csrf_token"

# Validate configuration
if JWT_SECRET == "change-this-in-production-with-environment-variable":
    if os.getenv("FLASK_ENV") == "production":
        raise ValueError("JWT_SECRET must be set in production!")
    log.warning("JWT_SECRET is default - set JWT_SECRET env var in production")


# ──────────────────────────────────────────────────────────────────────────────
# CSRF TOKEN MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

class CSRFTokenManager:
    """
    Generates and validates CSRF tokens for protecting state-changing operations.
    
    Token Format: {token}|{timestamp}|{signature}
    Signature: HMAC-SHA256 of (token + timestamp)
    """
    
    @staticmethod
    def generate() -> str:
        """Generate a new CSRF token."""
        token = secrets.token_urlsafe(32)
        timestamp = datetime.now(timezone.utc).isoformat()
        signature = CSRFTokenManager._sign(f"{token}|{timestamp}")
        return f"{token}|{timestamp}|{signature}"
    
    @staticmethod
    def _sign(data: str) -> str:
        """Create HMAC-SHA256 signature."""
        return hmac.new(
            JWT_SECRET.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def validate(token: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a CSRF token.
        
        Returns:
            (is_valid, error_reason)
        """
        try:
            parts = token.split("|")
            if len(parts) != 3:
                return False, "Invalid token format"
            
            token_val, timestamp_str, signature = parts
            
            # Verify signature
            expected_sig = CSRFTokenManager._sign(f"{token_val}|{timestamp_str}")
            if not hmac.compare_digest(signature, expected_sig):
                return False, "Invalid signature"
            
            # Check expiration
            timestamp = datetime.fromisoformat(timestamp_str)
            if datetime.now(timezone.utc) - timestamp > CSRF_TOKEN_EXPIRY:
                return False, "Token expired"
            
            return True, None
        
        except Exception as e:
            log.warning(f"CSRF validation failed: {str(e)}")
            return False, str(e)


# ──────────────────────────────────────────────────────────────────────────────
# JWT TOKEN MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

class JWTManager:
    """
    Manages JWT access and refresh tokens.
    
    Access Token: Short-lived (15 min), sent in HttpOnly cookie
    Refresh Token: Long-lived (7 days), sent in HttpOnly cookie
    """
    
    @staticmethod
    def generate_access_token(
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a short-lived access token.
        
        Args:
            user_id: Unique user identifier
            additional_claims: Extra JWT claims (e.g., {"role": "admin"})
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,  # subject (RFC 7519)
            "iat": now,      # issued at
            "exp": now + JWT_ACCESS_TOKEN_EXPIRY,  # expiration
            "type": "access",
            "jti": secrets.token_urlsafe(16),  # JWT ID for revocation
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        log.debug(f"Generated access token for user {user_id}")
        return token
    
    @staticmethod
    def generate_refresh_token(user_id: str) -> str:
        """
        Generate a long-lived refresh token.
        
        Args:
            user_id: Unique user identifier
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + JWT_REFRESH_TOKEN_EXPIRY,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16),  # JWT ID for revocation
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        log.debug(f"Generated refresh token for user {user_id}")
        return token
    
    @staticmethod
    def verify_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Verify and decode a JWT token.
        
        Returns:
            (is_valid, payload, error_reason)
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return True, payload, None
        except jwt.ExpiredSignatureError:
            return False, None, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            log.warning(f"Token verification failed: {str(e)}")
            return False, None, str(e)
    
    @staticmethod
    def get_from_request() -> Optional[str]:
        """Extract JWT token from request (cookie only)."""
        # IMPORTANT: Never check localStorage or Authorization header for JWT
        # Cookies provide automatic CSRF protection via SameSite
        return request.cookies.get("access_token")
    
    @staticmethod
    def get_from_refresh_request() -> Optional[str]:
        """Extract refresh token from request."""
        return request.cookies.get("refresh_token")


# ──────────────────────────────────────────────────────────────────────────────
# COOKIE SETTING HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def set_access_token_cookie(response, access_token: str) -> None:
    """
    Set access token in an HttpOnly, Secure, SameSite cookie.
    
    Args:
        response: Flask response object
        access_token: JWT access token
    """
    response.set_cookie(
        "access_token",
        access_token,
        max_age=int(JWT_ACCESS_TOKEN_EXPIRY.total_seconds()),
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path=COOKIE_PATH,
    )
    log.debug("Set access_token cookie")


def set_refresh_token_cookie(response, refresh_token: str) -> None:
    """
    Set refresh token in an HttpOnly, Secure, SameSite cookie.
    
    Args:
        response: Flask response object
        refresh_token: JWT refresh token
    """
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=int(JWT_REFRESH_TOKEN_EXPIRY.total_seconds()),
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path=COOKIE_PATH,
    )
    log.debug("Set refresh_token cookie")


def set_csrf_token_cookie(response, csrf_token: str) -> None:
    """
    Set CSRF token in a regular (not HttpOnly) cookie.
    Frontend can read this and send it back in X-CSRF-Token header.
    
    Args:
        response: Flask response object
        csrf_token: CSRF token
    """
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=int(CSRF_TOKEN_EXPIRY.total_seconds()),
        secure=COOKIE_SECURE,
        httponly=False,  # Frontend must read this
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path=COOKIE_PATH,
    )
    log.debug("Set csrf_token cookie")


def clear_auth_cookies(response) -> None:
    """Clear all authentication cookies (for logout)."""
    for cookie_name in ["access_token", "refresh_token", CSRF_COOKIE_NAME]:
        response.set_cookie(
            cookie_name,
            "",
            max_age=0,  # Immediate expiration
            secure=COOKIE_SECURE,
            httponly=(cookie_name != CSRF_COOKIE_NAME),
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path=COOKIE_PATH,
        )
    log.debug("Cleared auth cookies")


# ──────────────────────────────────────────────────────────────────────────────
# FLASK ROUTE DECORATORS
# ──────────────────────────────────────────────────────────────────────────────

from functools import wraps
from flask import jsonify

def require_jwt(f):
    """
    Decorator to require valid JWT authentication.
    
    Usage:
        @app.route("/api/protected")
        @require_jwt
        def protected_route():
            user_id = g.user_id
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import g
        
        token = JWTManager.get_from_request()
        if not token:
            return jsonify({"error": "Missing authentication token"}), 401
        
        is_valid, payload, error = JWTManager.verify_token(token)
        if not is_valid:
            return jsonify({"error": f"Invalid token: {error}"}), 401
        
        # Check token hasn't been revoked (see Task 3)
        if _is_token_revoked(payload.get("jti")):
            return jsonify({"error": "Token has been revoked"}), 401
        
        # Store user info in g for use in route
        g.user_id = payload.get("sub")
        g.jwt_payload = payload
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_csrf(f):
    """
    Decorator to require valid CSRF token for state-changing operations.
    
    Usage:
        @app.route("/api/resource", methods=["POST"])
        @require_csrf
        def update_resource():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # CSRF only required for state-changing methods
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return f(*args, **kwargs)
        
        # Get CSRF token from header
        csrf_token = request.headers.get(CSRF_HEADER_NAME)
        if not csrf_token:
            return jsonify({"error": "Missing CSRF token"}), 403
        
        # Validate token
        is_valid, error = CSRFTokenManager.validate(csrf_token)
        if not is_valid:
            return jsonify({"error": f"Invalid CSRF token: {error}"}), 403
        
        log.debug(f"CSRF validation passed for {request.method} {request.path}")
        return f(*args, **kwargs)
    
    return decorated_function


# ──────────────────────────────────────────────────────────────────────────────
# TOKEN REVOCATION (Task 3 integration)
# ──────────────────────────────────────────────────────────────────────────────

def _is_token_revoked(jti: str) -> bool:
    """
    Check if a token has been revoked (Task 3).
    Placeholder for now - implemented in revocation module.
    """
    # TODO: Check revoked_tokens table
    return False


def revoke_token(jti: str, user_id: str, reason: str = "unknown") -> None:
    """
    Revoke a specific JWT token (Task 3).
    """
    log.info(f"Revoking token {jti} for user {user_id}: {reason}")
    # TODO: Insert into revoked_tokens table
    pass
