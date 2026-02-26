import os
import time
from flask import Flask, g, request

from .db import close_db, init_db
from .utils import get_request_id, log_event
from .main import register_routes

def create_app():
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = os.environ.get("DATABASE_PATH", "./orders.db")

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.before_request
    def attach_request_context():
        g.request_id = get_request_id()
        g.start_time = time.time()

    @app.after_request
    def log_after(response):
        duration_ms = int((time.time() - g.start_time) * 1000)
        log_event(
            "request.complete",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        response.headers["X-Request-Id"] = g.request_id
        return response

    @app.get("/health")
    def health():
        return {"ok": True}

    # register API routes
    register_routes(app)

    return app