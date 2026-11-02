"""Shared test fixtures.

Every test gets a brand-new, empty in-memory SQLite database, so tests never
depend on each other and never need PostgreSQL. CI has no database.
"""
import os

# app.config reads DB_PASSWORD; tests never use it, but it must exist.
os.environ.setdefault("DB_PASSWORD", "unused-in-tests")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app import db


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared in-memory DB for the whole test
    )
    db.engine = eng
    db.SessionLocal.configure(bind=eng)
    db.Base.metadata.create_all(eng)
    yield eng
    db.Base.metadata.drop_all(eng)
    eng.dispose()
    db.engine = None


@pytest.fixture()
def session(engine):
    s = db.SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def client(engine):
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def employee_payload():
    """A valid request body. Call it and override fields per test."""

    def make(**overrides):
        body = {"name": "Asha K", "email": "asha@corp.com", "department": "IT", "salary": 50000}
        body.update(overrides)
        return body

    return make