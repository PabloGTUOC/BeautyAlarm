# BeautyAlarm — Delivery Plan

Living document. Update the status column as work lands; the gap IDs are stable
and referenced from commit messages and [CLAUDE.md](CLAUDE.md).

**Last updated:** 2026-09-24

## Status at a glance

| Phase | Scope | Closes | Status |
|---|---|---|---|
| 0 | Lock the spec | S1–S14 | ✅ Done |
| 1 | Make it boot | G1, G19, G21 | ✅ Done† |
| 2 | Backend data model and API | G8, G12–G16 | ✅ Done |
| 3 | Vue PWA client | G3, G5, G6, G9, G10, G11, G23, G24, G26 | ✅ Done |
| 4 | Web Push notifications | G2, G25 | ✅ Done‡ |
| 5 | Progress view | G7 | ✅ Done |
| 6 | Infra hardening | G17, G18, G20, G27 | ✅ Done† |
| 7 | Tests and CI | G22 | ✅ Done |
| 8 | Multi-product routines and tracked services | G28, G30–G39 | ✅ Done§ |
| 9 | Household accounts | G40–G45 | ✅ Done¶ |

† Resolved on 2026-09-21: the stack was built and run on the user's machine.
Both images build, the MySQL healthcheck and `service_healthy` gating work, all
three migrations apply on real MySQL, and nginx serves the PWA and proxies
`/api/`. See the session log in [CLAUDE.md](CLAUDE.md).

‡ Delivery to a real browser push service is still unproven. VAPID keys are
configured and the scheduler starts, but no browser had subscribed at the time
of writing. The selection logic, subscription storage and endpoint behaviour are
covered by tests.

§ Verified on the running stack against real MySQL: both migrations applied to
live data with no loss, 80 backend and 36 frontend tests pass, and both features
were exercised end to end through the API. The UI was reviewed and measured in a
headless browser across five states, three widths and both colour schemes; it
has not been driven on a real phone.

¶ Verified against live MySQL: two accounts registered through the API, each
invisible to the other across every endpoint, sign-out revoking server-side.

**Open gaps: G29, G46, G47.** Everything else is closed or obsolete.

## Gap register

Gaps found reviewing the code against the original brief (2026-09-21), plus
those discovered while building. Spec-level gaps (S-series) were resolved in
Phase 0 as decisions D1–D10 in [specs.md](specs.md).

The client moved from Flutter to a Vue PWA partway through (D1a), which closed
some gaps by deletion and made one obsolete.

### Blockers

| ID | Gap | Status |
|---|---|---|
| G1 | Tables never created: no `alembic upgrade`, no `create_all`, no entrypoint | ✅ Phase 1 — `backend/entrypoint.sh` migrates, then execs the server |
| G2 | No notification code at all | ✅ Phase 4 — Web Push end to end (D1b) |
| G3 | API base URL hardcoded to `127.0.0.1` | ✅ Phase 3 — same-origin `/api` behind nginx and the Vite proxy (D9) |
| G4 | `INTERNET` permission only in the Android debug manifest | ⬛ Obsolete — there is no Android app |

### Promised in the spec, missing in code

| ID | Gap | Status |
|---|---|---|
| G5 | No day-of-week filtering — "Today's Routine" showed everything every day | ✅ Phase 3 — the view is driven by `GET /routines/today` |
| G6 | Completion state local and ephemeral | ✅ Phase 3 — hydrated from the API; verified to survive a reload |
| G7 | No calendar or streak view | ✅ Phase 5 — heatmap, streak tiles, 30-day adherence |
| G8 | No PUT/PATCH/DELETE; delete button was a `// TODO` | ✅ Phase 2 |
| G9 | `notification_time` never set by the UI; days hardcoded to `[1..7]` | ✅ Phase 3 — weekday chips and a time picker |
| G10 | Every routine created a new product | ✅ Phase 3 — `findOrCreateProduct` matches on name and brand |
| G11 | No skip action | ✅ Phase 3 |

### Correctness and safety

| ID | Gap | Status |
|---|---|---|
| G12 | Nullable columns everywhere; no validation of days or times | ✅ Phase 2 |
| G13 | Bad `product_id` returned a 500 | ✅ Phase 2 — 404 |
| G14 | No unique constraint on (routine, day) | ✅ Phase 2 — `uq_daily_logs_routine_date` |
| G15 | No authentication | ✅ Phase 2 — bearer token (D5) |
| G16 | CORS accepted any localhost port | ✅ Phase 2 — configuration-driven; production is same-origin |

### Infrastructure and quality

