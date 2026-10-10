def setup_client(client, points):
    client.post("/clients", json={"name": "Arun", "program": "FL", "weight": 70})
    for p in points:
        client.post("/clients/Arun/progress", json={"adherence": p})


def test_progress_chart_svg(client):
    setup_client(client, [50, 70, 90])
    res = client.get("/clients/Arun/progress/chart.svg")
    assert res.status_code == 200
    assert res.mimetype == "image/svg+xml"
    body = res.get_data(as_text=True)
    assert "Weekly Adherence Progress - Arun" in body
    assert body.count("<circle") == 3


def test_progress_chart_without_data(client):
    setup_client(client, [])
    res = client.get("/clients/Arun/progress/chart.svg")
    assert res.status_code == 404


def test_progress_chart_unknown_client(client):
    assert client.get("/clients/Nobody/progress/chart.svg").status_code == 404
