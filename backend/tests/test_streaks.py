from datetime import date, timedelta

from app.models import DailyLog, LogStatus, Routine, RoutineKind, TrackerStatus
from app.services import compute_streaks, is_due, tracker_state

TODAY = date(2026, 9, 21)  # a Monday, ISO weekday 1


def routine(routine_id, days, is_active=True, end_date=None, start_date=None):
    return Routine(
        id=routine_id,
        name=f"Routine {routine_id}",
        kind=RoutineKind.scheduled,
        days_of_week=days,
        time_period="night",
        is_active=is_active,
        start_date=start_date,
        end_date=end_date,
    )


def tracked(routine_id, target_interval_days=35, start_date=None):
    """A tracked routine (D11) — no weekday schedule at all."""
    return Routine(
        id=routine_id,
        name=f"Tracked {routine_id}",
        kind=RoutineKind.tracked,
        days_of_week=None,
        time_period=None,
        target_interval_days=target_interval_days,
        start_date=start_date,
        is_active=True,
    )


def log(routine_id, day, status=LogStatus.completed):
    return DailyLog(routine_id=routine_id, log_date=day, status=status, timestamp=None)


def test_is_due_uses_iso_weekdays():
    monday = routine(1, [1])
    assert is_due(monday, TODAY)                        # 2026-09-21 is a Monday
    assert not is_due(monday, TODAY + timedelta(days=1))


def test_is_due_respects_pause_and_end_date():
    assert not is_due(routine(1, [1], is_active=False), TODAY)
    assert not is_due(routine(1, [1], end_date=TODAY - timedelta(days=1)), TODAY)
    assert is_due(routine(1, [1], end_date=TODAY), TODAY)


def test_no_logs_means_no_streak():
    assert compute_streaks([routine(1, [1, 2, 3, 4, 5, 6, 7])], [], TODAY) == (0, 0)


def test_consecutive_completed_days_count():
    daily = routine(1, [1, 2, 3, 4, 5, 6, 7])
    logs = [log(1, TODAY - timedelta(days=n)) for n in range(4)]
    current, longest = compute_streaks([daily], logs, TODAY)
    assert (current, longest) == (4, 4)


def test_today_incomplete_does_not_break_the_streak():
    daily = routine(1, [1, 2, 3, 4, 5, 6, 7])
    logs = [log(1, TODAY - timedelta(days=n)) for n in range(1, 4)]  # nothing today yet
    current, _ = compute_streaks([daily], logs, TODAY)
    assert current == 3


def test_a_skip_today_breaks_the_streak():
    daily = routine(1, [1, 2, 3, 4, 5, 6, 7])
    logs = [log(1, TODAY - timedelta(days=n)) for n in range(1, 4)]
    logs.append(log(1, TODAY, LogStatus.skipped))
    current, _ = compute_streaks([daily], logs, TODAY)
    assert current == 0


def test_days_with_nothing_due_are_neutral():
    # Due Mondays only. Today is Monday; the previous Monday was completed, and
    # the six days between them have nothing due, so the streak survives them.
    mondays = routine(1, [1])
    logs = [log(1, TODAY), log(1, TODAY - timedelta(days=7))]
    current, longest = compute_streaks([mondays], logs, TODAY)
    assert (current, longest) == (2, 2)


def test_every_due_routine_must_be_completed():
    a = routine(1, [1, 2, 3, 4, 5, 6, 7])
    b = routine(2, [1, 2, 3, 4, 5, 6, 7])
    logs = [log(1, TODAY), log(1, TODAY - timedelta(days=1)), log(2, TODAY - timedelta(days=1))]
    # Yesterday both were done; today only routine 1 is, so today does not count.
    current, _ = compute_streaks([a, b], logs, TODAY)
    assert current == 1


