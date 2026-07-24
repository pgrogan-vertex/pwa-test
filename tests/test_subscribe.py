VALID_SUBSCRIPTION = {
    "endpoint": "https://push.example.com/abc123",
    "keys": {"p256dh": "some-p256dh-key", "auth": "some-auth-key"},
}


def test_subscribe_requires_auth(client):
    resp = client.post("/api/subscribe", json=VALID_SUBSCRIPTION)
    assert resp.status_code == 401


def test_subscribe_accepts_valid_subscription(auth_client):
    resp = auth_client.post("/api/subscribe", json=VALID_SUBSCRIPTION)
    assert resp.status_code == 201
    assert resp.get_json() == {"status": "subscribed"}


def test_subscribe_rejects_missing_endpoint(auth_client):
    invalid = {"keys": {"p256dh": "x", "auth": "y"}}
    resp = auth_client.post("/api/subscribe", json=invalid)
    assert resp.status_code == 400


def test_subscribe_rejects_missing_keys(auth_client):
    invalid = {"endpoint": "https://push.example.com/abc123"}
    resp = auth_client.post("/api/subscribe", json=invalid)
    assert resp.status_code == 400


def test_subscribe_rejects_non_json_body(auth_client):
    resp = auth_client.post("/api/subscribe", data="not json")
    assert resp.status_code == 400


def test_subscribe_is_idempotent(auth_client):
    import main

    auth_client.post("/api/subscribe", json=VALID_SUBSCRIPTION)
    resp = auth_client.post("/api/subscribe", json=VALID_SUBSCRIPTION)
    assert resp.status_code == 201
    assert main.load_subscriptions() == [VALID_SUBSCRIPTION]
