"""
src/finder/api/auth.py
---------------------
PHASE A: JWT Authentication + Multi-User Support

Authentication endpoints for SaaS multi-user support.
"""

import logging
from flask import Blueprint, request, jsonify, make_response, g
from werkzeug.security import generate_password_hash, check_password_hash

from finder.shared.database import get_db
from finder.shared.jwt_security import (
    JWTManager,
    CSRFTokenManager,
    require_jwt,
    set_access_token_cookie,
    set_refresh_token_cookie,
    set_csrf_token_cookie,
    clear_auth_cookies,
)

log = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    Register new user.

    Request JSON:
        email (str): User email
        password (str): Password (min 8 chars)
        full_name (str): Full name (optional)

    Returns:
        201: User created + JWT cookies set
        400: Invalid input
        409: Email already exists
    """
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()

    # Validate input
    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400

    if not password or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    db = get_db()

    # Check if user exists
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    # Create user
    password_hash = generate_password_hash(password, method="pbkdf2:sha256")
    cursor = db.execute(
        "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
        (email, password_hash, full_name),
    )
    db.commit()
    user_id = cursor.lastrowid

    log.info(f"User registered: {email} (id={user_id})")

    # Generate tokens
    response = make_response(
        {"status": "registered", "user_id": user_id, "email": email}, 201
    )

    access_token = JWTManager.generate_access_token(str(user_id))
    refresh_token = JWTManager.generate_refresh_token(str(user_id))
    csrf_token = CSRFTokenManager.generate()

    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    set_csrf_token_cookie(response, csrf_token)

    return response


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user.

    Request JSON:
        email (str): User email
        password (str): Password

    Returns:
        200: Authenticated + JWT cookies set
        400: Missing credentials
        401: Invalid credentials
    """
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    db = get_db()
    user = db.execute(
        "SELECT id, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        log.warning(f"Failed login attempt: {email}")
        return jsonify({"error": "Invalid credentials"}), 401

    # Update last login
    db.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
    db.commit()

    log.info(f"User logged in: {email}")

    # Generate tokens
    response = make_response({"status": "authenticated", "user_id": user["id"]})

    access_token = JWTManager.generate_access_token(str(user["id"]))
    refresh_token = JWTManager.generate_refresh_token(str(user["id"]))
    csrf_token = CSRFTokenManager.generate()

    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    set_csrf_token_cookie(response, csrf_token)

    return response, 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    Refresh access token using refresh token.

    Uses refresh token from cookie to issue new access token.

    Returns:
        200: New access token issued
        401: Invalid/expired refresh token
    """
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "No refresh token"}), 401

    is_valid, payload, error = JWTManager.verify_token(refresh_token)
    if not is_valid or payload.get("type") != "refresh":
        return jsonify({"error": f"Invalid refresh token: {error}"}), 401

    user_id = payload.get("sub")
    response = make_response({"status": "refreshed"})

    access_token = JWTManager.generate_access_token(user_id)
    set_access_token_cookie(response, access_token)

    log.debug(f"Token refreshed for user {user_id}")
    return response, 200


@auth_bp.route("/logout", methods=["POST"])
@require_jwt
def logout():
    """
    Logout user (clear auth cookies).

    Returns:
        200: Logged out
    """
    response = make_response({"status": "logged out"})
    clear_auth_cookies(response)
    log.info(f"User logged out: {g.user_id}")
    return response, 200


@auth_bp.route("/profile", methods=["GET"])
@require_jwt
def profile():
    """
    Get current user profile.

    Returns:
        200: User profile
        404: User not found
    """
    db = get_db()
    user = db.execute(
        "SELECT id, email, full_name, created_at, last_login FROM users WHERE id = ?",
        (int(g.user_id),),
    ).fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return (
        jsonify(
            {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "created_at": user["created_at"],
                "last_login": user["last_login"],
            }
        ),
        200,
    )


@auth_bp.route("/csrf-token", methods=["GET"])
def get_csrf_token():
    """
    Get a new CSRF token.

    Frontend calls this to refresh CSRF token before state-changing operations.

    Returns:
        200: CSRF token in cookie + response body
    """
    csrf_token = CSRFTokenManager.generate()
    response = make_response({"csrf_token": csrf_token})
    set_csrf_token_cookie(response, csrf_token)
    return response, 200


@auth_bp.route("/validate", methods=["POST"])
@require_jwt
def validate():
    """
    Validate current JWT token.

    Used by frontend to check if session is still valid.

    Returns:
        200: Token valid + user info
        401: Token invalid
    """
    return (
        jsonify(
            {
                "valid": True,
                "user_id": g.user_id,
                "email": g.jwt_payload.get("email"),
            }
        ),
        200,
    )
