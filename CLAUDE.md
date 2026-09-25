# CLAUDE.md

Working notes for Claude Code sessions in this repository.

## What this project is

A self-hosted beauty/skincare routine tracker: FastAPI + MySQL on a home NAS,
an installable Vue PWA on the phone, Cloudflare Tunnel between them. See
[README.md](README.md) for the product summary.

## Current state (2026-09-24)

Phases 0–8 are complete. Phase 8 (multi-product routines and tracked services)
is on the branch `phase8-multi-product-tracked`, **not yet merged to `main`**.

**Proven on real hardware.** The stack was built and run on the user's Mac on
2026-09-21. Both images build; the MySQL healthcheck and `service_healthy`
gating work; every migration applies to real MySQL; nginx serves the PWA and
proxies `/api/`. 80 backend tests, 36 frontend tests, `vue-tsc` and `vite build`
clean. Both Phase 8 features were exercised end to end against live MySQL.

**Still not proven:**

1. **A real Web Push delivery.** VAPID keys are configured and the scheduler
   runs, but no browser has ever subscribed. This is the last untested path.
2. **The Phase 8 PWA in a browser.** The backend is verified through the API;
   the rebuilt frontend has not been driven in a real browser. Note the Chrome
   extension used for automation could not reach `localhost` in this
   environment — the user has to do it by hand.

**Open gaps:** **G29** (no offline cache or write queue). Everything else in the
register is closed or obsolete.

**Running it:**

```bash
cp .env.example .env          # then change the passwords
docker compose up --build
curl localhost:8000/healthz   # expect {"status":"ok","database":"ok"}
open http://localhost:8080    # paste the API token into Settings first
```

Nothing renders until the bearer token from `.env` is entered in Settings —
every endpoint but `/healthz` is behind it. An empty screen almost always means
a missing token rather than a broken deployment.

## Read these first

1. **[PRODUCT.md](PRODUCT.md)** — who this is for and the design principles any
   UI work answers to, including the 44px target floor and the anti-references.
2. **[specs.md](specs.md)** — the locked v1 specification. Decisions D1a–D12 in
   §3 resolve the ambiguities in the original brief. Treat them as settled;
   changing one is a spec change, so update specs.md in the same commit.
3. **[PLAN.md](PLAN.md)** — the gap register (G1–G39) and the phased plan.
   This is the source of truth for what is done and what is next.

## Keeping the docs current

**Every session that changes code must leave PLAN.md and this file accurate
before it ends.** Specifically:

* Flip the status of any gap you closed in PLAN.md's register and in its
  status-at-a-glance table (⬜ not started → 🚧 in progress → ✅ done).
* Bump `Last updated` in PLAN.md.
* If you discovered a new gap, add it to the register with the next free G
  number and assign it to a phase. Do not renumber existing IDs — they are
  referenced from commit messages and session notes.
* If you changed an architectural decision, update specs.md §3 and say so in
  the session log below.
* Append a session-log entry (see the format at the bottom).

## Conventions

* **ISO weekdays, 1 = Monday … 7 = Sunday** (D2). Python's
  `datetime.isoweekday()` matches this. **Python's `weekday()` is 0-based and
  JavaScript's `getDay()` is 0=Sunday — neither may be used directly.** The
  client converts once, in `isoWeekday()` in `frontend/src/dates.ts`.
* **Local date vs UTC timestamp** (§4). `DailyLog.log_date` is the local
  calendar date per `APP_TIMEZONE` and is what "today", uniqueness, and streaks
  are computed on. `DailyLog.timestamp` is the UTC instant. Mixing them puts a
  00:30 check-off on the wrong day.
* **`time_period` never triggers anything** — it is a display bucket.
  `notification_time` is the only trigger source (§4).
* **Never format a date with `toISOString()`** in the client. It converts to UTC
  first and lands on the wrong day near midnight. Use `toLocalIsoDate()`.
* **The API runs a single worker** (D10). The notification scheduler lives in
  the process; a second worker would send every notification twice.
* **No secrets in the repo.** Configuration comes from the environment; commit
  `.env.example`, never `.env`.
* **Migrations, not `create_all`.** Schema changes go through an Alembic
  revision. The container runs `alembic upgrade head` on start.
* **A routine has a kind** (D11). `scheduled` recurs on weekdays; `tracked` is
  measured by days elapsed against `target_interval_days`. **Anything that asks
  "was this due on day X" must exclude tracked routines** — `is_due` already
  does, and `services.scheduled_only()` exists for the places that filter a list
  themselves. Forgetting this does not raise: it silently pins every streak at
  zero (G33).
