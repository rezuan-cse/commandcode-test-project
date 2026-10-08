# Production hardening

Why the production deployment (`render.yaml`, the `production` branch) is
configured more strictly than the development defaults — and what is still
deliberately left open while the system is in client testing.

## What was tightened, and why

### 1. Data reset is off (`RPCI_ALLOW_DATA_RESET=false`)

**Why:** with the switch on, any administrator can empty the entire books from
Administration → Data ("Empty everything" / "Start over"). That is a useful
tool while testing with throwaway data, but on a deployment holding real
figures it puts the whole ledger one click away from destruction — by mistake,
or by a compromised admin session. There is no undo; recovery would depend on
whatever backup exists at that moment.

**Trade-off:** while testing with throwaway data, flip it back to `"true"` in
the Render dashboard. Note that a Blueprint re-sync will set it back to
`"false"`, which is the safe direction for the setting to fail in.

### 2. CORS is locked to the production origin (`RPCI_CORS_ORIGINS=https://rpci.onrender.com`)

**Why:** the interface is compiled into the same Docker image and served by
the API itself, so no browser ever needs cross-origin access. `*` would let
any website on the internet call the API from its visitors' browsers. The
practical risk is limited (authentication travels in the `Authorization`
header, not cookies, and `allow_credentials` stays off), but an open CORS
policy is still an unnecessary hole — and a confusing one for anyone auditing
the deployment later.

### 3. Interactive API docs are off (`RPCI_DOCS_ENABLED=false`)

**Why:** `/docs`, `/redoc` and `/openapi.json` were publicly reachable and
advertised every endpoint, request shape and error format to anyone who asked.
That is genuinely useful in development, which is why the default stays `true`
locally. In production it is a free reconnaissance map for an attacker, so the
blueprint disables it. The API itself is unaffected — only the documentation
pages disappear.

## What is deliberately left open (for now)

These were reviewed and **not** changed, because the system is still in the
client-testing phase:

- **The five `@rpci.demo` accounts** (password `rpci`) still exist in the
  production database. `RPCI_SEED_DEMO_USERS=false` stops new ones being
  created, but the existing ones stay sign-in-able until an administrator
  deletes them. Before go-live: create the real administrator with
  `scripts/create_user.py`, then delete all five demo accounts from
  Roles & Access. Until then, everyone with the link has an admin login —
  acceptable for testing, never for real books.
- **Free-tier sleep.** The service sleeps after ~15 minutes idle (30–60s cold
  start). A cron-job.org monitor pings `/healthz` every 5 minutes to keep it
  awake; this is intentionally kept outside the repository.
- **Backups.** `scripts/backup_db.py` exists but nothing schedules it. Before
  go-live, verify Neon's backup/PITR settings in the Neon dashboard and put
  the script on a nightly schedule somewhere — then restore one backup into a
  scratch database to prove the restore works.

## Checklist for go-live day

1. Real administrator created via `scripts/create_user.py`.
2. All five `@rpci.demo` accounts deleted from Roles & Access.
3. Confirm `RPCI_ALLOW_DATA_RESET=false` is in effect on the live service.
4. Confirm `/docs` and `/openapi.json` return 404 on the public URL.
5. Nightly backup scheduled and one restore proven into a scratch database.
6. `RPCI_DATABASE_URL` points at the production Postgres (never SQLite).
7. Rotate the Neon database password — it was shared in plain text (screenshots,
   shell history) during the testing phase.
