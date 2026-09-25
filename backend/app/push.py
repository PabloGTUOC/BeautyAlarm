"""Web Push delivery (D1b)."""

import json
import logging
from typing import Optional

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from .config import get_settings
from .models import PushSubscription
from .services import utcnow

logger = logging.getLogger("uvicorn.error")

# The browser has discarded these subscriptions; they will never work again.
DEAD_STATUSES = {404, 410}

# A skincare reminder that surfaces three hours late is noise, not a reminder.
TTL_SECONDS = 3600


def send_to_user(
    db: Session, user_id: int, title: str, body: str, url: str = "/"
) -> int:
    """Push to one person's devices only (D4a).

    There is deliberately no send-to-everyone helper: in a household, a function
    that fans out to every subscription in the table is a bug waiting to be
    called, and it would put one person's reminders on another's phone.

    Returns the number delivered. Dead subscriptions are deleted as they are
    found, so the table cleans itself up without a separate job.
    """
    settings = get_settings()
    if not settings.push_enabled:
        logger.warning("push: VAPID keys are not configured, nothing sent")
        return 0

    payload = json.dumps({"title": title, "body": body, "url": url})
    delivered = 0

    subscriptions = (
        db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
    )
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
                ttl=TTL_SECONDS,
            )
            delivered += 1
        except WebPushException as exc:
            status: Optional[int] = (
                exc.response.status_code if exc.response is not None else None
            )
            if status in DEAD_STATUSES:
                logger.info(
                    "push: dropping dead subscription %s (HTTP %s)", subscription.id, status
                )
                db.delete(subscription)
            else:
                logger.warning(
                    "push: delivery to subscription %s failed (HTTP %s)",
                    subscription.id,
                    status,
                )
                subscription.last_failure_at = utcnow()

    db.commit()
    return delivered
