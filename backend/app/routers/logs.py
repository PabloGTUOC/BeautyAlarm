from datetime import date, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..auth import require_token
from ..database import get_db
from .routines import get_routine_or_404

router = APIRouter(prefix="/logs", tags=["logs"], dependencies=[Depends(require_token)])

MAX_CALENDAR_DAYS = 366


@router.post("/", response_model=schemas.DailyLog)
def upsert_log(payload: schemas.DailyLogCreate, db: Session = Depends(get_db)):
    """Idempotent per (routine, local date) — D6. Re-posting updates the status."""
    get_routine_or_404(payload.routine_id, db)

    log_date = payload.log_date or services.today_local()
    timestamp = payload.timestamp or services.utcnow()

    log = (
        db.query(models.DailyLog)
        .filter(
            models.DailyLog.routine_id == payload.routine_id,
            models.DailyLog.log_date == log_date,
        )
        .one_or_none()
    )
    if log is None:
        log = models.DailyLog(
            routine_id=payload.routine_id,
            log_date=log_date,
            timestamp=timestamp,
            status=payload.status,
        )
        db.add(log)
    else:
        log.status = payload.status
        log.timestamp = timestamp

    db.commit()
    db.refresh(log)
    return log


@router.get("/", response_model=List[schemas.DailyLog])
def read_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(models.DailyLog)
        .order_by(models.DailyLog.log_date.desc(), models.DailyLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# Declared before /{log_id} so "calendar" is not parsed as an id.
@router.get("/calendar", response_model=List[schemas.CalendarDay])
def read_calendar(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' must not be earlier than 'from'",
        )
    if (date_to - date_from).days + 1 > MAX_CALENDAR_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"range must span at most {MAX_CALENDAR_DAYS} days",
        )

    routines = db.query(models.Routine).all()
    logs = (
        db.query(models.DailyLog)
        .filter(models.DailyLog.log_date.between(date_from, date_to))
        .all()
    )
    by_date: Dict[date, Dict[int, models.LogStatus]] = {}
    for log in logs:
        by_date.setdefault(log.log_date, {})[log.routine_id] = log.status

    days: List[schemas.CalendarDay] = []
    day = date_from
    while day <= date_to:
        due = services.due_on(routines, day)
        statuses = by_date.get(day, {})
        # Counted over the routines due that day, so the numbers agree with the
        # streak definition (D7) rather than with logs left behind by a routine
        # whose schedule has since changed.
        completed = sum(
            1 for r in due if statuses.get(r.id) == models.LogStatus.completed
        )
        skipped = sum(1 for r in due if statuses.get(r.id) == models.LogStatus.skipped)
        days.append(
            schemas.CalendarDay(
                date=day, due=len(due), completed=completed, skipped=skipped
            )
        )
        day += timedelta(days=1)
    return days


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(log_id: int, db: Session = Depends(get_db)):
    """Undo a check-off, returning the routine to pending for that day."""
    log = db.get(models.DailyLog, log_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log {log_id} does not exist",
        )
    db.delete(log)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
