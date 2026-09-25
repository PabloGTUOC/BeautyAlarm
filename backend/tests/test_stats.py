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
    assert rows[0]["routine_name"] == "Nightly retinol"
    assert rows[0]["due"] == 7
    assert rows[0]["completed"] == 2


def test_adherence_skips_routines_never_due_in_the_window(client, product):
    today = date.today()
    other_weekday = (today.isoweekday() % 7) + 1
    make_routine(client, product["id"], days_of_week=[other_weekday])
    assert client.get("/stats/adherence?days=1").json() == []


# --- Phase 8: adherence scoping (D12, G28, G33) ---

def test_adherence_excludes_tracked_routines(client, product):
    """A tracked routine is never due on a date, so it has no adherence (D12)."""
    from tests.conftest import make_tracked

    make_routine(client, product["id"])
    make_tracked(client, name="Haircut", target_interval_days=35)

    rows = client.get("/stats/adherence?days=7").json()
    assert [r["routine_name"] for r in rows] == ["Nightly retinol"]


def test_adherence_does_not_count_days_before_the_routine_existed(client, product):
    """G28, seen in real data: a routine created 2 days ago reported due=13."""
    today = date.today()
    started = today - timedelta(days=2)
    make_routine(
        client, product["id"], name="New routine", start_date=started.isoformat()
    )

    rows = client.get("/stats/adherence?days=30").json()
    assert len(rows) == 1
    assert rows[0]["due"] == 3, "only the days since start_date, inclusive"
