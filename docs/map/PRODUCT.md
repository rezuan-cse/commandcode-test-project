# Product map — where things live

Start here when a task touches code. Open the row's files, not the whole tree.
Design/rule docs are in `docs/guides/`.

| Task | Where | Notes |
|---|---|---|
| Ledger core: chart of accounts, opening balances, journal entries | `backend/app/modules/{accounts,opening_balances,journal_entries}/` | `models · schemas · repository · service · router`. Balance rule enforced in `journal_entries/service.py`. |
| Inventory costing, items, BOM | `backend/app/modules/{inventory_ledger,items_bom}/` | Weighted average + append-only ledger. Costs keep 8 dp. Items have CRUD; deletion is refused once anything refers to the item. |
| Customers and suppliers | `backend/app/modules/parties/` | One list, typed customer/supplier/both. Sales and purchases link to a record (`party_code`) while keeping the name text, so history reads unchanged. `POST /parties/import-existing` adopts names already on posted transactions and links them. |
| Purchases / production / sales posting | `backend/app/modules/{purchases,production,sales}/service.py` | Each `post()` is one atomic transaction that writes stock + a balanced journal entry. |
| Corrections (reverse, never edit/delete) | `backend/app/modules/journal_entries/service.py::reverse_for_transaction` + each module's `reverse()` | Mirror entry with a `-REV` voucher; guarded against double-reverse. |
| Reports (GL, TB, P&L, Balance Sheet, integrity) | `backend/app/modules/reports/` | Live queries, never stored twice. |
| Roles & permissions matrix | `backend/app/modules/users_roles/service.py` | `RESOURCES`, `RESOURCE_LABELS`, `MATRIX`. Mirror in `frontend/src/shared/permissions.ts`. Every cell is tested. |
| Authentication, TOTP 2FA, passwords | `backend/app/modules/auth/` | Two-step sign-in; roles come from the signed token. |
| Configurable rules (company, VAT, tax, payroll, approval) | `backend/app/modules/settings/` | Catalogue + typed getters; values live in the DB `settings` table, never hardcoded. |
| VAT/tax on transactions | `backend/app/modules/vat_tax/` + `purchases/sales service.py` | Off unless `vat.charge_vat` is set. |
| Payroll | `backend/app/modules/payroll/` | Employees, runs, balanced payroll JE. |
| Approval gate | `backend/app/modules/approvals/` + the reverse paths | Off unless `posting.require_second_approval` is set. |
| Data import / reset / fresh start | `backend/app/modules/data/`, `backend/app/seed/` | Starter CoA, workbook import, reset modes. |
| Account mappings (account codes) | `backend/app/core/accounting.py` | Inventory/revenue/COGS by segment/category. |
| Money, voucher numbering, enums, exceptions | `backend/app/core/` | `money.py`, `numbering.py`, `enums.py`, `exceptions.py`. |
| App wiring, routers, startup seeding | `backend/app/main.py`, `backend/app/core/db.py` | `models_registry.py` registers tables; `sync_schema()` is additive only. |
| Interface | `frontend/src/features/` (one folder per backend module) | `frontend/src/shared/` = API client, auth/demo context, formatters, UI primitives. |

## Guides

| Question | Document |
|---|---|
| How is the backend/frontend structured, and what rules must hold? | [../guides/architecture.md](../guides/architecture.md) |
| How do I run, build, test, deploy? What env vars exist? | [OPERATIONS.md](OPERATIONS.md) |
| What does each test cover? | [../guides/testing.md](../guides/testing.md) |
| What is built, and how do I demo it? | [../guides/product-guide.md](../guides/product-guide.md) |
| What is deliberately out of scope? | [../guides/scope-and-open-items.md](../guides/scope-and-open-items.md) |
