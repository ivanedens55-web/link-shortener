"""Settings read from environment variables. Fails fast on missing or unsafe values."""
import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    access_token_minutes: int
    cors_origins: list[str]
    public_base_url: str
    environment: str

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    jwt_secret = _required("JWT_SECRET")
    if len(jwt_secret) < 32:
        raise ConfigError("JWT_SECRET must be at least 32 characters.")

    origins = [o.strip().rstrip("/") for o in _required("CORS_ORIGINS").split(",") if o.strip()]
    if "*" in origins:
        raise ConfigError('CORS_ORIGINS must list exact origins, never "*".')

    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    if environment not in ("development", "production"):
        raise ConfigError("ENVIRONMENT must be 'development' or 'production'.")

    return Settings(
        database_url=_required("DATABASE_URL"),
        jwt_secret=jwt_secret,
        access_token_minutes=int(os.environ.get("ACCESS_TOKEN_MINUTES", "30")),
        cors_origins=origins,
        public_base_url=_required("PUBLIC_BASE_URL").rstrip("/"),
        environment=environment,
    )