| ID | Gap | Status |
|---|---|---|
| G17 | DB credentials hardcoded; 3306 published | ✅ Phase 6 — `.env`, and 3306 only in the dev override |
| G18 | Named volume rather than NAS storage; no backup | ✅ Phase 6 — `DB_DATA_PATH` bind mount, `scripts/backup.sh` |
| G19 | No healthcheck — the API raced MySQL | ✅ Phase 1 |
| G20 | No `cloudflared` service | ✅ Phase 6 — behind the `tunnel` profile |
| G21 | `--reload` in the production image | ✅ Phase 1 |
| G22 | Stale `widget_test.dart`; no backend tests; no CI | ✅ Phase 7 — 52 backend + 19 frontend tests, GitHub Actions |
| G23 | `getProducts()` dead, `getLogs()` unused | ✅ Phase 3 — deleted with the Flutter client |

### Found while building

| ID | Gap | Status |
|---|---|---|
| G24 | `frontend/` held a Flutter client after the move to a PWA (D1a) | ✅ Phase 3 — removed and replaced |
| G25 | No push subscription storage, VAPID keys or scheduler | ✅ Phase 4 |
| G26 | No web app manifest, service worker or icons | ✅ Phase 3 — `vite-plugin-pwa`, generated icons |
| G27 | The built PWA had nothing serving it | ✅ Phase 6 — nginx image proxying `/api` (D9) |
| **G28** | **Routines have no `start_date`**, so nothing distinguishes "did not exist yet" from "missed". The calendar treats days before the first log as unknown, which is right for a fresh install and wrong for a routine added later. Confirmed against live data on 2026-09-24: routines created two days earlier reported `due: 13` over a 30-day adherence window. | ✅ Phase 8 — `start_date` added in M2, honoured by `is_due`; the client-side workaround in `ProgressView` is gone |
| **G29** | **No offline support.** The shell is precached so the app opens, but every screen needs the API: no cached checklist, no write queue. | ⬜ **Open** — D6's upsert semantics already make replay safe |

### Phase 8 — requested after first real use (2026-09-24)

| ID | Gap | Status |
|---|---|---|
| **G30** | **A routine holds exactly one product.** A layered routine — hyaluronic acid, then peptides, then moisturiser — cannot be expressed except as three separate routines that must be ticked separately. | ✅ Phase 8 — `routine_products` join table with `position` (D8a) |
| **G31** | **Routines have no name.** Every label in the UI is `routine.product.name`, which has nothing to borrow from once a routine has three products or none. | ✅ Phase 8 — required `name` column, backfilled from the old product name plus slot |
| **G32** | **Every routine is a weekday schedule.** Things done on an interval rather than a schedule — a haircut, a facial — cannot be modelled at all. | ✅ Phase 8 — `kind` plus `target_interval_days` (D11) |
| **G33** | **Streaks and adherence would count tracked routines as daily misses.** D7 asks whether every routine due that day is completed; a tracked routine is never due on a given day, so leaving it in pins the streak at zero forever. | ✅ Phase 8 — `scheduled_only()` scopes streaks and adherence (D12) |
| **G34** | **Today has no Tracking section** and the API returns no elapsed-time data, so "23 days since your last haircut" cannot be shown. | ✅ Phase 8 — `tracking` section on `/routines/today` |
| **G35** | **The scheduler cannot notify on an elapsed interval** — selection is purely weekday plus `notification_time`. | ✅ Phase 8 — `tracked_overdue_at()`, repeating every second day (D12) |
| **G36** | **The routine editor is single-product and schedule-only** — no kind toggle, no ordered product picker, no interval field. | ✅ Phase 8 — kind toggle, ordered product picker, interval field |
| **G38** | **Every touch target was below the 44px minimum**, measured on a 390px viewport: buttons 37px, tab-bar links 35px, weekday chips 30px — 24 of 24 controls failing, in an app used one-handed and half-awake. Found by measuring the rendered PWA, not by reading the CSS. | ✅ Phase 8 — `--tap` floor applied to every control; 0 of 24 failing, verified in both themes at 320/390/430px |
| **G39** | **The Today view's three non-happy states were never designed or rendered.** Finishing every routine produced a void: struck-through rows and empty space, no acknowledgement, and the streak hidden on another tab. A failed load showed the raw server string over a blank screen with no retry. The empty state told a user with six routines to "add a routine to get started" on a rest day, and offered no control to do it with. All three were found by stubbing states, not by reading code. | ✅ Phase 8 — completion state carrying the streak, plain-language error with a retry, and an empty state that tells first run apart from a rest day |
| **G37** | **The test suite was not hermetic.** `conftest.py` set `DATABASE_URL`, `APP_TIMEZONE` and `API_TOKEN` but not the VAPID pair, so running it inside the `api` container inherited the deployment's real keys from `.env`: "unconfigured" tests saw a configured app and the scheduler started against a database the fixtures never created. Green in CI, red on the machine the stack runs on. | ✅ Phase 8 — `conftest.py` clears both VAPID keys |

