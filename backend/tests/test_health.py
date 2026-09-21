def test_root(client):
    assert client.get("/").json() == {"message": "Welcome to the Beauty Routine Tracker API"}


def test_healthz_reports_database(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
