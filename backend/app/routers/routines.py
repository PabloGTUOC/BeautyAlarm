from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..auth import require_token
from ..database import get_db
from .products import get_product_or_404

router = APIRouter(
    prefix="/routines", tags=["routines"], dependencies=[Depends(require_token)]
)


def get_routine_or_404(routine_id: int, db: Session) -> models.Routine:
    routine = db.get(models.Routine, routine_id)
    if routine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routine {routine_id} does not exist",
        )
    return routine


@router.post("/", response_model=schemas.Routine, status_code=status.HTTP_201_CREATED)
def create_routine(routine: schemas.RoutineCreate, db: Session = Depends(get_db)):
    # Checked up front so a bad product_id is a 404 rather than a foreign-key 500.
    get_product_or_404(routine.product_id, db)
    db_routine = models.Routine(**routine.model_dump())
    db.add(db_routine)
    db.commit()
    db.refresh(db_routine)
    return db_routine


@router.get("/", response_model=List[schemas.Routine])
def read_routines(
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(models.Routine)
    if not include_inactive:
        query = query.filter(models.Routine.is_active.is_(True))
    return query.order_by(models.Routine.id).offset(skip).limit(limit).all()


# Declared before /{routine_id} so "today" is not parsed as an id.
@router.get("/today", response_model=schemas.TodayResponse)
def read_today(db: Session = Depends(get_db)):
    """The checklist in one call: routines due today, each with its log if any."""
    today = services.today_local()
    routines = db.query(models.Routine).all()
    due = services.due_on(routines, today)

    logs = (
        db.query(models.DailyLog)
        .filter(models.DailyLog.log_date == today)
        .all()
    )
    logs_by_routine = {log.routine_id: log for log in logs}

    entries = [
        schemas.TodayEntry(
            routine=schemas.Routine.model_validate(routine),
            log=(
                schemas.DailyLog.model_validate(logs_by_routine[routine.id])
                if routine.id in logs_by_routine
                else None
            ),
        )
        for routine in due
    ]
    return schemas.TodayResponse(date=today, entries=entries)


@router.get("/{routine_id}", response_model=schemas.Routine)
def read_routine(routine_id: int, db: Session = Depends(get_db)):
    return get_routine_or_404(routine_id, db)


@router.patch("/{routine_id}", response_model=schemas.Routine)
def update_routine(
    routine_id: int, payload: schemas.RoutineUpdate, db: Session = Depends(get_db)
):
    routine = get_routine_or_404(routine_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if "product_id" in changes:
        get_product_or_404(changes["product_id"], db)
    for field, value in changes.items():
        setattr(routine, field, value)
    db.commit()
    db.refresh(routine)
    return routine


@router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_routine(routine_id: int, db: Session = Depends(get_db)):
    """Hard delete. Its logs go with it — they describe this routine and nothing else."""
    routine = get_routine_or_404(routine_id, db)
    db.delete(routine)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
