import os
import tempfile

# The application builds its engine at import time from the environment, and the
# default URL needs a MySQL driver, so point it at SQLite before anything is
# imported from app.
_TMPDIR = tempfile.mkdtemp(prefix="beautyalarm-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/app.db"
os.environ["APP_TIMEZONE"] = "UTC"
os.environ["API_TOKEN"] = ""

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


def make_routine(client, product_id, **overrides):
    payload = {
        "product_id": product_id,
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
        "time_period": "night",
    }
    payload.update(overrides)
    response = client.post("/routines/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
