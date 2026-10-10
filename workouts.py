"""Workout, body-metric and BMI helpers (ACEest v2.2.4)."""
from datetime import date

from clients import parse_number

WORKOUT_TYPES = [
    "Strength", "Hypertrophy", "Conditioning", "Cardio", "Mixed", "Mobility"]


def _iso_date(payload, errors):
    raw = str(payload.get("date") or date.today().isoformat()).strip()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        errors.append("date must be YYYY-MM-DD")
        return raw


def validate_workout(payload):
    errors = []
    workout_type = str(payload.get("workout_type") or "").strip()
    if workout_type not in WORKOUT_TYPES:
        errors.append("workout_type must be one of: " + ", ".join(WORKOUT_TYPES))
    clean = {
        "date": _iso_date(payload, errors),
        "workout_type": workout_type,
        "duration_min": parse_number(payload, "duration_min", int, 60, 1, 600, errors),
        "notes": str(payload.get("notes") or "").strip(),
        "exercise": None,
    }
    exercise = payload.get("exercise")
    if isinstance(exercise, dict) and str(exercise.get("name") or "").strip():
        clean["exercise"] = {
            "name": str(exercise["name"]).strip(),
            "sets": parse_number(exercise, "sets", int, 3, 1, 100, errors),
            "reps": parse_number(exercise, "reps", int, 10, 1, 1000, errors),
            "weight": parse_number(exercise, "weight", float, 0.0, 0, 1000, errors),
        }
    return clean, errors


def validate_metrics(payload):
    errors = []

    def optional(field, maximum):
        value = parse_number(payload, field, float, None, 0, maximum, errors)
        return value if value else None

    clean = {
        "date": _iso_date(payload, errors),
        "weight": optional("weight", 500),
        "waist": optional("waist", 300),
        "bodyfat": optional("bodyfat", 100),
    }
    return clean, errors


def bmi_info(height_cm, weight_kg):
    """Return BMI, category and risk note (same bands as the desktop app)."""
    h = height_cm / 100.0
    bmi = round(weight_kg / (h * h), 1)
    if bmi < 18.5:
        category, risk = "Underweight", "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category, risk = "Normal", "Low risk if active and strong."
    elif bmi < 30:
        category, risk = "Overweight", (
            "Moderate risk; focus on adherence and progressive activity.")
    else:
        category, risk = "Obese", (
            "Higher risk; prioritize fat loss, consistency, and supervision.")
    return {"bmi": bmi, "category": category, "risk": risk}
