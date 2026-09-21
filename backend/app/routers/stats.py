from datetime import timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..auth import require_token
from ..database import get_db

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(require_token)])


@router.get("/streak", response_model=schemas.StreakResponse)
def read_streak(db: Session = Depends(get_db)):
    routines = db.query(models.Routine).all()
    logs = db.query(models.DailyLog).all()
    current, longest = services.compute_streaks(routines, logs, services.today_local())
    return schemas.StreakResponse(current=current, longest=longest)


@router.get("/adherence", response_model=List[schemas.RoutineAdherence])
def read_adherence(days: int = Query(default=30, ge=1, le=366), db: Session = Depends(get_db)):
    """How often each routine was completed out of the times it was due."""
    today = services.today_local()
    start = today - timedelta(days=days - 1)

    routines = db.query(models.Routine).all()
    completed_dates: Dict[int, set] = {}
    for routine_id, log_date in (
        db.query(models.DailyLog.routine_id, models.DailyLog.log_date)
        .filter(
            models.DailyLog.log_date.between(start, today),
            models.DailyLog.status == models.LogStatus.completed,
        )
    ):
        completed_dates.setdefault(routine_id, set()).add(log_date)

    results = []
    for routine in routines:
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
                product_name=routine.product.name if routine.product else "Unknown product",
                due=len(due_dates),
                completed=sum(1 for day in due_dates if day in done),
            )
        )
    results.sort(key=lambda r: (r.completed / r.due, r.product_name))
    return results
