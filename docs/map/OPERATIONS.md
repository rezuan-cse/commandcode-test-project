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
| Generate demo activity | `backend/.venv/bin/python scripts/generate_demo_data.py --months 18` | Posts 18 months of purchases, production, sales, payments and payroll through the service layer. Refuses a non-empty database unless `--force`; `--wipe-first` empties the books (fresh chart, accounts kept) and generates in one step. Testing phase only — wipe before go-live. |
| CI | *(none)* | There is no build or test CI. Run the checks below by hand before deploying. |
| Health probe | `GET /healthz` | Returns `{"status":"ok"}`. |
| Deploy (VPS) | `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build` | See [../guides/vps-deployment.md](../guides/vps-deployment.md). |
| Rollback | Redeploy the previous image/commit | Data lives in Postgres (`RPCI_DATABASE_URL`). |

## Configuration (env var names)

All are prefixed `RPCI_`. Common ones:

`RPCI_DATABASE_URL`, `RPCI_JWT_SECRET`, `RPCI_ACCESS_TOKEN_MINUTES`,
`RPCI_UTC_OFFSET_HOURS`, `RPCI_DEMO_PASSWORD`, `RPCI_SEED_DEMO_USERS`,
`RPCI_LOGIN_MAX_ATTEMPTS`, `RPCI_LOGIN_LOCKOUT_MINUTES`, `RPCI_SEED_MODE`,
`RPCI_SEED_FROM_EXCEL_PATH`, `RPCI_CORS_ORIGINS`, `RPCI_ALLOW_DATA_RESET`,
`RPCI_DOCS_ENABLED`, `RPCI_DEFAULT_SEGMENT`, `RPCI_ENVIRONMENT`.

- `RPCI_DATABASE_URL`: SQLite path/URL for local dev, or a `postgresql://…` connection string for production. The app rewrites `postgres://` / `postgresql://` to the installed `psycopg` driver, so a plain Postgres URL works unchanged.
- `RPCI_JWT_SECRET`: required in production (`RPCI_ENVIRONMENT=production`) so sessions survive restarts.
- `RPCI_SEED_DEMO_USERS=false` for real books; create the first admin with `scripts/create_user.py` or the first-run setup flow.
- `RPCI_ALLOW_DATA_RESET=false` and `RPCI_DOCS_ENABLED=false` on production deployments.

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
`RPCI_`-prefixed variables.
