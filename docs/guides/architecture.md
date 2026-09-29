# Architecture and coding rules

## Layout

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
    vat_tax/            VAT/tax on transactions, from the settings table
    payroll/            employees, runs, and their balanced posting
    approvals/          the optional second-person approval gate
    reports/            live queries, never stored twice
    users_roles/        RBAC matrix and enforcement
    settings/           configurable rules (catalogue + typed getters)
    data/               workbook import and start-over
  seed/                 workbook parsing and loading, starter chart of accounts
frontend/src/
  features/             one folder per backend module
  shared/               API client, formatting, shared components
```

## Rules the code holds to, from section 7 of the specification

- **One module, one folder.** A router never runs a query — it calls `service.py`,
  which calls `repository.py`.
- **Money is `Decimal` end to end**, stored as `Numeric`. No floats anywhere.
- **Average and unit costs keep 8 decimal places** so the figures match the
  workbook's full division precision.
- **Postings are one transaction.** A failure rolls back ledger, order, and
  journal together — proven by tests that inject a mid-transaction failure.
- **Configuration is not hardcoded.** Rates live in the settings table.
- **Permissions are server-side**, with a test for every cell of the matrix.

## A note on migrations

The specification calls for Alembic. The demo does not use it. Instead
`sync_schema()` in `backend/app/core/db.py` adds missing tables and columns at
startup, which is what lets a deployment with existing data gain new fields
without being rebuilt.

It is additive only — no drops, renames, type changes, or backfills — and it
raises rather than guessing a value for a NOT NULL column with no default. It
also **refuses to start on a type mismatch**, because a narrowed money column
would truncate silently, and reports any column no model claims, which is what a
botched rename leaves behind.

That covers the changes this project makes, so Alembic is deferred until the
schema needs something this cannot express. Practical consequence: a new column
must be nullable or carry a `server_default`.
