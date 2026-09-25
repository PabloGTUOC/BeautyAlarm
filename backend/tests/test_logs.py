from datetime import date, timedelta

from tests.conftest import make_routine


def test_upsert_is_idempotent_per_day(client, product):
    routine = make_routine(client, product["id"])

    first = client.post("/logs/", json={"routine_id": routine["id"], "status": "completed"})
    assert first.status_code == 200
    assert first.json()["log_date"] == date.today().isoformat()

    second = client.post("/logs/", json={"routine_id": routine["id"], "status": "skipped"})
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]  # updated, not duplicated
    assert second.json()["status"] == "skipped"
    assert len(client.get("/logs/").json()) == 1


def test_log_for_missing_routine_is_404(client, signed_in):
    assert client.post("/logs/", json={"routine_id": 999, "status": "completed"}).status_code == 404


def test_delete_log_returns_routine_to_pending(client, product):
    today = date.today()
    routine = make_routine(client, product["id"], days_of_week=[today.isoweekday()])
    log = client.post("/logs/", json={"routine_id": routine["id"], "status": "completed"}).json()

    assert client.delete(f"/logs/{log['id']}").status_code == 204
    assert client.get("/routines/today").json()["entries"][0]["log"] is None


def test_delete_missing_log_is_404(client, signed_in):
    assert client.delete("/logs/999").status_code == 404


def test_calendar_counts_against_due_routines(client, product):
    today = date.today()
    yesterday = today - timedelta(days=1)
    routine = make_routine(client, product["id"], days_of_week=[1, 2, 3, 4, 5, 6, 7])
    client.post(
        "/logs/",
        json={"routine_id": routine["id"], "status": "completed", "log_date": yesterday.isoformat()},
    )

    days = client.get(f"/logs/calendar?from={yesterday}&to={today}").json()
    assert len(days) == 2
    assert days[0] == {"date": yesterday.isoformat(), "due": 1, "completed": 1, "skipped": 0}
    assert days[1] == {"date": today.isoformat(), "due": 1, "completed": 0, "skipped": 0}


def test_calendar_rejects_a_backwards_range(client, signed_in):
    today = date.today()
    response = client.get(f"/logs/calendar?from={today}&to={today - timedelta(days=1)}")
    assert response.status_code == 422


def test_calendar_rejects_an_oversized_range(client, signed_in):
    today = date.today()
    response = client.get(f"/logs/calendar?from={today - timedelta(days=400)}&to={today}")
    assert response.status_code == 422


# --- Backdating (recording something that already happened) ---

def test_a_past_date_can_be_recorded(client, signed_in, product):
    """Seeding history when you start using the app: "my last haircut was..."."""
    from tests.conftest import make_tracked

    tracked = make_tracked(client, name="Haircut", target_interval_days=35)
    then = (date.today() - timedelta(days=23)).isoformat()
    response = client.post(
        "/logs/", json={"routine_id": tracked["id"], "status": "completed", "log_date": then}
    )
    assert response.status_code == 200
    assert response.json()["log_date"] == then

    entry = client.get("/routines/today").json()["tracking"][0]
    assert entry["days_since"] == 23
    assert entry["last_completed"] == then


def test_a_future_date_is_rejected(client, signed_in, product):
    """Otherwise a typo makes "days since" negative, which reads as nonsense."""
    routine = make_routine(client, product["id"])
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = client.post(
        "/logs/",
        json={"routine_id": routine["id"], "status": "completed", "log_date": tomorrow},
    )
    assert response.status_code == 422
    assert "future" in response.json()["detail"].lower()


def test_today_is_still_allowed(client, signed_in, product):
    routine = make_routine(client, product["id"])
    response = client.post(
        "/logs/",
        json={
            "routine_id": routine["id"],
            "status": "completed",
            "log_date": date.today().isoformat(),
        },
    )
    assert response.status_code == 200


def test_rerecording_the_same_day_replaces_rather_than_duplicates(client, signed_in, product):
    """D6 still holds for a backdated write, so correcting a date is safe."""
    routine = make_routine(client, product["id"])
    then = (date.today() - timedelta(days=5)).isoformat()
    first = client.post(
        "/logs/", json={"routine_id": routine["id"], "status": "completed", "log_date": then}
    ).json()
    second = client.post(
        "/logs/", json={"routine_id": routine["id"], "status": "skipped", "log_date": then}
    ).json()
    assert first["id"] == second["id"]
    assert second["status"] == "skipped"
