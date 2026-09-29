# RPCI Cloud Accounting & Production ERP — Demo

A working prototype of the accounting and production system described in
`RPCI_ERP_BUILD_SPEC.md`, preloaded with the client's own data from
`RPCI Accounts.xlsx`.

The point of the demo is that it runs **their books**, not invented numbers. Open
the Trial Balance and it nets to zero. Open the Balance Sheet and it balances at
801,600. Open Elephent Cement in the stock ledger and it shows 790 kg at
32.27848101 — exactly what their spreadsheet shows, but computed live.

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
> structure, and the few permission questions the specification left open. Each
> row has a sample answer the client can work from.

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
**Administration → Data**, or run the seeder (see the deployment guide).

### Developing the interface

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload    # API on :8000
cd frontend && npm run dev                              # UI on :5173, proxies /api
```

### Docker

```bash
docker compose up --build      # http://localhost:8000
```

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
| Deployment in detail | [DEPLOYMENT.md](DEPLOYMENT.md) |

## Verifying the numbers

```bash
cd backend && .venv/bin/python -m pytest tests -q          # test suite
cd .. && backend/.venv/bin/python scripts/seed_from_excel.py --check
```

The import reproduces the workbook's figures: trial balance difference `0`, total
assets `801600`, balance sheet check `0`, manufacturing P&L `4000 / 2400 / 1600 /
40%`, RMC-003 at `790` kg and `32.27848101` average cost. See
[docs/guides/testing.md](docs/guides/testing.md) for the full table.

## What is built

Phases 1–3 are complete (ledger core; inventory and production; sales and segment
reporting). Phase 4 adds real authentication, a server-enforced permission matrix,
and configurable VAT/tax, payroll and approval rules. Phase 5 is the deployment
configuration. Full detail in
[docs/guides/product-guide.md](docs/guides/product-guide.md).
