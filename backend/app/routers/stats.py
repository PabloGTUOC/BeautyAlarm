from fastapi import APIRouter, Depends
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
