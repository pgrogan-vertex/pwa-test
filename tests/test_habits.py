def test_fields_lists_configured_habit_fields(auth_client):
    resp = auth_client.get("/api/habits/fields")
    assert resp.status_code == 200
    keys = {f["key"] for f in resp.get_json()["fields"]}
    assert keys == {"sleep_hours", "notes"}


def test_today_not_logged_initially(auth_client):
    resp = auth_client.get("/api/habits/today")
    assert resp.status_code == 200
    assert resp.get_json() == {"logged": False, "metrics": {}}


def test_save_then_today_reflects_it(auth_client):
    resp = auth_client.post(
        "/api/habits", json={"metrics": {"sleep_hours": 7.5, "notes": "slept great"}}
    )
    assert resp.status_code == 201

    resp = auth_client.get("/api/habits/today")
    data = resp.get_json()
    assert data["logged"] is True
    assert data["metrics"] == {"sleep_hours": 7.5, "notes": "slept great"}


def test_save_upserts_same_day(auth_client):
    auth_client.post("/api/habits", json={"metrics": {"sleep_hours": 6}})
    auth_client.post("/api/habits", json={"metrics": {"sleep_hours": 8}})

    resp = auth_client.get("/api/habits/today")
    assert resp.get_json()["metrics"]["sleep_hours"] == 8


def test_save_rejects_empty_metrics(auth_client):
    resp = auth_client.post("/api/habits", json={"metrics": {}})
    assert resp.status_code == 400


def test_save_rejects_unknown_field(auth_client):
    resp = auth_client.post("/api/habits", json={"metrics": {"mood": "great"}})
    assert resp.status_code == 400


def test_save_rejects_wrong_type_for_number_field(auth_client):
    resp = auth_client.post("/api/habits", json={"metrics": {"sleep_hours": "eight"}})
    assert resp.status_code == 400


def test_save_rejects_bool_for_number_field(auth_client):
    resp = auth_client.post("/api/habits", json={"metrics": {"sleep_hours": True}})
    assert resp.status_code == 400


def test_save_rejects_wrong_type_for_text_field(auth_client):
    resp = auth_client.post("/api/habits", json={"metrics": {"notes": 123}})
    assert resp.status_code == 400


def test_delete_today_clears_entry(auth_client):
    auth_client.post("/api/habits", json={"metrics": {"sleep_hours": 8}})

    resp = auth_client.delete("/api/habits/today")
    assert resp.status_code == 200

    resp = auth_client.get("/api/habits/today")
    assert resp.get_json() == {"logged": False, "metrics": {}}


def test_habits_endpoints_require_auth(client):
    assert client.get("/api/habits/fields").status_code == 401
    assert client.get("/api/habits/today").status_code == 401
    assert client.post("/api/habits", json={"metrics": {"sleep_hours": 8}}).status_code == 401
    assert client.delete("/api/habits/today").status_code == 401


def test_daily_check_sends_when_not_logged(client):
    resp = client.post("/api/jobs/daily-check", headers={"X-Cron-Secret": "test-cron-secret"})
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": 0}


def test_daily_check_skips_when_already_logged(auth_client):
    auth_client.post("/api/habits", json={"metrics": {"sleep_hours": 8}})

    resp = auth_client.post("/api/jobs/daily-check", headers={"X-Cron-Secret": "test-cron-secret"})
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": 0, "skipped": "already logged today"}
