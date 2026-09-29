# What is built, and a demo walkthrough

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

**Phase 4 — Roles, authentication, VAT/tax, payroll, approvals (complete)**
- Authentication is real: hashed passwords, signed sessions, and a TOTP second
  factor with single-use recovery codes
- The full permission matrix is enforced server-side against the role in the
  token; every cell is tested
- Menus a role cannot read are hidden, and screens it may read but not change
  open read-only rather than presenting a form that cannot be submitted
- Sales receipts: a printable document per posted sale, read from the stored
  lines so it cannot disagree with the ledger; a VAT breakdown and a tax-invoice
  style when the client turns VAT on
- VAT/tax on transactions, computed from the settings table: output VAT on sales,
  input VAT on purchases, and a VAT summary report. Off until the rules are
  confirmed.
- Payroll: employees, a run that splits gross into its components, applies
  deductions, and posts one balanced entry; printable payslips
- A configurable approval gate, off by default: a covered action is held for a
  second person to approve on the Approvals screen
- Nothing unconfirmed is hardcoded — every rate and rule is editable from
  Administration → Configuration, with the client's confirmed answers pre-filled

**Phase 5 — Deployment and data (complete)**
- Dockerfile, docker-compose, and a Render blueprint for a public HTTPS URL, with
  a starter chart of accounts so a fresh deployment is usable immediately
- Import the client's own workbook, or start the books over, from
  Administration → Data

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

### Unlocking an account

If someone loses their phone *and* their recovery codes, an administrator can
clear their second factor from **Roles & Access**, and they sign in with a
password again. An administrator can also issue a new password, and enable or
disable an account.

Three deliberate constraints:

- **You cannot act on your own account** through these screens — that is what the
  Security page is for, and an accidental self-reset is far more likely than an
  intended one.
- **You cannot disable your own account.** That is what keeps the system
  administrable: an administrator can only disable somebody else, and disabling
  one of two leaves one.
- **Every action is recorded** in an append-only log, so "who cleared this, and
  when" is answerable afterwards.

*Still to do:* an issued password is not a forced change — the user can keep
using it. Requiring a change at next sign-in is the tidier behaviour and needs a
small extra flow.

## Correcting a mistake

A wrong posting is **reversed, never edited or deleted.** Any posted sale,
purchase or production run has a **Reverse** button; it asks for a reason and
then posts a mirror image — the stock moves back and the entry is reversed.

The original stays on the record, marked as reversed. The correction sits beside
it, with its own voucher number ending `-REV`.

Three reasons it works this way:

- **Editing would silently corrupt stock valuation.** Change a past purchase
  quantity and every later issue cost, every COGS figure and the closing stock
  value change — but the journal entries already posted do not. The stock sheet
  and the accounts would then disagree, which is the exact problem this system
  exists to remove.
- **The inventory ledger is append-only.** Every running balance depends on the
  row before it; editing one invalidates all those after.
- **Deleting destroys the evidence.** "Reversed on 3 November by Rahim" is a fact
  the client can defend. A vanished entry is not.

A reversal is refused if it cannot be done honestly — taking back stock that has
already been consumed, or un-making something that has since been sold. Those
cases need the later transaction reversed first.

*Still to consider:* whether reversing should require a second person. The build
specification raises approval for postings as an open question, and a reversal is
where it matters most.

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

Nothing in the walkthrough is destructive. **Reset data** on the Dashboard puts
the books back to the starting state at any point, so a reviewer can try things
without wondering whether what they see is their own doing.
