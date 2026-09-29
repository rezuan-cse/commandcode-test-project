# Scope boundaries and open items

## Scope boundaries in this demo

Deliberately excluded, and scheduled for the production build:

- Database-level triggers for the double-entry rule (the demo enforces it in the
  service layer, covered by tests that inject a mid-transaction failure)
- Alembic migrations (the demo uses an additive schema sync; see
  [architecture.md](architecture.md))
- Opening-balance editing and locking UI (imported data is shown read-only)
- VAT computation on transactions, payroll, and receipts
- Automated backups to S3

## Open items awaiting the client

Collected in [`CLIENT_QUESTIONS.md`](../../CLIENT_QUESTIONS.md) / `.docx` — company
details, VAT rates and scope, AIT/TDS/VDS, the payroll structure, and who may reverse
or approve a posting. Everything the client has not confirmed lives in the `settings`
table, flagged **pending client**, and is editable from **Administration →
Configuration** — nothing unconfirmed is hardcoded.

Known "still to do" behaviours:

- An administrator-issued password is not a forced change; the user can keep using
  it. Requiring a change at next sign-in needs a small extra flow.
- Whether reversing a posting should require a second person. The build
  specification raises approval for postings as an open question, and a reversal
  is where it matters most.
