"""The backend's routes and methods must match docs/openapi.yaml exactly."""
from pathlib import Path

import yaml

from app.main import create_app
from tests.conftest import make_settings

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "openapi.yaml"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def contract_routes() -> set[tuple[str, str]]:
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return {
        (path, method.upper())
        for path, ops in spec["paths"].items()
        for method in ops
        if method in HTTP_METHODS
    }


def app_routes() -> set[tuple[str, str]]:
    # FastAPI builds its own OpenAPI document from the routes it actually serves,
    # so comparing against it doesn't depend on FastAPI's internal route classes.
    app = create_app(make_settings())  # no DB connection is opened without the lifespan
    return {
        (path, method.upper())
        for path, ops in app.openapi()["paths"].items()
        for method in ops
        if method in HTTP_METHODS
    }


def test_every_contract_route_is_implemented():
    missing = contract_routes() - app_routes()
    assert not missing, f"In contract but not in backend: {sorted(missing)}"


def test_backend_has_no_undocumented_routes():
    extra = app_routes() - contract_routes()
    assert not extra, f"In backend but not in contract: {sorted(extra)}"
