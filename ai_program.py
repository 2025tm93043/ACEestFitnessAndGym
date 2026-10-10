"""Random-based workout program generator (the desktop 'Generate AI Program', v3.1.2)."""
import random

EXERCISES = {
    "Strength": ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up", "Barbell Row"],
    "Hypertrophy": ["Leg Press", "Incline Dumbbell Press", "Lat Pulldown", "Lateral Raise",
                    "Bicep Curl", "Tricep Extension"],
    "Conditioning": ["Running", "Cycling", "Rowing", "Burpees", "Jump Rope",
                     "Kettlebell Swings"],
    "Full Body": ["Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row", "Dumbbell Press"],
}

LEVELS = {
    "beginner": {"sets": (2, 3), "reps": (8, 12), "days": 3},
    "intermediate": {"sets": (3, 4), "reps": (8, 15), "days": 4},
    "advanced": {"sets": (4, 5), "reps": (6, 15), "days": 5},
}

WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def focus_for(program_name):
    program_name = program_name or ""
    if "Fat Loss" in program_name:
        return "Conditioning"
    if "Muscle Gain" in program_name:
        return "Hypertrophy"
    return "Full Body"


def generate(program_name, experience, seed=None):
    """Return (focus, plan) where plan is a list of {day, exercise, sets, reps}."""
    level = LEVELS[experience.lower()]
    rng = random.Random(seed)
    focus = focus_for(program_name)
    per_day = 3 if level["days"] < 4 else 4
    plan = []
    for day in WEEK[:level["days"]]:
        for exercise in rng.sample(EXERCISES[focus], k=per_day):
            plan.append({
                "day": day,
                "exercise": exercise,
                "sets": rng.randint(*level["sets"]),
                "reps": rng.randint(*level["reps"]),
            })
    return focus, plan
