"""ACEest Fitness & Gym - Flask application."""
from flask import Flask, jsonify

import programs
from version import __version__


def error(message, status):
    return jsonify({"error": message}), status


def create_app(config=None):
    app = Flask(__name__)
    if config:
        app.config.update(config)

    # --- ROUTES-BEGIN ---
    @app.get("/")
    def index():
        return jsonify({"service": "ACEest Fitness & Gym", "version": __version__})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "version": __version__})

    @app.get("/programs")
    def list_programs():
        return jsonify([
            {"code": p["code"], "name": name, "color": p["color"]}
            for name, p in programs.PROGRAMS.items()
        ])

    @app.get("/programs/<code>")
    def get_program(code):
        name, program = programs.resolve(code)
        if not program:
            return error("Program not found", 404)
        return jsonify({"name": name, **program})

    @app.get("/site-metrics")
    def site_metrics():
        return jsonify(programs.SITE_METRICS)
    # --- ROUTES-END ---

    @app.errorhandler(404)
    def not_found(_):
        return error("Not found", 404)

    @app.errorhandler(405)
    def method_not_allowed(_):
        return error("Method not allowed", 405)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
