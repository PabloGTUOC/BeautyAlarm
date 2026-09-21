from datetime import date, timedelta

from tests.conftest import make_routine


def test_streak_endpoint_starts_at_zero(client):
    assert client.get("/stats/streak").json() == {"current": 0, "longest": 0}


def test_streak_endpoint_counts_today(client, product):
    today = date.today()
    routine = make_routine(client, product["id"], days_of_week=[today.isoweekday()])
    client.post("/logs/", json={"routine_id": routine["id"], "status": "completed"})
    assert client.get("/stats/streak").json()["current"] == 1


def test_adherence_reports_due_and_completed(client, product):
    today = date.today()
    routine = make_routine(client, product["id"], days_of_week=[1, 2, 3, 4, 5, 6, 7])
    for offset in (0, 1):
        client.post(
            "/logs/",
            json={
                "routine_id": routine["id"],
                "status": "completed",
                "log_date": (today - timedelta(days=offset)).isoformat(),
            },
        )

    rows = client.get("/stats/adherence?days=7").json()
    assert len(rows) == 1
    assert rows[0]["product_name"] == "Retinol"
    assert rows[0]["due"] == 7
    assert rows[0]["completed"] == 2


def test_adherence_skips_routines_never_due_in_the_window(client, product):
    today = date.today()
    other_weekday = (today.isoweekday() % 7) + 1
    make_routine(client, product["id"], days_of_week=[other_weekday])
    assert client.get("/stats/adherence?days=1").json() == []
