from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, push, schemas
from ..auth import require_token
from ..config import get_settings
from ..database import get_db
from ..services import utcnow

router = APIRouter(prefix="/push", tags=["push"], dependencies=[Depends(require_token)])


def require_push_configured() -> None:
    if not get_settings().push_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web Push is not configured: set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY",
        )


@router.get("/public-key", response_model=schemas.PushPublicKey)
def read_public_key():
    require_push_configured()
    return schemas.PushPublicKey(public_key=get_settings().vapid_public_key)


@router.post("/subscribe", response_model=schemas.PushSubscription)
def subscribe(payload: schemas.PushSubscriptionCreate, db: Session = Depends(get_db)):
    """Register a browser. Re-subscribing with the same endpoint refreshes its keys."""
    require_push_configured()
    subscription = (
        db.query(models.PushSubscription)
        .filter(models.PushSubscription.endpoint == payload.endpoint)
        .one_or_none()
    )
    if subscription is None:
        subscription = models.PushSubscription(
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
            created_at=utcnow(),
        )
        db.add(subscription)
    else:
        subscription.p256dh = payload.keys.p256dh
        subscription.auth = payload.keys.auth
        subscription.last_failure_at = None
    db.commit()
    db.refresh(subscription)
    return subscription


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(payload: schemas.PushEndpoint, db: Session = Depends(get_db)):
    db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == payload.endpoint
    ).delete()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test", response_model=schemas.PushResult)
def send_test(db: Session = Depends(get_db)):
    require_push_configured()
    delivered = push.send_to_all(
        db, title="BeautyAlarm", body="Notifications are working.", url="/"
    )
    return schemas.PushResult(delivered=delivered)
