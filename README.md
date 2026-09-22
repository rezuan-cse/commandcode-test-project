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

Open <http://localhost:8000>. The database is created and seeded from the
workbook on first boot.

### Developing the interface

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload    # API on :8000
cd frontend && npm run dev                              # UI on :5173, proxies /api
```

### Docker

```bash
docker compose up --build      # http://localhost:8000
```

### Deploying to a public URL

**See [DEPLOYMENT.md](DEPLOYMENT.md)** for the full guide, including why Vercel
and Netlify cannot host the API by themselves and which option to pick.

The short version: `render.yaml` is a Render blueprint. Point Render at the
repository, apply the blueprint, and it builds the Docker image and serves the
demo over HTTPS on a single URL. No other configuration is needed — the workbook
is baked into the image and the database seeds itself on first boot.

To put the *interface* on Vercel or Netlify instead, deploy the API to Render and
set `VITE_API_BASE` on the static host. `frontend/vercel.json` and
`frontend/netlify.toml` are already in place.

---

## Signing in

Authentication is real. Passwords are hashed with bcrypt, sessions are signed
JWTs, and the permission matrix is evaluated against the role inside the token —
never against anything the browser claims.

One account is seeded per role, all with the password **`rpci`** (set
`RPCI_DEMO_PASSWORD` to change it). The sign-in screen lists them, and clicking a
row fills the form:

| Email | Role | Can do |
|---|---|---|
| `admin@rpci.demo` | Admin | everything |
| `accountant@rpci.demo` | Accountant | journal entries, reports |
| `store@rpci.demo` | Store / Production | items, production runs |
| `sales@rpci.demo` | Sales Staff | purchases, sales |
| `owner@rpci.demo` | Owner / Viewer | read only |

Signing in as different people is how the permission rules are demonstrated. It
also replaced the old `X-Demo-Role` header, which anyone could set by hand — the
test suite now asserts that header is ignored.

### Two-factor authentication

TOTP, for use with Google Authenticator, Authy or similar. Enrol from
**Administration → Security**: scan the QR code, then enter a code to prove the
app works before it is switched on. Eight single-use recovery codes are issued
once, and are the way back in if the authenticator is lost.

It is off by default so nobody is locked out of a shared demo. Turning it on is a
good thing to show a client.

The flow is deliberately two-step: a password alone yields a short-lived
*challenge* token that can only be exchanged for a code. Only the code step
issues a session, so a stolen password is not by itself enough, and a challenge
token cannot be replayed as a session. Both properties are tested.

## Verifying the numbers

The import is checked against the workbook, both by the test suite and by a
standalone script:

```bash
cd backend && .venv/bin/python -m pytest tests -q          # 87 tests
cd .. && backend/.venv/bin/python scripts/seed_from_excel.py --check
```

Expected output:

| Figure | Value | Source |
|---|---|---|
| Trial balance difference | `0` | Trial Balance sheet |
| Total assets | `801600` | Balance Sheet sheet |
| Balance sheet check | `0` | Balance Sheet sheet |
| Manufacturing P&L | `4000 / 2400 / 1600 / 40%` | P&L by Segment sheet |
| RMC-003 quantity | `790` | Item Master sheet |
| RMC-003 average cost | `32.27848101` | Item Master sheet |

---

## What is built

The demo covers Phases 1–3 of the specification functionally, with Phase 4 and 5
represented by working stubs and deployment configuration.

**Phase 1 — Ledger core (complete)**
- Chart of accounts, 89 accounts imported, each tagged with a segment
- Opening balances as of the cutover date, locked and proving debit = credit
- Manual journal entries, rejected unless the entry balances
- General Ledger, Trial Balance, P&L by Segment, Balance Sheet — all derived live

**Phase 2 — Inventory and production (complete)**
- Item master; quantity on hand and average cost are computed, never typed
- BOM master with recursive multi-stage explosion
- Purchase entry, raising stock and updating weighted-average cost
- Production entry: atomic posting that consumes components, computes unit cost,
  receipts the output, and writes a balanced journal entry

**Phase 3 — Sales and segment reporting (complete)**
- Sales entry: reduces stock at average cost and posts revenue and COGS in one entry
- Segment dashboard, with segment totals reconciling to company-wide figures

**Phase 4 — Roles, authentication, VAT/tax, payroll (in progress)**
- Authentication is real: hashed passwords, signed sessions, and a TOTP second
  factor with single-use recovery codes
- The full permission matrix is enforced server-side against the role in the
  token; every cell is tested
- VAT and payroll rules live in a configuration table, flagged pending client
  confirmation, so no unconfirmed rule is hardcoded
- *Still to build:* VAT computation on transactions, payroll, and receipts

**Phase 5 — Deployment (configuration in place)**
- Dockerfile, docker-compose, and a Render blueprint for a public HTTPS URL

---

## A finding worth raising with the client

The integrity panel on the dashboard reports one failing check:

```
General Ledger inventory equals stock ledger value
  GL inventory 301400 vs stock ledger 775500 (variance -474100)
