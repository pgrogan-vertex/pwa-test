import importlib

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    """A fresh Flask app per test, backed by an isolated temp DATA_DIR.

    main.py reads its config (env vars) and opens/initializes the habits DB at
    *import* time, so each test reloads the module after setting env vars -
    that's what actually gives every test its own throwaway SQLite file and
    subscriptions.json instead of sharing state (or touching the real ones).
    """
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-vapid-private-key")
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "test-vapid-public-key")
    monkeypatch.setenv("VAPID_CLAIM_EMAIL", "mailto:test@example.com")
    monkeypatch.setenv("CRON_SECRET", "test-cron-secret")
    monkeypatch.setenv("SECRET_KEY", "test-flask-secret-key")
    monkeypatch.setenv("SITE_PASSWORD", "test-site-password")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    import main as main_module

    importlib.reload(main_module)
    main_module.app.config.update(TESTING=True)
    return main_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A client that's already logged in."""
    client.post("/login", data={"password": "test-site-password"})
    return client
