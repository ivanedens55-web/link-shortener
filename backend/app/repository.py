"""All SQL lives here. Every query uses %s / %(name)s placeholders (parameterised),
never string-built SQL. Every query on links filters by user_id (ownership)."""
from psycopg import Connection, errors

from .codes import generate_code

# ---------- Users ----------

def create_user(conn: Connection, email: str, password_hash: str) -> dict | None:
    """Return the new user, or None if the email is already registered."""
    try:
        with conn.transaction():  # savepoint, so a duplicate doesn't poison the request's transaction
            return conn.execute(
                "insert into shortener_users (email, password_hash) values (%s, %s) "
                "returning id, email, created_at",
                (email, password_hash),
            ).fetchone()
    except errors.UniqueViolation:
        return None


def get_user_by_email(conn: Connection, email: str) -> dict | None:
    return conn.execute(
        "select id, email, password_hash, created_at from shortener_users where email = %s", (email,)
    ).fetchone()


def get_user_by_id(conn: Connection, user_id: int) -> dict | None:
    return conn.execute(
        "select id, email, created_at from shortener_users where id = %s", (user_id,)
    ).fetchone()


# ---------- Links ----------

_LINK_COLUMNS = """
    l.id, l.code, l.target_url, l.created_at,
    (select count(*) from shortener_clicks c where c.link_id = l.id) as click_count
"""


class CodeTaken(Exception):
    pass


def create_link(conn: Connection, user_id: int, target_url: str, custom_code: str | None) -> dict:
    """Insert a link. Custom code taken -> CodeTaken. Random code collision -> retry."""
    attempts = 1 if custom_code else 5
    for _ in range(attempts):
        code = custom_code or generate_code()
        try:
            with conn.transaction():
                row = conn.execute(
                    "insert into shortener_links (user_id, code, target_url) values (%s, %s, %s) returning id",
                    (user_id, code, target_url),
                ).fetchone()
            return get_link(conn, user_id, row["id"])
        except errors.UniqueViolation:
            continue
    raise CodeTaken()


def list_links(conn: Connection, user_id: int, limit: int, offset: int) -> tuple[list[dict], int]:
    rows = conn.execute(
        f"select {_LINK_COLUMNS} from shortener_links l where l.user_id = %s "
        "order by l.created_at desc, l.id desc limit %s offset %s",
        (user_id, limit, offset),
    ).fetchall()
    total = conn.execute(
        "select count(*) as n from shortener_links where user_id = %s", (user_id,)
    ).fetchone()["n"]
    return rows, total


def get_link(conn: Connection, user_id: int, link_id: int) -> dict | None:
    return conn.execute(
        f"select {_LINK_COLUMNS} from shortener_links l where l.id = %s and l.user_id = %s",
        (link_id, user_id),
    ).fetchone()


def delete_link(conn: Connection, user_id: int, link_id: int) -> bool:
    row = conn.execute(
        "delete from shortener_links where id = %s and user_id = %s returning id", (link_id, user_id)
    ).fetchone()
    return row is not None


# ---------- Redirect + clicks ----------

def find_target_and_record_click(conn: Connection, code: str, referrer: str | None) -> str | None:
    link = conn.execute(
        "select id, target_url from shortener_links where code = %s", (code,)
    ).fetchone()
    if link is None:
        return None
    conn.execute(
        "insert into shortener_clicks (link_id, referrer_host) values (%s, %s)", (link["id"], referrer)
    )
    return link["target_url"]


# ---------- Stats ----------

# Window = the last `days` UTC calendar days, including today.
_WINDOW_START = "(((now() at time zone 'utc')::date - (%(days)s - 1))::timestamp at time zone 'utc')"


def link_stats(conn: Connection, link_id: int, days: int) -> dict:
    params = {"link_id": link_id, "days": days}
    total = conn.execute(
        "select count(*) as n from shortener_clicks where link_id = %(link_id)s", params
    ).fetchone()["n"]

    # generate_series gives every day in the window, so days with zero clicks still appear.
    daily = conn.execute(
        f"""
        with window_days as (
            select generate_series(
                (now() at time zone 'utc')::date - (%(days)s - 1),
                (now() at time zone 'utc')::date,
                interval '1 day'
            )::date as day
        ),
        counts as (
            select (clicked_at at time zone 'utc')::date as day, count(*) as clicks
            from shortener_clicks
            where link_id = %(link_id)s and clicked_at >= {_WINDOW_START}
            group by 1
        )
        select d.day as date, coalesce(c.clicks, 0) as clicks
        from window_days d left join counts c on c.day = d.day
        order by d.day
        """,
        params,
    ).fetchall()

    top_referrers = conn.execute(
        f"""
        select coalesce(referrer_host, 'direct') as referrer, count(*) as clicks
        from shortener_clicks
        where link_id = %(link_id)s and clicked_at >= {_WINDOW_START}
        group by 1
        order by clicks desc, referrer
        limit 5
        """,
        params,
    ).fetchall()

    return {
        "link_id": link_id,
        "total_clicks": total,
        "window_clicks": sum(row["clicks"] for row in daily),
        "days": days,
        "daily": daily,
        "top_referrers": top_referrers,
    }
