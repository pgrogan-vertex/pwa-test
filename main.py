import json
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request
from pywebpush import webpush, WebPushException

load_dotenv()

app = Flask(__name__)

SUBSCRIPTIONS_FILE = Path("subscriptions.json")
VAPID_PRIVATE_KEY = os.environ["VAPID_PRIVATE_KEY"]
VAPID_PUBLIC_KEY = os.environ["VAPID_PUBLIC_KEY"]
VAPID_CLAIM_EMAIL = os.environ["VAPID_CLAIM_EMAIL"]


def load_subscriptions():
    if SUBSCRIPTIONS_FILE.exists():
        return json.loads(SUBSCRIPTIONS_FILE.read_text())
    return []


def save_subscriptions(subscriptions):
    SUBSCRIPTIONS_FILE.write_text(json.dumps(subscriptions))


@app.get("/")
def root():
    return render_template("index.html")


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Flask!"}


@app.get("/api/vapid-public-key")
def vapid_public_key():
    return {"publicKey": VAPID_PUBLIC_KEY}


@app.post("/api/subscribe")
def subscribe():
    subscription = request.get_json()
    subscriptions = load_subscriptions()
    if subscription not in subscriptions:
        subscriptions.append(subscription)
        save_subscriptions(subscriptions)
    return {"status": "subscribed"}, 201


@app.post("/api/notify")
def notify():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "Test notification from your PWA!")

    subscriptions = load_subscriptions()
    still_valid = []
    sent = 0
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps({"title": "PWA Notification", "body": message}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL},
            )
            still_valid.append(subscription)
            sent += 1
        except WebPushException:
            pass  # subscription expired or invalid; drop it

    save_subscriptions(still_valid)
    return {"sent": sent}
