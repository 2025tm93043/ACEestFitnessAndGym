import sqlite3

import pytest

import workouts
from db import init_db


def add(client, **kw):
    body = {"name": "Arun", "program": "FL-5", "age": 30, "height": 175, "weight": 80,
            "target_weight": 72, "target_adherence": 90}
    body.update(kw)
    return client.post("/clients", json=body)


def test_client_goals_and_height_are_stored(client):
    add(client)
    body = client.get("/clients/Arun").get_json()
    assert body["height"] == 175
    assert body["target_weight"] == 72
    assert body["calories"] == 1920  # 80 x 24 (FL 5-day)


def test_optional_fields_become_null(client):
    client.post("/clients", json={"name": "Min", "program": "BG"})
    body = client.get("/clients/Min").get_json()
    assert body["age"] is None and body["weight"] is None and body["calories"] is None


def test_summary_block(client):
    add(client)
    client.post("/clients/Arun/progress", json={"adherence": 60})
    client.post("/clients/Arun/progress", json={"adherence": 81})
    client.post("/clients/Arun/metrics",
                json={"date": "2026-01-02", "weight": 79, "waist": 90, "bodyfat": 22})
    s = client.get("/clients/Arun").get_json()["summary"]
    assert s["program_notes"] == "5-day split, higher volume fat loss"
    assert s["goals"] == "Target Weight: 72.0 kg; Target Adherence: 90%"
    assert s["weeks_logged"] == 2
    assert s["average_adherence"] == 70.5
    assert s["last_metrics"]["waist"] == 90


def test_summary_without_data(client):
    client.post("/clients", json={"name": "Min", "program": "BG"})
    s = client.get("/clients/Min").get_json()["summary"]
    assert s["goals"] == "None" and s["weeks_logged"] == 0 and s["last_metrics"] is None


def test_log_workout_with_exercise_and_history(client):
    add(client)
    res = client.post("/clients/Arun/workouts", json={
        "date": "2026-02-01", "workout_type": "Strength", "duration_min": 45,
        "notes": "heavy", "exercise": {"name": "Squat", "sets": 5, "reps": 5, "weight": 100}})
    assert res.status_code == 201
    client.post("/clients/Arun/workouts",
                json={"date": "2026-03-01", "workout_type": "Mobility"})
    history = client.get("/clients/Arun/workouts").get_json()
    assert [h["date"] for h in history] == ["2026-03-01", "2026-02-01"]
    assert history[0]["duration_min"] == 60 and history[0]["exercises"] == []
    assert history[1]["exercises"][0] == {"name": "Squat", "sets": 5, "reps": 5, "weight": 100.0}


@pytest.mark.parametrize("payload", [
    {},
    {"workout_type": "Yoga"},
    {"workout_type": "Strength", "date": "01-02-2026"},
    {"workout_type": "Strength", "duration_min": 0},
])
def test_workout_validation(client, payload):
    add(client)
    assert client.post("/clients/Arun/workouts", json=payload).status_code == 400


def test_workout_unknown_client_and_bad_body(client):
    assert client.post("/clients/Nobody/workouts",
                       json={"workout_type": "Mixed"}).status_code == 404
    add(client)
    assert client.post("/clients/Arun/workouts", data="x").status_code == 400
    assert client.get("/clients/Nobody/workouts").status_code == 404


def test_metrics_log_and_weight_chart(client):
    add(client)
    assert client.get("/clients/Arun/metrics/weight-chart.svg").status_code == 404
    client.post("/clients/Arun/metrics", json={"date": "2026-01-01", "weight": 80})
    client.post("/clients/Arun/metrics", json={"date": "2026-01-08", "weight": 78.5})
    client.post("/clients/Arun/metrics", json={"date": "2026-01-09", "waist": 88})
    rows = client.get("/clients/Arun/metrics").get_json()
    assert len(rows) == 3 and rows[2]["weight"] is None
    res = client.get("/clients/Arun/metrics/weight-chart.svg")
    assert res.mimetype == "image/svg+xml"
    assert res.get_data(as_text=True).count("<circle") == 2


def test_metrics_validation(client):
    add(client)
    assert client.post("/clients/Arun/metrics", json={"bodyfat": 150}).status_code == 400
    assert client.post("/clients/Arun/metrics", json={"date": "x"}).status_code == 400
    assert client.post("/clients/Nobody/metrics", json={}).status_code == 404
    assert client.get("/clients/Nobody/metrics").status_code == 404
    assert client.get("/clients/Nobody/metrics/weight-chart.svg").status_code == 404
    assert client.post("/clients/Arun/metrics", data="x").status_code == 400


@pytest.mark.parametrize("h,w,bmi,cat", [
    (180, 55, 17.0, "Underweight"),
    (175, 70, 22.9, "Normal"),
    (175, 85, 27.8, "Overweight"),
    (170, 100, 34.6, "Obese"),
])
def test_bmi_bands(h, w, bmi, cat):
    info = workouts.bmi_info(h, w)
    assert info["bmi"] == bmi and info["category"] == cat and info["risk"]


def test_bmi_endpoint(client):
    add(client)
    assert client.get("/clients/Arun/bmi").get_json()["category"] == "Overweight"
    client.post("/clients", json={"name": "NoH", "program": "BG", "weight": 60})
    assert client.get("/clients/NoH/bmi").status_code == 400
    assert client.get("/clients/Nobody/bmi").status_code == 404


def test_migrates_old_clients_table(tmp_path):
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, "
                 "age INTEGER, weight REAL, program TEXT, calories INTEGER)")
    conn.execute("INSERT INTO clients (name, weight) VALUES ('Old', 70)")
    conn.commit()
    conn.close()
    init_db(path)
    cols = {r[1] for r in sqlite3.connect(path).execute("PRAGMA table_info(clients)")}
    assert {"height", "target_weight", "target_adherence"} <= cols
    assert sqlite3.connect(path).execute("SELECT name FROM clients").fetchone()[0] == "Old"
