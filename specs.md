# Beauty Routine Tracker — Specification

**Status:** v1 locked (Phase 0, 2026-09-21; frontend and notification decisions
revised 2026-09-21) · **Plan:** see [PLAN.md](PLAN.md)

## 1. Overview

A self-hosted tracker for daily beauty and skincare routines. A user registers
the products they use, schedules each one to specific days of the week and a
time of day, gets a notification when a routine is due, and checks it off. Over
time the app shows how consistent they have been.

Everything runs on the user's own hardware (a home NAS). The only third party
involved is the Cloudflare Tunnel that exposes it, and the browser vendor's push
service that delivers notifications.

## 2. Scope

### In scope for v1

* Managing products and the routines that use them (full create/read/update/delete).
* Scheduling a routine to any subset of weekdays, in a morning or night slot,
  with a notification time.
* Web Push notifications when a routine is due.
* A daily checklist with completed / skipped / pending states that survives a
  reload.
* A calendar and streak view over the completion history.
* Single-user, self-hosted deployment behind Cloudflare Tunnel.

### Explicitly out of scope for v1

* Multiple user accounts and sign-up flows (see D4 — the schema leaves room).
* Native iOS/Android applications. The client is an installable PWA (D1a).
* Product inventory, expiry tracking, shopping lists, photos, ingredient data.
* **Offline use.** The service worker precaches the app shell, so BeautyAlarm
  opens without a connection, but every screen needs the API — there is no
  cached checklist and no write queue. D6's upsert semantics were chosen to make
  a future write queue safe to replay; the queue itself is not built (PLAN.md G29).

## 3. Locked decisions

These resolve ambiguities in the original brief. Changing one is a spec change,
not an implementation detail.

| ID | Decision | Rationale |
|----|----------|-----------|
| **D1a** | **The client is a Vue 3 PWA**, installable to the home screen, not a Flutter app. | The client is a list, some checkboxes and a calendar. A PWA delivers that without an Android/iOS toolchain, app stores, or signing keys, and it updates by deploying static files. |
| **D1b** | **Notifications are Web Push (VAPID), driven by a scheduler inside the API.** A service worker receives them; the backend decides when to send. | A PWA cannot schedule its own alarms — the Notification Triggers API never shipped beyond a Chromium origin trial. Web Push is the only mechanism that reaches a closed app, and it is inherently server-driven. **Consequence: reminders require the NAS to be awake and able to reach the browser vendor's push service.** On iOS, push works only once the PWA is added to the home screen (Safari 16.4+). |
| **D2** | **Weekdays are ISO: 1 = Monday … 7 = Sunday.** Validated at the API; never stored outside 1–7. | Matches JavaScript's `getDay()` only after adjustment (it is 0=Sunday), and Python's `datetime.isoweekday()` exactly. The adjustment happens once, in the client's date helper. Python's `weekday()` is 0-based and must not be used. |
| **D3** | **`days_of_week` is a JSON array of ints**, not a bitmask. Sorted, unique, non-empty. | Readable in a `mysql` shell and in API responses. A bitmask saves bytes nobody is short of. |
| **D4** | **Single user.** No `User` table in v1, no login. Every table still carries a nullable `user_id` column so multi-user is an additive change later. | The brief marked multi-user optional. Adding the column now costs nothing; retrofitting it across four tables later costs a migration and a client rewrite. |
| **D5** | **Auth is a shared bearer token** (`API_TOKEN`), with Cloudflare Access in front of the tunnel as the real gate. | The brief put the API on the public internet with no auth at all. One token is the least machinery that closes that. A token held in browser storage is weak on its own, which is why Access carries the real weight. |
| **D6** | **One log row per `(routine_id, log_date)`**, enforced by a unique constraint. `completed` and `skipped` are both explicit user actions; the absence of a row means *pending*. No nightly job backfills skips. | Makes logging idempotent, makes "did I do it today" a lookup rather than a scan, and lets an offline client replay writes safely. |
| **D7** | **A streak is consecutive local days on which every routine due that day has a `completed` log.** Days with nothing due are neutral: they neither break a streak nor extend it. A `skipped` log breaks it. Today cannot extend a streak while still in progress, but does not break one unless it holds a skip. | "Or streak view" in the brief was unmeasurable. This is computable from the logs alone and matches what a user means by "I didn't miss a day". |
| **D8** | **A treatment is a product.** One `Product` model covers both words in the brief. | Nothing in v1 needs a multi-product procedure. If one appears, it becomes a `Treatment` grouping products — an additive change. |
| **D9** | **nginx serves the built PWA and reverse-proxies `/api/` to the API**, so the client and API share one origin behind one tunnel. | Same-origin removes CORS from production entirely, gives the service worker a clean scope, and means the tunnel exposes exactly one hostname. |
| **D10** | **The scheduler is an asyncio loop inside the API process**, waking every 60 seconds. No extra container, no extra dependency. | Minute granularity is all a skincare reminder needs. It does mean the API must run a **single** worker — two workers would send every notification twice. |

## 4. Conventions

* **Timezone.** The deployment has exactly one timezone, set by the `APP_TIMEZONE`
  environment variable (IANA name, e.g. `Europe/Madrid`). All "today", "due",
  scheduling and streak logic resolves against it.
* **Timestamps** are stored UTC. `DailyLog.timestamp` is the exact moment the
  user acted.
* **Local dates.** `DailyLog.log_date` is the *local* calendar date the log
  belongs to, stored as `DATE`. This is the column uniqueness, "today", and
  streaks are computed on — never the UTC timestamp, which would put a 00:30
  check-off on the wrong day.