```

This is not a bug in the demo. In the original workbook, the Inventory Ledger is
a memo sheet — the Instructions tab says so explicitly: it tracks quantities and
costs but never posts journals. As a result 474,100 of stock value exists in the
stock sheet with no matching entry in the general ledger. Two concrete symptoms:

- Resin A (RMA-014) shows 500 kg at 1,500 = 750,000 in the stock ledger, but the
  accounts carry only 90,000 of raw materials.
- Elephent Cement (RMC-003) records 7,000 against a suggested 6,825 for the same
  210 kg issue — the workbook's own suggested-value column disagrees with what
  was typed.

The ERP cannot reproduce this, because every stock movement posts its own journal
entry in the same transaction. That is precisely the class of error the system
removes, and it is worth showing the client rather than hiding.

---

## A suggested demo walkthrough

The order matters: the workbook has stock for only one raw material, so buy the
components before trying to produce anything. That sequence is also the honest
picture of how the business actually runs.

1. **Dashboard** — five segments side by side, net profit 1,600, and the integrity
   panel. Point out that three checks pass and the fourth flags the stock-versus-
   ledger gap in their current books.
2. **Trial Balance** — pick any date; the difference is always zero.
3. **Inventory & BOM** — search `RMC-003`. It reads 790 kg at 32.27848101, matching
   their Item Master exactly because it is derived from the same movements.
4. **Inventory & BOM → Explode BOM** — explode `TRD-018` for 50 units. The
   requirement flattens to 210 kg of Elephent Cement, which is exactly the row in
   their own Production Entry sheet.
5. **Purchase Entry** — press **Load TRD-018 requirements** to fill the grid with
   everything the BOM needs, then post. Watch each item's average cost appear, and
   the balanced entry that debits inventory and credits the supplier payable.
6. **Production Entry** — produce 50 units of `TRD-018`. Show the cost build-up and
   the journal entry it is about to write, then post it. Stock falls, the new
   average cost appears, and the segment P&L updates. Then tick **inject a failure**
   and post again — nothing changes, because the transaction rolled back.
7. **Sales Entry** — sell some `TRD-018`. Revenue and COGS post together in one
   balanced entry, and the Trading segment appears on the dashboard.
8. **Reports → Balance Sheet** — the final check still reads zero after everything.
9. **Roles & Access** — sign out, sign in as *Sales Staff*. The Ledger menu is
   gone and Production Entry is no longer offered, because that role may not read
   them. Sales Entry opens normally. Try the Chart of Accounts address directly
   and the server still refuses — the menu is not the security.
10. **Configuration** — VAT, payroll, and the approval switches, each marked
    *pending client* rather than silently assumed.

Nothing in the walkthrough is destructive. **Reset demo data** on the Dashboard
puts the books back to the workbook state at any point, so a reviewer can try
things without wondering whether what they see is their own doing.

---

## Architecture

```
backend/app/
  core/                 config, database session, money and rate helpers,
                        account mappings, voucher numbering, exceptions
  modules/
    accounts/           models · schemas · repository · service · router
    opening_balances/   "
    journal_entries/    "
    items_bom/          "
    inventory_ledger/   weighted-average costing engine
    purchases/          atomic auto-posting
    production/         atomic auto-posting
    sales/              atomic auto-posting
    reports/            live queries, never stored twice
    users_roles/        RBAC matrix and enforcement
    settings/           configurable rules
  seed/                 workbook parsing and loading
frontend/src/
  features/             one folder per backend module
  shared/               API client, formatting, shared components
```

Rules the code holds to, from section 7 of the specification:

- **One module, one folder.** A router never runs a query — it calls `service.py`,
  which calls `repository.py`.
- **Money is `Decimal` end to end**, stored as `Numeric`. No floats anywhere.
- **Average and unit costs keep 8 decimal places** so the figures match the
  workbook's full division precision.
- **Postings are one transaction.** A failure rolls back ledger, order, and
  journal together — proven by tests that inject a mid-transaction failure.
- **Configuration is not hardcoded.** Rates live in the settings table.
- **Permissions are server-side**, with a test for every cell of the matrix.

---

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests -q
```

