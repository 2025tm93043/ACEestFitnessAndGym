"""ACEest Fitness & Gym - Flask application."""
from flask import Flask, jsonify, request

import clients
import programs
from version import __version__


def error(message, status, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


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

    @app.get("/programs/<code>/calories")
    def program_calories(code):
        name, _ = programs.resolve(code)
        if not name:
            return error("Program not found", 404)
        try:
            weight = float(request.args.get("weight", ""))
        except ValueError:
            return error("weight (kg) query parameter is required", 400)
        if weight <= 0:
            return error("weight must be greater than 0", 400)
        return jsonify({
            "program": name,
            "weight": weight,
            "calories": programs.estimate_calories(weight, name),
        })

    @app.post("/clients")
    def save_client():
        payload = json_body()
        if payload is None:
            return error("JSON body required", 400)
        clean, problems = clients.validate_client(payload)
        if problems:
            return error("Please fill client name and program.", 400, problems)
        clean["calories"] = programs.estimate_calories(clean["weight"], clean["program"])
        return jsonify({
            "message": f"Client {clean['name']} saved successfully.",
            "client": clean,
        }), 201

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
