"""SAPL Flask Demo -- main application entry point.

Configures SAPL PEP integration with all 7 constraint handler types
and includes blueprints for basic and constraint enforcement demos.
"""

from __future__ import annotations

import atexit
import os

import structlog
from dotenv import load_dotenv
from flask import Flask, jsonify

from sapl_flask.extension import SaplFlask

from handlers import register_all_handlers
from routes.basic import basic_bp
from routes.constraints import constraints_bp
from routes.services import services_bp
from routes.streaming import streaming_bp

log = structlog.get_logger()

load_dotenv()

app = Flask(__name__)
app.config["SAPL_BASE_URL"] = os.getenv("SAPL_PDP_URL", "http://localhost:8443")
app.config["SAPL_ALLOW_INSECURE_CONNECTIONS"] = True

sapl = SaplFlask(app)
register_all_handlers(sapl)
atexit.register(sapl.close)

app.register_blueprint(basic_bp, url_prefix="/api")
app.register_blueprint(constraints_bp, url_prefix="/api/constraints")
app.register_blueprint(streaming_bp, url_prefix="/api/streaming")
app.register_blueprint(services_bp, url_prefix="/api/services")

log.info("SAPL configured with all constraint handlers registered")


@app.route("/")
def root():
    """Health check / root endpoint."""
    return jsonify({"status": "ok", "application": "SAPL Flask Demo"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port, debug=True)
