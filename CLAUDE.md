# CLAUDE.md

Working notes for Claude Code sessions in this repository.

## What this project is

A self-hosted beauty/skincare routine tracker: FastAPI + MySQL on a home NAS,
an installable Vue PWA on the phone, Cloudflare Tunnel between them. See
[README.md](README.md) for the product summary.

## Current state (2026-09-21)

All seven phases in [PLAN.md](PLAN.md) are complete and merged to `main`. The
backend, the PWA, Web Push, the progress view, the Docker stack and CI all
exist.

**Proven:** 52 backend tests, 19 frontend tests, `vue-tsc` and `vite build`
clean. The built PWA was driven in a headless browser against a live API —
check-off persisted across a reload, undo reverted it, streaks computed
correctly from seeded history, no console errors.

**Not proven — do this first.** No container has ever been built and nothing
has ever run against MySQL, because the environment that wrote this code had
Docker Hub blocked. The API was exercised on SQLite and the PWA through
`vite preview`. So on a machine with registry access:

```bash
cp .env.example .env          # then change the passwords
docker compose up --build     # first real boot
curl localhost:8000/healthz   # expect {"status":"ok","database":"ok"}
open http://localhost:8080    # the app
```

Watch for these, in likelihood order:

1. **Migration `b2f1c4d7e9a3` on MySQL.** It changes column types, adds NOT NULL
   constraints, and contains a foreign-key rework guarded to non-SQLite that has
   never executed. This is the most likely thing to fail.
2. The MySQL healthcheck command and the `service_healthy` gating.
3. `frontend/nginx.conf` — the SPA fallback and the `/api/` proxy.
4. A real Web Push delivery. No push has ever reached a browser endpoint.

**Open gaps:** **G28** (routines have no `start_date`, so the calendar cannot
tell "did not exist yet" from "missed"; worked around client-side in
`ProgressView.vue`) and **G29** (no offline cache or write queue). Both are
written up in PLAN.md. Everything else in the register is closed or obsolete.

## Read these first

1. **[specs.md](specs.md)** — the locked v1 specification. Decisions D1a–D10 in
   §3 resolve the ambiguities in the original brief. Treat them as settled;
   changing one is a spec change, so update specs.md in the same commit.
2. **[PLAN.md](PLAN.md)** — the gap register (G1–G29) and the phased plan.
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
