def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_index_reports_version(client):
    assert client.get("/").get_json()["service"] == "ACEest Fitness & Gym"


def test_list_programs(client):
    data = client.get("/programs").get_json()
    assert [p["code"] for p in data] == ["FL-3", "FL-5", "MG-PPL", "BG"]


def test_get_program_by_code_case_insensitive(client):
    res = client.get("/programs/fl")
    body = res.get_json()
    assert res.status_code == 200
    assert body["name"] == "Fat Loss (FL) – 3 day"
    assert "Back Squat" in body["workout"]
    assert body["color"] == "#e74c3c"


def test_get_program_has_workout_and_diet(client):
    for code in ("FL", "FL-5", "MG", "BG"):
        body = client.get(f"/programs/{code}").get_json()
        assert body["workout"] and body["diet"]


def test_unknown_program_404(client):
    res = client.get("/programs/XX")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_site_metrics(client):
    assert client.get("/site-metrics").get_json() == {
        "capacity_users": 150,
        "area_sqft": 10000,
        "break_even_members": 250,
    }


def test_unknown_route_returns_json_404(client):
    res = client.get("/nope")
    assert res.status_code == 404
    assert res.get_json() == {"error": "Not found"}


def test_legacy_short_codes_are_aliases():
    assert client_name("FL") == "Fat Loss (FL) \u2013 3 day"
    assert client_name("mg") == "Muscle Gain (MG) \u2013 PPL"


def client_name(code):
    import programs
    return programs.resolve(code)[0]
