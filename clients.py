"""Client validation and persistence helpers."""
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

    clean = {
        "name": name,
        "program": program_name,
        "age": parse_number(payload, "age", int, 0, 0, 120, errors),
        "weight": parse_number(payload, "weight", float, 0.0, 0, 500, errors),
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
        "INSERT OR REPLACE INTO clients (name, age, weight, program, calories) "
        "VALUES (:name, :age, :weight, :program, :calories)",
        clean,
    )
    db.commit()
    return get_client(clean["name"])