* **A routine owns an ordered list of products** (D8a), through
  `routine_products.position`, and may own none. Read them with
  `routine.products`, never `routine.product` — that attribute is gone. One
  check-off still covers the whole routine (D6).
* **A routine's label is `routine.name`**, which is required. Do not fall back
  to a product name: a routine may have three products or none.
* **Replacing a routine's products needs a flush between the delete and the
  insert.** Assigning a new list straight over the old one makes SQLAlchemy
  insert first, and a reorder re-inserts product ids that are still there,
  tripping `uq_routine_products_routine_product`.

## Commands

```bash
cp .env.example .env
docker compose up --build          # dev stack (override file applies automatically)
docker compose -f docker-compose.yml up --build   # production-shaped run
docker compose --profile tunnel up -d             # adds Cloudflare Tunnel
docker compose exec api alembic revision --autogenerate -m "message"
docker compose exec api python scripts/generate_vapid_keys.py
curl localhost:8000/healthz

cd backend  && pytest
cd frontend && npm test && npm run typecheck && npm run build
```

## Git

Development happens on the branch named in the session prompt, never directly on
`main`. Reference gap IDs (`G1`, `G14`) in commit messages so the register stays
traceable.

---

## Session log

Newest entries at the top. Each entry records where the session ended so the
next one can pick up without re-deriving context.

### 2026-09-25 — UX critique, and the three states nobody had looked at

Ran an Impeccable critique on the Today view, the first scored review this
project has had. **24/40.** Snapshot in
`.impeccable/critique/2026-09-25T10-35-13Z__frontend-src-views-todayview-vue.md`,
which `/impeccable polish` can read as a backlog.

The deterministic detector returned zero findings on `frontend/src`. That is a
real result, not an empty scan: it fires on a planted bad file, and it flags the
exact `border-left: 3px solid var(--danger)` this codebase shipped one round
earlier. No visual overlay was produced and none is claimed, because the Chrome
extension cannot reach `localhost` here.

**Everything worth fixing was in a state that had never been rendered (G39).**
Screenshots of normal data look fine; stubbing the other states did not.

* **No completion moment.** Finishing every routine gave struck-through rows and
  empty space. The ending is what gets remembered, and this one said nothing.
  There is now a completion panel carrying the streak, which was previously
  invisible unless you opened the Progress tab. It appears only when every due
  routine is *completed*; a partly skipped day reads "Nothing left for today,
  1 done, 1 skipped" instead, because celebrating skips would be a lie.
* **Error state.** Raw `Internal Server Error` over a blank screen, no way back.
  Now plain language, the technical detail kept as secondary text, a Retry that
  re-runs the load, and `role="alert"` so a screen reader announces it. The date
  in the header also survives the failure now, instead of vanishing exactly when
  the user is most disoriented.
* **Empty state, which was a logic bug I introduced.** `isEmpty` conflated "no
  routines at all" with "a rest day", so someone with six routines was told to
  "add a routine to get started", with no control to do it with. The two cases
  are now told apart by a lazy `listRoutines()` call made only when the screen
  would otherwise be blank; first run gets an **Add a routine** button, a rest
  day gets "Your streak is safe."

Also added per-section progress counts (2/2, 1/1), which the critique flagged as
missing under visibility of system status.

**Verified:** 36 frontend tests, up from 29, covering all three states plus the
"do not celebrate a skipped day" rule and the retry path. 80 backend tests,
`vue-tsc` and `vite build` clean, detector clean, no horizontal scroll at
320/390/430px. Rebuilt and redeployed the `web` image.

**Left open deliberately.** The critique's other findings are in the snapshot and
not yet acted on: no bulk "mark all done" (N routines is still N taps every day),
`confirm()` still guards routine deletion, and completing a routine does not
announce itself to a screen reader. The open question worth answering before
more UI work: **should Skip exist at all on the daily list?** It is a second
full-size control on every row, and an absent log already means pending.

**Ended at:** branch `phase8-multi-product-tracked`, committed.

**Next:** a real phone, and a real push. Then G29.

### 2026-09-25 — Mobile design pass

The app is installed to a phone and used one-handed, morning and night, but no
screen had ever been looked at rendered. Ran the Impeccable design skill over
the PWA. Register: **product** (design serves the task). Wrote
[PRODUCT.md](PRODUCT.md) with the users, personality, anti-references and
accessibility bar, confirmed with the user.

