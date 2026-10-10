"""ACEest Fitness & Gym - Flask application."""
import csv
import io
import os
from datetime import datetime

from flask import Flask, Response, g, jsonify, request
from werkzeug.security import check_password_hash

import ai_program
import auth
import charts
import clients
import db
import programs
import reports
import workouts
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
    app.config["SECRET_KEY"] = os.environ.get("ACEEST_SECRET_KEY", "dev-only-change-me")
    app.config["REQUIRE_AUTH"] = True
    if config:
        app.config.update(config)
    db.init_app(app)

    public_endpoints = {"index", "health", "login"}

    @app.before_request
    def require_login():
        if (not app.config["REQUIRE_AUTH"] or request.endpoint is None
                or request.endpoint in public_endpoints):
            return None
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        user = auth.verify_token(app.config["SECRET_KEY"], token)
        if not user:
            return error("Authentication required", 401)
        g.user = user
        return None

    # --- ROUTES-BEGIN ---
    @app.get("/")
    def index():
        return jsonify({"service": "ACEest Fitness & Gym", "version": __version__})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "version": __version__})

    @app.post("/login")
    def login():
        payload = json_body() or {}
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "").strip()
        row = db.get_db().execute(
            "SELECT password, role FROM users WHERE username=?", (username,)).fetchone()
        if not row or not check_password_hash(row["password"], password):
            return error("Invalid credentials", 401)
        token = auth.make_token(app.config["SECRET_KEY"], username, row["role"])
        return jsonify({"token": token, "username": username, "role": row["role"]})

    @app.get("/me")
    def me():
        return jsonify(g.user)

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
        conn = db.get_db()
        weeks, avg = conn.execute(
            "SELECT COUNT(*), AVG(adherence) FROM progress WHERE client_name=?", (name,)
        ).fetchone()
        last = conn.execute(
            "SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name=? "
            "ORDER BY date DESC, id DESC LIMIT 1", (name,)).fetchone()
        goals = []
        if client["target_weight"]:
            goals.append(f"Target Weight: {client['target_weight']} kg")
        if client["target_adherence"]:
            goals.append(f"Target Adherence: {client['target_adherence']}%")
        _, program = programs.resolve(client["program"])
        client["summary"] = {
            "program_notes": program["description"] if program else "",
            "goals": "; ".join(goals) if goals else "None",
            "weeks_logged": weeks,
            "average_adherence": round(avg, 1) if avg is not None else 0,
            "last_metrics": dict(last) if last else None,
        }
        return jsonify(client)

    @app.get("/clients/<name>/bmi")
    def client_bmi(name):
        client = clients.get_client(name)
        if not client:
            return error("Client not found", 404)
        if not client["height"] or not client["weight"]:
            return error("Enter valid height and weight first", 400)
        info = workouts.bmi_info(client["height"], client["weight"])
        return jsonify({"client": name, **info})

    @app.post("/clients/<name>/ai-program")
    def ai_program_route(name):
        client = clients.get_client(name)
        if not client:
            return error("Client not found", 404)
        payload = json_body() or {}
        experience = str(payload.get("experience") or "").strip().lower()
        if experience not in ai_program.LEVELS:
            return error("Invalid experience level (beginner/intermediate/advanced)", 400)
        focus, plan = ai_program.generate(client["program"], experience, payload.get("seed"))
        return jsonify({"client": name, "experience": experience, "focus": focus,
                        "plan": plan})

    @app.get("/clients/<name>/report.pdf")
    def client_report(name):
        client = clients.get_client(name)
        if not client:
            return error("Client not found", 404)
        return Response(reports.client_report_pdf(client), mimetype="application/pdf", headers={
            "Content-Disposition": f"attachment; filename={name}_report.pdf"})

    @app.post("/clients/<name>/workouts")
    def log_workout(name):
        if not clients.get_client(name):
            return error("Client not found", 404)
        payload = json_body()
        if payload is None:
            return error("JSON body required", 400)
        clean, problems = workouts.validate_workout(payload)
        if problems:
            return error("Invalid workout", 400, problems)
        conn = db.get_db()
        cur = conn.execute(
            "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, clean["date"], clean["workout_type"], clean["duration_min"], clean["notes"]))
        ex = clean["exercise"]
        if ex:
            conn.execute(
                "INSERT INTO exercises (workout_id, name, sets, reps, weight) "
                "VALUES (?, ?, ?, ?, ?)",
                (cur.lastrowid, ex["name"], ex["sets"], ex["reps"], ex["weight"]))
        conn.commit()
        return jsonify({"message": "Workout logged successfully", "id": cur.lastrowid}), 201

    @app.get("/clients/<name>/workouts")
    def workout_history(name):
        if not clients.get_client(name):
            return error("Client not found", 404)
        conn = db.get_db()
        rows = conn.execute(
            "SELECT id, date, workout_type, duration_min, notes FROM workouts "
            "WHERE client_name=? ORDER BY date DESC, id DESC", (name,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["exercises"] = [dict(e) for e in conn.execute(
                "SELECT name, sets, reps, weight FROM exercises WHERE workout_id=? "
                "ORDER BY id", (row["id"],))]
            result.append(item)
        return jsonify(result)

    @app.post("/clients/<name>/metrics")
    def log_metrics(name):
        if not clients.get_client(name):
            return error("Client not found", 404)
        payload = json_body()
        if payload is None:
            return error("JSON body required", 400)
        clean, problems = workouts.validate_metrics(payload)
        if problems:
            return error("Invalid metrics", 400, problems)
        conn = db.get_db()
        conn.execute(
            "INSERT INTO metrics (client_name, date, weight, waist, bodyfat) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, clean["date"], clean["weight"], clean["waist"], clean["bodyfat"]))
        conn.commit()
        return jsonify({"message": "Metrics logged successfully", **clean}), 201

    @app.get("/clients/<name>/metrics")
    def metrics_history(name):
        if not clients.get_client(name):
            return error("Client not found", 404)
        rows = db.get_db().execute(
            "SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name=? "
            "ORDER BY date, id", (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/clients/<name>/metrics/weight-chart.svg")
    def weight_chart(name):
        if not clients.get_client(name):
            return error("Client not found", 404)
        rows = db.get_db().execute(
            "SELECT date, weight FROM metrics WHERE client_name=? AND weight IS NOT NULL "
            "ORDER BY date, id", (name,)).fetchall()
        if not rows:
            return error("No weight metrics available for this client", 404)
        values = [r["weight"] for r in rows]
        svg = charts.line_chart_svg(
            f"Weight Trend - {name}", [r["date"] for r in rows], values, "Weight (kg)",
            ymin=min(values) - 2, ymax=max(values) + 2, color="#ffa500")
        return Response(svg, mimetype="image/svg+xml")

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
