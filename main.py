import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, send_from_directory
from pywebpush import webpush, WebPushException

load_dotenv()

app = Flask(__name__)

SUBSCRIPTIONS_FILE = Path(os.environ.get("DATA_DIR", ".")) / "subscriptions.json"
HABITS_DB = Path(os.environ.get("DATA_DIR", ".")) / "habits.db"
VAPID_PRIVATE_KEY = os.environ["VAPID_PRIVATE_KEY"]
VAPID_PUBLIC_KEY = os.environ["VAPID_PUBLIC_KEY"]
VAPID_CLAIM_EMAIL = os.environ["VAPID_CLAIM_EMAIL"]
CRON_SECRET = os.environ["CRON_SECRET"]

# Add a numeric field here any time there's a new metric to track day-to-day.
HABIT_FIELDS = [
    {"key": "sleep_hours", "label": "Sleep (hours)", "type": "number"},
    {"key": "notes", "label": "Notes", "type": "text", "required": False},
]
HABIT_FIELDS_BY_KEY = {field["key"]: field for field in HABIT_FIELDS}


def get_habits_db():
    conn = sqlite3.connect(HABITS_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_habits_db():
    with get_habits_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_entries (
                entry_date TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                metric_value NUMERIC NOT NULL,
                recorded_at TEXT NOT NULL,
                UNIQUE(entry_date, metric_key)
            )
            """
        )


init_habits_db()


def load_subscriptions():
    if SUBSCRIPTIONS_FILE.exists():
        return json.loads(SUBSCRIPTIONS_FILE.read_text())
    return []


def save_subscriptions(subscriptions):
    SUBSCRIPTIONS_FILE.write_text(json.dumps(subscriptions))


def send_push(title, body):
    """Push `title`/`body` to every stored subscription, pruning any that fail."""
    subscriptions = load_subscriptions()
    still_valid = []
    sent = 0
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL},
                headers={"Urgency": "high"},
                ttl=3600,
            )
            still_valid.append(subscription)
            sent += 1
        except WebPushException:
            pass  # subscription expired or invalid; drop it

    save_subscriptions(still_valid)
    return sent


@app.get("/")
def root():
    return render_template("index.html")


@app.get("/sw.js")
def service_worker():
    # Served from the root (not /static/) so its default scope covers the whole site.
    return send_from_directory("static", "sw.js")


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Flask!"}


@app.get("/api/vapid-public-key")
def vapid_public_key():
    return {"publicKey": VAPID_PUBLIC_KEY}


def is_valid_subscription(subscription):
    """Check the shape browsers send from PushManager.subscribe(): endpoint + p256dh/auth keys."""
    if not isinstance(subscription, dict):
        return False
    if not isinstance(subscription.get("endpoint"), str) or not subscription["endpoint"]:
        return False
    keys = subscription.get("keys")
    if not isinstance(keys, dict):
        return False
    return isinstance(keys.get("p256dh"), str) and isinstance(keys.get("auth"), str)


@app.post("/api/subscribe")
def subscribe():
    subscription = request.get_json(silent=True)
    if not is_valid_subscription(subscription):
        return {"error": "invalid subscription"}, 400
    subscriptions = load_subscriptions()
    if subscription not in subscriptions:
        subscriptions.append(subscription)
        save_subscriptions(subscriptions)
    return {"status": "subscribed"}, 201


@app.get("/api/habits/fields")
def habit_fields():
    return {"fields": HABIT_FIELDS}


@app.get("/api/habits/today")
def habits_today():
    today = date.today().isoformat()
    with get_habits_db() as conn:
        rows = conn.execute(
            "SELECT metric_key, metric_value FROM metric_entries WHERE entry_date = ?",
            (today,),
        ).fetchall()
    metrics = {row["metric_key"]: row["metric_value"] for row in rows}
    return {"logged": bool(metrics), "metrics": metrics}


@app.post("/api/habits")
def save_habits():
    payload = request.get_json(silent=True) or {}
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        return {"error": "invalid metrics"}, 400

    today = date.today().isoformat()
    recorded_at = datetime.utcnow().isoformat()

    rows = []
    for key, value in metrics.items():
        field = HABIT_FIELDS_BY_KEY.get(key)
        if field is None:
            return {"error": f"invalid metric: {key}"}, 400
        if field["type"] == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return {"error": f"invalid metric: {key}"}, 400
        elif not isinstance(value, str):
            return {"error": f"invalid metric: {key}"}, 400
        rows.append((today, key, value, recorded_at))

    with get_habits_db() as conn:
        conn.executemany(
            """
            INSERT INTO metric_entries (entry_date, metric_key, metric_value, recorded_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(entry_date, metric_key) DO UPDATE SET
                metric_value = excluded.metric_value,
                recorded_at = excluded.recorded_at
            """,
            rows,
        )
    return {"status": "saved"}, 201


@app.post("/api/notify")
def notify():
    if request.headers.get("X-Cron-Secret") != CRON_SECRET:
        return {"error": "unauthorized"}, 401

    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "Test notification from your PWA!")
    sent = send_push("PWA Notification", message)
    return {"sent": sent}


@app.post("/api/jobs/daily-check")
def daily_check():
    if request.headers.get("X-Cron-Secret") != CRON_SECRET:
        return {"error": "unauthorized"}, 401

    today = date.today().isoformat()
    with get_habits_db() as conn:
        already_logged = conn.execute(
            "SELECT 1 FROM metric_entries WHERE entry_date = ? LIMIT 1",
            (today,),
        ).fetchone()
    if already_logged:
        return {"sent": 0, "skipped": "already logged today"}

    sent = send_push("Daily Check-in", "Don't forget to log today's habits.")
    return {"sent": sent}


if __name__ == "__main__":
    app.run(debug=True)
