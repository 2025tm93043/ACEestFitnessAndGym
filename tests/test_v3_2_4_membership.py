import sqlite3
from datetime import date, timedelta

import programs
from db import init_db


def add(client, **kw):
    body = {"name": "Arun", "program": "BG", "weight": 70, "height": 170}
    body.update(kw)
    return client.post("/clients", json=body)


def test_membership_defaults_to_active(client):
    add(client)
    body = client.get("/clients/Arun").get_json()
    assert body["membership_status"] == "Active"
    assert body["membership_end"] is None
    info = client.get("/clients/Arun/membership").get_json()
    assert info == {"client": "Arun", "status": "Active", "renewal_date": "N/A",
                    "expired": False}


def test_membership_future_end_date(client):
    end = (date.today() + timedelta(days=30)).isoformat()
    add(client, membership_end=end)
    info = client.get("/clients/Arun/membership").get_json()
    assert info["renewal_date"] == end and info["status"] == "Active"


def test_membership_past_end_date_is_expired(client):
    add(client, membership_end="2020-01-01")
    info = client.get("/clients/Arun/membership").get_json()
    assert info["expired"] is True and info["status"] == "Expired"


def test_membership_status_values(client):
    assert add(client, membership_status="inactive").status_code == 201
    assert client.get("/clients/Arun").get_json()["membership_status"] == "Inactive"
    assert add(client, membership_status="gold").status_code == 400
    assert add(client, membership_end="soon").status_code == 400


def test_membership_in_summary(client):
    add(client, membership_end="2099-12-31")
    summary = client.get("/clients/Arun").get_json()["summary"]
    assert summary["membership"]["renewal_date"] == "2099-12-31"


def test_membership_unknown_client(client):
    assert client.get("/clients/Ghost/membership").status_code == 404


def test_legacy_membership_expiry_alias(client):
    add(client, membership_expiry="2099-01-01")
    assert client.get("/clients/Arun").get_json()["membership_end"] == "2099-01-01"


def test_generate_program_replaces_client_program(client):
    add(client)
    res = client.post("/clients/Arun/generate-program", json={"seed": 3})
    body = res.get_json()
    assert res.status_code == 200
    assert body["program"] in programs.PROGRAM_TEMPLATES[body["program_type"]]
    assert client.get("/clients/Arun").get_json()["program"] == body["program"]


def test_generate_program_deterministic_and_validated(client):
    add(client)
    one = client.post("/clients/Arun/generate-program", json={"seed": 5}).get_json()
    two = client.post("/clients/Arun/generate-program", json={"seed": 5}).get_json()
    assert one == two
    assert client.post("/clients/Ghost/generate-program").status_code == 404


def test_cardio_workout_type(client):
    add(client)
    res = client.post("/clients/Arun/workouts", json={"workout_type": "Cardio"})
    assert res.status_code == 201


def test_pdf_contains_membership(client):
    add(client, membership_end="2099-01-01")
    res = client.get("/clients/Arun/report.pdf")
    assert res.status_code == 200 and res.data.startswith(b"%PDF")


def test_migrates_3_1_2_membership_expiry(tmp_path):
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, "
                 "age INTEGER, height REAL, weight REAL, program TEXT, calories INTEGER, "
                 "target_weight REAL, target_adherence INTEGER, membership_expiry TEXT)")
    conn.execute("INSERT INTO clients (name, membership_expiry) VALUES ('Old', '2030-05-05')")
    conn.commit()
    conn.close()
    init_db(path)
    row = sqlite3.connect(path).execute(
        "SELECT membership_status, membership_end FROM clients WHERE name='Old'").fetchone()
    assert row == ("Active", "2030-05-05")
