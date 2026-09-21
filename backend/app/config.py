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

    # Shared bearer token (D5). Empty disables authentication entirely, which is
    # only acceptable on a development machine; main.py warns loudly at startup.
    api_token: str = ""

    # Exact allowed origins, comma separated. The mobile app does not need CORS;
    # this exists for the Flutter web dev server.
    cors_origins: str = ""
    cors_origin_regex: str = ""

    model_config = {"case_sensitive": False}

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
