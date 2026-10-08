from datetime import date, datetime, timedelta, timezone

from tests.conftest import requires_db

pytestmark = requires_db


def make_link(client, auth, code="promo", url="https://example.com/landing?ref=x"):
    return client.post("/api/links", json={"target_url": url, "custom_code": code}, headers=auth).json()


def test_redirect_is_302_uncached_and_counts_click(client, auth):
    link = make_link(client, auth)
    r = client.get("/r/promo", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "https://example.com/landing?ref=x"
    assert r.headers["cache-control"] == "no-store"
    assert client.get(f"/api/links/{link['id']}", headers=auth).json()["click_count"] == 1


def test_redirect_needs_no_auth_and_unknown_code_is_404(client):
    r = client.get("/r/nothere", follow_redirects=False)
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_referrer_stored_as_host_only(client, auth, admin_conn):
    make_link(client, auth)
    client.get("/r/promo", headers={"Referer": "https://t.co/abc?secret=1"}, follow_redirects=False)
    assert admin_conn.execute("select referrer_host from shortener_clicks").fetchone()[0] == "t.co"


def test_stats_daily_series_and_top_referrers(client, auth, admin_conn):
    link = make_link(client, auth)
    for ref in ["https://t.co/a", "https://t.co/b", "https://news.ycombinator.com/", None]:
        headers = {"Referer": ref} if ref else {}
        client.get("/r/promo", headers=headers, follow_redirects=False)
    # One old click, outside a 7-day window but inside all-time totals.
    admin_conn.execute(
        "insert into shortener_clicks (link_id, clicked_at, referrer_host) values (%s, %s, 'old.example')",
        (link["id"], datetime.now(timezone.utc) - timedelta(days=20)),
    )

    stats = client.get(f"/api/links/{link['id']}/stats?days=7", headers=auth).json()
    assert stats["total_clicks"] == 5
    assert stats["days"] == 7
    assert len(stats["daily"]) == 7
    today = datetime.now(timezone.utc).date()
    assert stats["daily"][-1] == {"date": today.isoformat(), "clicks": 4}
    assert date.fromisoformat(stats["daily"][0]["date"]) == today - timedelta(days=6)
    assert stats["window_clicks"] == 4 == sum(d["clicks"] for d in stats["daily"])
    assert stats["top_referrers"][0] == {"referrer": "t.co", "clicks": 2}
    referrers = {r["referrer"] for r in stats["top_referrers"]}
    assert referrers == {"t.co", "news.ycombinator.com", "direct"}  # old.example is outside the window


def test_stats_default_window_is_30_days(client, auth):
    link = make_link(client, auth)
    stats = client.get(f"/api/links/{link['id']}/stats", headers=auth).json()
    assert stats["days"] == 30 and len(stats["daily"]) == 30
    assert stats["total_clicks"] == stats["window_clicks"] == 0
