"""CORS, security headers, error leakage and least-privilege database role."""
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import FRONTEND, TEST_DB, make_settings, requires_db

pytestmark = requires_db


def test_security_headers_present(client):
    h = client.get("/health").headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "strict-transport-security" not in h  # dev mode


def test_hsts_in_production(admin_conn):
    with TestClient(create_app(make_settings(environment="production"))) as c:
        assert "max-age=" in c.get("/health").headers["strict-transport-security"]


def test_cors_allows_frontend_only(client):
    allowed = client.options("/api/links", headers={
        "Origin": FRONTEND, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type"})
    assert allowed.headers.get("access-control-allow-origin") == FRONTEND

    evil = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers


def test_unexpected_errors_are_generic_json(client, monkeypatch):
    from app import repository

    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail: /srv/app/db.py")

    monkeypatch.setattr(repository, "get_user_by_email", boom)
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "longenough"},
                    headers={"Origin": FRONTEND})
    assert r.status_code == 500
    assert r.json() == {"error": {"code": "internal_error",
                                  "message": "Something went wrong on our side. Please try again."}}
    assert "secret" not in r.text
    assert r.headers.get("access-control-allow-origin") == FRONTEND  # browser can read the error


@pytest.mark.parametrize("sql", [
    "drop table shortener_links",
    "create table shortener_evil (id int)",
    "truncate shortener_clicks",
    "update shortener_users set email = 'x@example.com'",
    "delete from shortener_users",
    "alter table shortener_links add column x int",
])
def test_app_role_cannot_do_more_than_it_needs(client, sql):
    with psycopg.connect(TEST_DB) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(sql)