### Phase 9 — household accounts (2026-09-25)

| ID | Gap | Status |
|---|---|---|
| **G40** | **One shared API token could not tell two people apart.** The whole app was single-user: one token in browser storage, no accounts, no sign-in. | ✅ Phase 9 — `users` table, argon2id passwords, `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me` (D5a) |
| **G41** | **No sessions.** Nothing to revoke, nothing to expire, nothing to sign out of. | ✅ Phase 9 — server-side `sessions` table, opaque token stored only as a SHA-256, httpOnly `SameSite=Lax` cookie, swept on expiry |
| **G42** | **Every query was unscoped.** With accounts added but filters missing, one housemate would silently see another's products, routines, logs and streaks. No error, just wrong rows. | ✅ Phase 9 — every read and write filters on `user_id`, plus `tests/test_multiuser.py`, which was verified to fail when a single filter is removed |
| **G43** | **Push went to every device in the house.** `send_to_all` fanned out across the whole subscription table, so one person's reminder would buzz everyone's phone. | ✅ Phase 9 — `send_to_user` only; the scheduler groups due routines by owner. There is deliberately no send-to-everyone helper left to call by mistake |
| **G44** | **No sign-in UI**, and Settings asked for a raw API token. | ✅ Phase 9 — sign-in/register screen, route guard, auth store, and an Account section with sign-out |
| **G45** | **Open registration on a publicly tunnelled app** is an open door. | ✅ Phase 9 — `ALLOW_REGISTRATION` flag and per-address rate limiting (D14); Cloudflare Access remains the perimeter |
| **G48** | **A routine's products were missing from Today.** `TrackingRow` never rendered them at all, so a tracked routine — which the editor explicitly offers products for — showed a name and a day counter and nothing to apply. `TodayRow` separately hid the line below two products, so a single-product routine you named yourself showed only its name. `RoutinesView` did it a third way. Three copies of the same logic, drifted. | ✅ Fixed — one shared `describeProducts()` used by all three rows |
| **G46** | **`user_id` is nullable**, so a row with no owner is representable. It is invisible and unreachable, because every query filters on the column, but the database does not forbid it. A NOT NULL migration was written and then removed: the container runs `alembic upgrade head` on boot, so it refused to start on a database with pre-Phase-9 rows, and the API could not come up until somebody registered, which they could not do while it was down. | ⬜ **Open** — tighten to NOT NULL in a later revision, once deployments have run `create_user.py --adopt-to` |
| **G47** | **An account cannot be deleted.** `users → products` cascades, but `routine_products.product_id` is `ON DELETE RESTRICT` (D8a, so a product in use cannot be hard-deleted), and the two rules collide: MySQL refuses the delete. Found while removing test accounts from the live database. There is no delete-account endpoint yet, so nothing is broken today, but the topology is wrong and will bite the first time somebody leaves the household. | ⬜ **Open** — delete a user's routines before their products, in an ordered application-level operation |

## Phases

### Phase 0 — Lock the spec ✅
Rewrote `specs.md` around decisions D1–D8, later revised to D1a/D1b/D9/D10 when
the client moved to a PWA. Created `PLAN.md`, `README.md` and `CLAUDE.md`.

### Phase 1 — Make it boot ✅ *(G1, G19, G21)*
`entrypoint.sh` runs `alembic upgrade head` before exec'ing the server, with a
bounded retry. MySQL healthcheck plus `depends_on: condition: service_healthy`.
`--reload` moved out of the image. `GET /healthz` reports database reachability.

### Phase 2 — Backend data model and API ✅ *(G8, G12–G16)*
Migration `b2f1c4d7e9a3`: NOT NULL columns, `log_date` with its unique
constraint, lifecycle fields, soft delete, reserved `user_id`, `TIME` for
`notification_time`, FK `ON DELETE` rules. Full CRUD, log upsert,
`/routines/today`, `/logs/calendar`, `/stats/streak`, `/stats/adherence`.
Bearer-token auth and configuration-driven CORS.

### Phase 3 — Vue PWA client ✅ *(G3, G5, G6, G9–G11, G23, G24, G26)*
Vue 3 + Vite + Pinia + vue-router, installable, with generated icons and a
service worker. Today checklist driven by `/routines/today` with done/skip/undo,
routine list and editor with weekday chips and a time picker, product reuse,
settings for the API token.

### Phase 4 — Web Push ✅ *(G2, G25)*
Migration `c7d3e81f5b20` adds `push_subscriptions`. `app/push.py` sends via
pywebpush and prunes dead endpoints on 404/410. `app/scheduler.py` runs an
asyncio loop in the API process (D10), acting once per local minute and skipping
routines already logged today. Client subscribes from Settings; `public/push-sw.js`
displays and focuses.