def test_longest_survives_a_later_break():
    daily = routine(1, [1, 2, 3, 4, 5, 6, 7])
    logs = [log(1, TODAY - timedelta(days=n)) for n in (5, 6, 7, 8)]
    logs.append(log(1, TODAY - timedelta(days=2), LogStatus.skipped))
    current, longest = compute_streaks([daily], logs, TODAY)
    assert longest == 4
    assert current == 0


# --- Phase 8: tracked routines and start_date (D11, D12, G28, G33) ---

def test_tracked_routines_are_never_due_on_a_date():
    """A tracked routine has no weekday schedule, so is_due is always False (D11)."""
    haircut = tracked(1)
    for offset in range(7):
        assert not is_due(haircut, TODAY + timedelta(days=offset))


def test_tracked_routines_do_not_break_the_streak():
    """G33: the regression that would pin every streak at zero.

    A tracked routine has no log on almost every day. If it counted as due, each
    of those days would score as broken and the streak could never advance past
    one day.
    """
    scheduled = routine(1, [1, 2, 3, 4, 5, 6, 7])
    haircut = tracked(2)
    logs = [log(1, TODAY - timedelta(days=n)) for n in range(5)]

    current, longest = compute_streaks([scheduled, haircut], logs, TODAY)
    assert (current, longest) == (5, 5)

    # And identical to the same history without the tracked routine present.
    assert compute_streaks([scheduled], logs, TODAY) == (current, longest)


def test_start_date_stops_history_counting_as_missed():
    """G28: before it existed, a routine cannot have been missed."""
    created = TODAY - timedelta(days=2)
    daily = routine(1, [1, 2, 3, 4, 5, 6, 7], start_date=created)

    assert not is_due(daily, created - timedelta(days=1))
    assert is_due(daily, created)
    assert is_due(daily, TODAY)


def test_tracker_state_counts_from_the_last_completed_log():
    haircut = tracked(1, target_interval_days=35)
    logs = [log(1, TODAY - timedelta(days=23))]

    last, days_since, status = tracker_state(haircut, logs, TODAY)
    assert last == TODAY - timedelta(days=23)
    assert days_since == 23
    assert status is TrackerStatus.waiting


def test_the_target_day_is_due_and_the_day_after_is_overdue():
    """Reported from real use: "every 2 days" showed as overdue on day 2, which
    called somebody late on the day they were acting on time."""
    haircut = tracked(1, target_interval_days=35)
    for days, expected in (
        (34, TrackerStatus.waiting),
        (35, TrackerStatus.due),
        (36, TrackerStatus.overdue),
        (40, TrackerStatus.overdue),
    ):
        logs = [log(1, TODAY - timedelta(days=days))]
        _, days_since, status = tracker_state(haircut, logs, TODAY)
        assert (days_since, status) == (days, expected), days


def test_a_short_interval_is_due_not_overdue_on_the_day():
    """The exact case reported: every 2 days, last done 2 days ago."""
    nightly = tracked(1, target_interval_days=2)
    _, days_since, status = tracker_state(nightly, [log(1, TODAY - timedelta(days=2))], TODAY)
    assert (days_since, status) == (2, TrackerStatus.due)


def test_tracker_state_falls_back_to_start_date_when_never_logged():
    haircut = tracked(1, target_interval_days=35, start_date=TODAY - timedelta(days=10))
    last, days_since, status = tracker_state(haircut, [], TODAY)
    assert last is None
    assert days_since == 10
    assert status is TrackerStatus.waiting


def test_tracker_state_has_no_opinion_without_a_baseline():
    """No log and no start_date: claiming it is overdue would be a guess."""
    haircut = tracked(1, target_interval_days=35)
    assert tracker_state(haircut, [], TODAY) == (None, None, TrackerStatus.waiting)


def test_tracker_state_ignores_skips():
    """A skipped haircut is not a haircut."""
    haircut = tracked(1, target_interval_days=35)
    logs = [log(1, TODAY - timedelta(days=2), status=LogStatus.skipped)]
    assert tracker_state(haircut, logs, TODAY) == (None, None, TrackerStatus.waiting)