**How it was checked.** The Chrome automation extension cannot reach `localhost`
in this environment, so the app was driven with headless Chrome through
`puppeteer-core` instead, at 320 / 390 / 430px in both colour schemes, against a
**throwaway mock API** rather than the real database — the user was using the
live app at the time. Everything below was measured in the rendered page.

**The measured defect (G38).** Every touch target was under the 44px minimum:
buttons 37px, tab-bar links 35px, weekday chips 30px. 24 of 24 controls failing.
Now 0 of 24, with `--tap` as the floor. Contrast already passed everywhere and
the existing rose palette was preserved: identity beats regeneration.

**Design changes.**

* **Today** — the product list now spans the full row instead of being boxed
  into the 55% beside the buttons, where a three-product stack wrapped to three
  lines. Section headings became real headings with a morning / night / tracking
  dot, which finally uses the `--morning` and `--night` tokens that had been in
  the palette unused since Phase 3.
* **Tracking** — the elapsed count leads at 1.5rem, because it is the question
  the section exists to answer. `0` and `null` render as "Done today" and "Not
  recorded yet" rather than a bare figure.
* **Editor** — grouped into What it is / Products / When; a segmented control
  instead of two loose pills; the new-product inputs stacked, since three
  controls in one row truncated both placeholders at 390px; the weekday row is a
  7-column grid (4 below 360px, where seven 44px chips cannot fit); Save and
  Cancel ride in a sticky bar above the tab bar instead of sitting below it.
* **Progress** — the twin big-number streak cards are one sentence. "Hover or
  focus a day" said hover on a touch device; it now says tap, and taps work.
  Adherence rows are a divided list rather than a card each.
* Added focus-visible rings, 150–220ms state transitions, and a
  `prefers-reduced-motion` path (verified collapsing to ~0s).

**Two bugs the rendering caught that review had not:**

* **A design rule I had broken myself.** The overdue tracker used a coloured
  `border-left`, the side-stripe pattern. Replaced with a tinted surface; the
  "Overdue" word carries the state so it never depends on colour alone.
* **The adherence bars had been invisible.** A stale `.bar-fill` rule left over
  from the markup it replaced won on order and referenced `--level-3`, a
  variable scoped to `.viz-root`, which the list is not inside. It resolved to
  transparent. Reading the CSS would not have shown this; the rendered page did.

**Verified:** 80 backend, 29 frontend, `vue-tsc` and `vite build` clean. No
horizontal scroll at 320 / 390 / 430px. Rebuilt and redeployed the `web` image.

**Ended at:** branch `phase8-multi-product-tracked`, still uncommitted.

**Next:** unchanged — drive the PWA on a real phone and confirm a push. Then G29.
A `DESIGN.md` has not been written; `/impeccable document` would generate one
from the tokens now that the visual system is settled.

### 2026-09-24 — First real run, then Phase 8

Two sessions' worth of work in one: the container stack ran for the first time,
and the user asked for two features after using it.

**Part 1 — the stack runs.** `docker compose up --build` on the user's Mac, with
Docker Hub reachable. Everything on the old risk list passed:

* Both images built; `db → healthy → api` gating worked, no race.
* **Migration `b2f1c4d7e9a3` applied cleanly to MySQL** — the FK rework that had
  never executed produced exactly the intended schema (`notification_time` as
  `TIME`, `product_id` NOT NULL, RESTRICT on routines, CASCADE on logs).
* nginx SPA fallback and the `/api/` proxy both answer 200.
* D6's upsert is idempotent on MySQL; the `(routine_id, log_date)` unique key
  holds and a second check-off updates in place rather than 500ing.
* The midnight trap is handled: forcing the clock to 22:30 UTC (00:30 Madrid)
  resolved `today_local()` to the next local day, not the UTC one.

Push delivery is still unproven — VAPID keys are configured and the scheduler
starts, but no browser has subscribed. **The Chrome automation extension could
not reach `localhost` at all** (requests never arrived at nginx), so every
browser check in this session had to be done by the user.

