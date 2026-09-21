from datetime import date, timedelta

from app.models import DailyLog, LogStatus, Routine
from app.services import compute_streaks, is_due

TODAY = date(2026, 9, 21)  # a Monday, ISO weekday 1


def routine(routine_id, days, is_active=True, end_date=None):
    return Routine(
        id=routine_id,
        product_id=1,
        days_of_week=days,
        time_period="night",
        is_active=is_active,
        end_date=end_date,
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
