"""
src/finder/shared/response.py
----------------------------
Standard JSON response helpers for Flask API routes.
"""

from flask import jsonify


def success_response(message: str = "Success", data=None, status_code: int = 200):
    payload = {
        "status": "success",
        "message": message,
        "data": data,
    }
    return jsonify(payload), status_code


def error_response(code: str, message: str, status_code: int = 400):
    payload = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }
    return jsonify(payload), status_code