| File | Covers |
|---|---|
| `test_workbook_reconciliation.py` | The seeded database reproduces the workbook's figures |
| `test_journal_balance.py` | Balanced entries post; unbalanced and duplicate vouchers are refused |
| `test_production_posting.py` | Costing, balanced auto-posting, insufficient stock, rollback |
| `test_sales_posting.py` | Revenue and COGS together, margin, overselling, rollback |
| `test_role_permissions.py` | Every role's read and write access, enforced over HTTP |
| `test_auth.py` | Passwords, the TOTP second factor, recovery codes, password change |
| `test_demo_reset.py` | The demo can be restored to the workbook state, Admin only |
| `test_schema_sync.py` | A deployed database gains new tables and columns without losing rows |

The interface has its own tests, because the figures shown on screen must round
the same way the ledger does:

```bash
cd frontend && npm test
```

| File | Covers |
|---|---|
| `shared/format.test.ts` | Money, quantity, and percentage formatting, including the rounding cases from the worked example |
| `features/sales/SalesPage.test.tsx` | The sale price follows the chosen item, and a typed price is never overwritten |

---

## Configuration

Copy `.env.example` to `.env`, or set the variables directly:

| Variable | Default | Purpose |
|---|---|---|
| `RPCI_DATABASE_URL` | `sqlite:///./rpci_demo.db` | Where the books live — SQLite or Postgres |
| `RPCI_JWT_SECRET` | *(random per process)* | Session signing key. Set it on any deployment |
| `RPCI_ACCESS_TOKEN_MINUTES` | `720` | How long a session lasts |
| `RPCI_DEMO_PASSWORD` | `rpci` | Password for the seeded demo accounts |
| `RPCI_AUTO_SEED` | `true` | Seed from the workbook on first boot |
| `RPCI_SEED_FROM_EXCEL_PATH` | `../RPCI Accounts.xlsx` | Workbook to import |
| `RPCI_CORS_ORIGINS` | `*` | Origins allowed to call the API |
| `RPCI_ALLOW_DEMO_RESET` | `true` | Allow an Admin to restore the workbook state |

If `RPCI_JWT_SECRET` is unset, a random key is generated at process start. That
keeps local development frictionless and means there is no guessable default in
the source, but it signs everyone out whenever the service restarts. Generate a
real one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### SQLite or Postgres

SQLite is the default: one file, no setup. It is lost whenever the container is
rebuilt, which is fine locally and for a demo held in a single sitting.

For a link you leave with the client, point `RPCI_DATABASE_URL` at a Postgres
database so nothing they enter disappears when the host sleeps:

```bash
RPCI_DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

Paste a hosted URL unchanged — the application rewrites `postgres://` and
`postgresql://` to the installed `psycopg` driver, so no `+psycopg` suffix is
needed. Tables are created and seeded from the workbook on first boot, and left
alone afterwards. See [DEPLOYMENT.md](DEPLOYMENT.md), option C.

The suite runs against either engine:

```bash
cd backend
.venv/bin/python -m pytest tests -q                      # SQLite
RPCI_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host/db \
  .venv/bin/python -m pytest tests -q                    # Postgres
```

Reset the demo from the Dashboard, by deleting the database file, or with
`backend/.venv/bin/python scripts/seed_from_excel.py --rebuild`.

---

## Scope boundaries in this demo

Deliberately excluded, and scheduled for the production build:

- Database-level triggers for the double-entry rule (the demo enforces it in the
  service layer, covered by tests that inject a mid-transaction failure)
- Alembic migrations (the demo uses an additive schema sync; see below)
- Opening-balance editing and locking UI (imported data is shown read-only)
- VAT computation on transactions, payroll, and receipts
- Automated backups to S3

### A note on migrations

The specification calls for Alembic. The demo does not use it. Instead
`sync_schema()` in `backend/app/core/db.py` adds missing tables and columns at
startup, which is what lets a deployment with existing data gain new fields
without being rebuilt.

It is additive only — no drops, renames, type changes, or backfills — and it
raises rather than guessing a value for a NOT NULL column with no default. That
covers the changes this project makes, but Alembic is the right answer once the
schema starts moving in ways this cannot express.
