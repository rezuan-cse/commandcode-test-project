# RPCI ERP — Implementation Plan

**Source spec:** `RPCI_ERP_BUILD_SPEC.md` (240 lines, final consolidated).
**Excel data:** `RPCI Accounts.xlsx` — existing chart-of-accounts workbook, to be imported as a one-time seed in Phase 1.

This plan covers **all five phases** end-to-end but stays lean by detailing Phase 1 fully (architecture choices must hold across phases) and summarizing later phases so each phase plan can be expanded before execution begins.

---

## 0. Guiding principles (apply to every phase)

1. **Module-folder structure is mandatory** (spec §7.1). Each backend feature is `models.py / schemas.py / repository.py / service.py / router.py / tests/`. One module = one folder. Routers contain **no** DB or business logic — they call `service.py`.
2. **Money is `Decimal` / `NUMERIC(18,4)` end-to-end.** No floats, anywhere.
3. **Double-entry is enforced at the DB layer**, not just in code: a PostgreSQL trigger + a `CHECK` on a derived view rejects unbalanced journals (see §1.4).
4. **All production/sales/purchase postings are one DB transaction.** Failure anywhere → full rollback.
5. **Config lives in env vars + a `settings` table**, never hardcoded (VAT rates, payroll, anything `TBD`).
6. **Frontend mirrors backend module boundaries** (`src/features/<module>/…`).
7. **No function > ~50 lines**, type hints + docstrings on every function.
8. **Every module ships its own tests:** happy path + unbalanced-entry rejection + (for prod/sales) rollback case.

---

## 1. Repo layout (created once, populated phase-by-phase)

```
commandcode-test-project/
├── backend/
│   ├── app/
│   │   ├── core/                  # config, db session, security, deps, exceptions
│   │   ├── modules/
│   │   │   ├── accounts/          # Chart of Accounts
│   │   │   ├── opening_balances/
│   │   │   ├── journal_entries/
│   │   │   ├── items_bom/         # Item Master + BOM Master + recursive explosion
│   │   │   ├── inventory_ledger/  # append-only ledger, weighted-average
│   │   │   ├── purchases/         # Purchase Entry (Phase 2)
│   │   │   ├── production/        # Production Entry (Phase 2)
│   │   │   ├── sales/             # Sales Entry (Phase 3)
│   │   │   ├── reports/           # GL / TB / P&L / BS / Inventory valuation
│   │   │   ├── vat_tax/           # Phase 4
│   │   │   ├── payroll/           # Phase 4
│   │   │   └── users_roles/       # auth + RBAC middleware
│   │   └── main.py
│   ├── alembic/                   # migrations
│   ├── tests/                     # cross-module integration tests
│   ├── pyproject.toml             # poetry/uv, ruff, mypy, pytest
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── features/
│   │   │   ├── accounts/
│   │   │   ├── journal/
│   │   │   ├── items/
│   │   │   ├── production/
│   │   │   ├── sales/
│   │   │   ├── reports/
│   │   │   └── auth/
│   │   ├── shared/                # api client, auth context, RBAC hooks, formatters
│   │   └── main.tsx
│   ├── vite.config.ts
│   └── Dockerfile
├── infra/
│   ├── docker-compose.yml         # api + postgres + nginx
│   ├── nginx.conf
│   └── backup/                    # pg_dump → S3 cron + script
├── scripts/
│   └── seed_from_excel.py         # one-time import of RPCI Accounts.xlsx
├── RPCI_ERP_BUILD_SPEC.md         # (already present)
├── RPCI Accounts.xlsx             # (already present)
└── RPCI_ERP_PLAN.md               # (this file)
```

---

## 2. Phase 1 — Ledger Core  *(fully detailed)*

### 2.1 Backend modules to create

