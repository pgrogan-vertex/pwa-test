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
python main.py            # dev server, or:
gunicorn main:app --bind 0.0.0.0:8000
```

There is no test suite or linter configured in this repo yet.

## Deployment

Hosted on Railway (`railway.toml`, `builder = "nixpacks"`). Both `Procfile` and `railway.toml` run:
```
gunicorn main:app --bind 0.0.0.0:$PORT
```
Keep these two files' start commands in sync if either changes.

## Architecture

- `main.py` — Flask app. Two routes: `/` renders `templates/index.html`; `/api/hello` returns JSON. Uses Flask's default conventions (static files served from `static/` at `/static/...`, templates rendered from `templates/`) rather than explicit configuration — don't add custom static/template folder config unless the directory layout changes.
- `templates/index.html` — the PWA shell. Contains inline CSS and a `<script>` block that: registers `static/sw.js` as the service worker, tracks online/offline status via `navigator.onLine`, and implements the "Add to Home Screen" install button via the `beforeinstallprompt` event. Note: `beforeinstallprompt` only fires on Chromium-based browsers (desktop/Android) — iOS Safari never fires it, so the install button is silently inert there by design of the current implementation.
- `static/manifest.json` — PWA manifest (name, icons, display mode, theme color).
- `static/sw.js` — service worker. Cache-first strategy for shell assets (`/`, manifest, sw.js itself), network-first with a JSON offline fallback for `/api/*` requests. The cache name is version-stamped (`hello-pwa-vN`); **bump this version string whenever shell assets change**, since the `activate` handler deletes caches that don't match the current name — this is the mechanism that busts stale client caches.
- `static/icon.svg` — app icon, referenced by both the manifest and `apple-touch-icon`.
