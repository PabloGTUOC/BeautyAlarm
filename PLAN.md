# BeautyAlarm — Delivery Plan

Living document. Update the status column as work lands; the gap IDs are stable
and referenced from commit messages and [CLAUDE.md](CLAUDE.md).

**Last updated:** 2026-09-21

## Status at a glance

| Phase | Scope | Closes | Status |
|---|---|---|---|
| 0 | Lock the spec | S1–S14 | ✅ Done |
| 1 | Make it boot | G1, G19, G21 | ✅ Done† |
| 2 | Backend data model and API | G8, G12–G16 | ⬜ Not started |
| 3 | Frontend catches up | G3, G5, G6, G9, G10, G11, G23 | ⬜ Not started |
| 4 | Notifications | G2, G4 | ⬜ Not started |
| 5 | Progress view | G7 | ⬜ Not started |
| 6 | Infra hardening | G17, G18, G20 | ⬜ Not started |
| 7 | Tests and CI | G22 | ⬜ Not started |

† Code complete and locally verified; the containerised run is still unproven —
see Phase 1 below and the session log in [CLAUDE.md](CLAUDE.md).

## Gap register

Gaps found reviewing the code against the original brief (2026-09-21). The
spec-level gaps (S-series) were resolved in Phase 0 and are recorded as
decisions D1–D8 in [specs.md](specs.md).

### Blockers — the stack does not work without these

| ID | Gap | Location | Status |
|---|---|---|---|
| G1 | Tables are never created: no `alembic upgrade`, no `create_all`, no entrypoint | `backend/Dockerfile`, `docker-compose.yml` | ✅ Phase 1 |
| G2 | No notification code at all — package declared, never imported | `frontend/lib/**` | ⬜ Phase 4 |
| G3 | API base URL hardcoded to `127.0.0.1`, unreachable from emulator or device | `frontend/lib/services/api_service.dart` | ⬜ Phase 3 |
| G4 | `INTERNET` permission only in the debug manifest; release builds cannot reach the API | `frontend/android/app/src/main/AndroidManifest.xml` | ⬜ Phase 4 |

### Promised in the spec, missing in code

| ID | Gap | Location | Status |
|---|---|---|---|
| G5 | No day-of-week filtering — "Today's Routine" shows every routine every day | `frontend/lib/screens/home_screen.dart` | ⬜ Phase 3 |
| G6 | Completion state is local and ephemeral; resets on every rebuild | `frontend/lib/widgets/routine_card.dart` | ⬜ Phase 3 |
| G7 | No calendar or streak view | — | ⬜ Phase 5 |
| G8 | No PUT/PATCH/DELETE on any resource; delete button is a `// TODO` | `backend/app/main.py`, `frontend/lib/screens/manage_routines_screen.dart` | ⬜ Phase 2 |
| G9 | `notification_time` never set by the UI; days hardcoded to `[1..7]` | `frontend/lib/screens/add_routine_screen.dart` | ⬜ Phase 3 |
| G10 | Every routine creates a new product — duplicates accumulate | `frontend/lib/providers/routine_provider.dart` | ⬜ Phase 3 |
| G11 | No skip action anywhere | — | ⬜ Phase 3 |

### Correctness and safety

| ID | Gap | Status |
|---|---|---|
| G12 | Almost every column nullable; no validation on `days_of_week` values or `notification_time` format | ⬜ Phase 2 |
| G13 | Bad `product_id` returns a 500 `IntegrityError` instead of 404 | ⬜ Phase 2 |
| G14 | No unique constraint on (routine, day) → duplicate logs | ⬜ Phase 2 |
| G15 | No authentication, on an API the spec puts on the public internet | ⬜ Phase 2 |
| G16 | CORS accepts any localhost port — dev-only config with no production path | ⬜ Phase 2 |

### Infrastructure and quality

| ID | Gap | Status |
|---|---|---|
| G17 | DB credentials hardcoded in compose; 3306 published to the host | 🚧 Phase 6 — the 3306 publish moved to the dev override in Phase 1, so it is gone from the production stack; the hardcoded credentials remain |
| G18 | Named Docker volume rather than the NAS path the spec calls for; no backup | ⬜ Phase 6 |
| G19 | No healthcheck — the API races MySQL on boot | ✅ Phase 1 |
| G20 | No `cloudflared` service | ⬜ Phase 6 |
| G21 | `--reload` baked into the production image CMD | ✅ Phase 1 |
| G22 | `widget_test.dart` references a nonexistent `MyApp` and will not compile; no backend tests; no CI | ⬜ Phase 7 |
| G23 | `getProducts()` is dead code; `getLogs()` is fetched but never read | ⬜ Phase 3 |

