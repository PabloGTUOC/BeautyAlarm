from datetime import date, datetime, time, timedelta

import pytest

from app.config import get_settings
from app.models import (
    DailyLog,
    LogStatus,
    Product,
    Routine,
    RoutineKind,
    RoutineProduct,
    TimePeriod,
)
from app.scheduler import routines_due_at, tracked_due_at
from tests.conftest import make_routine, register

MONDAY = date(2026, 9, 21)


@pytest.fixture
def push_client(client, monkeypatch):
    """A signed-in client with push configured: every push route needs both."""
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-private")
    get_settings.cache_clear()
    register(client)
    yield client
    get_settings.cache_clear()


SUBSCRIPTION = {
    "endpoint": "https://push.example.com/abc",
    "keys": {"p256dh": "key-one", "auth": "auth-one"},
}


def test_public_key_unavailable_until_configured(client, signed_in):
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
        "name": "Nightly retinol",
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
        "time_period": TimePeriod.night,
        "notification_time": time(22, 0),
        "is_active": True,
    }
    fields.update(overrides)
    routine = Routine(**fields)
    routine.product_links = [RoutineProduct(product_id=product.id, position=0)]
    db.add(routine)
    db.commit()
    return routine


def _tracked(db, **overrides):
    """A tracked routine with no products, e.g. a haircut (D11)."""
    fields = {
        "name": "Haircut",
        "kind": RoutineKind.tracked,
        "target_interval_days": 35,
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


# --- Phase 8: overdue tracked notifications (D12, G35) ---

def _complete(db, routine, days_ago):
    day = MONDAY - timedelta(days=days_ago)
    db.add(
        DailyLog(
            routine_id=routine.id,
            log_date=day,
            timestamp=datetime.combine(day, time(12, 0)),
            status=LogStatus.completed,
        )
    )
    db.commit()


def test_tracked_routine_is_silent_before_its_target(db_session):
    routine = _tracked(db_session, target_interval_days=35)
    _complete(db_session, routine, 34)
    assert tracked_due_at(db_session, MONDAY, time(22, 0)) == []


def test_tracked_routine_notifies_on_the_target_day_as_due_not_overdue(db_session):
    """The day the interval is reached is the day to act, not the day you are
    late. Flagging it overdue told people they had missed something on time."""
    from app.models import TrackerStatus

    routine = _tracked(db_session, target_interval_days=35)
    _complete(db_session, routine, 35)
    selected = tracked_due_at(db_session, MONDAY, time(22, 0))
    assert len(selected) == 1
    assert selected[0][1] is TrackerStatus.due


def test_the_day_after_the_target_is_silent_then_overdue(db_session):
    """Day 36 is deliberately quiet: the cadence is the due day, then every
    second day (D12). Day 37 comes back, and by then it really is overdue."""
    from app.models import TrackerStatus

    routine = _tracked(db_session, target_interval_days=35)
    _complete(db_session, routine, 36)
    assert tracked_due_at(db_session, MONDAY, time(22, 0)) == []

    for log in db_session.query(DailyLog).all():
        db_session.delete(log)
    db_session.commit()
    _complete(db_session, routine, 37)
    selected = tracked_due_at(db_session, MONDAY, time(22, 0))
    assert selected[0][1] is TrackerStatus.overdue


def test_overdue_tracker_repeats_every_second_day(db_session):
    """D12: notify on the target day, then every other day — not daily."""
    routine = _tracked(db_session, target_interval_days=35)
    fired = []
    for days_ago in range(35, 42):
        for log in db_session.query(DailyLog).all():
            db_session.delete(log)
        db_session.commit()
        _complete(db_session, routine, days_ago)
        if tracked_due_at(db_session, MONDAY, time(22, 0)):
            fired.append(days_ago)
    assert fired == [35, 37, 39, 41]


def test_tracked_routine_ignores_a_non_matching_minute(db_session):
    routine = _tracked(db_session, target_interval_days=35)
    _complete(db_session, routine, 40)
    assert tracked_due_at(db_session, MONDAY, time(9, 0)) == []


def test_paused_tracked_routine_is_never_selected(db_session):
    routine = _tracked(db_session, target_interval_days=35, is_active=False)
    _complete(db_session, routine, 40)
    assert tracked_due_at(db_session, MONDAY, time(22, 0)) == []
