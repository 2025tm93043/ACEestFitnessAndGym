import programs


def test_programs_have_calorie_factors():
    assert programs.PROGRAMS["Fat Loss (FL)"]["calorie_factor"] == 22
    assert programs.PROGRAMS["Muscle Gain (MG)"]["calorie_factor"] == 35
    assert programs.PROGRAMS["Beginner (BG)"]["calorie_factor"] == 26


def test_estimate_calories():
    assert programs.estimate_calories(70, "Fat Loss (FL)") == 1540
    assert programs.estimate_calories(80.5, "Muscle Gain (MG)") == 2817
    assert programs.estimate_calories(0, "Beginner (BG)") is None
    assert programs.estimate_calories(70, "Unknown") is None


def test_calories_endpoint(client):
    res = client.get("/programs/BG/calories?weight=60")
    assert res.status_code == 200
    assert res.get_json()["calories"] == 1560


def test_calories_endpoint_validation(client):
    assert client.get("/programs/BG/calories").status_code == 400
    assert client.get("/programs/BG/calories?weight=abc").status_code == 400
    assert client.get("/programs/BG/calories?weight=-5").status_code == 400
    assert client.get("/programs/XX/calories?weight=60").status_code == 404


def test_save_client_ok(client):
    res = client.post("/clients", json={
        "name": "Arun", "program": "FL", "age": 28, "weight": 82,
    })
    body = res.get_json()
    assert res.status_code == 201
    assert body["message"] == "Client data saved"
    assert body["client"]["program"] == "Fat Loss (FL)"
    assert body["client"]["calories"] == 1804


def test_save_client_requires_name_and_program(client):
    res = client.post("/clients", json={"age": 20})
    assert res.status_code == 400
    assert "name is required" in res.get_json()["details"]
    assert "program is required" in res.get_json()["details"]


def test_save_client_rejects_bad_values(client):
    res = client.post("/clients", json={
        "name": "X", "program": "FL", "weight": 900, "age": "old"})
    assert res.status_code == 400
    assert len(res.get_json()["details"]) == 2


def test_save_client_unknown_program(client):
    res = client.post("/clients", json={"name": "X", "program": "ZZ"})
    assert res.status_code == 400


def test_save_client_requires_json(client):
    assert client.post("/clients", data="not json").status_code == 400
