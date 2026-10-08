"""Pydantic models: every request and response shape, matching docs/openapi.yaml."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

CODE_PATTERN = r"^[A-Za-z0-9_-]{3,32}$"
MAX_URL_LENGTH = 2048
Code = Annotated[str, Field(pattern=CODE_PATTERN)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are rejected, not silently ignored


class Credentials(StrictModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class User(BaseModel):
    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class LinkCreate(StrictModel):
    # HttpUrl only accepts http/https, so javascript:, data:, file: etc. are rejected.
    target_url: HttpUrl
    custom_code: Code | None = None

    @field_validator("target_url")
    @classmethod
    def limit_url_length(cls, value: HttpUrl) -> HttpUrl:
        # Checked after normalisation, to match the database CHECK (<= 2048) exactly.
        if len(str(value)) > MAX_URL_LENGTH:
            raise ValueError(f"URL must be {MAX_URL_LENGTH} characters or fewer")
        return value


class Link(BaseModel):
    id: int
    code: str
    short_url: str
    target_url: str
    created_at: datetime
    click_count: int


class LinkList(BaseModel):
    items: list[Link]
    total: int


class DailyClicks(BaseModel):
    date: date
    clicks: int


class ReferrerClicks(BaseModel):
    referrer: str
    clicks: int


class LinkStats(BaseModel):
    link_id: int
    total_clicks: int
    window_clicks: int
    days: int
    daily: list[DailyClicks]
    top_referrers: list[ReferrerClicks]
