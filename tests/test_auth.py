def test_root_redirects_to_login_when_unauthenticated(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_api_route_returns_401_json_when_unauthenticated(client):
    resp = client.get("/api/habits/today")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "unauthorized"}


def test_login_page_is_public(client):
    resp = client.get("/login")
    assert resp.status_code == 200


def test_login_wrong_password_rejected(client):
    resp = client.post("/login", data={"password": "wrong"})
    assert resp.status_code == 401
    assert b"Incorrect password" in resp.data


def test_login_wrong_password_does_not_grant_access(client):
    client.post("/login", data={"password": "wrong"})
    resp = client.get("/")
    assert resp.status_code == 302


def test_login_correct_password_grants_access(client):
    resp = client.post("/login", data={"password": "test-site-password"})
    assert resp.status_code == 302

    resp = client.get("/")
    assert resp.status_code == 200


def test_logout_revokes_access(auth_client):
    resp = auth_client.get("/")
    assert resp.status_code == 200

    auth_client.post("/logout")

    resp = auth_client.get("/")
    assert resp.status_code == 302


def test_healthz_sw_and_static_are_public(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/sw.js").status_code == 200
    assert client.get("/static/manifest.json").status_code == 200


def test_cron_endpoint_ignores_session_and_requires_secret(client):
    # No session, no header - should be rejected by the route's own check, not
    # redirected to /login (the before_request hook exempts cron paths).
    resp = client.post("/api/jobs/daily-check")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "unauthorized"}


def test_cron_endpoint_works_with_correct_secret_and_no_session(client):
    resp = client.post("/api/jobs/daily-check", headers={"X-Cron-Secret": "test-cron-secret"})
    assert resp.status_code == 200
