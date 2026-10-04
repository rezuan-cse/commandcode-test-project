# Operations map — run, test, ship

| Task | Command / Where | Notes |
|---|---|---|
| First-time backend setup | `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` | Python 3.11+ (image uses 3.13). |
| First-time frontend setup | `cd frontend && npm install --include=dev && npm run build` | Node 20+ (image uses 22). |
| Run everything on one port | `cd backend && .venv/bin/uvicorn app.main:app --port 8000` | Serves API + built SPA at <http://localhost:8000>. |
| Develop the interface | `cd backend && .venv/bin/uvicorn app.main:app --reload` and `cd frontend && npm run dev` | Vite on :5173 proxies `/api` to :8000. |
| Docker locally | `docker compose up --build` | Uses the `rpci-data` volume. |
| Backend tests (SQLite) | `cd backend && .venv/bin/python -m pytest tests -q` | See [../guides/testing.md](../guides/testing.md). |
| Backend tests (Postgres) | `RPCI_TEST_DATABASE_URL=postgresql+psycopg://… .venv/bin/python -m pytest tests -q` | Run before deploying. |
| Frontend tests | `cd frontend && npm test` | Vitest. |
| Frontend typecheck | `cd frontend && npm run typecheck` | `tsc -b`. |
| Verify the workbook figures | `backend/.venv/bin/python scripts/seed_from_excel.py --check` | Prints the reconciliation table. |
| CI | *(none)* | There is no build or test CI. Run the checks below by hand before deploying. |
| Keeping the service awake | **cron-job.org** (external account) | Pings `https://rpci.onrender.com/healthz` every 5 min. Render's free tier sleeps after ~15 min. Deliberately **not** in this repository: GitHub's scheduler dropped most runs. See [../guides/deployment.md](../guides/deployment.md). |
| Health probe | `GET /healthz` | Returns `{"status":"ok"}`. |
| Deploy (public HTTPS) | Apply `render.yaml` on Render | See [../guides/deployment.md](../guides/deployment.md) and `DEPLOYMENT.md`. |
| Rollback | Redeploy the previous image / re-apply the blueprint | Data lives in Postgres when `RPCI_DATABASE_URL` is set. |

## Configuration (env var names)

All are prefixed `RPCI_`. Full table with defaults: [../guides/deployment.md](../guides/deployment.md).

`RPCI_DATABASE_URL`, `RPCI_JWT_SECRET`, `RPCI_ACCESS_TOKEN_MINUTES`,
`RPCI_UTC_OFFSET_HOURS`, `RPCI_DEMO_PASSWORD`, `RPCI_SEED_DEMO_USERS`,
`RPCI_LOGIN_MAX_ATTEMPTS`, `RPCI_LOGIN_LOCKOUT_MINUTES`, `RPCI_SEED_MODE`,
`RPCI_SEED_FROM_EXCEL_PATH`, `RPCI_CORS_ORIGINS`, `RPCI_ALLOW_DATA_RESET`,
`RPCI_DEFAULT_SEGMENT`.

## Accounts and backups

| Task | Command | Notes |
|---|---|---|
| Make the first administrator | `backend/.venv/bin/python scripts/create_user.py` | Needed when `RPCI_SEED_DEMO_USERS=false`; prints the password once. |
| Back up | `backend/.venv/bin/python scripts/backup_db.py --out <dir>` | SQLite or Postgres, any host. Run nightly. |
| Restore (prove it) | `backend/.venv/bin/python scripts/restore_db.py <archive> --scratch <url>` | Restores into a scratch database instead. |
| Restore (live) | `... restore_db.py <archive> --yes` | Destructive; stop the app first. |

A data reset and a workbook import both keep the **user accounts** — only the
books are replaced — so neither can lock everybody out.

Rules the configuration follows: no secret or real value in a router; the app reads only
`RPCI_`-prefixed variables; a Supabase/Neon URL is pasted unchanged (the app rewrites
`postgres://` → `postgresql+psycopg://`).
