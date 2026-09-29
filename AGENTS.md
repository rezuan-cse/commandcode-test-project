# AGENTS.md

RPCI Cloud Accounting & Production ERP — a FastAPI + React double-entry accounting and
production system for a Bangladeshi resin manufacturer. It runs the client's real
bookkeeping: every stock movement posts its own balanced journal entry, costing is
weighted-average, and a wrong posting is reversed, never edited or deleted.

## Read first

1. This file.
2. The router for your task in [docs/map/PRODUCT.md](docs/map/PRODUCT.md).
3. Only the files that router links.

The code is the authority. Where a doc and the code disagree, trust the code and fix the
doc in the same change.

## Hard rules

- **One module, one folder.** A router never runs a query — it calls `service.py`, which
  calls `repository.py`. Backend: `backend/app/modules/<module>/`.
- **Money is `Decimal` end to end**, stored as `Numeric`. No floats anywhere. Unit and
  average costs keep 8 decimal places.
- **Postings are one transaction.** A failure rolls back stock, order and journal
  together.
- **Configuration is not hardcoded.** Company details, VAT/tax, payroll and approval rules
  live in the `settings` table, edited from Administration → Configuration.
- **Permissions are server-side**, evaluated against the role in the signed token. The
  frontend matrix only hides actions; the server is the boundary. Keep
  `backend/app/modules/users_roles/service.py` and `frontend/src/shared/permissions.ts`
  in step.
- **Schema changes are additive only.** `sync_schema()` adds tables and columns at
  startup; a new column must be nullable or carry a `server_default`. See
  [docs/guides/architecture.md](docs/guides/architecture.md).
- **Do not commit, push or deploy unless asked.**

## Workflow

- Work on `main` unless told otherwise.
- After changing code, run the checks that cover it (see commands below). Fix failures
  before finishing.
- A change that adds, moves or removes a file a router names updates that router in the
  same change. Keep this file under ~8 KB; move reference material into `docs/`.

## Commands

```bash
# Backend — run, test
cd backend && .venv/bin/uvicorn app.main:app --port 8000     # API + built SPA
cd backend && .venv/bin/python -m pytest tests -q            # test suite

# Frontend — dev, test, typecheck, build
cd frontend && npm run dev        # :5173, proxies /api
cd frontend && npm test           # vitest
cd frontend && npm run typecheck  # tsc -b
cd frontend && npm run build

# Verify the workbook import (sample data)
backend/.venv/bin/python scripts/seed_from_excel.py --check
```

## Project map

| Task | Where |
|---|---|
| Find the code for a feature | [docs/map/PRODUCT.md](docs/map/PRODUCT.md) |
| Run, test, deploy, env vars | [docs/map/OPERATIONS.md](docs/map/OPERATIONS.md) |
| Architecture and coding rules | [docs/guides/architecture.md](docs/guides/architecture.md) |
| What each test covers | [docs/guides/testing.md](docs/guides/testing.md) |
| What is built, how to demo it | [docs/guides/product-guide.md](docs/guides/product-guide.md) |
| Out of scope / open items | [docs/guides/scope-and-open-items.md](docs/guides/scope-and-open-items.md) |
