import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration, read from the environment (specs.md section 4, 9)."""

    database_url: str = "mysql+mysqldb://beauty_user:beautypassword@localhost:3306/beauty_alarm"

    # IANA name. Every "today", due-date and streak calculation resolves against
    # this single timezone (D4 — one deployment, one user, one timezone).
    app_timezone: str = "UTC"

    # --- Accounts and sessions (D5a) ---
    # How long a sign-in lasts. Household phones, so long by default.
    session_ttl_days: int = 30
    # Set Secure on the session cookie. Off for plain-http localhost development;
    # on for any real deployment, which is served over HTTPS through the tunnel.
    cookie_secure: bool = False
    # Open registration (D14). Turn off once the household has signed up.
    allow_registration: bool = True
    # Sign-in and sign-up attempts allowed per client address per window.
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 300

    # Production is same-origin behind nginx (D9), so these exist for the Vite
    # dev server only.
    cors_origins: str = ""
    cors_origin_regex: str = ""

    # Web Push (D1b). Generate a pair with scripts/generate_vapid_keys.py.
    # Without them the push endpoints answer 503 and the scheduler stays idle.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"

    # How often the scheduler wakes. Below 60s so no minute is ever skipped.
    scheduler_interval_seconds: int = 20

    model_config = {"case_sensitive": False}

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
