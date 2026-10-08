"""Connection pool. Every request borrows one connection; the transaction commits
when the request finishes without an error and rolls back otherwise."""
from collections.abc import Iterator

from fastapi import Request
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def create_pool(database_url: str) -> ConnectionPool:
    # Small pool: Render free tier + Supabase session pooler have tight connection limits.
    return ConnectionPool(
        database_url,
        min_size=1,
        max_size=5,
        kwargs={"row_factory": dict_row},
        open=False,
    )


def get_conn(request: Request) -> Iterator[Connection]:
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        yield conn