**`core/`**
- `config.py` — Pydantic `Settings` reading env vars (`DATABASE_URL`, `JWT_SECRET`, `JWT_ALG`, `ACCESS_TOKEN_EXPIRE_MINUTES`).
- `db.py` — SQLAlchemy engine + `SessionLocal` + `get_db` dependency.
- `security.py` — `hash_password`, `verify_password` (bcrypt via passlib), `create_access_token`, `decode_token`.
- `deps.py` — `get_current_user`, `require_role(*roles)` dependency factories (RBAC, §4).
- `exceptions.py` — typed domain errors mapped to HTTP 4xx.

**`modules/users_roles/`**
- Models: `User`, `Role` (Admin / Accountant / Store / Sales / Viewer), `UserRole`.
- Schemas: login, user CRUD.
- Repository: `get_by_email`, role lookups.
- Service: `authenticate`, `issue_token`.
- Router: `/auth/login`, `/auth/me`, `/users` (Admin only).
- Seed: an `alembic` seed migration creates the five roles and one initial admin (`admin@rpci` / password from env).

**`modules/accounts/`** — Chart of Accounts
- Model: `Account(id, code PK, name, type ENUM[Asset|Liability|Equity|Revenue|COGS|Expense|OtherIncome], segment ENUM[Import|Manufacturing|Packaging|Trading|Application|Shared], normal_balance ENUM[Dr|Cr], is_active)`.
- Schemas: `AccountCreate`, `AccountOut`.
- Service: enforce code uniqueness; `type → normal_balance` default validation.
- Router: `GET/POST/PUT/DELETE /accounts` — write endpoints require Admin/Accountant per §4.
- Tests: create unique code, reject duplicate, reject invalid type/segment combo.

**`modules/opening_balances/`**
- Model: `OpeningBalance(id, account_id FK, segment, debit NUMERIC(18,4), credit NUMERIC(18,4), as_of_date, locked BOOL, locked_at, created_by)`.
- Service: `lock_as_of(date, user)` — checks `sum(debit) == sum(credit)` across the batch, then sets `locked=true`. Block save if unbalanced. Once locked, edits require Admin and write to `opening_balance_audit` (who, when, before/after JSONB).
- Router: `POST /opening-balances` (bulk), `POST /opening-balances/lock`, `GET /opening-balances?as_of=…`.
- Tests: unbalanced batch rejected; locked batch rejects edits; admin override creates audit row.

**`modules/journal_entries/`** — manual JEs
- Models: `JournalEntry(id, voucher_no UNIQUE, date, narration, source ENUM[Manual|Production|Sales|Purchase|Payroll], posted_at, posted_by, reversed_by_id NULLABLE)`, `JournalLine(id, entry_id FK, account_id FK, segment ENUM[…], debit, credit, narration)`.
- Schemas: `JournalEntryCreate` (with nested `lines`), `JournalEntryOut`.
- **DB-level balance enforcement** — see §1.4 below.
- Service: validate `sum(debit)==sum(credit)` in code **and** rely on DB constraint; idempotent voucher number; on edit after posting, write `journal_audit` row.
- Router: `POST /journal-entries`, `GET /journal-entries`, `GET /journal-entries/{id}` (Accountant+ for write; all roles view per §4).
- Tests: balanced entry persists; unbalanced rejected by API; double-submit of same voucher rejected.

**`modules/reports/`** — read-only live views
Implemented as **PostgreSQL views + thin read endpoints** (no materialized tables). Each is a SQL view in a migration, exposed by a service that just runs `SELECT * FROM v_…`.

- `v_general_ledger(account_id, period_start, period_end)` — opening + per-period Dr/Cr + closing.
- `v_trial_balance(as_of_date)` — one row per account, terminates with a balancing row that must always = 0.
- `v_pnl_by_segment(period_start, period_end, segment?)` — per-segment and company-wide; gross margin %.
- `v_balance_sheet(as_of_date)` — Assets/Liabilities/Equity totals with a `is_balanced BOOL` column that must always be `true`.

Endpoints (`GET /reports/…`) are RBAC-gated per §4 (Owner/Viewer can read all).

**Database-level double-entry enforcement (§7.2 hard requirement):**
- Migration installs a **row-level trigger** on `journal_lines`:
  - After insert/update/delete, it recomputes totals for the affected `entry_id` and raises `EXCEPTION` if `sum(debit) != sum(credit)`.
