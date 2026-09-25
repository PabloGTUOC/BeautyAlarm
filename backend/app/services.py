"""Date, due-ness and streak logic (specs.md sections 4, 6 and decision D7)."""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

from .config import get_settings
from .models import DailyLog, LogStatus, Routine, RoutineKind


def app_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def today_local() -> date:
    """The current local calendar date per APP_TIMEZONE."""
    return datetime.now(app_timezone()).date()


def utcnow() -> datetime:
    """Naive UTC, matching how timestamps are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_scheduled(routine: Routine) -> bool:
    """Whether a routine recurs on weekdays rather than on an interval (D11)."""
    return routine.kind is RoutineKind.scheduled


def scheduled_only(routines: Iterable[Routine]) -> List[Routine]:
    """Filter to routines that streaks and adherence may consider (D12).

    A tracked routine is never due on a particular day, so counting it would
    score every day as broken and pin the streak at zero permanently.
    """
    return [r for r in routines if is_scheduled(r)]


def is_due(routine: Routine, day: date) -> bool:
    """Whether a routine is due on a local date (specs.md section 6).

    Only scheduled routines are ever "due on a date". A tracked routine has no
    weekday schedule at all, so it is never due in this sense (D11) — use
    ``tracker_state`` for those.
    """
    if not routine.is_active:
        return False
    if not is_scheduled(routine):
        return False
    # Before the routine existed, it could not have been missed (G28).
    if routine.start_date is not None and day < routine.start_date:
        return False
    if routine.end_date is not None and day > routine.end_date:
        return False
    return day.isoweekday() in (routine.days_of_week or [])


def due_on(routines: Iterable[Routine], day: date) -> List[Routine]:
    return [r for r in routines if is_due(r, day)]


def last_completed_date(logs: Iterable[DailyLog], routine_id: int) -> Optional[date]:
    """The most recent local date this routine was completed, if ever."""
    dates = [
        log.log_date
        for log in logs
        if log.routine_id == routine_id and log.status is LogStatus.completed
    ]
    return max(dates) if dates else None


def tracker_state(
    routine: Routine, logs: Iterable[DailyLog], today: date
) -> Tuple[Optional[date], Optional[int], bool]:
    """Elapsed-time state of a tracked routine (D11).

    Returns ``(last_completed, days_since, overdue)``. ``days_since`` counts
    from the last completed log, falling back to ``start_date`` so a routine
    created today does not immediately read as overdue by an unbounded amount.
    With neither, both values are null and the routine is not overdue: there is
    no baseline to measure from, so claiming it is overdue would be a guess.
    """
    last = last_completed_date(logs, routine.id)
    baseline = last or routine.start_date
    if baseline is None:
        return None, None, False

    days_since = (today - baseline).days
    target = routine.target_interval_days
    overdue = target is not None and days_since >= target
    return last, days_since, overdue


def _logs_by_date(logs: Iterable[DailyLog]) -> Dict[date, Dict[int, LogStatus]]:
    grouped: Dict[date, Dict[int, LogStatus]] = {}
    for log in logs:
        grouped.setdefault(log.log_date, {})[log.routine_id] = log.status
    return grouped


def compute_streaks(
    routines: List[Routine], logs: List[DailyLog], today: date
) -> Tuple[int, int]:
    """Current and longest streak per D7.

    A day counts when every routine due that day has a completed log. Days with
    nothing due are neutral: they neither break a streak nor extend it. A skipped
    log breaks it. Today is the one exception — while it is still in progress it
    cannot extend a streak, but neither does it break one unless it holds a skip.

    Due-ness is evaluated against the *current* routine configuration, so editing
    a routine's schedule retroactively changes which past days counted. That is a
    deliberate simplification: the alternative is versioning every routine.

    Tracked routines are excluded entirely (D12). They are never due on a given
    day, so leaving them in would make ``state`` return "broken" for every day
    they had no log — which is every day — and the streak would never move off
    zero.
    """
    routines = scheduled_only(routines)
    by_date = _logs_by_date(logs)
    if not by_date:
        return 0, 0

    def state(day: date) -> str:
        due = due_on(routines, day)
        if not due:
            return "neutral"
        statuses = by_date.get(day, {})
        if all(statuses.get(r.id) == LogStatus.completed for r in due):
            return "complete"
        return "broken"

    def has_skip(day: date) -> bool:
        return LogStatus.skipped in by_date.get(day, {}).values()

    earliest = min(by_date)
    one_day = timedelta(days=1)

    # Current streak: walk backwards from today.
    current = 0
    day = today
    if state(day) != "complete":
        if has_skip(day):
            day = None  # today is explicitly broken
        else:
            day = today - one_day  # today is still in progress
    while day is not None and day >= earliest:
        day_state = state(day)
        if day_state == "complete":
            current += 1
        elif day_state == "broken":
            break
        day -= one_day

    # Longest streak: sweep forward over the recorded history.
    longest = 0
    run = 0
    day = earliest
    while day <= today:
        day_state = state(day)
        if day == today and day_state == "broken" and not has_skip(day):
            day_state = "neutral"  # in progress, not yet a failure
        if day_state == "complete":
            run += 1
            longest = max(longest, run)
        elif day_state == "broken":
            run = 0
        day += one_day

    return current, max(longest, current)
