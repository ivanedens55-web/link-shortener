"""App factory: wires settings, DB pool, CORS, security headers, error handling and routes.

Run with:  uvicorn app.main:create_app --factory --env-file .env --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, load_settings
from .db import create_pool
from .errors import error_response, logger, register_error_handlers
from .routers import auth, links, redirect

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool.open()
        yield
        app.state.pool.close()

    app = FastAPI(title="Link Shortener API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.pool = create_pool(settings.database_url)

    register_error_handlers(app)

    # Middleware order: the LAST one added runs FIRST (outermost).
    @app.middleware("http")
    async def catch_unhandled(request: Request, call_next):
        # Turns crashes into our JSON error *inside* CORS, so browsers can still read the error.
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            return error_response(500, "internal_error", "Something went wrong on our side. Please try again.")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # exact origins from env, never "*"
        allow_credentials=False,               # token travels in a header, not a cookie
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(links.router)
    app.include_router(redirect.router)
    return app
