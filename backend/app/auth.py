"""Per-user accounts and sessions (D5a).

Passwords are argon2id. Sign-in mints a 256-bit opaque token, returns it in an
httpOnly cookie, and stores only its SHA-256, so a database leak yields no
usable sessions. Sessions live in a table rather than in a JWT so that signing
out actually revokes rather than merely promising to.
"""

import hashlib
import secrets
import time
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DbSession

from .config import get_settings
from .database import get_db
from .models import Session, User
from .services import utcnow

COOKIE_NAME = "beautyalarm_session"

_hasher = PasswordHasher()

# A dummy hash to verify against when the address is unknown, so a missing
# account costs the same time as a wrong password and the endpoint cannot be
# used to discover who has an account.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: Optional[str], password: str) -> bool:
    """Constant-ish time check. A null hash still burns the same work."""
    try:
        _hasher.verify(password_hash or _DUMMY_HASH, password)
        return password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_session(db: DbSession, user: User) -> str:
    """Start a session and return the raw token, which is never stored."""
    raw = secrets.token_urlsafe(32)
    now = utcnow()
    db.add(
        Session(
            user_id=user.id,
            token_hash=_hash_token(raw),
            created_at=now,
            expires_at=now + timedelta(days=get_settings().session_ttl_days),
            last_seen_at=now,
        )
    )
    user.last_login_at = now
    db.commit()
    return raw


def set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        raw_token,
        max_age=settings.session_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        # Lax is what stands in for CSRF tokens here: the client and API share
        # one origin (D9), so no legitimate request is cross-site, and Lax
        # blocks cross-site POSTs.
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def revoke_session(db: DbSession, raw_token: Optional[str]) -> None:
    if not raw_token:
        return
    db.query(Session).filter(Session.token_hash == _hash_token(raw_token)).delete()
    db.commit()


def _lookup(db: DbSession, raw_token: Optional[str]) -> Optional[User]:
    if not raw_token:
        return None
    row = (
        db.query(Session)
        .filter(Session.token_hash == _hash_token(raw_token))
        .one_or_none()
    )
    if row is None:
        return None
    if row.expires_at <= utcnow():
        # Sweep on read: an expired session is deleted rather than left to rot.
        db.delete(row)
        db.commit()
        return None

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None

    row.last_seen_at = utcnow()
    db.commit()
    return user


def current_user(
    request: Request, db: DbSession = Depends(get_db)
) -> User:
    """The signed-in user, or 401.

    Every authenticated route depends on this, and every query then filters on
    ``user.id``. Both halves are required: the dependency alone only proves
    somebody is signed in, not that the row they asked for is theirs.
    """
    user = _lookup(db, request.cookies.get(COOKIE_NAME))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in"
        )
    return user


def optional_user(request: Request, db: DbSession = Depends(get_db)) -> Optional[User]:
    return _lookup(db, request.cookies.get(COOKIE_NAME))


# --- Rate limiting -----------------------------------------------------------
# In-process and unsynchronised, which is correct here only because the API runs
# a single worker (D10). A second worker would give each its own counter.
_attempts: Dict[str, List[float]] = {}


def rate_limit(request: Request) -> None:
    settings = get_settings()
    window = settings.auth_rate_window_seconds
    now = time.monotonic()
    key = request.client.host if request.client else "unknown"

    recent = [t for t in _attempts.get(key, []) if now - t < window]
    if len(recent) >= settings.auth_rate_limit:
        recent.append(now)
        _attempts[key] = recent
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again in a few minutes.",
        )
    recent.append(now)
    _attempts[key] = recent


def reset_rate_limits() -> None:
    """Test helper: the limiter is process state, so it leaks between tests."""
    _attempts.clear()


def owned_or_404(model, obj_id: int, user: User, db: DbSession, label: str):
    """Fetch a row by id, but only if it belongs to this user.

    Somebody else's id is a 404, not a 403: a 403 would confirm the row exists.
    """
    row = (
        db.query(model)
        .filter(model.id == obj_id, model.user_id == user.id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} {obj_id} does not exist",
        )
    return row
