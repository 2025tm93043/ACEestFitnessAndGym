import pytest

import ai_program
from app import create_app


def add(client, **kw):
    body = {"name": "Arun", "program": "MG", "age": 30, "height": 175, "weight": 80,
            "membership_expiry": "2027-01-31"}
    body.update(kw)
    return client.post("/clients", json=body)


# ---------- login ----------
def test_login_success(anon_client):
    res = anon_client.post("/login", json={"username": "admin", "password": "admin"})
    body = res.get_json()
    assert res.status_code == 200
    assert body["role"] == "Admin" and body["token"]


@pytest.mark.parametrize("payload", [
    {"username": "admin", "password": "wrong"},
    {"username": "ghost", "password": "admin"},
    {},
])
def test_login_failure(anon_client, payload):
    res = anon_client.post("/login", json=payload)
    assert res.status_code == 401
    assert res.get_json()["error"] == "Invalid credentials"


def test_protected_routes_need_token(anon_client):
    assert anon_client.get("/clients").status_code == 401
    assert anon_client.get("/programs").status_code == 401
    bad = anon_client.get("/clients", headers={"Authorization": "Bearer nonsense"})
    assert bad.status_code == 401


def test_public_routes_stay_open(anon_client):
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/").status_code == 200


def test_unknown_route_is_404_even_without_token(anon_client):
    assert anon_client.get("/nope").status_code == 404


def test_me(client):
    assert client.get("/me").get_json() == {"username": "admin", "role": "Admin"}


def test_token_is_accepted(anon_client):
    token = anon_client.post(
        "/login", json={"username": "admin", "password": "admin"}).get_json()["token"]
    res = anon_client.get("/clients", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


def test_auth_can_be_disabled(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "a.db"), "REQUIRE_AUTH": False})
    assert app.test_client().get("/clients").status_code == 200


def test_admin_password_stored_hashed(app):
    import sqlite3
    row = sqlite3.connect(app.config["DATABASE"]).execute(
        "SELECT password FROM users WHERE username='admin'").fetchone()
    assert row[0] != "admin"


# ---------- membership expiry ----------
def test_membership_expiry_saved(client):
    add(client)
    assert client.get("/clients/Arun").get_json()["membership_expiry"] == "2027-01-31"


def test_membership_expiry_validated(client):
    assert add(client, membership_expiry="31/01/2027").status_code == 400


# ---------- AI program ----------
@pytest.mark.parametrize("level,days,per_day", [
    ("beginner", 3, 3), ("intermediate", 4, 4), ("advanced", 5, 4)])
def test_ai_program_shape(client, level, days, per_day):
    add(client)
    res = client.post("/clients/Arun/ai-program", json={"experience": level, "seed": 1})
    body = res.get_json()
    assert res.status_code == 200
    assert body["focus"] == "Hypertrophy"
    assert len(body["plan"]) == days * per_day
    assert len({r["day"] for r in body["plan"]}) == days


def test_ai_program_is_deterministic_with_seed(client):
    add(client)
    one = client.post("/clients/Arun/ai-program", json={"experience": "advanced", "seed": 7})
    two = client.post("/clients/Arun/ai-program", json={"experience": "advanced", "seed": 7})
    assert one.get_json() == two.get_json()


def test_ai_program_respects_ranges(client):
    add(client)
    plan = client.post("/clients/Arun/ai-program",
                       json={"experience": "beginner"}).get_json()["plan"]
    assert all(2 <= r["sets"] <= 3 and 8 <= r["reps"] <= 12 for r in plan)


def test_ai_program_focus_per_program():
    assert ai_program.focus_for("Fat Loss (FL) \u2013 3 day") == "Conditioning"
    assert ai_program.focus_for("Muscle Gain (MG) \u2013 PPL") == "Hypertrophy"
    assert ai_program.focus_for("Beginner (BG)") == "Full Body"
    assert ai_program.focus_for(None) == "Full Body"


def test_ai_program_errors(client):
    add(client)
    assert client.post("/clients/Arun/ai-program", json={"experience": "pro"}).status_code == 400
    assert client.post("/clients/Arun/ai-program", json={}).status_code == 400
    assert client.post("/clients/Ghost/ai-program",
                       json={"experience": "beginner"}).status_code == 404


# ---------- PDF ----------
def test_pdf_report(client):
    add(client)
    res = client.get("/clients/Arun/report.pdf")
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert res.data.startswith(b"%PDF")


def test_pdf_report_unknown_client(client):
    assert client.get("/clients/Ghost/report.pdf").status_code == 404


def test_pdf_handles_unicode_program_names(client):
    add(client, program="FL-3", name="Zo\u00eb \u2013 test")
    assert client.get("/clients/Zo\u00eb \u2013 test/report.pdf").status_code == 200
