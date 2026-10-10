import charts


def add(client, **kw):
    body = {"name": "Arun", "program": "FL", "weight": 80}
    body.update(kw)
    return client.post("/clients", json=body)


def progress(client, name, adherence):
    return client.post(f"/clients/{name}/progress", json={"adherence": adherence})


def test_export_csv(client):
    add(client)
    res = client.get("/clients/export.csv")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    lines = res.get_data(as_text=True).strip().splitlines()
    assert lines[0] == "Name,Age,Weight,Program,Calories"
    assert lines[1] == "Arun,0,80.0,Fat Loss (FL),1760"


def test_export_csv_without_clients(client):
    assert client.get("/clients/export.csv").status_code == 404


def test_chart_data_uses_latest_progress(client):
    add(client)
    add(client, name="Bala")
    progress(client, "Arun", 40)
    progress(client, "Arun", 60)
    progress(client, "Bala", 90)
    assert client.get("/clients/chart-data").get_json() == {
        "labels": ["Arun", "Bala"], "adherence": [60, 90]}


def test_chart_svg(client):
    assert client.get("/clients/chart.svg").status_code == 404
    add(client)
    progress(client, "Arun", 50)
    res = client.get("/clients/chart.svg")
    assert res.mimetype == "image/svg+xml"
    assert "<svg" in res.get_data(as_text=True)


def test_charts_escape_labels():
    svg = charts.bar_chart_svg("t", ["<b>"], [10])
    assert "<b>" not in svg and "&lt;b&gt;" in svg


def test_line_chart_handles_single_and_flat_series():
    assert "<polyline" in charts.line_chart_svg("t", ["a"], [5])
    assert "<polyline" in charts.line_chart_svg("t", ["a", "b"], [5, 5], ymin=5, ymax=5)
