import charts


def add(client, **kw):
    body = {"name": "Arun", "program": "FL", "weight": 80, "adherence": 60, "notes": "ok"}
    body.update(kw)
    return client.post("/clients", json=body)


def test_clients_are_stored_in_memory(client):
    assert client.get("/clients").get_json() == []
    add(client)
    add(client, name="Bala", program="MG", adherence=90)
    names = [c["name"] for c in client.get("/clients").get_json()]
    assert names == ["Arun", "Bala"]


def test_notes_are_kept(client):
    add(client, notes="knee pain")
    assert client.get("/clients").get_json()[0]["notes"] == "knee pain"


def test_export_csv(client):
    add(client)
    res = client.get("/clients/export.csv")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    lines = res.get_data(as_text=True).strip().splitlines()
    assert lines[0] == "Name,Age,Weight,Program,Adherence,Notes"
    assert lines[1].startswith("Arun,0,80.0,Fat Loss (FL),60")


def test_export_csv_without_clients(client):
    assert client.get("/clients/export.csv").status_code == 404


def test_chart_data(client):
    add(client)
    add(client, name="Bala", adherence=90)
    assert client.get("/clients/chart-data").get_json() == {
        "labels": ["Arun", "Bala"], "adherence": [60, 90]}


def test_chart_svg(client):
    assert client.get("/clients/chart.svg").status_code == 404
    add(client)
    res = client.get("/clients/chart.svg")
    assert res.mimetype == "image/svg+xml"
    assert "<svg" in res.get_data(as_text=True)


def test_charts_escape_labels():
    svg = charts.bar_chart_svg("t", ["<b>"], [10])
    assert "<b>" not in svg and "&lt;b&gt;" in svg


def test_line_chart_handles_single_and_flat_series():
    assert "<polyline" in charts.line_chart_svg("t", ["a"], [5])
    assert "<polyline" in charts.line_chart_svg("t", ["a", "b"], [5, 5], ymin=5, ymax=5)
