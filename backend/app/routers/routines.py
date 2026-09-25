from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..auth import current_user, owned_or_404
from ..database import get_db
from .products import get_product_or_404

router = APIRouter(prefix="/routines", tags=["routines"])


def get_routine_or_404(
    routine_id: int, db: Session, user: models.User
) -> models.Routine:
    """Scoped to the owner (D4a). Another user's id is a 404, not a 403."""
    return owned_or_404(models.Routine, routine_id, user, db, "Routine")


def _set_products(
    routine: models.Routine, product_ids: List[int], db: Session, user: models.User
) -> None:
    """Replace a routine's products with this ordered list (D8a).

    Each id is checked up front so a bad one is a 404 rather than a foreign-key
    500. ``position`` is the index in the list, which is the application order.
    """
    # Owner-scoped, so a routine cannot be built from somebody else's products.
    for product_id in product_ids:
        get_product_or_404(product_id, db, user)

    # Clear and flush before inserting. Assigning the new list straight over the
    # old one makes SQLAlchemy emit the INSERTs first, and reordering a routine
    # re-inserts product ids that are still present — which trips
    # uq_routine_products_routine_product.
    if routine.product_links:
        routine.product_links.clear()
        db.flush()

    routine.product_links = [
        models.RoutineProduct(product_id=product_id, position=index)
        for index, product_id in enumerate(product_ids)
    ]


@router.post("/", response_model=schemas.Routine, status_code=status.HTTP_201_CREATED)
def create_routine(
    routine: schemas.RoutineCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    payload = routine.model_dump()
    product_ids = payload.pop("product_ids")
    db_routine = models.Routine(**payload, user_id=user.id)
    _set_products(db_routine, product_ids, db, user)
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
    user: models.User = Depends(current_user),
):
    query = db.query(models.Routine).filter(models.Routine.user_id == user.id)
    if not include_inactive:
        query = query.filter(models.Routine.is_active.is_(True))
    return query.order_by(models.Routine.id).offset(skip).limit(limit).all()


# Declared before /{routine_id} so "today" is not parsed as an id.
@router.get("/today", response_model=schemas.TodayResponse)
def read_today(
    db: Session = Depends(get_db), user: models.User = Depends(current_user)
):
    """The checklist in one call.

    Two parts: scheduled routines due today with their logs, and every active
    tracked routine with its elapsed-time state (D11). The tracking list is
    always returned, not only when something is overdue, so the client can show
    "23 days since your last haircut" every day.
    """
    today = services.today_local()
    routines = db.query(models.Routine).filter(models.Routine.user_id == user.id).all()
    due = services.due_on(routines, today)

    logs = (
        db.query(models.DailyLog)
        .filter(
            models.DailyLog.log_date == today,
            models.DailyLog.user_id == user.id,
        )
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

    tracked = [
        r
        for r in routines
        if r.is_active and r.kind is models.RoutineKind.tracked
    ]
    tracking = []
    if tracked:
        # Only completed logs matter for "days since", and only for these
        # routines — the whole log table would be wasteful to load.
        tracked_ids = [r.id for r in tracked]
        history = (
            db.query(models.DailyLog)
            .filter(
                models.DailyLog.routine_id.in_(tracked_ids),
                models.DailyLog.status == models.LogStatus.completed,
                models.DailyLog.user_id == user.id,
            )
            .all()
        )
        for routine in tracked:
            last, days_since, overdue = services.tracker_state(routine, history, today)
            tracking.append(
                schemas.TrackingEntry(
                    routine=schemas.Routine.model_validate(routine),
                    last_completed=last,
                    days_since=days_since,
                    overdue=overdue,
                )
            )
        # Most urgent first: overdue before not, then longest elapsed.
        tracking.sort(key=lambda t: (not t.overdue, -(t.days_since or 0)))

    return schemas.TodayResponse(date=today, entries=entries, tracking=tracking)


@router.get("/{routine_id}", response_model=schemas.Routine)
def read_routine(
    routine_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    return get_routine_or_404(routine_id, db, user)


@router.patch("/{routine_id}", response_model=schemas.Routine)
def update_routine(
    routine_id: int,
    payload: schemas.RoutineUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    routine = get_routine_or_404(routine_id, db, user)
    changes = payload.model_dump(exclude_unset=True)
    product_ids = changes.pop("product_ids", None)

    # Kind coherence has to be judged on the merged result: a patch that only
    # sets kind='tracked' is legal on its own but leaves stale weekdays behind
    # (D11). Validate what the routine will actually look like afterwards.
    merged = {
        "kind": routine.kind,
        "days_of_week": routine.days_of_week,
        "time_period": routine.time_period,
        "target_interval_days": routine.target_interval_days,
        **{k: v for k, v in changes.items() if k in {
            "kind", "days_of_week", "time_period", "target_interval_days"
        }},
    }
    try:
        schemas._check_kind_fields(
            merged["kind"],
            merged["days_of_week"],
            merged["time_period"],
            merged["target_interval_days"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    for field, value in changes.items():
        setattr(routine, field, value)
    if product_ids is not None:
        _set_products(routine, product_ids, db, user)
    db.commit()
    db.refresh(routine)
    return routine


@router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_routine(
    routine_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    """Hard delete. Its logs go with it — they describe this routine and nothing else."""
    routine = get_routine_or_404(routine_id, db, user)
    db.delete(routine)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