**Part 2 — Phase 8.** The user asked for routines made of several products, and
for routines that are services tracked by elapsed time ("23 days since your last
haircut"). This is a spec change: **D8 is superseded by D8a**, and **D11** and
**D12** are new. Decisions taken with the user: one tick per routine regardless
of product count, a required target interval with overdue push, a Tracking
section always visible, required routine names, and a two-day repeat for overdue
reminders.

Two migrations, both round-tripped on SQLite and applied to live MySQL:
`d4a9f2c1b8e7` (join table, backfill, drop `product_id`) and `e5b1a7d3c9f2`
(kind, name, target interval, start_date). **No data was lost** — 152 logs before
and after — and all three downgrade guards fire with readable messages.

Closed **G28** and **G30–G37**. 52 backend tests became 80; 19 frontend became 29.

**Two things worth knowing:**

* **A real bug was caught by a new test, not by review.** Reordering a routine's
  products tripped the unique constraint, because SQLAlchemy emits the INSERTs
  before the DELETEs. It needed a `flush()` between them. It would have broken
  the editor's reorder the first time anyone used it.
* **G37: the test suite was not hermetic.** Run inside the `api` container it
  inherited the real VAPID keys from `.env`, so "unconfigured" tests saw a
  configured app. Green in CI, red on the machine the stack runs on.

**Data note.** Two seeded routines (`Niacinamide Serum — night`, `Gentle
Cleanser — morning`) and their 47 logs disappeared during the session. Traced
through the MySQL binary log: two ORM cascade deletes matching exactly the
`DELETE /routines/{id}` endpoint, after the migration. Not a migration fault and
not a bug — that endpoint is documented as a hard delete that takes its logs
with it. Both were seed data created earlier in the same session, so nothing the
user authored was lost.

**Ended at:** branch `phase8-multi-product-tracked`, all work committed to the
working tree but **not committed to git and not merged**. Stack running with the
Phase 8 images.

**Next:** drive the Phase 8 PWA in a browser (Today's Tracking section, the
ordered product picker, the kind toggle), then a real push on a phone. Then G29.

### 2026-09-21 — Documentation audit

**Did:** no code changes. Audited the four Markdown files for drift after the
phase work and fixed what was wrong:

* `specs.md` §6 was missing `GET /stats/adherence`. The endpoint is implemented,
  tested and used by the progress view, and §7 describes the feature — only the
  API table never got the row.
* `CLAUDE.md` still described the register as G1–G23. It runs to G29.
* Added a **Current state** section to the top of this file. The state was only
  recorded in the session log at the bottom, so a fresh session had to read to
  the end to find out that nothing has been containerised yet. It now leads with
  what is proven, the exact first commands, and what is most likely to break.

**Verified:** every internal Markdown link resolves, every file path named in
the docs exists, and the test counts the docs claim are real — 52 backend and
19 frontend, both re-run.

**Ended at:** docs accurate against the code at this commit. Working tree clean.

**Next:** unchanged — first real `docker compose up --build`, then G28.

### 2026-09-21 — Phases 2 to 7, and the move to a PWA

**Decision change.** Partway through, the client moved from Flutter to a Vue
PWA at the user's direction. That invalidated **D1** (local notifications, no
server infrastructure): a PWA cannot schedule its own alarms, because the
Notification Triggers API never shipped past a Chromium origin trial. specs.md
§3 now carries **D1a** (Vue PWA), **D1b** (Web Push driven by a scheduler in the
API), **D9** (nginx serves the app and proxies `/api`, so production is
same-origin) and **D10** (the scheduler is an asyncio loop, so the API must run
a single worker). The consequence to remember: **reminders now need the NAS
awake and able to reach the browser vendor's push service**, which the original
D1 deliberately avoided.

**Did:** Phases 2–7. Backend data model, full CRUD, auth, derived views. Deleted
the Flutter client and built the Vue PWA (checklist, routine editor, progress,
settings). Web Push end to end: `push_subscriptions`, VAPID, delivery with dead
endpoint pruning, an in-process scheduler, and the client subscription flow.
Progress view with a validated single-hue heatmap. nginx image, `.env`,
NAS bind mount, `cloudflared` profile, backup script. 52 backend and 19 frontend
tests, and GitHub Actions running both.

**Verified:** backend suite 52 passed; frontend suite 19 passed; `vue-tsc` clean;
`vite build` clean. Drove the built PWA in headless Chromium against the real
API: the checklist rendered both sections, checking a routine off persisted
across a reload (G6), undo reverted it, the routine list and editor rendered,
and the Progress view showed streaks of 8 and 19 computed from six weeks of
seeded history with 84 heatmap cells and a working hover readout. Zero console
errors. Both compose files pass `docker compose config`.

