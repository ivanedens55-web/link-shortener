"""Pure-logic tests: no database needed."""
import pytest

from app.codes import ALPHABET, CODE_LENGTH, generate_code, referrer_host
from app.config import ConfigError, load_settings
from app.security import create_access_token, decode_access_token, hash_password, verify_password

SECRET = "unit-test-secret-that-is-longer-than-32-characters"


def test_generated_codes_have_expected_shape_and_vary():
    codes = {generate_code() for _ in range(200)}
    assert len(codes) == 200
    assert all(len(c) == CODE_LENGTH and set(c) <= set(ALPHABET) for c in codes)


@pytest.mark.parametrize(
    "header, expected",
    [
        ("https://news.ycombinator.com/item?id=1", "news.ycombinator.com"),
        ("https://WWW.Example.com/path", "www.example.com"),
        (None, None),
        ("", None),
        ("not a url", None),
    ],
)
def test_referrer_host_keeps_only_the_host(header, expected):
    assert referrer_host(header) == expected


def test_password_hashing_round_trip():
    hashed = hash_password("s3cret-pass")
    assert hashed != "s3cret-pass" and hashed.startswith("$argon2id$")
    assert verify_password("s3cret-pass", hashed)
    assert not verify_password("wrong-pass", hashed)
    assert not verify_password("s3cret-pass", None)  # unknown user


def test_token_round_trip_and_rejections():
    token = create_access_token(42, SECRET, minutes=5)
    assert decode_access_token(token, SECRET) == 42
    assert decode_access_token(token, "another-secret-that-is-also-long-enough!!") is None
    assert decode_access_token(token[:-2] + "xx", SECRET) is None
    assert decode_access_token(create_access_token(42, SECRET, minutes=-1), SECRET) is None  # expired


def _base_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8000")


def test_settings_reject_wildcard_cors(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ConfigError):
        load_settings()


def test_settings_reject_short_jwt_secret(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("JWT_SECRET", "short")
    with pytest.raises(ConfigError):
        load_settings()


def test_settings_load_valid_env(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://app.example.com/")
    assert load_settings().cors_origins == ["http://localhost:3000", "https://app.example.com"]
