# CLAUDE.md

Working notes for Claude Code sessions in this repository.

## What this project is

A self-hosted beauty/skincare routine tracker: FastAPI + MySQL on a home NAS,
Flutter app on the phone, Cloudflare Tunnel between them. See
[README.md](README.md) for the product summary.

## Read these first

1. **[specs.md](specs.md)** — the locked v1 specification. Decisions D1–D8 in §3
   resolve the ambiguities in the original brief. Treat them as settled;
   changing one is a spec change, so update specs.md in the same commit.
2. **[PLAN.md](PLAN.md)** — the gap register (G1–G23) and the phased plan.
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

* **ISO weekdays, 1 = Monday … 7 = Sunday** (D2). Dart's `DateTime.weekday` and
  Python's `datetime.isoweekday()` both match this. **Python's `weekday()` is
  0-based — never use it here.**
* **Local date vs UTC timestamp** (§4). `DailyLog.log_date` is the local
  calendar date per `APP_TIMEZONE` and is what "today", uniqueness, and streaks
  are computed on. `DailyLog.timestamp` is the UTC instant. Mixing them puts a
  00:30 check-off on the wrong day.
* **`time_period` never triggers anything** — it is a display bucket.
  `notification_time` is the only trigger source (§4).
* **No secrets in the repo.** Configuration comes from the environment; commit
  `.env.example`, never `.env`.
* **Migrations, not `create_all`.** Schema changes go through an Alembic
  revision. The container runs `alembic upgrade head` on start.

## Commands

```bash
docker compose up --build          # dev stack (override file applies automatically)
docker compose -f docker-compose.yml up --build   # production-shaped run
docker compose exec api alembic revision --autogenerate -m "message"
docker compose exec api alembic upgrade head
curl localhost:8000/healthz

cd frontend && flutter analyze && flutter test
```

## Git

Development happens on the branch named in the session prompt, never directly on
`main`. Reference gap IDs (`G1`, `G14`) in commit messages so the register stays
traceable.

---

## Session log

Newest entries at the top. Each entry records where the session ended so the
next one can pick up without re-deriving context.

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
