import os
import tempfile

# The application builds its engine at import time from the environment, and the
# default URL needs a MySQL driver, so point it at SQLite before anything is
# imported from app.
_TMPDIR = tempfile.mkdtemp(prefix="beautyalarm-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/app.db"
os.environ["APP_TIMEZONE"] = "UTC"
os.environ["API_TOKEN"] = ""
# Cleared, not merely unset: running the suite inside the api container would
# otherwise inherit the deployment's real VAPID pair from .env, which makes
# "unconfigured" tests see a configured app and starts the scheduler against a
# database the fixtures never created.
os.environ["VAPID_PUBLIC_KEY"] = ""
os.environ["VAPID_PRIVATE_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def db_session():
    """A fresh in-memory database per test, shared across connections."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client, monkeypatch):
    """A client against an API that requires a bearer token."""
    monkeypatch.setenv("API_TOKEN", "test-token")
    get_settings.cache_clear()
    yield client
    get_settings.cache_clear()


@pytest.fixture
def product(client):
    response = client.post("/products/", json={"name": "Retinol", "brand": "CeraVe"})
    assert response.status_code == 201
    return response.json()


def make_routine(client, product_id=None, **overrides):
    """Create a scheduled routine. ``product_id`` is a convenience for the common
    one-product case; pass ``product_ids=[...]`` for an ordered multi-product one,
    or neither for a routine with no products."""
    payload = {
        "name": "Nightly retinol",
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
        "time_period": "night",
        "product_ids": [product_id] if product_id is not None else [],
    }
    payload.update(overrides)
    response = client.post("/routines/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def make_tracked(client, **overrides):
    """Create a tracked routine (D11), e.g. a haircut."""
    payload = {
        "name": "Haircut",
        "kind": "tracked",
        "target_interval_days": 35,
        "product_ids": [],
    }
    payload.update(overrides)
    response = client.post("/routines/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def routine_model(**overrides):
    """A detached Routine for unit-testing the pure service functions."""
    from app.models import Routine, RoutineKind

    fields = {
        "id": 1,
        "name": "Routine",
        "kind": RoutineKind.scheduled,
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
        "time_period": None,
        "target_interval_days": None,
        "start_date": None,
        "end_date": None,
        "is_active": True,
    }
    fields.update(overrides)
    return Routine(**fields)
