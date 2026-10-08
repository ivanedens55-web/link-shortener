from datetime import datetime, timedelta, timezone

import jwt

from tests.conftest import JWT_SECRET, register_and_login, requires_db

pytestmark = requires_db


def test_register_returns_user_without_password(client):
    r = client.post("/api/auth/register", json={"email": "New@Example.com", "password": "longenough"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@example.com"  # normalised to lowercase
    assert "password" not in body and "password_hash" not in body


def test_password_is_stored_hashed(client, admin_conn):
    client.post("/api/auth/register", json={"email": "a@example.com", "password": "plain-text-pw"})
    stored = admin_conn.execute("select password_hash from shortener_users").fetchone()[0]
    assert stored != "plain-text-pw" and stored.startswith("$argon2id$")


def test_duplicate_email_is_409_case_insensitive(client):
    client.post("/api/auth/register", json={"email": "dup@example.com", "password": "longenough"})
    r = client.post("/api/auth/register", json={"email": "DUP@example.com", "password": "longenough"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_login_success_and_me(client):
    headers = register_and_login(client, "me@example.com")
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200 and r.json()["email"] == "me@example.com"


def test_login_wrong_password_and_unknown_email_look_the_same(client):
    client.post("/api/auth/register", json={"email": "x@example.com", "password": "longenough"})
    wrong = client.post("/api/auth/login", json={"email": "x@example.com", "password": "wrongpassword"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrongpassword"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_tampered_and_expired_tokens_rejected(client, auth):
    tampered = {"Authorization": auth["Authorization"][:-3] + "abc"}
    assert client.get("/api/auth/me", headers=tampered).status_code == 401

    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired = jwt.encode({"sub": "1", "iat": past, "exp": past}, JWT_SECRET, algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_token_signed_with_other_secret_rejected(client, auth):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "attacker-secret-attacker-secret-attacker!", algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
