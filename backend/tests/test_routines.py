from datetime import date, timedelta

from tests.conftest import make_routine


def test_create_validates_product(client):
    response = client.post(
        "/routines/",
        json={"product_id": 999, "days_of_week": [1], "time_period": "morning"},
    )
    assert response.status_code == 404  # not a foreign-key 500


def test_days_are_sorted_and_deduplicated(client, product):
    routine = make_routine(client, product["id"], days_of_week=[5, 1, 5, 3])
    assert routine["days_of_week"] == [1, 3, 5]


def test_invalid_days_rejected(client, product):
    for days in ([], [0], [8], [1, 9]):
        response = client.post(
            "/routines/",
            json={
                "product_id": product["id"],
                "days_of_week": days,
                "time_period": "morning",
            },
        )
        assert response.status_code == 422, days


def test_notification_time_parsed_as_time(client, product):
    routine = make_routine(client, product["id"], notification_time="22:00")
    assert routine["notification_time"] == "22:00:00"


def test_today_returns_only_routines_due_today(client, product):
    today = date.today()
    due = make_routine(client, product["id"], days_of_week=[today.isoweekday()])
    other = (today.isoweekday() % 7) + 1
    make_routine(client, product["id"], days_of_week=[other])

    body = client.get("/routines/today").json()
    assert body["date"] == today.isoformat()
    assert [entry["routine"]["id"] for entry in body["entries"]] == [due["id"]]
    assert body["entries"][0]["log"] is None  # pending


def test_today_excludes_paused_and_expired(client, product):
    today = date.today()
    make_routine(client, product["id"], days_of_week=[today.isoweekday()], is_active=False)
    make_routine(
        client,
        product["id"],
        days_of_week=[today.isoweekday()],
        end_date=(today - timedelta(days=1)).isoformat(),
    )
    assert client.get("/routines/today").json()["entries"] == []


def test_today_carries_the_log(client, product):
    today = date.today()
    routine = make_routine(client, product["id"], days_of_week=[today.isoweekday()])
    client.post("/logs/", json={"routine_id": routine["id"], "status": "completed"})

    entry = client.get("/routines/today").json()["entries"][0]
    assert entry["log"]["status"] == "completed"


def test_patch_validates_new_product(client, product):
    routine = make_routine(client, product["id"])
    assert client.patch(f"/routines/{routine['id']}", json={"product_id": 999}).status_code == 404


def test_patch_updates_schedule(client, product):
    routine = make_routine(client, product["id"])
    response = client.patch(f"/routines/{routine['id']}", json={"days_of_week": [2, 4]})
    assert response.status_code == 200
    assert response.json()["days_of_week"] == [2, 4]
    assert response.json()["time_period"] == "night"  # untouched


def test_delete_removes_routine_and_its_logs(client, product):
    routine = make_routine(client, product["id"])
    client.post("/logs/", json={"routine_id": routine["id"], "status": "completed"})
    assert len(client.get("/logs/").json()) == 1

    assert client.delete(f"/routines/{routine['id']}").status_code == 204
    assert client.get(f"/routines/{routine['id']}").status_code == 404
    assert client.get("/logs/").json() == []
