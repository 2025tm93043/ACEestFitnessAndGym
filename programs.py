"""Static program catalogue (4 programs since ACEest v2.2.4).

Legacy short codes FL / MG still resolve (aliases of FL-3 / MG-PPL).
"""

PROGRAMS = {
    "Fat Loss (FL) – 3 day": {
        "code": "FL-3",
        "aliases": ["FL"],
        "description": "3-day full-body fat loss",
        "calorie_factor": 22,
        "color": "#e74c3c",
        "workout": (
            "Mon: Back Squat 5x5 + Core\n"
            "Wed: Bench Press + 21-15-9\n"
            "Fri: Deadlift + Box Jumps"
        ),
        "diet": (
            "Breakfast: Egg Whites + Oats\n"
            "Lunch: Grilled Chicken + Brown Rice\n"
            "Dinner: Fish Curry + Millet Roti\n"
            "Target: ~2000 kcal"
        ),
    },
    "Fat Loss (FL) – 5 day": {
        "code": "FL-5",
        "aliases": [],
        "description": "5-day split, higher volume fat loss",
        "calorie_factor": 24,
        "color": "#e74c3c",
        "workout": (
            "Mon: Back Squat 5x5 + Core\n"
            "Tue: EMOM 20min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: Deadlift + Box Jumps\n"
            "Fri: Zone 2 Cardio 30min"
        ),
        "diet": (
            "Breakfast: Egg Whites + Oats\n"
            "Lunch: Grilled Chicken + Brown Rice\n"
            "Dinner: Fish Curry + Millet Roti\n"
            "Target: ~2200 kcal"
        ),
    },
    "Muscle Gain (MG) – PPL": {
        "code": "MG-PPL",
        "aliases": ["MG"],
        "description": "Push/Pull/Legs hypertrophy",
        "calorie_factor": 35,
        "color": "#2ecc71",
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
        ),
        "diet": (
            "Breakfast: Eggs + Peanut Butter Oats\n"
            "Lunch: Chicken Biryani\n"
            "Dinner: Mutton Curry + Rice\n"
            "Target: ~3200 kcal"
        ),
    },
    "Beginner (BG)": {
        "code": "BG",
        "aliases": [],
        "description": "3-day simple beginner full-body",
        "calorie_factor": 26,
        "color": "#3498db",
        "workout": (
            "Full Body Circuit:\n"
            "- Air Squats\n"
            "- Ring Rows\n"
            "- Push-ups\n"
            "Focus: Technique & Consistency"
        ),
        "diet": (
            "Balanced Tamil Meals\n"
            "Idli / Dosa / Rice + Dal\n"
            "Protein Target: 120g/day"
        ),
    },
}

SITE_METRICS = {
    "capacity_users": 150,
    "area_sqft": 10000,
    "break_even_members": 250,
}


def resolve(identifier):
    """Return (name, program) for a program code or full name (case-insensitive)."""
    if not identifier:
        return None, None
    key = str(identifier).strip().lower()
    for name, data in PROGRAMS.items():
        names = [name.lower(), data["code"].lower()] + [a.lower() for a in data["aliases"]]
        if key in names:
            return name, data
    return None, None


def estimate_calories(weight, program_name):
    """Daily calorie estimate = weight (kg) x program calorie factor."""
    program = PROGRAMS.get(program_name)
    if not program or not weight or weight <= 0:
        return None
    return int(weight * program["calorie_factor"])
