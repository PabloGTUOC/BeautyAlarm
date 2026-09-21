# Beauty Routine Tracker — Specification

**Status:** v1 locked (Phase 0, 2026-09-21) · **Plan:** see [PLAN.md](PLAN.md)

## 1. Overview

A self-hosted tracker for daily beauty and skincare routines. A user registers
the products they use, schedules each one to specific days of the week and a
time of day, gets a notification on their phone when a routine is due, and
checks it off. Over time the app shows how consistent they have been.

The backend runs on the user's own hardware (a home NAS); the Flutter app talks
to it over a Cloudflare Tunnel. Nothing is hosted by a third party except the
tunnel itself.

## 2. Scope

### In scope for v1

* Managing products and the routines that use them (full create/read/update/delete).
* Scheduling a routine to any subset of weekdays, in a morning or night slot,
  with a notification time.
* Local notifications on the phone when a routine is due.
* A daily checklist with completed / skipped / pending states that survives an
  app restart.
* A calendar and streak view over the completion history.
* Single-user, self-hosted deployment behind Cloudflare Tunnel with token auth.

### Explicitly out of scope for v1

* Multiple user accounts and sign-up flows (see D4 — the schema leaves room).
* Server-pushed notifications via FCM/APNs (see D1).
* Multi-device notification consistency. If the same account is installed on two
  phones, both schedule their own alarms from the same routine data. They will
  agree as long as both have synced.
* Product inventory, expiry tracking, shopping lists, photos, ingredient data.
* A web UI. The API is consumed by the Flutter app only.

## 3. Locked decisions

These resolve ambiguities in the original brief. Changing one is a spec change,
not an implementation detail.

| ID | Decision | Rationale |
|----|----------|-----------|
| **D1** | **Local notifications.** The phone schedules its own alarms with `flutter_local_notifications` + `timezone`. No FCM, no Firebase project, no server-side scheduler. | Alarms must fire when the NAS is off or the tunnel is down. A server push path would make a personal skincare reminder depend on three moving parts instead of zero. |
| **D2** | **Weekdays are ISO: 1 = Monday … 7 = Sunday.** Validated at the API; never stored outside 1–7. | Matches Dart `DateTime.weekday` and Python `datetime.isoweekday()` exactly, so no translation layer exists to get wrong. Note that Python's `weekday()` is 0-based and must not be used. |
| **D3** | **`days_of_week` is a JSON array of ints**, not a bitmask. Sorted, unique, non-empty. | Readable in a `mysql` shell and in API responses; the migration already uses it. A bitmask saves bytes nobody is short of. |
| **D4** | **Single user.** No `User` table in v1, no login. Every table still carries a nullable `user_id` column from the first migration so multi-user is an additive change later. | The brief marked multi-user optional. Adding the column now costs nothing; retrofitting it across three tables later costs a migration and a client rewrite. |
| **D5** | **Auth is a shared bearer token** (`API_TOKEN`) checked by middleware on every route except `/healthz`, with Cloudflare Access in front of the tunnel as a second layer. | The brief put the API on the public internet with no auth at all. One token is the least machinery that closes that. |
| **D6** | **One log row per `(routine_id, log_date)`**, enforced by a unique constraint. `completed` and `skipped` are both explicit user actions; the absence of a row means *pending*. No nightly job backfills skips. | Makes logging idempotent, makes "did I do it today" a lookup rather than a scan, and avoids a background worker that would need the NAS awake at midnight. |
| **D7** | **A streak is consecutive local days on which every routine due that day has a `completed` log.** Days with nothing due are neutral: they neither break a streak nor extend it. A `skipped` log breaks it. | "Or streak view" in the brief was unmeasurable. This definition is computable from the logs alone and matches what a user means by "I didn't miss a day". |
| **D8** | **A treatment is a product.** One `Product` model covers both words in the brief. | Nothing in v1 needs a multi-product procedure. If one appears, it becomes a `Treatment` grouping products — an additive change. |

## 4. Conventions

* **Timezone.** The deployment has exactly one timezone, set by the `APP_TIMEZONE`
  environment variable (IANA name, e.g. `Europe/Madrid`). All "today", "due",
  and streak logic resolves against it. The phone uses its own device timezone
  for scheduling alarms; the two are expected to match in practice, and a
  mismatch only shifts when the alarm fires, never what gets recorded.
* **Timestamps** are stored UTC. `DailyLog.timestamp` is the exact moment the
  user acted.
* **Local dates.** `DailyLog.log_date` is the *local* calendar date (per
  `APP_TIMEZONE`) the log belongs to, stored as `DATE`. This is the column
  uniqueness, "today", and streaks are computed on — never the UTC timestamp,
  which would put a 00:30 check-off on the wrong day.
* **Times of day** (`notification_time`) are local wall-clock `TIME` values with
  no date and no offset, e.g. `08:00:00`.
* **`time_period` is a display bucket, not a trigger.** `notification_time` is
  the single source of truth for when a notification fires. If
  `notification_time` is null, no notification is scheduled for that routine and
  it simply appears in its morning or night section of the checklist.

