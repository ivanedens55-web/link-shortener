from fastapi import APIRouter

from .. import repository
from ..deps import AppSettings, CurrentUser, DbConn
from ..errors import AppError
from ..schemas import Credentials, Token, User
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=User, status_code=201)
def register(body: Credentials, conn: DbConn):
    user = repository.create_user(conn, body.email, hash_password(body.password))
    if user is None:
        raise AppError(409, "conflict", "An account with this email already exists.")
    return user


@router.post("/login", response_model=Token)
def login(body: Credentials, conn: DbConn, settings: AppSettings):
    user = repository.get_user_by_email(conn, body.email)
    # verify_password runs even when the user doesn't exist (same timing either way).
    if not verify_password(body.password, user["password_hash"] if user else None):
        raise AppError(401, "unauthorized", "Email or password is incorrect.")
    token = create_access_token(user["id"], settings.jwt_secret, settings.access_token_minutes)
    return Token(access_token=token, expires_in=settings.access_token_minutes * 60)


@router.get("/me", response_model=User)
def me(user: CurrentUser):
    return user
