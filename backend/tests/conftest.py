"""Tests run against a REAL Postgres database with db/schema.sql applied.

TEST_DATABASE_URL       -> connects as the restricted app role (what the app uses)
TEST_ADMIN_DATABASE_URL -> connects as the owner, only to wipe tables between tests
DB tests are skipped (not failed) if these aren't set.
"""
import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TEST_DB = os.environ.get("TEST_DATABASE_URL")
ADMIN_DB = os.environ.get("TEST_ADMIN_DATABASE_URL")
JWT_SECRET = "test-secret-that-is-definitely-longer-than-32-chars"
FRONTEND = "http://localhost:3000"

requires_db = pytest.mark.skipif(
    not (TEST_DB and ADMIN_DB), reason="TEST_DATABASE_URL / TEST_ADMIN_DATABASE_URL not set"
)


def make_settings(**overrides) -> Settings:
    values = dict(
        database_url=TEST_DB or "postgresql://unused",
        jwt_secret=JWT_SECRET,
        access_token_minutes=30,
        cors_origins=[FRONTEND],
        public_base_url="http://short.test",
        environment="development",
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def admin_conn():
    with psycopg.connect(ADMIN_DB, autocommit=True) as conn:
        yield conn


@pytest.fixture
def client(admin_conn):
    admin_conn.execute("truncate shortener_clicks, shortener_links, shortener_users restart identity cascade")
    with TestClient(create_app(make_settings())) as c:
        yield c


def register_and_login(client, email="ivan@example.com", password="correct-horse") -> dict:
    """Returns an Authorization header for a fresh user."""
    assert client.post("/api/auth/register", json={"email": email, "password": password}).status_code == 201
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth(client):
    return register_and_login(client)
