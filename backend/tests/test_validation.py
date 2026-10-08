"""Every bad input gets a 422 in the standard error format, with no internals leaked."""
import pytest

from tests.conftest import requires_db

pytestmark = requires_db


def assert_error(r, status, code):
    assert r.status_code == status
    body = r.json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code
    text = r.text.lower()
    for leak in ("traceback", "psycopg", "select ", "insert ", "/app/", "site-packages"):
        assert leak not in text


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "longenough"},
        {"email": "a@example.com", "password": "short"},
        {"email": "a@example.com", "password": "x" * 129},
        {"email": "a@example.com"},
        {"email": "a@example.com", "password": "longenough", "is_admin": True},  # unknown field
    ],
)
def test_register_rejects_bad_bodies(client, payload):
    assert_error(client.post("/api/auth/register", json=payload), 422, "validation_error")


def test_malformed_json(client):
    r = client.post("/api/auth/login", content="{not json", headers={"Content-Type": "application/json"})
    assert_error(r, 422, "validation_error")
    assert r.json()["error"]["message"] == "Request body must be valid JSON."


@pytest.mark.parametrize(
    "payload",
    [
        {"target_url": "javascript:alert(1)"},
        {"target_url": "ftp://example.com/file"},
        {"target_url": "not a url"},
        {"target_url": "https://example.com/" + "a" * 2040},  # > 2048 after normalising
        {"target_url": "https://example.com", "custom_code": "ab"},  # too short
        {"target_url": "https://example.com", "custom_code": "has space"},
        {"target_url": "https://example.com", "custom_code": "../admin"},
    ],
)
def test_create_link_rejects_bad_bodies(client, auth, payload):
    assert_error(client.post("/api/links", json=payload, headers=auth), 422, "validation_error")


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=abc"])
def test_list_rejects_bad_query(client, auth, query):
    assert_error(client.get(f"/api/links?{query}", headers=auth), 422, "validation_error")


@pytest.mark.parametrize("path", ["/api/links/0", "/api/links/abc", "/api/links/1/stats?days=0", "/api/links/1/stats?days=91"])
def test_rejects_bad_path_and_query(client, auth, path):
    assert_error(client.get(path, headers=auth), 422, "validation_error")


def test_unknown_route_uses_error_format(client):
    assert_error(client.get("/nope"), 404, "not_found")