## 5. Data model

All tables carry a nullable `user_id INT` per D4, unused in v1.

### `products`
| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `name` | VARCHAR(255) NOT NULL | indexed |
| `brand` | VARCHAR(255) NULL | |
| `notes` | VARCHAR(1000) NULL | |
| `archived_at` | DATETIME NULL | soft delete; archived products keep their history and stop appearing in pickers |

### `routines`
| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `product_id` | INT NOT NULL FK → `products.id` | `ON DELETE RESTRICT` — a product with routines cannot be hard-deleted |
| `days_of_week` | JSON NOT NULL | sorted unique ints in 1–7, non-empty (D2, D3) |
| `time_period` | ENUM('morning','night') NOT NULL | display bucket only |
| `notification_time` | TIME NULL | null means no alarm |
| `is_active` | BOOL NOT NULL DEFAULT TRUE | pause without deleting |
| `end_date` | DATE NULL | routine stops being due after this local date; supports courses like "retinol 3×/week for 8 weeks" |

### `daily_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `routine_id` | INT NOT NULL FK → `routines.id` | `ON DELETE CASCADE` |
| `log_date` | DATE NOT NULL | local date (§4) |
| `timestamp` | DATETIME NOT NULL | UTC instant of the action |
| `status` | ENUM('completed','skipped') NOT NULL | absence of a row = pending (D6) |
| | UNIQUE (`routine_id`, `log_date`) | |

## 6. API

All routes require `Authorization: Bearer $API_TOKEN` except `/healthz` (D5).

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | liveness + DB reachability; unauthenticated |
| GET/POST | `/products/` | list (excludes archived by default) / create |
| GET/PATCH/DELETE | `/products/{id}` | fetch / partial update / archive |
| GET/POST | `/routines/` | list / create |
| GET/PATCH/DELETE | `/routines/{id}` | fetch / partial update / delete |
| GET | `/routines/today` | routines due today with each one's log status — the checklist in one call |
| POST | `/logs/` | upsert a log for `(routine_id, log_date)` |
| DELETE | `/logs/{id}` | undo a check-off |
| GET | `/logs/calendar?from=&to=` | per-day completion summary for the calendar |
| GET | `/stats/streak` | current and longest streak per D7 |

A routine is **due on a local date** when it is `is_active`, the date's ISO
weekday is in `days_of_week`, and the date is on or before `end_date` (if set).

Referencing a missing `product_id` or `routine_id` returns **404**, never a 500
from a foreign-key violation.

## 7. Features

### Routine configuration
Add, edit, pause, and delete routines. Pick a product from the existing list or
create a new one inline — the same product is never duplicated by adding a
second routine for it. Choose any subset of weekdays, a morning or night slot,
and optionally a notification time.

### Notifications
Per D1, the app schedules one recurring local notification per routine per
selected weekday, at `notification_time`, in the device timezone. The schedule is
rebuilt whenever routines change and re-registered after a device reboot.
Tapping a notification opens the checklist. Routines with no
`notification_time`, or that are paused or past `end_date`, schedule nothing.

Android needs `POST_NOTIFICATIONS` (13+), exact-alarm permission (12+), and
`RECEIVE_BOOT_COMPLETED`. iOS requests notification permission on first launch.

### Checklist
The today screen lists routines due today, split into Morning and Night, each
showing completed / skipped / pending from the server. Checking off writes a log
and unchecking deletes it. State survives restarts because it is read back from
the API, not held in widget state.

### Progress
A calendar heatmap of completion per day plus current and longest streak (D7),
and a 30-day adherence percentage per routine.

### Offline
The checklist caches the last successful response so it renders without the
tunnel, marked stale. Writes made offline are queued and replayed on
reconnect; the upsert semantics of D6 make replay safe.

## 8. Infrastructure

Target host: AMD Ryzen, 16 GB RAM, home NAS. One `docker-compose.yml`:

* **`db`** — MySQL 8, data bind-mounted to a NAS path, not published to the host
  network. Healthchecked.
* **`api`** — FastAPI on uvicorn. Runs `alembic upgrade head` on start, so a
  clean volume boots to a working API with no manual steps. Waits for `db` to
  be healthy.
* **`cloudflared`** — Cloudflare Tunnel exposing `api` only.

Development overrides (`--reload`, source bind mount, published ports) live in
`docker-compose.override.yml` and never ship in the image.

Secrets come from a git-ignored `.env`. Nightly `mysqldump` to the NAS with a
documented restore path.

## 9. Security

* Bearer token on every route but `/healthz` (D5), plus Cloudflare Access.
* CORS origins come from configuration; the permissive localhost rule is
  development-only.
* No credentials in the repo. `.env` is git-ignored and `.env.example` documents
  the keys.
* The database port is never published outside the compose network.

## 10. Open questions

Deferred, not forgotten:

* Whether paused routines should still appear greyed out on the checklist.
* Whether a skipped day should be distinguishable from a missed (never touched)
  day in the calendar view.
* Retention: the logs table grows ~5 rows/day forever. No pruning planned.
