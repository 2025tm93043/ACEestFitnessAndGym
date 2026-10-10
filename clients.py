"""Client input validation (ACEest v1.1)."""
import programs


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
        "adherence": parse_number(payload, "adherence", int, 0, 0, 100, errors),
        "notes": str(payload.get("notes") or "").strip(),
    }
    return clean, errors
