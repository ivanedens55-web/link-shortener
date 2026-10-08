from tests.conftest import register_and_login, requires_db

pytestmark = requires_db


def create(client, headers, **body):
    body.setdefault("target_url", "https://example.com/some/long/path")
    return client.post("/api/links", json=body, headers=headers)


def test_create_with_random_code(client, auth):
    r = create(client, auth)
    assert r.status_code == 201
    link = r.json()
    assert len(link["code"]) == 7
    assert link["short_url"] == f"http://short.test/r/{link['code']}"
    assert link["click_count"] == 0


def test_create_with_custom_code_and_conflict(client, auth):
    assert create(client, auth, custom_code="my-promo").json()["code"] == "my-promo"
    other = register_and_login(client, "other@example.com")
    r = create(client, other, custom_code="my-promo")
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"


def test_links_require_auth(client):
    assert client.get("/api/links").status_code == 401
    assert client.post("/api/links", json={"target_url": "https://example.com"}).status_code == 401


def test_list_shows_only_own_links_newest_first(client, auth):
    create(client, auth, custom_code="first")
    create(client, auth, custom_code="second")
    other = register_and_login(client, "other@example.com")
    create(client, other, custom_code="theirs")

    body = client.get("/api/links", headers=auth).json()
    assert body["total"] == 2
    assert [l["code"] for l in body["items"]] == ["second", "first"]


def test_pagination(client, auth):
    for i in range(3):
        create(client, auth, custom_code=f"code{i}")
    body = client.get("/api/links?limit=2&offset=2", headers=auth).json()
    assert body["total"] == 3 and len(body["items"]) == 1


def test_other_users_link_is_404_for_get_delete_and_stats(client, auth):
    link_id = create(client, auth).json()["id"]
    intruder = register_and_login(client, "intruder@example.com")
    for method, path in [("GET", f"/api/links/{link_id}"), ("DELETE", f"/api/links/{link_id}"),
                         ("GET", f"/api/links/{link_id}/stats")]:
        r = client.request(method, path, headers=intruder)
        assert r.status_code == 404, path
    # The owner's link survived the delete attempt
    assert client.get(f"/api/links/{link_id}", headers=auth).status_code == 200


def test_delete_removes_link_and_its_clicks(client, auth, admin_conn):
    link = create(client, auth, custom_code="gone").json()
    client.get("/r/gone", follow_redirects=False)
    assert client.delete(f"/api/links/{link['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/links/{link['id']}", headers=auth).status_code == 404
    assert client.get("/r/gone", follow_redirects=False).status_code == 404
    assert admin_conn.execute("select count(*) from shortener_clicks").fetchone()[0] == 0