## Phases

### Phase 0 — Lock the spec ✅

Rewrite `specs.md` around decisions D1–D8: notification architecture, weekday
convention, timezone and local-date rule, log semantics, streak definition,
auth model, product/treatment unification, lifecycle fields. Add explicit
non-goals. Every later phase cites it.

**Exit criterion:** no open architectural question blocks an implementation phase.

### Phase 1 — Make it boot ✅

*Closes G1, G19, G21.*

* `backend/entrypoint.sh` runs `alembic upgrade head`, then execs the server.
* Dockerfile drops `--reload`; dev overrides move to `docker-compose.override.yml`.
* MySQL healthcheck plus `depends_on: condition: service_healthy`.
* `GET /healthz` reporting DB reachability.

**Exit criterion:** `docker compose up` on a clean volume yields an API serving
requests against migrated tables, with no manual steps.

**Outstanding:** the exit criterion has not been observed against real
containers. The session that did this work had Docker Hub blocked by egress
policy and could not pull `python:3.11-slim` or `mysql:8.0`, so the entrypoint,
migration, API round-trips, and both `/healthz` paths were exercised directly
against SQLite instead. The image build, the MySQL healthcheck command, and the
`service_healthy` gating remain unproven. Run `docker compose up --build` on a
clean volume before relying on this phase.

### Phase 2 — Backend data model and API

*Closes G8, G12–G16.*

One migration adding: NOT NULL where the model requires it, `log_date DATE` with
`UNIQUE(routine_id, log_date)`, `Routine.is_active` and `end_date`,
`Product.archived_at`, nullable `user_id` on all three tables, FK `ondelete`
rules, `notification_time` as `TIME`. Pydantic validators for weekdays 1–7
(sorted, unique, non-empty). Full CRUD for products and routines, upsert for
logs, 404 on missing foreign keys. New endpoints `GET /routines/today`,
`GET /logs/calendar`, `GET /stats/streak`. Bearer-token middleware and
configuration-driven CORS.

**Exit criterion:** every endpoint in specs.md §6 exists and behaves as specified.

### Phase 3 — Frontend catches up

*Closes G3, G5, G6, G9, G10, G11, G23.*

`API_BASE_URL` via `--dart-define` defaulting to `10.0.2.2`; bearer token header.
Today screen driven by `/routines/today`, so checkboxes hydrate from the server
and can be unchecked. Skip action. Product autocomplete against `/products/`
instead of blind creation. Edit and delete wired to the Phase 2 endpoints.
Day-of-week picker and time picker in the add/edit form.

**Exit criterion:** the checklist shows only today's routines and its state
survives an app restart.

### Phase 4 — Notifications

*Closes G2, G4.*

`NotificationService` over `flutter_local_notifications`; promote `timezone` to
a direct dependency. Android: `INTERNET` and `POST_NOTIFICATIONS` in the main
manifest, exact-alarm permission, `RECEIVE_BOOT_COMPLETED` with reschedule on
boot, runtime permission request on 13+. iOS: Darwin initialization settings and
permission request. One recurring `zonedSchedule` per routine per weekday from
`notification_time` using the D2 mapping; full reschedule after any routine
mutation; cancel on delete. Tapping a notification deep-links to the checklist.

**Exit criterion:** a routine scheduled for the next minute raises a
notification on a physical device, and still does after a reboot.

### Phase 5 — Progress view

*Closes G7.*

Calendar heatmap plus current and longest streak per D7, and 30-day adherence
per routine, off the Phase 2 endpoints.

### Phase 6 — Infrastructure hardening

*Closes G17, G18, G20.*

`.env` and `env_file`, secrets out of the repo, `.env.example` committed, 3306
unpublished. DB volume bind-mounted to the NAS path. `cloudflared` service plus
a Cloudflare Access policy. `mysqldump` backup cron with a documented restore.
Offline read cache and queued writes in the app.

### Phase 7 — Tests and CI

*Closes G22.*

pytest + httpx against a throwaway database covering every endpoint and the
streak math. Replace the stale `widget_test.dart` with provider tests over a
mocked `ApiService` plus a today-screen widget test. GitHub Actions running
`pytest`, `flutter analyze`, `flutter test`.

## Sequencing notes

* Phases 1 and 2 are the unlock — the stack does not survive a cold start today,
  and frontend work cannot be verified until it does.
* Phases 4 and 5 are independent of each other and may be reordered.
* Phase 6 must land before the API is ever exposed through the tunnel; Phase 2's
  auth work is a prerequisite for it.
