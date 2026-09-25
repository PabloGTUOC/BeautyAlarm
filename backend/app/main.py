import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth, health, logs, products, push, routines, stats
from .scheduler import run_scheduler

settings = get_settings()
logger = logging.getLogger("uvicorn.error")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Run the notification scheduler alongside the API (D10)."""
    task = None
    if settings.push_enabled:
        task = asyncio.create_task(run_scheduler())
    else:
        logger.info(
            "VAPID keys are not configured: notifications are disabled and the "
            "scheduler will not start."
        )
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="Beauty Routine Tracker API", lifespan=lifespan)

if settings.allow_registration:
    logger.info(
        "ALLOW_REGISTRATION is on: anyone who can reach this API can create an "
        "account. Turn it off once the household has signed up (specs.md D14)."
    )

# Origins come from configuration (specs.md section 9). Production is
# same-origin behind nginx (D9); this is for the Vite dev server, which sets the
# regex in docker-compose.override.yml.
if settings.cors_origin_list or settings.cors_origin_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_methods=["*"],
        allow_headers=["*"],
        # The session cookie has to survive the cross-origin dev setup.
        allow_credentials=True,
    )

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(routines.router)
app.include_router(logs.router)
app.include_router(stats.router)
app.include_router(push.router)
