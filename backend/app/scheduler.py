"""The notification scheduler (D1b, D10).

An asyncio loop inside the API process. It wakes more often than once a minute
and acts once per distinct local minute, so a slow tick delays a notification
but never skips or repeats one.

This runs in exactly one process. Two uvicorn workers would send every
notification twice.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime, time
from typing import Dict, List

from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal
from .models import DailyLog, LogStatus, Routine, RoutineKind
from .push import send_to_user
from .services import app_timezone, due_on, tracker_state

logger = logging.getLogger("uvicorn.error")


def routines_due_at(db: Session, day: date, at: time) -> List[Routine]:
    """Routines to notify about for a given local day and minute.

    A routine already logged today is left out — having checked it off, being
    reminded about it is just nagging.
    """
    due = due_on(db.query(Routine).all(), day)
    logged = {
        routine_id
        for (routine_id,) in db.query(DailyLog.routine_id).filter(
            DailyLog.log_date == day
        )
    }
    return [
        routine
        for routine in due
        if routine.notification_time is not None
        and routine.notification_time.hour == at.hour
        and routine.notification_time.minute == at.minute
        and routine.id not in logged
    ]


#: Days between repeat notifications for an overdue tracked routine (D12).
OVERDUE_REPEAT_DAYS = 2


def tracked_overdue_at(db: Session, day: date, at: time) -> List[Routine]:
    """Overdue tracked routines to notify about at this local minute (D11, D12).

    Notifies on the day the target is passed, then every second day while it
    stays overdue. The cadence is derived from ``days_since`` rather than stored,
    so it needs no "last notified" column and cannot drift: at exactly the target
    the remainder is 0, the next day 1 (silent), the day after 0 again.
    """
    tracked = [
        r
        for r in db.query(Routine).all()
        if r.kind is RoutineKind.tracked
        and r.is_active
        and r.notification_time is not None
        and r.notification_time.hour == at.hour
        and r.notification_time.minute == at.minute
    ]
    if not tracked:
        return []

    history = (
        db.query(DailyLog)
        .filter(
            DailyLog.routine_id.in_([r.id for r in tracked]),
            DailyLog.status == LogStatus.completed,
        )
        .all()
    )

    selected = []
    for routine in tracked:
        _, days_since, overdue = tracker_state(routine, history, day)
        if not overdue or days_since is None:
            continue
        if (days_since - routine.target_interval_days) % OVERDUE_REPEAT_DAYS == 0:
            selected.append(routine)
    return selected


def dispatch(minute: datetime) -> int:
    """Send whatever is due at this local minute. Returns notifications delivered."""
    db = SessionLocal()
    try:
        delivered = 0
        day, at = minute.date(), minute.time()

        # Grouped by owner: everyone in the house is on their own schedule, and
        # each person's reminder goes only to their own devices (D4a).
        by_user: Dict[int, List[Routine]] = defaultdict(list)
        for routine in routines_due_at(db, day, at):
            by_user[routine.user_id].append(routine)

        for user_id, routines in by_user.items():
            period = routines[0].time_period.value
            names = ", ".join(r.name for r in routines)
            delivered += send_to_user(
                db,
                user_id,
                title=f"Time for your {period} routine",
                body=names or f"{len(routines)} routine(s) due",
                url="/",
            )

        # One notification per overdue tracked routine: they are unrelated
        # errands, so batching them into one line would bury the detail.
        for routine in tracked_overdue_at(db, day, at):
            _, days_since, _ = tracker_state(routine, db.query(DailyLog).filter(
                DailyLog.routine_id == routine.id,
                DailyLog.status == LogStatus.completed,
            ).all(), day)
            delivered += send_to_user(
                db,
                routine.user_id,
                title=f"{routine.name} is overdue",
                body=f"{days_since} days since the last one "
                     f"(target: every {routine.target_interval_days}).",
                url="/",
            )
        return delivered
    finally:
        db.close()


async def run_scheduler() -> None:
    interval = get_settings().scheduler_interval_seconds
    logger.info("scheduler: started, waking every %ss", interval)
    last_minute = None
    while True:
        try:
            minute = datetime.now(app_timezone()).replace(second=0, microsecond=0)
            if minute != last_minute:
                last_minute = minute
                delivered = await asyncio.to_thread(dispatch, minute)
                if delivered:
                    logger.info(
                        "scheduler: delivered %s notification(s) for %s",
                        delivered,
                        minute.isoformat(),
                    )
        except Exception:  # never let one bad tick kill the loop
            logger.exception("scheduler: tick failed")
        await asyncio.sleep(interval)
