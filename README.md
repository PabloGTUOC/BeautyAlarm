# BeautyAlarm

A self-hosted tracker for daily beauty and skincare routines — schedule your
products by weekday and time of day, get a notification when one is due, and
check it off. Runs on your own NAS; your data never leaves it.

## What it does

* **Routines** — register products and schedule each one to any set of weekdays,
  in a morning or night slot.
* **Reminders** — the phone raises a local notification when a routine is due,
  and keeps working when the server is offline.
* **Checklist** — mark each routine completed or skipped; state is stored
  server-side and survives restarts.
* **Progress** — calendar heatmap and streaks over your completion history.

## Stack

| Layer | Technology |
|---|---|
| Mobile app | Flutter (iOS/Android), Riverpod |
| API | FastAPI, SQLAlchemy 2, Alembic |
| Database | MySQL 8 |
| Deployment | Docker Compose on a home NAS, exposed via Cloudflare Tunnel |

## Repository layout

```
backend/           FastAPI service
  app/             models, schemas, routes, DB session
  alembic/         migrations
  entrypoint.sh    runs migrations, then uvicorn
frontend/          Flutter app
  lib/models/      API data classes
  lib/providers/   Riverpod state
  lib/screens/     today, manage, add-routine
  lib/services/    HTTP client
docker-compose.yml           production stack
docker-compose.override.yml  local dev overrides (auto-applied)
```

## Running it

Requires Docker with Compose v2.

```bash
docker compose up --build
```

The API comes up on <http://localhost:8000> with database migrations already
applied — no manual `alembic` step. Interactive docs at
<http://localhost:8000/docs>, liveness at `/healthz`.

`docker compose up` picks up `docker-compose.override.yml` automatically, which
adds hot reload and a source bind mount. For a production-shaped run:

```bash
docker compose -f docker-compose.yml up --build
```

Running the Flutter app against a local API:

```bash
cd frontend
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000   # Android emulator
```

## Documentation

* [specs.md](specs.md) — the locked v1 specification: scope, decisions, data
  model, API contract.
* [PLAN.md](PLAN.md) — gap register and the phased plan to close it, with
  current status.
* [CLAUDE.md](CLAUDE.md) — working conventions and the session log.
