"""ACEest Fitness & Gym - Flask application."""
import csv
import io
import os
from datetime import datetime

from flask import Flask, Response, jsonify, request

import charts
import clients
import db
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
    app.config["DATABASE"] = os.environ.get("ACEEST_DB", "aceest_fitness.db")
    if config:
        app.config.update(config)
    db.init_app(app)

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

    # ---------- clients (SQLite) ----------
    @app.post("/clients")
    def save_client():
        payload = json_body()
        if payload is None:
            return error("JSON body required", 400)
        clean, problems = clients.validate_client(payload)
        if problems:
            return error("Name and Program required", 400, problems)
        return jsonify({"message": "Client data saved",
                        "client": clients.save_client(clean)}), 201

    @app.get("/clients")
    def list_clients():
        return jsonify(clients.list_clients())

    @app.get("/clients/export.csv")
    def export_csv():
        rows = clients.list_clients()
        if not rows:
            return error("No clients to export.", 404)
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Name", "Age", "Weight", "Program", "Calories"])
        for c in rows:
            writer.writerow([c["name"], c["age"], c["weight"], c["program"], c["calories"]])
        return Response(out.getvalue(), mimetype="text/csv", headers={
            "Content-Disposition": "attachment; filename=clients.csv"})

    def latest_adherence():
        rows = db.get_db().execute(
            "SELECT client_name, adherence FROM progress WHERE id IN "
            "(SELECT MAX(id) FROM progress GROUP BY client_name) ORDER BY client_name"
        ).fetchall()
        return [r["client_name"] for r in rows], [r["adherence"] for r in rows]

    @app.get("/clients/chart-data")
    def chart_data():
        labels, values = latest_adherence()
        return jsonify({"labels": labels, "adherence": values})

    @app.get("/clients/chart.svg")
    def chart_svg():
        labels, values = latest_adherence()
        if not labels:
            return error("No progress data to chart.", 404)
        svg = charts.bar_chart_svg("Client Progress", labels, values, "Adherence %")
        return Response(svg, mimetype="image/svg+xml")

    @app.get("/clients/<name>")
    def load_client(name):
        client = clients.get_client(name)
        if not client:
            return error("Client not found", 404)
        return jsonify(client)

    @app.post("/clients/<name>/progress")
    def save_progress(name):
        if not clients.get_client(name):
            return error("Client not found", 404)
        payload = json_body()
        if payload is None:
            return error("JSON body required", 400)
        problems = []
        adherence = clients.parse_number(payload, "adherence", int, None, 0, 100, problems)
        if adherence is None and not problems:
            problems.append("adherence is required")
        if problems:
            return error("Invalid progress", 400, problems)
        week = datetime.now().strftime("Week %U - %Y")
        conn = db.get_db()
        conn.execute("INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
                     (name, week, adherence))
        conn.commit()
        return jsonify({"message": "Weekly progress logged", "client": name,
                        "week": week, "adherence": adherence}), 201

    @app.get("/clients/<name>/progress")
    def get_progress(name):
        if not clients.get_client(name):
            return error("Client not found", 404)
        rows = db.get_db().execute(
            "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id", (name,)
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/clients/<name>/progress/chart.svg")
    def progress_chart(name):
        if not clients.get_client(name):
            return error("Client not found", 404)
        rows = db.get_db().execute(
            "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id", (name,)
        ).fetchall()
        if not rows:
            return error("No progress data available for this client", 404)
        svg = charts.line_chart_svg(
            f"Weekly Adherence Progress - {name}", [r["week"] for r in rows],
            [r["adherence"] for r in rows], "Adherence (%)", ymin=0, ymax=100)
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
