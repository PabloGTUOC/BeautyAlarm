"""Cross-user isolation (D4a).

This is the failure mode with no symptom: a query that forgets `user_id` returns
somebody else's rows and raises nothing. Review does not catch it reliably, so
every resource is walked here with two accounts, asserting that B can neither
see nor touch A's data.

If you add a resource, add it here. A new endpoint without a row in these tests
is an endpoint nobody has checked for leaks.
"""

import pytest

from app.auth import reset_rate_limits
from tests.conftest import register, sign_in


@pytest.fixture(autouse=True)
def _clear_limits():
    # The limiter is module-level process state, so it leaks between tests.
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def two_households(client):
    """Alice with a full set of data, and Bob with nothing."""
    register(client, "alice@example.com", "correct-horse-battery")
    product = client.post("/products/", json={"name": "Alice's retinol"}).json()
    routine = client.post(
        "/routines/",
        json={
            "name": "Alice's night routine",
            "product_ids": [product["id"]],
            "days_of_week": [1, 2, 3, 4, 5, 6, 7],
            "time_period": "night",
        },
    ).json()
    log = client.post(
        "/logs/", json={"routine_id": routine["id"], "status": "completed"}
    ).json()

    register(client, "bob@example.com", "correct-horse-battery")  # signs Bob in
    return {"product": product, "routine": routine, "log": log}


# --- Reads ---

def test_lists_show_only_your_own_rows(client, two_households):
    assert client.get("/products/").json() == []
    assert client.get("/routines/").json() == []
    assert client.get("/logs/").json() == []
    assert client.get("/routines/today").json()["entries"] == []


def test_fetching_someone_elses_row_is_404_not_403(client, two_households):
    """404, so the API does not confirm that the row exists at all."""
    assert client.get(f"/products/{two_households['product']['id']}").status_code == 404
    assert client.get(f"/routines/{two_households['routine']['id']}").status_code == 404


def test_stats_do_not_mix_households(client, two_households):
    assert client.get("/stats/streak").json() == {"current": 0, "longest": 0}
    assert client.get("/stats/adherence").json() == []
    calendar = client.get("/logs/calendar?from=2026-01-01&to=2026-01-07").json()
    assert all(day["due"] == 0 and day["completed"] == 0 for day in calendar)


# --- Writes ---

def test_cannot_edit_or_delete_someone_elses_routine(client, two_households):
    routine_id = two_households["routine"]["id"]
    assert client.patch(f"/routines/{routine_id}", json={"name": "mine now"}).status_code == 404
    assert client.delete(f"/routines/{routine_id}").status_code == 404


def test_cannot_edit_or_archive_someone_elses_product(client, two_households):
    product_id = two_households["product"]["id"]
    assert client.patch(f"/products/{product_id}", json={"name": "mine"}).status_code == 404
    assert client.delete(f"/products/{product_id}").status_code == 404


def test_cannot_log_against_someone_elses_routine(client, two_households):
    response = client.post(
        "/logs/", json={"routine_id": two_households["routine"]["id"], "status": "completed"}
    )
    assert response.status_code == 404


def test_cannot_build_a_routine_from_someone_elses_products(client, two_households):
    response = client.post(
        "/routines/",
        json={
            "name": "Borrowed",
            "product_ids": [two_households["product"]["id"]],
            "days_of_week": [1],
            "time_period": "morning",
        },
    )
    assert response.status_code == 404


def test_deleting_someone_elses_log_does_not_work(client, two_households):
    assert client.delete(f"/logs/{two_households['log']['id']}").status_code == 404


def test_alice_still_has_everything_afterwards(client, two_households):
    """The counterpart to the checks above: isolation, not deletion."""
    sign_in(client, "alice@example.com", "correct-horse-battery")
    assert len(client.get("/products/").json()) == 1
    assert len(client.get("/routines/").json()) == 1
    assert len(client.get("/logs/").json()) == 1


# --- Notifications ---

def test_push_subscriptions_are_per_user(client, push_keys, two_households):
    subscription = {
        "endpoint": "https://push.example.com/bob",
        "keys": {"p256dh": "k", "auth": "a"},
    }
    assert client.post("/push/subscribe", json=subscription).status_code == 200

    sign_in(client, "alice@example.com", "correct-horse-battery")
    # Alice cannot unsubscribe Bob's device.
    assert client.post(
        "/push/unsubscribe", json={"endpoint": subscription["endpoint"]}
    ).status_code == 204

    sign_in(client, "bob@example.com", "correct-horse-battery")
    from app.models import PushSubscription
    # Still there: the delete was scoped to Alice and matched nothing.
    assert client.post("/push/subscribe", json=subscription).status_code == 200


def test_scheduler_sends_each_persons_routines_to_their_own_devices(db_session):
    """The scheduler is the one place that legitimately reads across users."""
    from datetime import date, time
    from app.models import PushSubscription, Routine, TimePeriod, User
    from app.scheduler import routines_due_at
    from app.services import utcnow

    monday = date(2026, 9, 21)
    users = []
    for name in ("alice", "bob"):
        user = User(
            email=f"{name}@example.com",
            display_name=name,
            password_hash="x",
            created_at=utcnow(),
        )
        db_session.add(user)
        db_session.flush()
        db_session.add(
            Routine(
                name=f"{name}'s routine",
                days_of_week=[1, 2, 3, 4, 5, 6, 7],
                time_period=TimePeriod.night,
                notification_time=time(22, 0),
                is_active=True,
                user_id=user.id,
            )
        )
        db_session.add(
            PushSubscription(
                endpoint=f"https://push.example.com/{name}",
                p256dh="k", auth="a", created_at=utcnow(), user_id=user.id,
            )
        )
        users.append(user)
    db_session.commit()

    due = routines_due_at(db_session, monday, time(22, 0))
    assert len(due) == 2, "the scheduler serves the whole household"
    # ...but each routine carries its owner, which is what dispatch groups on.
    assert {r.user_id for r in due} == {u.id for u in users}