* **Times of day** (`notification_time`) are local wall-clock `TIME` values with
  no date and no offset, e.g. `08:00:00`.
* **`time_period` is a display bucket, not a trigger.** `notification_time` is
  the single source of truth for when a notification fires. If
  `notification_time` is null, nothing is scheduled and the routine simply
  appears in its morning or night section of the checklist.

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
| `product_id` | INT NOT NULL FK → `products.id` | `ON DELETE RESTRICT` |
| `days_of_week` | JSON NOT NULL | sorted unique ints in 1–7, non-empty (D2, D3) |
| `time_period` | ENUM('morning','night') NOT NULL | display bucket only |
| `notification_time` | TIME NULL | null means no notification |
| `is_active` | BOOL NOT NULL DEFAULT TRUE | pause without deleting |
| `end_date` | DATE NULL | routine stops being due after this local date |

### `daily_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `routine_id` | INT NOT NULL FK → `routines.id` | `ON DELETE CASCADE` |
| `log_date` | DATE NOT NULL | local date (§4) |
| `timestamp` | DATETIME NOT NULL | UTC instant of the action |
| `status` | ENUM('completed','skipped') NOT NULL | absence of a row = pending (D6) |
| | UNIQUE (`routine_id`, `log_date`) | |

### `push_subscriptions`
| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `endpoint` | VARCHAR(500) NOT NULL UNIQUE | the browser vendor's push endpoint |
| `p256dh` | VARCHAR(255) NOT NULL | client public key |
| `auth` | VARCHAR(255) NOT NULL | client auth secret |
| `created_at` | DATETIME NOT NULL | |
| `last_failure_at` | DATETIME NULL | set when a send fails; a 404/410 deletes the row instead |

## 6. API

All routes require `Authorization: Bearer $API_TOKEN` except `/healthz` (D5).

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | liveness + DB reachability; unauthenticated |
| GET/POST | `/products/` | list (excludes archived by default) / create |
| GET/PATCH/DELETE | `/products/{id}` | fetch / partial update / archive |
| GET/POST | `/routines/` | list / create |
| GET/PATCH/DELETE | `/routines/{id}` | fetch / partial update / delete |
| GET | `/routines/today` | routines due today with each one's log status |
| GET/POST | `/logs/` | recent logs / upsert a log for `(routine_id, log_date)` |
| DELETE | `/logs/{id}` | undo a check-off |
| GET | `/logs/calendar?from=&to=` | per-day due/completed/skipped counts |
| GET | `/stats/streak` | current and longest streak per D7 |
| GET | `/push/public-key` | the VAPID public key the client subscribes with |
| POST | `/push/subscribe` | register or refresh a browser subscription |
| POST | `/push/unsubscribe` | drop a subscription by endpoint |
| POST | `/push/test` | send a test notification to every subscription |

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
Per D1b, the API runs a scheduler that wakes every minute, resolves the current
local time, and pushes to every registered subscription for each routine that is
due now, has a matching `notification_time`, and has no log for today — a
routine already checked off does not nag. Each minute fires at most once.

The client registers a service worker, asks for notification permission from a
user gesture, subscribes with the VAPID public key, and posts the subscription
to the API. The service worker displays incoming pushes and focuses the
checklist when one is clicked. A push that returns 404 or 410 means the
subscription is dead and the row is deleted.

### Checklist
The today view lists routines due today, split into Morning and Night, each
showing completed / skipped / pending from the server. Checking off writes a log
and unchecking deletes it. State survives reloads because it is read from the
API, not held in component state.

### Progress
A calendar heatmap of completion per day plus current and longest streak (D7),
and a 30-day adherence percentage per routine.

## 8. Infrastructure

Target host: AMD Ryzen, 16 GB RAM, home NAS. One `docker-compose.yml`:

* **`db`** — MySQL 8, data bind-mounted to a NAS path, not published to the host
  network. Healthchecked.
* **`api`** — FastAPI on uvicorn, single worker (D10). Runs `alembic upgrade
  head` on start, so a clean volume boots to a working API with no manual steps.
  Waits for `db` to be healthy.
* **`web`** — nginx serving the built PWA and proxying `/api/` to `api` (D9).
* **`cloudflared`** — Cloudflare Tunnel exposing `web` only.

Development overrides (`--reload`, source bind mount, published ports) live in
`docker-compose.override.yml` and never ship in the image.

Secrets come from a git-ignored `.env`. Nightly `mysqldump` to the NAS with a
documented restore path.

## 9. Security

* Bearer token on every route but `/healthz` (D5), plus Cloudflare Access. The
  token lives in browser storage, so Access is what actually keeps strangers
  out; the token stops an accidentally-open tunnel from being trivially usable.
* Same-origin in production (D9), so CORS is not part of the production path.
  `CORS_ORIGINS` / `CORS_ORIGIN_REGEX` exist for the Vite dev server only.
* VAPID private key comes from the environment and is never sent to the client.
* No credentials in the repo. `.env` is git-ignored; `.env.example` documents
  the keys.
* The database port is never published outside the compose network.

## 10. Open questions

Deferred, not forgotten:

* Whether paused routines should still appear greyed out on the checklist.
* Whether a skipped day should be distinguishable from a missed day in the
  calendar view.
* Retention: the logs table grows ~5 rows/day forever. No pruning planned.
* Routines have no `start_date`, so nothing distinguishes "this routine did not
  exist yet" from "it was missed". The calendar works around it by treating days
  before the first recorded log as unknown, which is right for a fresh install
  and wrong for a routine added later (PLAN.md G28).
* Whether the scheduler should retry a push that failed transiently, or leave
  the reminder missed.
