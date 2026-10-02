"""AI Career Intelligence Platform REST API."""
import os
import secrets
from datetime import timedelta
from flask import Flask, jsonify, request, session
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from dotenv import load_dotenv
from routes import register_blueprints
from utils.error_handler import ApiError

load_dotenv()
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "local-development-only-change-me"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    JSON_SORT_KEYS=False,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None" if os.getenv("FRONTEND_URL", "").startswith("https://") else "Lax",
    SESSION_COOKIE_SECURE=os.getenv("FRONTEND_URL", "").startswith("https://"),
)
origins = [x.strip() for x in os.getenv("FRONTEND_URL", "http://localhost:5500,http://127.0.0.1:5500").split(",") if x.strip()]
CORS(app, supports_credentials=True, origins=origins)
register_blueprints(app)

@app.before_request
def protect_cookie_sessions():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and session.get("user_id"):
        public_auth = {"/api/auth/register", "/api/auth/login", "/api/auth/forgot-password", "/api/auth/reset-password"}
        if request.path not in public_auth:
            supplied = request.headers.get("X-CSRF-Token", "")
            expected = session.get("csrf_token", "")
            if not expected or not secrets.compare_digest(supplied, expected):
                return jsonify(error={"code": "csrf_failed", "message": "Please refresh the page and try again."}), 403

@app.get("/api/health")
def health():
    return jsonify(status="ok", service="AI Career Intelligence API", ai_configured=bool(os.getenv("GEMINI_API_KEY")))

@app.errorhandler(ApiError)
def handle_api_error(error):
    return jsonify(error={"code": error.code, "message": error.message}), error.status

@app.errorhandler(413)
def too_large(_):
    return jsonify(error={"code": "file_too_large", "message": "Please upload a file smaller than 5 MB."}), 413

@app.errorhandler(404)
def not_found(_):
    return jsonify(error={"code": "not_found", "message": "That API route was not found."}), 404

@app.errorhandler(Exception)
def unexpected(error):
    if isinstance(error, HTTPException):
        return jsonify(error={"code": error.name.lower().replace(" ", "_"), "message": error.description}), error.code
    app.logger.exception("Unhandled request error")
    return jsonify(error={"code": "server_error", "message": "Something interrupted the request. Your saved data is safe; please try again."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG") == "1")
