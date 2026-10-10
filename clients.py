"""Client validation and persistence helpers."""
from datetime import date

import programs
from db import get_db


def parse_number(payload, field, cast, default, minimum, maximum, errors):
    raw = payload.get(field)
    if raw in (None, ""):
        return default
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        errors.append(f"{field} must be a number")
        return default
    if not (minimum <= value <= maximum):
        errors.append(f"{field} must be between {minimum} and {maximum}")
        return default
    return value


def validate_client(payload):
    """Return (clean_dict, errors_list)."""
    errors = []
    name = str(payload.get("name") or "").strip()
    if not name:
        errors.append("name is required")

    program_name, _ = programs.resolve(payload.get("program"))
    if not payload.get("program"):
        errors.append("program is required")
    elif not program_name:
        errors.append("unknown program")

    def positive(field, cast, maximum):
        value = parse_number(payload, field, cast, None, 0, maximum, errors)
        return value if value else None  # 0 / missing -> NULL, like the desktop app

    expiry = str(payload.get("membership_expiry") or "").strip()
    if expiry:
        try:
            expiry = date.fromisoformat(expiry).isoformat()
        except ValueError:
            errors.append("membership_expiry must be YYYY-MM-DD")

    clean = {
        "name": name,
        "program": program_name,
        "age": positive("age", int, 120),
        "height": positive("height", float, 300),
        "weight": positive("weight", float, 500),
        "target_weight": positive("target_weight", float, 500),
        "target_adherence": positive("target_adherence", int, 100),
        "membership_expiry": expiry or None,
    }
    return clean, errors


def row_to_dict(row):
    return dict(row) if row is not None else None


def get_client(name):
    row = get_db().execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    return row_to_dict(row)


def list_clients():
    rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def save_client(clean):
    """INSERT OR REPLACE a client (upsert by unique name) and return the stored row."""
    clean = dict(clean)
    clean["calories"] = programs.estimate_calories(clean["weight"], clean["program"])
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO clients (name, age, height, weight, program, calories, "
        "target_weight, target_adherence, membership_expiry) VALUES (:name, :age, :height, "
        ":weight, :program, :calories, :target_weight, :target_adherence, "
        ":membership_expiry)",
        clean,
    )
    db.commit()
    return get_client(clean["name"])
