"""Sign-up, sign-in, sign-out (D5a, D14)."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import (
    COOKIE_NAME,
    clear_session_cookie,
    create_session,
    current_user,
    hash_password,
    rate_limit,
    revoke_session,
    set_session_cookie,
    verify_password,
)
from ..config import get_settings
from ..database import get_db
from ..services import utcnow

router = APIRouter(prefix="/auth", tags=["auth"])

# One message for both "no such address" and "wrong password", so the endpoint
# cannot be used to find out who has an account.
BAD_CREDENTIALS = "Email or password is incorrect"


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register(
    payload: schemas.RegisterRequest,
    response: Response,
    _: None = Depends(rate_limit),
    db: DbSession = Depends(get_db),
):
    if not get_settings().allow_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is closed on this deployment.",
        )

    email = payload.email.strip().lower()
    if db.query(models.User).filter(models.User.email == email).first() is not None:
        # Registration necessarily reveals that an address is taken; there is no
        # way around it without an email round trip, and there is no mail server.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    user = models.User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        created_at=utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    set_session_cookie(response, create_session(db, user))
    return user


@router.post("/login", response_model=schemas.User)
def login(
    payload: schemas.LoginRequest,
    response: Response,
    _: None = Depends(rate_limit),
    db: DbSession = Depends(get_db),
):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).one_or_none()

    # Always verify, even with no user, so the timing does not differ.
    ok = verify_password(user.password_hash if user else None, payload.password)
    if not ok or user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=BAD_CREDENTIALS
        )

    set_session_cookie(response, create_session(db, user))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)):
    """Revokes server-side, so the token is dead even if the cookie survives."""
    revoke_session(db, request.cookies.get(COOKIE_NAME))
    clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=schemas.User)
def me(user: models.User = Depends(current_user)):
    return user


@router.get("/config", response_model=schemas.AuthConfig)
def auth_config():
    """Lets the sign-in screen hide the register tab when registration is off."""
    return schemas.AuthConfig(allow_registration=get_settings().allow_registration)
