import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import health, logs, products, routines, stats

settings = get_settings()

app = FastAPI(title="Beauty Routine Tracker API")

if not settings.auth_enabled:
    logging.getLogger("uvicorn.error").warning(
        "API_TOKEN is not set: every endpoint is unauthenticated. Set it before "
        "exposing this API through the tunnel (specs.md D5)."
    )

# Origins come from configuration (specs.md section 9). The mobile app does not
# need CORS at all; this is for the Flutter web dev server, which sets the regex
# in docker-compose.override.yml.
if settings.cors_origin_list or settings.cors_origin_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(products.router)
app.include_router(routines.router)
app.include_router(logs.router)
app.include_router(stats.router)
