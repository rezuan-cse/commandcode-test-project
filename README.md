# RPCI Cloud Accounting & Production ERP

An accounting and production system for a Bangladeshi resin manufacturer, built on
FastAPI and React. Every stock movement posts its own balanced journal entry, costing
is weighted-average, and a wrong posting is reversed rather than edited or deleted.

> **New to the system?** Read [USER_MANUAL.md](USER_MANUAL.md) first. It explains
> each screen in plain language, lists who can do what, and walks through a
> complete buy → make → sell example with real numbers.
>
> A Word version, [USER_MANUAL.docx](USER_MANUAL.docx), is included for sharing
> with the client. Regenerate it after editing the manual with:
>
> ```bash
> backend/.venv/bin/python scripts/md_to_docx.py USER_MANUAL.md
> ```
>
> **Information still needed from the client** is collected in
> [CLIENT_QUESTIONS.md](CLIENT_QUESTIONS.md) / `.docx` — tax rates, payroll
> structure, and the few permission questions the specification left open.

---

## Quick start

Requires Python 3.11+ and Node 20+.

```bash
# 1. Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Frontend (built once; the backend serves it)
cd ../frontend
npm install --include=dev
npm run build

# 3. Run everything on one port
cd ../backend
.venv/bin/uvicorn app.main:app --port 8000
```

Open <http://localhost:8000>. On first boot the books start from a built-in
starter chart of accounts; import the client's workbook any time from
**Administration → Data**, or run the seeder.

### Developing the interface

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload    # API on :8000
cd frontend && npm run dev                              # UI on :5173, proxies /api
```

### Docker (local)

```bash
docker compose up --build      # http://localhost:8000
```

For the production VPS deployment (Postgres, Caddy, Cloudflare Tunnel), see
[docs/guides/vps-deployment.md](docs/guides/vps-deployment.md).

---

## Documentation

For AI agents, [AGENTS.md](AGENTS.md) is the entry point. The full detail lives in:

| Topic | Document |
|---|---|
| Where the code lives | [docs/map/PRODUCT.md](docs/map/PRODUCT.md) |
| Run, test, deploy, env vars | [docs/map/OPERATIONS.md](docs/map/OPERATIONS.md) |
| Architecture and coding rules | [docs/guides/architecture.md](docs/guides/architecture.md) |
| Tests and the reconciliation figures | [docs/guides/testing.md](docs/guides/testing.md) |
| What is built, and a demo walkthrough | [docs/guides/product-guide.md](docs/guides/product-guide.md) |
| Scope boundaries and open items | [docs/guides/scope-and-open-items.md](docs/guides/scope-and-open-items.md) |
| VPS deployment | [docs/guides/vps-deployment.md](docs/guides/vps-deployment.md) |

## Verifying the numbers

```bash
cd backend && .venv/bin/python -m pytest tests -q          # test suite
cd .. && backend/.venv/bin/python scripts/seed_from_excel.py --check
```

The import reproduces the workbook's figures: trial balance difference `0`, total
assets `801600`, balance sheet check `0`, manufacturing P&L `4000 / 2400 / 1600 /
40%`, RMC-003 at `790` kg and `32.27848101` average cost. See
[docs/guides/testing.md](docs/guides/testing.md) for the full table.
