# Scope boundaries and open items

## Built and working

Worth stating plainly, because earlier drafts of this file listed several of these
as "not yet built" after they had in fact shipped:

- **Double-entry postings** on every stock movement, sale, purchase and production
  run, in one transaction with the stock, the order and the journal committed
  together.
- **VAT on sales**: the rate applied is recorded on each invoice line, so changing
  the rate later never rewrites what was already posted. A business customer can
  carry a BIN; a retail walk-in does not need one.
- **Payroll** — employees, runs, payslips, and configurable departments and
  designations.
- **Approvals** — a second person can be required to approve a reversal, with the
  rule held in configuration rather than hardcoded.
- **Receipts and payments** against invoices or on account, with reversal
  re-activating the invoice automatically.
- **Customers and suppliers** as records with their own code, which posted
  invoices keep as the identity they were printed under.
- **Reports**: trial balance, general ledger, balance sheet (with retained earnings
  carried so multi-year books balance), period comparison, and low stock.
- **CSV/Excel export** on the operational screens, writing raw stored numbers so
  Excel sums them rather than display-formatted text.

## Deliberately excluded

Scheduled for a later build, and not needed for the client to run the business:

- Database-level triggers for the double-entry rule. It is enforced in the service
  layer and covered by tests that inject a mid-transaction failure, so nothing can
  post half an entry — but the guarantee lives in application code rather than in
  the schema. Adding constraints would need a migration and a backfill.
- Alembic migrations. Schema changes are additive and applied at startup by
  `sync_schema()`, which adds tables and nullable columns and never drops
  anything. See [architecture.md](architecture.md).
- Opening-balance editing UI. Imported opening balances are shown read-only.
- Automated backup to object storage as a scheduled job inside the application.
  Backups are scripted instead (`deploy/backup.sh` on a VPS, `scripts/backup_db.py`
  anywhere) and scheduled by cron or a GitHub Action. Keeping them out of the app
  means a backup still runs when the app does not.

## Open items awaiting the client

Collected in [`CLIENT_QUESTIONS.md`](../../CLIENT_QUESTIONS.md) / `.docx` — company
details, VAT rates and scope, AIT/TDS/VDS, the payroll structure, and who may reverse
or approve a posting. Everything the client has not confirmed lives in the `settings`
table, flagged **pending client**, and is editable from **Administration →
Configuration** — nothing unconfirmed is hardcoded.

Known "still to do" behaviours:

- **The VAT summary and the Mushak documents.** VAT is captured on every posting and
  a customer's BIN is stored, but two things are not built: the **Mushak 6.3 tax
  invoice** (a compliant receipt layout) and the **Mushak 9.1 summary** (output VAT
  by rate slab, input VAT, net payable). Both need the client's BIN and the rate
  slabs confirmed by their accountant before the layout can be finished, which is
  why they are waiting rather than forgotten.
- An administrator-issued password is not a forced change; the user can keep using
  it. Requiring a change at next sign-in needs a small extra flow.
- **The sample workbook import stays in the build but must not be offered at
  handover.** Administration → **Data** currently exposes **Restore sample
  workbook**, which replaces the books. It is useful for testing and dangerous once
  the client's real figures are in. It is to be removed, or made unavailable, before
  the system is handed over.

## Before handover

- Remove or disable **Restore sample workbook** from Administration → Data.
- Delete the five demo sign-in accounts once the client's own administrator exists,
  and turn off the shortcut card on the sign-in screen.
- Put the client's BIN and TIN into Configuration → Company details.
- Confirm a backup has been taken *and restored* at least once.
