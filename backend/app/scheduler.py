"""The notification scheduler (D1b, D10).

An asyncio loop inside the API process. It wakes more often than once a minute
and acts once per distinct local minute, so a slow tick delays a notification
but never skips or repeats one.

This runs in exactly one process. Two uvicorn workers would send every
notification twice.
"""

import asyncio
import logging
from datetime import date, datetime, time
from typing import List

from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal
from .models import DailyLog, Routine
from .push import send_to_all
from .services import app_timezone, due_on

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


def dispatch(minute: datetime) -> int:
    """Send whatever is due at this local minute. Returns notifications delivered."""
    db = SessionLocal()
    try:
        routines = routines_due_at(db, minute.date(), minute.time())
        if not routines:
            return 0
        period = routines[0].time_period.value
        names = ", ".join(r.product.name for r in routines if r.product is not None)
        return send_to_all(
            db,
            title=f"Time for your {period} routine",
            body=names or f"{len(routines)} routine(s) due",
            url="/",
        )
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
