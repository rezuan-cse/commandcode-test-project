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

### `RPCI Accounts.xlsx` does not reconcile, and cannot be fixed from this side

The client's own working workbook has an Inventory Ledger that does not agree with
its general ledger:

| | Value |
|---|---|
| Inventory Ledger (memo sheet) | 775,500 |
| General ledger inventory accounts (12xx) | 301,400 |
| **Variance** | **474,100** |

Confirmed by reading the workbook directly, independent of this application, so it
is in the file rather than in the import. Three separate causes:

1. **The memo sheet never posts journals.** The workbook's own *Instructions* sheet
   states this: the Inventory Ledger tracks quantity and cost only. The two sides
   are kept in step by hand, and here they are not.
2. **Three scratch rows with keyboard-mashed references** — `srthrfgh`, `fgfd`, and
   one with no reference at all — carry the entire stock balance
   (`RMA-014` production-in 750,000; `RMC-003` purchase-in 32,500; `RMC-003`
   production-out 7,000). **No journal entry exists for any of them.** The journal
   holds only four vouchers: PROD-001, PROD-002, PROD-003, SALE-001.
3. **The opening-stock rows are blank.** The GL opening balances declare 300,000 of
   inventory across accounts 1200/1210/1240/1250, but the Inventory Ledger's
   `Opening Stock` rows carry no quantity or value, so the stock ledger starts from
   nothing.

**This is not fixable by inventing figures.** Making the two sides agree requires the
real opening quantity and cost for each item, which only the client's accountant has.
The system therefore reproduces the workbook faithfully and lets the integrity check
flag the difference, rather than quietly forcing it to zero — see
`backend/tests/test_workbook_reconciliation.py`, which asserts this exact variance so
a future change cannot hide it.

**Use `SAMPLE_TEST_WORKBOOK.xlsx` for testing.** It reconciles exactly (6,000 =
6,000, all four checks pass) and uses round figures that can be checked by hand.

**To close this item**, ask the client for:
- the opening quantity and unit cost of each item at the cutover date, and
- the purchase and production vouchers behind those three stock rows.

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
