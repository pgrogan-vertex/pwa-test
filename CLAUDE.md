# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

This is a minimal Flask-based Progressive Web App (PWA) scaffold used to learn how to build and deploy apps that work well across phone, laptop, and PC. It is intentionally small ("hello world" level) — treat additions as incremental teaching steps rather than production feature work unless told otherwise.

## Commands

Set up and run locally:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in real values - main.py fails to start if any are missing
python main.py              # dev server, or:
gunicorn main:app --bind 0.0.0.0:8000
```

Run tests:
```
pip install -r requirements-dev.txt
pytest
```
Tests live in `tests/`, with fixtures in `conftest.py` (a fresh Flask app + isolated temp `DATA_DIR` per test, since `main.py` reads config and opens the habits DB at import time). There is no linter configured in this repo yet.

## Environment variables

All required, see `.env.example` for generation commands: `VAPID_PRIVATE_KEY`/`VAPID_PUBLIC_KEY`/`VAPID_CLAIM_EMAIL` (Web Push), `CRON_SECRET` (header auth for `/api/notify` and `/api/jobs/daily-check`), `SECRET_KEY` (Flask session signing), `SITE_PASSWORD` (the site's login password). `DATA_DIR` is optional, defaulting to the working directory.

`.env` is gitignored and never syncs to Railway — a `git push` does not update Railway's variables. Any time a new required env var is added to `main.py`, it must also be set on Railway directly (`railway variables --service pleasing-nurturing --set "KEY=value"`), or every gunicorn worker crashes on import with a `KeyError`. This has happened before; verify with `railway logs` and a live `curl` after deploying a change that touches config, don't just assume the push worked.

## Deployment

Hosted on Railway (`railway.toml`, `builder = "nixpacks"`). Both `Procfile` and `railway.toml` run:
```
gunicorn main:app --bind 0.0.0.0:$PORT --access-logfile - --error-logfile -
```
Keep these two files' start commands in sync if either changes.

## Architecture

- `main.py` — Flask app. Routes: `/` (renders `templates/index.html`); `/login` (GET/POST) and `/logout` (POST) for the auth gate; `/sw.js`; `/healthz`; `/api/hello`; `/api/vapid-public-key`; `/api/subscribe`; `/api/habits/fields`, `/api/habits/today` (GET/DELETE), `/api/habits` (POST); and the cron-secret-protected `/api/notify` + `/api/jobs/daily-check`. A `before_request` hook gates every route behind a logged-in Flask session except `/login`, `/healthz`, `/sw.js`, `/static/*`, and the two cron endpoints (those check the `X-Cron-Secret` header themselves instead of using a session). Uses Flask's default conventions (static files served from `static/` at `/static/...`, templates rendered from `templates/`) rather than explicit configuration — don't add custom static/template folder config unless the directory layout changes.
- Auth — a single shared password (`SITE_PASSWORD`), no per-user accounts. `/login` sets a signed session cookie (`SECRET_KEY`, `app.secret_key`, 30-day lifetime via `app.permanent_session_lifetime`).
- `templates/base.html` — shared page chrome: head boilerplate, base CSS (reset, `body`, `.card`, `h1`, `p`), and the service worker registration call (`window.swRegistration = navigator.serviceWorker.register(...)`). Other templates `{% extends "base.html" %}` and fill in `title`/`extra_style`/`content`/`extra_script` blocks for what's page-specific — put new shared chrome here, not copy-pasted into each page.
- `templates/index.html` — the PWA shell content. Its script chains off `window.swRegistration` (set in base.html) for SW status display, tracks online/offline status via `navigator.onLine`, implements "Add to Home Screen" via `beforeinstallprompt` (Chromium only — iOS Safari never fires it, so the button is silently inert there by design), the push-notification opt-in flow, and the daily habit check-in modal built from `/api/habits/fields`.
- `templates/login.html` — password form for the auth gate.
- `static/manifest.json` — PWA manifest (name, icons, display mode, theme color).
- `static/sw.js` — service worker. Page navigations (`/`, `/login`, and any future page route) are network-first: always fetch live so a stale cached page can't silently bypass the auth gate, refreshing the cache on every successful fetch and falling back to it only when offline. `/api/*` is network-first with a JSON offline fallback. Everything else (manifest, `sw.js` itself) is cache-first via the `SHELL` list. The cache name is version-stamped (`hello-pwa-vN`); **bump this version whenever a page's rendered output or a `SHELL` asset changes**, since the `activate` handler deletes caches that don't match the current name.
- `static/icon.svg` — app icon, referenced by both the manifest and `apple-touch-icon`.
- Habits — SQLite at `DATA_DIR/habits.db`, one row per day in a wide `daily_entries` table; columns come from `HABIT_FIELDS` in `main.py` and are added via `ALTER TABLE` at startup. `DATA_DIR` also holds `subscriptions.json` (push subscriptions); both point at a Railway volume in production so they survive redeploys.
