# BeautyAlarm

A self-hosted tracker for daily beauty and skincare routines — schedule your
products by weekday and time of day, get a push notification when one is due,
and check it off. Runs on your own NAS; your data never leaves it.

## What it does

* **Routines** — register products and schedule each to any set of weekdays, in
  a morning or night slot, with an optional notification time.
* **Reminders** — Web Push notifications when a routine is due. A routine you
  have already checked off does not nag.
* **Checklist** — mark each routine done or skipped; state lives on the server
  and survives a reload.
* **Progress** — streaks, a 12-week calendar heatmap, and 30-day adherence per
  routine.

## Stack

| Layer | Technology |
|---|---|
| Client | Vue 3 + Vite, installable PWA |
| API | FastAPI, SQLAlchemy 2, Alembic |
| Database | MySQL 8 |
| Notifications | Web Push (VAPID), scheduled inside the API |
| Deployment | Docker Compose on a home NAS, behind Cloudflare Tunnel |

## Repository layout

```
backend/           FastAPI service
  app/             models, schemas, routers, push delivery, scheduler
  alembic/         migrations
  tests/           pytest suite
  entrypoint.sh    runs migrations, then uvicorn
frontend/          Vue PWA
  src/views/       today, routines, editor, progress, settings
  src/stores/      Pinia state
  public/push-sw.js  service-worker push handlers
  nginx.conf       serves the build, proxies /api
scripts/backup.sh  nightly mysqldump with a documented restore
```

## Running it

Requires Docker with Compose v2.

```bash
cp .env.example .env     # then change the passwords
docker compose up --build
```

The API migrates itself on start — no manual `alembic` step. `docker compose up`
picks up `docker-compose.override.yml`, which adds hot reload, source mounts and
published ports:

* app — <http://localhost:8080>
* API — <http://localhost:8000>, docs at `/docs`, liveness at `/healthz`

For a production-shaped run (no reload, no published database port):

```bash
docker compose -f docker-compose.yml up --build
docker compose --profile tunnel up -d     # adds Cloudflare Tunnel
```

### Turning on notifications

```bash
docker compose exec api python scripts/generate_vapid_keys.py
```

Put the pair in `.env` as `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY`, restart, then
open Settings in the app and turn notifications on. On iOS you must add
BeautyAlarm to your home screen first — Safari only allows push from an
installed PWA.

Without those keys the app works fine; notifications are simply disabled and the
scheduler stays idle.

### Working on it directly

```bash
cd backend  && pip install -r requirements-dev.txt && pytest
cd frontend && npm install && npm run dev      # proxies /api to :8000
cd frontend && npm test && npm run typecheck
```

## Documentation

* [specs.md](specs.md) — the locked specification: scope, decisions D1–D10, data
  model, API contract.
* [PLAN.md](PLAN.md) — gap register and phase status, including what is still open.
* [CLAUDE.md](CLAUDE.md) — working conventions and the session log.
