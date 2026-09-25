from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, push, schemas
from ..auth import current_user
from ..config import get_settings
from ..database import get_db
from ..services import utcnow

router = APIRouter(prefix="/push", tags=["push"])


def require_push_configured() -> None:
    if not get_settings().push_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web Push is not configured: set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY",
        )


@router.get("/public-key", response_model=schemas.PushPublicKey)
def read_public_key(user: models.User = Depends(current_user)):
    require_push_configured()
    return schemas.PushPublicKey(public_key=get_settings().vapid_public_key)


@router.post("/subscribe", response_model=schemas.PushSubscription)
def subscribe(
    payload: schemas.PushSubscriptionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    """Register a browser for this user (D4a).

    The endpoint is globally unique, so a shared device that two people sign in
    on is re-pointed at whoever subscribed last rather than duplicated. That is
    the correct reading: the endpoint identifies the browser profile, and only
    one person's reminders should arrive there.
    """
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
            user_id=user.id,
        )
        db.add(subscription)
    else:
        subscription.p256dh = payload.keys.p256dh
        subscription.auth = payload.keys.auth
        subscription.last_failure_at = None
        subscription.user_id = user.id
    db.commit()
    db.refresh(subscription)
    return subscription


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(
    payload: schemas.PushEndpoint,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == payload.endpoint,
        models.PushSubscription.user_id == user.id,
    ).delete()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test", response_model=schemas.PushResult)
def send_test(
    db: Session = Depends(get_db), user: models.User = Depends(current_user)
):
    require_push_configured()
    # Only this user's own devices, never the household's.
    delivered = push.send_to_user(
        db, user.id, title="BeautyAlarm", body="Notifications are working.", url="/"
    )
    return schemas.PushResult(delivered=delivered)
