# Tests

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
| `test_reversal.py` | A reversal restores stock, average cost and the trial balance exactly |
| `test_auth.py` | Passwords, the TOTP second factor, recovery codes, password change |
| `test_account_admin.py` | Unlocking a locked-out account, and who may do it |
| `test_data.py` | Fresh start, workbook import, and starting the books over (Admin only) |
| `test_schema_sync.py` | A deployed database gains new tables and columns without losing rows, and drift is caught rather than ignored |
| `test_production_readiness.py` | Who entered a transaction comes from the session and not the body; a closed period refuses every posting; wrong passwords lock the account, and a reset releases it; emptying the books keeps the accounts |
| `test_item_master.py` | Adding, correcting and deleting items over HTTP: the code is normalised and fixed, a duplicate is refused, an item with history cannot be deleted, and a view-only role cannot write |
| `test_parties.py` | Customer and supplier records: the recorded name comes from the record not the form, adopting existing names claims their history and is safe to repeat, a partner with history cannot be deleted, and the "both" type appears in both lists |
| `test_payments.py` | Receipts and payments: a receipt settles an invoice in full or in part, an invoice cannot be overpaid, money with no invoice is held on account and applied later, reversing a receipt puts the invoice back to unpaid, the direction must match the invoice type, and the trial balance still agrees |
| `test_reports_comparison.py` | Period comparison: the movement between two months, a fall reported as negative, no percentage change against a period with nothing in it, a margin compared in points, and the figures agreeing with the plain P&L |
| `test_low_stock.py` | Reorder level and the low-stock list: a blank level means "not watched" and is never listed, an item exactly at its level is listed, the shortfall and its cost are right, enough stock clears it, and an inactive item is left off |
| `test_settings.py` | The client owns their configuration: every setting in the catalogue can be changed through the API, a silly value is refused, a change takes effect without a restart, a client's value is never reset by the boot-time seeding, and only an administrator may change one |

The interface has its own tests, because the figures shown on screen must round
the same way the ledger does:

```bash
cd frontend && npm test
```

| File | Covers |
|---|---|
| `shared/format.test.ts` | Money, quantity, and percentage formatting, including the rounding cases from the worked example |
| `shared/csv.test.ts` | CSV escaping: commas and quotes in a customer name stay in one cell, a stored amount is written unformatted so it still sums in Excel, and an empty export still has headings |
| `features/sales/SalesPage.test.tsx` | The sale price follows the chosen item, a typed price is never overwritten, and a view-only role sees no form |
| `features/sales/ReceiptPage.test.tsx` | The receipt itemises the posted lines and totals and does not claim to be a VAT invoice |

## Verifying the numbers

The import is checked against the workbook, both by the test suite and by a
standalone script:

```bash
cd backend && .venv/bin/python -m pytest tests -q          # 124 tests
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