### Phase 5 — Progress view ✅ *(G7)*
Streak tiles, a 12-week calendar heatmap and 30-day per-routine adherence. The
heatmap uses a single-hue sequential ramp validated in both light and dark
against this app's surfaces, with a legend, a hover/focus readout and a table view.

### Phase 6 — Infrastructure hardening ✅ *(G17, G18, G20, G27)*
nginx image serving the PWA and proxying `/api`. `.env` with `.env.example`;
no credentials in the repo. `DB_DATA_PATH` bind mount for NAS storage.
`cloudflared` behind a profile. `scripts/backup.sh` with a documented restore.

### Phase 7 — Tests and CI ✅ *(G22)*
52 backend tests (endpoints, validators, auth, streak rules, scheduler
selection, and a check that migrations match the models) and 19 frontend tests
(date helpers, VAPID decoding, checklist row). GitHub Actions runs both.

### Phase 8 — Multi-product routines and tracked services ✅ *(G28, G30–G36)*

Requested after the first real use of the running stack. Two changes to what a
routine *is*, locked as **D8a**, **D11** and **D12** in [specs.md](specs.md).

**Migrations.** Two, so each reverses independently.

* **M1** — create `routine_products`, backfill one row per existing routine
  (`SELECT id, product_id, 0 FROM routines`), then drop `routines.product_id`.
  Downgrade only works while every routine has ≤1 product; the revision says so.
* **M2** — add `name`, `kind`, `target_interval_days`, `start_date`; relax
  `days_of_week` and `time_period` to nullable. Backfill `name` from the routine's
  single product name plus its time period ("Retinol 0.5% — night"), and
  `start_date` from `MIN(log_date)` per routine. **`routines` has no `created_at`**,
  so the earliest log is the best available proxy, falling back to today.

⚠️ **M1 is the first migration in this project's life to drop a column holding
live rows.** Run `scripts/backup.sh` before applying it.

**Backend.** `is_due` branches on kind and honours `start_date`. New
`tracker_state(routine, today)` returns `last_completed`, `days_since` and
`overdue`. `compute_streaks` and adherence filter to `kind='scheduled'` (G33 —
the one place a mistake is silent rather than loud). `/routines/today` grows a
`tracking` section. Routine create/patch take an ordered `product_ids`, `kind`,
`name`, `target_interval_days` and `start_date`, with a per-kind validation
matrix returning 422 on contradictions.

**Breaking API change:** `routine.product` becomes `routine.products[]`. Backend
and frontend ship in one commit.

**Frontend.** Today gains a Tracking section with day counters and *mark done*.
The editor gains a kind toggle, an ordered add/remove/reorder product picker, a
name field and an interval field. `ProgressView` loses its client-side G28
workaround.

**Scheduler.** Tracked routines notify at `notification_time` when overdue, then
every second day while they stay overdue.

**Order of work.** 1. specs + plan. 2. M1, models, join-table CRUD. 3. M2, kind
validation, `is_due`/streak/adherence scoping. 4. `/routines/today` tracking.
5. Frontend. 6. Scheduler. 7. Docs and session log. Steps 2 and 3 each keep the
52 backend tests passing; step 5 updates the 19 frontend ones.

### Phase 9 — Household accounts ✅ *(G40–G45)*

Locked as **D4a**, **D5a** and **D14** in [specs.md](specs.md). Migration
`a7e2d64c1b93` adds `users` and `sessions` and turns the `user_id` columns D4
reserved in Phase 2 into real foreign keys, which is why this was additive
rather than a rewrite.

Products are per-user, so each person keeps their own catalogue. Sessions are
server-side rather than JWT so sign-out genuinely revokes. Registration is open
behind `ALLOW_REGISTRATION` and rate limiting.

**The dangerous part was scoping, not authentication.** Adding a login is
visible when it breaks; forgetting a `user_id` filter is not, and shows one
housemate another's data with no error. `tests/test_multiuser.py` walks every
resource with two accounts, and was itself verified by removing one filter and
confirming it fails. It caught a real leak during the work: `delete_log` took
the `current_user` dependency, which only proves somebody is signed in, and then
fetched the row by id without checking who owned it.

**Notifications did not need Firebase.** Web Push already reaches Chrome through
FCM's own infrastructure using the vendor-neutral protocol and the deployment's
own VAPID keys, so adding the Firebase SDK would have replaced a working
standards-based path with a cloud dependency, in an app whose point is running
on the household's own hardware. The change here was only to make delivery
per-user.

## Next

1. **G46** — tighten `user_id` to NOT NULL once deployments have adopted.
2. **G47** — make account deletion possible; the FK topology currently forbids it.
3. **G29** — cache the checklist response and queue writes while offline.
4. Confirm a real push arrives on a phone, now that it is per-user.
