"""Accounts, sessions and registration (D5a, D14)."""

import pytest

from app.auth import reset_rate_limits
from app.config import get_settings
from tests.conftest import register, sign_in

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def _clear_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


def test_healthz_stays_open(client):
    assert client.get("/healthz").status_code == 200


def test_endpoints_require_a_session(client):
    for path in ("/products/", "/routines/", "/logs/", "/stats/streak", "/routines/today"):
        assert client.get(path).status_code == 401, path


def test_register_signs_you_in(client):
    user = register(client)
    assert user["email"] == "test@example.com"
    assert "password" not in user and "password_hash" not in user
    assert client.get("/products/").status_code == 200


def test_login_then_logout_revokes_access(client):
    register(client)
    client.post("/auth/logout")
    assert client.get("/products/").status_code == 401

    sign_in(client)
    assert client.get("/products/").status_code == 200


def test_logout_kills_the_session_server_side(client, db_session):
    """Not just the cookie: a stolen token must stop working too."""
    from app.auth import COOKIE_NAME
    from app.models import Session

    register(client)
    token = client.cookies.get(COOKIE_NAME)
    assert db_session.query(Session).count() == 1

    client.post("/auth/logout")
    assert db_session.query(Session).count() == 0

    # Replay the old cookie: the row is gone, so it is worthless.
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/products/").status_code == 401


def test_wrong_password_is_rejected(client):
    register(client)
    client.post("/auth/logout")
    response = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_unknown_email_and_wrong_password_are_indistinguishable(client):
    """Otherwise the endpoint tells you who has an account."""
    register(client)
    client.post("/auth/logout")

    wrong = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "wrong-password"}
    )
    missing = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"}
    )
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json()["detail"] == missing.json()["detail"]


def test_password_is_never_returned_or_stored_in_the_clear(client, db_session):
    from app.models import User

    register(client)
    user = db_session.query(User).one()
    assert PASSWORD not in user.password_hash
    assert user.password_hash.startswith("$argon2")


def test_duplicate_email_is_rejected(client):
    register(client)
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": PASSWORD, "display_name": "Other"},
    )
    assert response.status_code == 409


def test_email_is_case_insensitive(client):
    register(client, email="Someone@Example.COM")
    client.post("/auth/logout")
    assert sign_in(client, email="someone@example.com")["email"] == "someone@example.com"


def test_short_passwords_are_rejected(client):
    response = client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "short", "display_name": "A"},
    )
    assert response.status_code == 422


def test_me_reports_the_signed_in_user(client):
    register(client, display_name="Pablo")
    assert client.get("/auth/me").json()["display_name"] == "Pablo"
    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401


def test_session_cookie_is_httponly(client):
    from app.auth import COOKIE_NAME

    response = client.post(
        "/auth/register",
        json={"email": "c@d.com", "password": PASSWORD, "display_name": "C"},
    )
    cookie = response.headers["set-cookie"]
    assert COOKIE_NAME in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie.replace("samesite=lax", "SameSite=lax")


def test_expired_sessions_are_refused_and_swept(client, db_session):
    from datetime import timedelta
    from app.models import Session
    from app.services import utcnow

    register(client)
    session = db_session.query(Session).one()
    session.expires_at = utcnow() - timedelta(seconds=1)
    db_session.commit()

    assert client.get("/products/").status_code == 401
    assert db_session.query(Session).count() == 0


# --- Registration gate (D14) ---

def test_registration_can_be_closed(client, monkeypatch):
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    get_settings.cache_clear()
    try:
        response = client.post(
            "/auth/register",
            json={"email": "late@example.com", "password": PASSWORD, "display_name": "L"},
        )
        assert response.status_code == 403
    finally:
        get_settings.cache_clear()


def test_auth_config_tells_the_client_whether_to_show_sign_up(client):
    assert client.get("/auth/config").json() == {"allow_registration": True}


def test_repeated_attempts_are_rate_limited(client, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT", "3")
    get_settings.cache_clear()
    try:
        codes = [
            client.post(
                "/auth/login", json={"email": "x@y.com", "password": "nope-nope-nope"}
            ).status_code
            for _ in range(5)
        ]
        assert 429 in codes, codes
    finally:
        get_settings.cache_clear()
