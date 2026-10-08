"""One error format for every response: {"error": {"code": ..., "message": ...}}.
Clients get short, safe messages. Full details go to the server log only."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("link_shortener")


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}}, headers=headers)


def _validation_message(exc: RequestValidationError) -> str:
    first = exc.errors()[0] if exc.errors() else {}
    if first.get("type") == "json_invalid":
        return "Request body must be valid JSON."
    # Location like ("body", "target_url") -> "target_url"; never echo the submitted value.
    field = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query", "path"))
    msg = first.get("msg", "Invalid value.")
    return f"{field}: {msg}" if field else msg


_STATUS_CODES = {401: "unauthorized", 404: "not_found", 405: "method_not_allowed", 409: "conflict"}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        return error_response(exc.status, exc.code, exc.message, headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError):
        return error_response(422, "validation_error", _validation_message(exc))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException):
        # Unknown routes / wrong methods raised by the framework itself.
        code = _STATUS_CODES.get(exc.status_code, "internal_error")
        message = {404: "Not found.", 405: "Method not allowed."}.get(exc.status_code, "Request failed.")
        return error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "internal_error", "Something went wrong on our side. Please try again.")
