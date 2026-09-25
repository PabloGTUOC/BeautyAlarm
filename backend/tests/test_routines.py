from datetime import date, timedelta

from tests.conftest import make_routine


def test_create_validates_product(client, signed_in):
    response = client.post(
        "/routines/",
        json={
            "name": "Ghost",
            "product_ids": [999],
            "days_of_week": [1],
            "time_period": "morning",
        },
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
                "name": "Bad days",
                "product_ids": [product["id"]],
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
    response = client.patch(f"/routines/{routine['id']}", json={"product_ids": [999]})
    assert response.status_code == 404


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


# --- Phase 8: multi-product routines (D8a, G30, G31) ---

def _product(client, name):
    return client.post("/products/", json={"name": name}).json()


def test_routine_holds_several_products_in_order(client, signed_in):
    ha = _product(client, "Hyaluronic Acid")
    pep = _product(client, "Peptides")
    moist = _product(client, "Moisturizer")

    routine = make_routine(
        client, product_ids=[ha["id"], pep["id"], moist["id"]], name="Night stack"
    )
    assert [p["name"] for p in routine["products"]] == [
        "Hyaluronic Acid",
        "Peptides",
        "Moisturizer",
    ]


def test_product_order_is_preserved_not_sorted(client, signed_in):
    """Application order is meaningful: hyaluronic acid goes on before moisturiser."""
    a = _product(client, "Zinc")       # alphabetically last
    b = _product(client, "Azelaic")    # alphabetically first
    routine = make_routine(client, product_ids=[a["id"], b["id"]], name="Ordered")
    assert [p["name"] for p in routine["products"]] == ["Zinc", "Azelaic"]


def test_products_can_be_reordered_by_patch(client, signed_in):
    a = _product(client, "First")
    b = _product(client, "Second")
    routine = make_routine(client, product_ids=[a["id"], b["id"]], name="Reorder me")

    response = client.patch(
        f"/routines/{routine['id']}", json={"product_ids": [b["id"], a["id"]]}
    )
    assert response.status_code == 200
    assert [p["name"] for p in response.json()["products"]] == ["Second", "First"]


def test_a_product_cannot_appear_twice_in_one_routine(client, product):
    response = client.post(
        "/routines/",
        json={
            "name": "Doubled",
            "product_ids": [product["id"], product["id"]],
            "days_of_week": [1],
            "time_period": "morning",
        },
    )
    assert response.status_code == 422


def test_routine_may_have_no_products(client, signed_in):
    """A haircut is an action, not a product application (D8a)."""
    routine = make_routine(client, name="Facial", product_ids=[])
    assert routine["products"] == []


def test_name_is_required(client, product):
    response = client.post(
        "/routines/",
        json={
            "product_ids": [product["id"]],
            "days_of_week": [1],
            "time_period": "morning",
        },
    )
    assert response.status_code == 422


# --- Phase 8: routine kinds (D11, G32) ---

def test_tracked_routine_needs_a_target_interval(client, signed_in):
    response = client.post(
        "/routines/", json={"name": "Haircut", "kind": "tracked", "product_ids": []}
    )
    assert response.status_code == 422


def test_tracked_routine_rejects_a_weekday_schedule(client, signed_in):
    """Silently ignoring the weekdays would leave the user believing they set one."""
    response = client.post(
        "/routines/",
        json={
            "name": "Haircut",
            "kind": "tracked",
            "target_interval_days": 35,
            "days_of_week": [1],
            "product_ids": [],
        },
    )
    assert response.status_code == 422


def test_scheduled_routine_rejects_a_target_interval(client, product):
    response = client.post(
        "/routines/",
        json={
            "name": "Nightly",
            "days_of_week": [1],
            "time_period": "night",
            "target_interval_days": 35,
            "product_ids": [product["id"]],
        },
    )
    assert response.status_code == 422


def test_patch_to_tracked_must_clear_the_schedule(client, product):
    """The merged result is what must be coherent, not the patch alone (D11)."""
    routine = make_routine(client, product["id"])
    stale = client.patch(
        f"/routines/{routine['id']}",
        json={"kind": "tracked", "target_interval_days": 35},
    )
    assert stale.status_code == 422, "stale weekdays must not survive the switch"

    clean = client.patch(
        f"/routines/{routine['id']}",
        json={
            "kind": "tracked",
            "target_interval_days": 35,
            "days_of_week": None,
            "time_period": None,
        },
    )
    assert clean.status_code == 200
    assert clean.json()["kind"] == "tracked"


# --- Phase 8: the Tracking section on /today (G34) ---

def test_today_separates_scheduled_from_tracked(client, product):
    from tests.conftest import make_tracked

    make_routine(client, product["id"])
    make_tracked(client, name="Haircut", target_interval_days=35)

    today = client.get("/routines/today").json()
    assert len(today["entries"]) == 1
    assert len(today["tracking"]) == 1
    assert today["tracking"][0]["routine"]["name"] == "Haircut"


def test_today_reports_days_since_the_last_completion(client, signed_in):
    from tests.conftest import make_tracked

    tracked = make_tracked(client, name="Haircut", target_interval_days=35)
    client.post(
        "/logs/",
        json={
            "routine_id": tracked["id"],
            "status": "completed",
            "log_date": (date.today() - timedelta(days=23)).isoformat(),
        },
    )

    entry = client.get("/routines/today").json()["tracking"][0]
    assert entry["days_since"] == 23
    assert entry["status"] == "waiting"
    assert entry["last_completed"] == (date.today() - timedelta(days=23)).isoformat()


def _track_since(client, days, target=35, name="Haircut"):
    from tests.conftest import make_tracked

    tracked = make_tracked(client, name=name, target_interval_days=target)
    client.post(
        "/logs/",
        json={
            "routine_id": tracked["id"],
            "status": "completed",
            "log_date": (date.today() - timedelta(days=days)).isoformat(),
        },
    )
    return client.get("/routines/today").json()["tracking"][0]


def test_today_flags_an_overdue_tracker(client, signed_in):
    entry = _track_since(client, 40)
    assert entry["days_since"] == 40
    assert entry["status"] == "overdue"


def test_the_target_day_reads_as_due_not_overdue(client, signed_in):
    """Reported: "every 2 days" said overdue on day 2, calling somebody late on
    the day they were acting on time."""
    entry = _track_since(client, 2, target=2, name="Night Routine Day 1")
    assert entry["days_since"] == 2
    assert entry["status"] == "due"
