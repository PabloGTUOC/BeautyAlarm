from datetime import timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..auth import current_user
from ..database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/streak", response_model=schemas.StreakResponse)
def read_streak(
    db: Session = Depends(get_db), user: models.User = Depends(current_user)
):
    routines = db.query(models.Routine).filter(models.Routine.user_id == user.id).all()
    logs = db.query(models.DailyLog).filter(models.DailyLog.user_id == user.id).all()
    current, longest = services.compute_streaks(routines, logs, services.today_local())
    return schemas.StreakResponse(current=current, longest=longest)


@router.get("/adherence", response_model=List[schemas.RoutineAdherence])
def read_adherence(
    days: int = Query(default=30, ge=1, le=366),
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    """How often each routine was completed out of the times it was due."""
    today = services.today_local()
    start = today - timedelta(days=days - 1)

    routines = db.query(models.Routine).filter(models.Routine.user_id == user.id).all()
    completed_dates: Dict[int, set] = {}
    for routine_id, log_date in (
        db.query(models.DailyLog.routine_id, models.DailyLog.log_date)
        .filter(
            models.DailyLog.log_date.between(start, today),
            models.DailyLog.status == models.LogStatus.completed,
            models.DailyLog.user_id == user.id,
        )
    ):
        completed_dates.setdefault(routine_id, set()).add(log_date)

    results = []
    # Tracked routines are excluded (D12): they are never due on a given date,
    # so every day would read as a miss. is_due enforces this too, but filtering
    # here keeps the intent visible.
    for routine in services.scheduled_only(routines):
        due_dates = [
            start + timedelta(days=offset)
            for offset in range(days)
            if services.is_due(routine, start + timedelta(days=offset))
        ]
        if not due_dates:
            continue
        done = completed_dates.get(routine.id, set())
        results.append(
            schemas.RoutineAdherence(
                routine_id=routine.id,
                routine_name=routine.name,
                due=len(due_dates),
                completed=sum(1 for day in due_dates if day in done),
            )
        )
    results.sort(key=lambda r: (r.completed / r.due, r.routine_name))
    return results