- Plus a `CHECK (debit >= 0 AND credit >= 0 AND NOT (debit > 0 AND credit > 0))` on each line.
- Inventory non-negative enforced similarly in Phase 2.

### 2.2 Frontend (Phase 1 slice)

- Login page → JWT in `httpOnly` cookie (preferred) or `localStorage`; API client attaches `Authorization: Bearer`.
- React Router with feature folders per module.
- Pages: `/accounts`, `/opening-balances`, `/journal/new`, `/journal`, `/reports/gl`, `/reports/tb`, `/reports/pnl`, `/reports/bs`.
- Shared `<DataTable>`, `<MoneyInput>` (uses string-based decimal to avoid float), `<SegmentSelect>`, `<RoleGate role="Admin">` wrapper.
- PWA manifest + service worker for offline form draft (later polish).

### 2.3 Seed from `RPCI Accounts.xlsx`
`scripts/seed_from_excel.py` (run once after first migration):
- Open workbook, read first sheet (assumed chart-of-accounts layout: code | name | type | segment | normal_balance).
- Map sheet rows → `Account` rows. Skip header. Warn (don't fail) on rows that don't parse — log to `scripts/seed_report.txt`.
- Print a count and a sample diff. Idempotent: skips codes that already exist.

### 2.4 Phase 1 acceptance criteria (from spec §9)
- [ ] Unbalanced journal entry rejected by API **and** by DB constraint if API is bypassed.
- [ ] Trial Balance always sums to zero.
- [ ] Balance Sheet `is_balanced = true` after any sequence of manual entries.
- [ ] Locked opening balances reject edits (except Admin with audit row).
- [ ] Each role in §4's table gets a 403 from the API for actions outside its permissions (smoke test of all 5 roles).
- [ ] `seed_from_excel.py` populates ≥ the codes present in `RPCI Accounts.xlsx`.

**Stop here, re-plan, then begin Phase 2.**

---

## 3. Phase 2 — Inventory & Production *(summary; expand before starting)*

### 3.1 New modules

**`modules/items_bom/`**
- `Item(id, code PK, name, category ENUM[RawMaterial|WIP|FinishedGood|Packaging|Trading|ImportedGoods], segment, uom, is_active)`.
- `BomComponent(parent_item_id, component_item_id, qty_per_unit NUMERIC(18,4), sequence)`. Self-referential via parent=component recursion.
- Service `explode_bom(item_id, target_qty)` uses a **recursive CTE** in PostgreSQL to flatten multi-stage BOM. Returns per-leaf raw-material requirements.

**`modules/inventory_ledger/`** (append-only)
- `InventoryLedgerRow(id, item_id, movement_type ENUM[Purchase|ProductionIn|ProductionOut|SaleOut|Adjustment], qty NUMERIC(18,4), unit_cost NUMERIC(18,4), running_qty NUMERIC(18,4), running_value NUMERIC(18,4), ref_entry_id FK to JournalEntry, ref_order_id, created_at)`.
- Computed fields `qty_on_hand` and `avg_cost` are **derived views**, never editable.
- DB trigger enforces `running_qty >= 0` (no negative stock without explicit adjustment).

**`modules/purchases/`** (assumed needed for raw material inflow)
- `PurchaseOrder` + lines. On post: atomic txn → inventory rows + balanced JE (Dr Inventory / Cr Cash or Accounts Payable).

**`modules/production/`** (the core automation — build carefully)
- `ProductionOrder` + `ProductionLine(component_item_id, qty_consumed)` + headers (labor_cost, overhead_cost).
- Service `post_production(order, user)` runs in one DB transaction:
  1. For each line: lookup current `avg_cost`, write `ProductionOut` inventory row at that cost.
  2. `total_cost = sum(line.qty * avg_cost) + labor + overhead`.
  3. `unit_cost = total_cost / produced_qty`.
  4. Write `ProductionIn` row for output item, recompute its weighted-average cost (`(old_value + in_value) / (old_qty + in_qty)`).
  5. Build balanced JE: Dr Finished Goods (total cost) / Cr Raw Material & WIP (consumed value) / Cr Cash/Payable (labor + overhead).
  6. **If any step raises, full rollback.** Tested by injecting a failure mid-transaction (mock or savepoint test) and asserting no partial rows.

### 3.2 Phase 2 acceptance
- [ ] Multi-stage production run correctly reduces multi-level component stock.
- [ ] Weighted-average cost updates correctly across multi-stage BOM.
- [ ] Auto-generated JE balances.
- [ ] Forced mid-transaction failure leaves zero new ledger/je rows.

---

## 4. Phase 3 — Sales & Segment Reporting *(summary)*

### 4.1 `modules/sales/`
- `SalesOrder` + lines. `post_sale` is one atomic txn:
  - Lookup `avg_cost` per item (snapshot it on the sale line so historical COGS doesn't drift).
  - Write `SaleOut` inventory rows.
  - Build balanced JE in **one** entry: Dr AR/Cash (sale total) / Cr Sales (sale total), **and** Dr COGS / Cr Inventory (cost total).
- Reports: extend `v_pnl_by_segment` with sales detail; segment dashboard page (revenue, COGS, GM%, by segment and company-wide).

### 4.2 Acceptance
- [ ] Sale reduces inventory at current weighted-average cost.
- [ ] Revenue + COGS JE posts in one entry, balanced.
- [ ] Segment P&L totals reconcile to company-wide P&L (sum of segments = company row).

---

## 5. Phase 4 — Roles, VAT/Tax, Payroll *(summary)*

- **Roles:** `require_role(...)` already wired in Phase 1; Phase 4 adds exhaustive route coverage + tests for every cell of §4's matrix.
- **`modules/vat_tax/`:** settings table (`vat_rate`, `ait_rate`, `tds_rules` JSON), `vat_transaction` lines on purchase/sale postings, net payable/receivable report. All rates from settings — never hardcoded.
- **`modules/payroll/`:** `Employee`, `SalaryStructure` (JSONB config), `PayrollRun` with computed gross/deductions/net; auto-posts balanced JE (Dr Salary Expense / Cr Cash/Bank).

### 5.1 Acceptance
- [ ] Every §4 role gets 403 on every action outside its matrix (server-side), verified by a parameterized test suite.

---

## 6. Phase 5 — Deployment & Polish *(summary)*

- `infra/docker-compose.yml`: `api`, `postgres:16`, `nginx` (TLS termination, reverse-proxy to API).
- Single Lightsail instance ($5–10/mo) behind Cloudflare free tier.
- `infra/backup/backup.sh`: nightly `pg_dump | gzip | aws s3 cp` via cron; 30-day retention lifecycle.
- Mobile responsive pass: ensure all forms work at 360px width; tables become stacked cards.
- Health endpoint `/healthz`, container restart policy `always`, volume for Postgres data.

### 6.1 Acceptance
- [ ] Reachable over HTTPS on real domain.
- [ ] Container restart preserves data.
- [ ] Restore-from-backup on a fresh DB produces identical schema + row counts.

---

## 7. Open items explicitly NOT blocking start
Per spec §10, these are deferred — we build with the stated default and keep configurable:
1. Exact VAT/AIT/TDS rates — configurable in `settings` table.
2. Payroll structure — JSONB config, generic form.
3. Purchase Entry — **assumed yes**, built in Phase 2.
4. Second-person approval for postings — out of scope for v1, leave a hook.
5. 2FA — out of scope for v1, JWT only.
6. Customer invoice/receipt printing — out of scope for v1, PWA print page later.

---

## 8. Execution order

1. **Phase 1 only** first. When its acceptance list passes, pause and re-plan Phase 2 (the production-posting transaction is the trickiest piece and benefits from its own dedicated plan).
2. Re-plan Phase 3, 4, 5 the same way — one phase at a time, accept-then-expand.
3. The `scripts/seed_from_excel.py` run is part of **first-boot** of Phase 1, never re-run in prod.

---

## 9. Verification matrix (per phase)
At the end of each phase, the following commands must succeed:

| Check | Command |
|---|---|
| Backend type-check | `mypy app/` |
| Backend lint | `ruff check app/` |
| Backend tests | `pytest -q` |
| DB migrations up | `alembic upgrade head` |
| OpenAPI docs reachable | `curl localhost:8000/docs` → 200 |
| Acceptance scenario | run the scenario script for that phase; assert exit 0 |

A phase is **not done** until every row above is green and every acceptance bullet in §9 of the spec is ticked.

---

## 10. Client Demo (deliverable before full Phase 1 build)

**Purpose:** a clickable, hosted demo that runs the client's *own* workbook data (89 accounts, opening balances, 3 sample production runs, 1 sale, inventory movements, reports) through the real double-entry and weighted-average-costing logic — so the client meeting is "look at your books in the new system" rather than "look at fake numbers in a mock UI."

**Scope:** Phase 1 of this plan, plus a thin slice of Phase 2 (production + inventory) and Phase 3 (sales + segment P&L). Skips for the demo: RBAC enforcement (single password OK), real auth flow polish, payroll, VAT, opening-balance locking, multi-stage BOM recursion (workbook only has 1-stage BOMs).

### 10.1 Stack adjustments for the demo
| Concern | Full plan | Demo |
|---|---|---|
| Database | PostgreSQL + NUMERIC + triggers | **SQLite** (single file, zero ops) + `Decimal` enforced in Python |
| Auth | JWT + RBAC matrix | Single shared password via env var; no user table |
| Deploy | Lightsail + Cloudflare | **Render free tier** (web service + persistent disk) |
| Money type | `NUMERIC(18,4)` + DB trigger | `Decimal` in Python + a `Decimal` column in SQLAlchemy |
| Frontend | Full PWA | React + Vite, mobile-responsive, no PWA install needed for demo |

Module-folder structure, `Decimal`-only money, and the "router → service → repository" rule still apply — so the demo code carries forward into Phase 1 with minimal rework.

### 10.2 Demo data load (one-time, on first boot)
`scripts/seed_from_excel.py` parses `RPCI Accounts.xlsx` (all 12 sheets) and writes into SQLite in dependency order:

1. **Chart of Accounts** → 89 rows (sheet 2). Bengali names preserved as `name_bn`; English transliteration/romanization stored as `name_en` (used in UI; toggleable).
2. **Item Master** → 35 sample items (sheet 5; rest are blank rows). Categories, segments, units preserved.
3. **Opening Balances** → from the General Ledger sheet's opening columns (sheet 9). 11 accounts with non-zero opening Dr/Cr.
4. **BOM Master** → 1 multi-stage product (TRD-018, 6 components).
5. **Journal Entries** → the 14 sample rows from sheet 4 (PROD-001/002/003 + SALE-001). These are pre-balanced and act as the seed history. Voucher numbers preserved.
6. **Inventory Ledger** → from sheet 8, the rows with values (RMA-014 Purchase-In, RMC-003 Purchase-In, RMC-003 Production-Out). Weighted-average cost recomputed by the demo logic to verify the workbook's numbers (RMC-003: 790 kg @ 32.27848101 should match).

Idempotent: if the DB already has rows, the seeder skips. Re-runnable by deleting the SQLite file.

### 10.3 Demo backend modules (subset of full plan)
- `core/` — config, db session, **no auth deps** (single-password gate at app level).
- `modules/accounts/` — full CRUD, read-only in demo.
- `modules/opening_balances/` — read-only view (no locking UI in demo).
- `modules/journal_entries/` — **read-only** for seed entries; a "post demo journal" endpoint that takes a balanced 2-line entry, validates in Python, writes atomically.
- `modules/items_bom/` — read-only list + BOM tree view + explode endpoint.
- `modules/inventory_ledger/` — append-only writer for the seed; read views for valuation.
- `modules/production/` — **active**: takes item + qty + components + labor/OH, runs the full atomic-posting logic (consume at avg cost → compute unit cost → update output avg → balanced JE). Tested with a demo scenario that walks PROD-003 against the seed inventory.
- `modules/sales/` — **active**: same atomic-posting pattern (avg-cost snapshot, Revenue + COGS in one JE).
- `modules/reports/` — all four reports (GL, TB, P&L by Segment, Balance Sheet) computed live from SQLAlchemy queries (not DB views, since SQLite has no views). All four must reproduce the workbook's numbers within rounding (P&L Manufacturing = 4,000 / 2,400 / 1,600 / 40%; Balance Sheet balanced at 801,600).

### 10.4 Demo frontend screens
1. **Dashboard** — five segment cards side-by-side: revenue / COGS / gross profit / margin %, company-wide totals, "balanced: yes/no" indicator with green tick.
2. **Chart of Accounts** — 89 rows, filterable by segment + type, search by code/name. Bengali + English toggle.
3. **Trial Balance** — table that sums to zero with a final row "Difference: 0.00". Date selector.
4. **General Ledger** — per-account detail, period filter, opening + period + closing columns (matches workbook layout).
5. **Inventory** — item list with on-hand qty + avg cost (live computed), expandable to show last 10 ledger rows. "BOM Explode" modal: pick item + qty → see raw-material requirements flattened.
6. **Production Entry** — the centerpiece form. Item dropdown, qty input, auto-suggests components from BOM (scaled by qty), labor/OH inputs, "Preview" panel shows component cost + labor + OH + unit cost + auto-generated balanced JE before posting. "Post" button → atomic transaction → toast "Posted PROD-004: balanced ✓" → screen updates.
7. **Sales Entry** — similar, shows Revenue + COGS preview before posting.
8. **Balance Sheet** — Assets / Liabilities / Equity, with the "Check: A − L − E = 0" line at the bottom. Green if zero, red if not (should never be red).

### 10.5 Demo acceptance criteria
- [ ] On first boot, seeding from `RPCI Accounts.xlsx` produces a DB that, when all four reports are rendered, matches the workbook's numbers exactly:
  - Manufacturing P&L: 4,000 / 2,400 / 1,600 / 40%
  - Balance Sheet balanced at 801,600
  - Trial Balance last row: 0
  - Inventory ledger `RMC-003` row shows 790 kg @ avg cost 32.27848101
- [ ] Posting a new production run (e.g., another 50 units of TRD-018) atomically: reduces RMC-001…005 + PKC-026 stock, increases TRD-018 stock at the calculated unit cost, posts a balanced 3-line JE, updates segment P&L.
- [ ] Posting a sale against FG001 reduces stock at current avg cost, posts a 4-line JE (Dr AR / Cr Sales + Dr COGS / Cr Inventory), updates Manufacturing segment.
- [ ] A forced mid-transaction failure (test-only endpoint that injects a savepoint failure) leaves zero partial rows.
- [ ] Mobile responsive: every screen usable at 360 px width.

### 10.6 Demo deployment
- **Render free tier** (or Railway/Fly.io): one web service, persistent disk for SQLite file.
- Environment: `SECRET_KEY`, `DEMO_PASSWORD`, `SEED_FROM_EXCEL_PATH` (defaults to bundled file).
- URL pattern: `https://rpci-demo.onrender.com` (or similar). Demo data resets on every deploy; documented in the README.
- Deploy script: `render.yaml` at project root, blueprint-deployable.

### 10.7 Out of demo scope (deferred to full Phase 1+)
- Real RBAC (Admin/Accountant/Store/Sales/Viewer) — demo uses single password
- Opening-balance locking flow (data shown read-only)
- Manual journal entry from UI (only production + sales posting in demo)
- Payroll, VAT/Tax, multi-stage BOM recursion UI
- PostgreSQL + DB triggers (SQLite + Python checks instead)
- Backup / disaster recovery (Render keeps the disk; good enough for a demo)

After the client approves the demo, the demo codebase becomes the starting point for **Phase 1** of the full plan, with the demo-scope items promoted into the production build per their original acceptance criteria.
