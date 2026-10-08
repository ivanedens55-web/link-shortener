"""Shared dependencies: settings, DB connection and the signed-in user."""
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Connection

from . import repository
from .config import Settings
from .db import get_conn
from .errors import AppError
from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

DbConn = Annotated[Connection, Depends(get_conn)]


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_settings)]


def get_current_user(
    conn: DbConn,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    if credentials is None:
        raise AppError(401, "unauthorized", "Please sign in.")
    user_id = decode_access_token(credentials.credentials, settings.jwt_secret)
    if user_id is None:
        raise AppError(401, "unauthorized", "Your session has expired. Please sign in again.")
    user = repository.get_user_by_id(conn, user_id)
    if user is None:  # token is valid but the account no longer exists
        raise AppError(401, "unauthorized", "Please sign in.")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]
