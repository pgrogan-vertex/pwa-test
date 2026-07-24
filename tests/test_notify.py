def test_notify_requires_cron_secret(client):
    resp = client.post("/api/notify", json={"message": "hi"})
    assert resp.status_code == 401


def test_notify_rejects_wrong_secret(client):
    resp = client.post("/api/notify", headers={"X-Cron-Secret": "wrong"}, json={"message": "hi"})
    assert resp.status_code == 401


def test_notify_with_no_subscribers_sends_zero(client):
    resp = client.post(
        "/api/notify",
        headers={"X-Cron-Secret": "test-cron-secret"},
        json={"message": "hi"},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": 0}
