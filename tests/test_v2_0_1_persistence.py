import sqlite3

from app import create_app


def add(client, **kw):
    body = {"name": "Arun", "program": "MG", "age": 30, "weight": 70}
    body.update(kw)
    return client.post("/clients", json=body)


def test_save_and_load_client(client):
    assert add(client).status_code == 201
    body = client.get("/clients/Arun").get_json()
    assert body["program"] == "Muscle Gain (MG)"
    assert body["calories"] == 2450
    assert body["age"] == 30


def test_save_client_is_upsert(client):
    add(client)
    add(client, weight=80, program="BG")
    rows = client.get("/clients").get_json()
    assert len(rows) == 1
    assert rows[0]["calories"] == 2080


def test_load_unknown_client(client):
    assert client.get("/clients/Ghost").status_code == 404


def test_data_survives_app_restart(tmp_path):
    cfg = {"TESTING": True, "DATABASE": str(tmp_path / "x.db")}
    create_app(cfg).test_client().post(
        "/clients", json={"name": "Z", "program": "FL", "weight": 50})
    again = create_app(cfg).test_client()
    assert again.get("/clients/Z").status_code == 200


def test_tables_created(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"clients", "progress"} <= tables


def test_save_progress_and_history(client):
    add(client)
    res = client.post("/clients/Arun/progress", json={"adherence": 80})
    assert res.status_code == 201
    assert res.get_json()["week"].startswith("Week ")
    client.post("/clients/Arun/progress", json={"adherence": 90})
    history = client.get("/clients/Arun/progress").get_json()
    assert [h["adherence"] for h in history] == [80, 90]


def test_progress_validation(client):
    add(client)
    assert client.post("/clients/Arun/progress", json={}).status_code == 400
    assert client.post("/clients/Arun/progress", json={"adherence": 101}).status_code == 400
    assert client.post("/clients/Ghost/progress", json={"adherence": 50}).status_code == 404
    assert client.get("/clients/Ghost/progress").status_code == 404
    assert client.post("/clients/Arun/progress", data="x").status_code == 400