**NOT verified:**
* **No container was ever built or run.** Docker Hub is blocked by this
  environment's egress policy (403 on `production.cloudfront.docker.com`), so
  `python:3.11-slim`, `mysql:8.0`, `node:22-alpine` and `nginx:1.27-alpine`
  could not be pulled. Everything was exercised directly instead — the API on
  SQLite, the PWA via `vite preview` with the same proxy shape nginx uses. The
  images, the MySQL healthcheck, the `service_healthy` gating and the nginx
  config are all unproven.
* **Nothing has run against MySQL.** The tests and both migrations ran on
  SQLite. Migration `b2f1c4d7e9a3` changes column types and adds NOT NULL
  constraints, and its foreign-key rework is MySQL-only code that never
  executed.
* **No push was ever delivered.** No browser push endpoint was reachable. The
  scheduler's selection logic, the subscription endpoints and the key generator
  are tested; `pywebpush` delivery itself is not.

**Ended at:** all seven phases complete, two gaps deliberately left open —
**G28** (routines have no `start_date`, so the calendar cannot tell "did not
exist yet" from "missed"; worked around client-side) and **G29** (no offline
cache or write queue; the shell is precached but every screen needs the API).
Both are written up in PLAN.md.

**Next:** run `docker compose up --build` on a machine with Docker Hub access
and confirm `/healthz`, the app at :8080 and a real push on a phone. Then G28,
which is a small migration plus a change to `is_due`.

### 2026-09-21 — Phases 0 and 1

**Did:**

* **Phase 0 (complete).** Reviewed the original brief and found 14 spec-level
  gaps (undecided notification architecture, no weekday convention, `time_period`
  vs `notification_time` redundancy, no log-uniqueness rule, timezone treated as
  optional, no auth on a publicly exposed API, unmeasurable streak definition,
  and more). Rewrote `specs.md` as a locked v1 spec resolving all of them as
  decisions D1–D8. Rewrote `README.md` as a product overview. Created `PLAN.md`
  with the G1–G23 gap register and a 7-phase plan. Created this file.
* **Phase 1 (complete).** Closed **G1**, **G19**, **G21**. Added
  `backend/entrypoint.sh` that runs `alembic upgrade head` before exec'ing the
  server, so a clean volume boots to migrated tables with no manual steps.
  Removed `--reload` from the production image and moved dev-only settings
  (reload, source bind mount, published DB port) into
  `docker-compose.override.yml`. Added a MySQL healthcheck with
  `depends_on: condition: service_healthy` so the API no longer races the
  database. Added `GET /healthz` reporting database reachability.

**Verified:** ran `entrypoint.sh` against a clean database — it applied the
migration, then started the server. Full round-trips through `POST/GET`
`/products/`, `/routines/`, and `/logs/` returned 200 against the created
tables. `/healthz` returned `{"status":"ok","database":"ok"}`, and
`{"status":"degraded","database":"unreachable"}` with HTTP 503 when the
database is unreachable. The entrypoint's retry loop gives up with exit 1
rather than starting a server against a dead database, and re-running it on an
already-migrated database is a no-op. `docker compose config` validates for
both the dev and production-shaped stacks.

**NOT verified — needs doing on a machine with Docker Hub access:**
`docker compose up --build` end to end. This session's egress policy blocks
Docker Hub (403 on `production.cloudfront.docker.com`), so `python:3.11-slim`
and `mysql:8.0` could not be pulled and no container was ever built or run.
Everything above was exercised with the same entrypoint script and app code
running directly against SQLite instead of the MySQL container. That leaves
three things unproven: the image build, the MySQL healthcheck command, and the
`depends_on: condition: service_healthy` gating. **Run `docker compose up
--build` on a clean volume as the first act of the next session that has
network access, and confirm `/healthz` answers, before treating Phase 1 as
closed.**

**Ended at:** Phase 1 code complete, locally verified, container run pending
the check above. Nothing in flight.

**Next:** Phase 2 — backend data model and API (G8, G12–G16). Starts with the
migration described in PLAN.md's Phase 2 section: NOT NULL columns, `log_date`
with its unique constraint, lifecycle fields, and the nullable `user_id`
columns. Note this migration changes `notification_time` from `VARCHAR(10)` to
`TIME` and adds a NOT NULL constraint to `routines.product_id`, so it is not
safe against a database holding rows that violate either — the dev volume is
empty, so this is only a concern if a NAS deployment already exists.
