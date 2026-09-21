"""Date, due-ness and streak logic (specs.md sections 4, 6 and decision D7)."""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple
from zoneinfo import ZoneInfo

from .config import get_settings
from .models import DailyLog, LogStatus, Routine


def app_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def today_local() -> date:
    """The current local calendar date per APP_TIMEZONE."""
    return datetime.now(app_timezone()).date()


def utcnow() -> datetime:
    """Naive UTC, matching how timestamps are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_due(routine: Routine, day: date) -> bool:
    """Whether a routine is due on a local date (specs.md section 6)."""
    if not routine.is_active:
        return False
    if routine.end_date is not None and day > routine.end_date:
        return False
    return day.isoweekday() in (routine.days_of_week or [])


def due_on(routines: Iterable[Routine], day: date) -> List[Routine]:
    return [r for r in routines if is_due(r, day)]


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
    """
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
