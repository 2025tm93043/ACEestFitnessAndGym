"""ACEest Fitness & Gym - Flask application."""
import csv
import io

from flask import Flask, Response, jsonify, request

import charts
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

    app.config["CLIENT_STORE"] = []  # in-memory client list (v1.1.2)
    store = app.config["CLIENT_STORE"]

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
        store.append(clean)
        return jsonify({
            "message": f"Client {clean['name']} saved successfully.",
            "client": clean,
        }), 201

    @app.get("/clients")
    def list_clients():
        return jsonify(store)

    @app.get("/clients/export.csv")
    def export_csv():
        if not store:
            return error("No clients to export.", 404)
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Name", "Age", "Weight", "Program", "Adherence", "Notes"])
        for c in store:
            writer.writerow([c["name"], c["age"], c["weight"], c["program"],
                             c["adherence"], c["notes"]])
        return Response(out.getvalue(), mimetype="text/csv", headers={
            "Content-Disposition": "attachment; filename=clients.csv"})

    @app.get("/clients/chart-data")
    def chart_data():
        return jsonify({"labels": [c["name"] for c in store],
                        "adherence": [c["adherence"] for c in store]})

    @app.get("/clients/chart.svg")
    def chart_svg():
        if not store:
            return error("No clients to chart.", 404)
        svg = charts.bar_chart_svg("Client Progress", [c["name"] for c in store],
                                   [c["adherence"] for c in store], "Adherence %")
        return Response(svg, mimetype="image/svg+xml")

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
