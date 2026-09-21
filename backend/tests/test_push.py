from datetime import date, time

import pytest

from app.config import get_settings
from app.models import Product, Routine, TimePeriod
from app.scheduler import routines_due_at
from tests.conftest import make_routine

MONDAY = date(2026, 9, 21)


@pytest.fixture
def push_client(client, monkeypatch):
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-private")
    get_settings.cache_clear()
    yield client
    get_settings.cache_clear()


SUBSCRIPTION = {
    "endpoint": "https://push.example.com/abc",
    "keys": {"p256dh": "key-one", "auth": "auth-one"},
}


def test_public_key_unavailable_until_configured(client):
    assert client.get("/push/public-key").status_code == 503


def test_public_key_returned_when_configured(push_client):
    assert push_client.get("/push/public-key").json() == {"public_key": "test-public"}


def test_subscribe_is_idempotent_per_endpoint(push_client):
    first = push_client.post("/push/subscribe", json=SUBSCRIPTION)
    assert first.status_code == 200

    refreshed = dict(SUBSCRIPTION, keys={"p256dh": "key-two", "auth": "auth-two"})
    second = push_client.post("/push/subscribe", json=refreshed)
    assert second.json()["id"] == first.json()["id"]  # refreshed, not duplicated


def test_unsubscribe_removes_the_endpoint(push_client):
    push_client.post("/push/subscribe", json=SUBSCRIPTION)
    assert push_client.post(
        "/push/unsubscribe", json={"endpoint": SUBSCRIPTION["endpoint"]}
    ).status_code == 204
    # Subscribing again creates a new row rather than reviving the old one.
    assert push_client.post("/push/subscribe", json=SUBSCRIPTION).status_code == 200


def test_test_push_with_no_subscribers_delivers_nothing(push_client):
    assert push_client.post("/push/test").json() == {"delivered": 0}


# --- scheduler selection logic ---

def _routine(db, **overrides):
    product = Product(name="Retinol")
    db.add(product)
    db.flush()
    fields = {
        "product_id": product.id,
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
        "time_period": TimePeriod.night,
        "notification_time": time(22, 0),
        "is_active": True,
    }
    fields.update(overrides)
    routine = Routine(**fields)
    db.add(routine)
    db.commit()
    return routine


def test_scheduler_matches_the_exact_minute(db_session):
    _routine(db_session)
    assert len(routines_due_at(db_session, MONDAY, time(22, 0))) == 1
    assert routines_due_at(db_session, MONDAY, time(22, 1)) == []
    assert routines_due_at(db_session, MONDAY, time(21, 0)) == []


def test_scheduler_ignores_routines_without_a_time(db_session):
    _routine(db_session, notification_time=None)
    assert routines_due_at(db_session, MONDAY, time(22, 0)) == []


def test_scheduler_respects_due_rules(db_session):
    _routine(db_session, days_of_week=[2])  # Tuesday only; MONDAY is a Monday
    assert routines_due_at(db_session, MONDAY, time(22, 0)) == []


def test_scheduler_does_not_nag_about_a_logged_routine(client, db_session, product):
    routine = make_routine(
        client, product["id"], days_of_week=[1], notification_time="22:00"
    )
    assert len(routines_due_at(db_session, MONDAY, time(22, 0))) == 1

    client.post(
        "/logs/",
        json={
            "routine_id": routine["id"],
            "status": "completed",
            "log_date": MONDAY.isoformat(),
        },
    )
    assert routines_due_at(db_session, MONDAY, time(22, 0)) == []
