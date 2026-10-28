# Test data sheet — what to type, and what you should see

Two ways to test, both supported. This sheet says which document to follow for
each, and gives the exact value for every field so the figures can be checked.

---

## Which document to follow

| I want to… | Follow | Data to enter |
|---|---|---|
| **Test as a brand-new company** (no previous books, which is Resinova's case) | **This sheet, Part A** — the walkthrough is also in `PRODUCTION_MANUAL.docx` under *Day one for a new company* | Type the values in Part A. No workbook. |
| **Test every screen against known figures** | **`SAMPLE_TEST_GUIDE.docx`** | Import `SAMPLE_TEST_WORKBOOK.xlsx` (Part B) |
| **Test the migration path** (bringing existing books across) | `PRODUCTION_MANUAL.docx` Test Cases 8, 8B and 20 | `SAMPLE_TEST_WORKBOOK.xlsx` for the sample; `RPCI Accounts.xlsx` for the client's real file |
| **Work through the 30 numbered test cases** | `PRODUCTION_MANUAL.docx` §3 — *End-to-End User Test Cases* | Part A for cases 1–21 and 25–30, Part C for the rest |
| **Learn the screens as an end user** | `USER_MANUAL.docx` | — |

`RPCI Accounts.xlsx` is **not** a test file. Its Inventory Ledger does not reconcile
with its general ledger (variance 474,100), so importing it always flags one
integrity check. That is the workbook, not the software. See
`docs/guides/scope-and-open-items.md`.

---

# Part A — a brand-new company, step by step

Every value below is deliberately a round number so the arithmetic can be checked
by hand.

## A0. Get a blank system

Pick one:

| Where | How | Warning |
|---|---|---|
| A new hosted deployment | Point `RPCI_DATABASE_URL` at a new empty database and restart | — |
| Your VPS | `docker compose -f docker-compose.prod.yml down -v`, then `up -d --build` | **`-v` deletes the database volume** — test deployments only |
| In the interface | Administration → **Data** → **Starting a new company** → **Start fresh** | Only shown when `RPCI_ALLOW_DATA_RESET` is on |

**You should see:** Chart of Accounts lists **48 accounts**, Inventory lists **no
items**, Journal Entries is empty, and the Dashboard shows four green checks with
the note that they compare nothing yet.

## A1. Sign in

| Situation | What to do |
|---|---|
| Fresh database with no accounts | The screen says **Create your administrator**. Fill: **Your name** `Resinova Owner`, **Email** `owner@resinovabd.com`, **Password** `first-run-password`, **Confirm password** the same. You are signed in immediately. |
| Demo deployment (5 accounts exist) | Sign in as `admin@rpci.demo`, password `rpci` |

**You should see:** the sidebar, and a **Getting started** card on the Dashboard.

## A2. Set the reporting period

Top bar, before entering anything:

| Field | Value |
|---|---|
| Period from | `2026-07-01` |
| As of | `2026-08-31` |

**Why:** every form's date defaults to **As of**, so this makes the first posting
land where you expect. The period also opens itself here once there is a posting —
it ends at the latest one.

## A3. Company details

Administration → **Configuration** → *Company details*. Press **Save**, then
**Confirm** on each row you agree with.

| Setting | Value |
|---|---|
| Company name | `Resinova Bangladesh` |
| Address | `10, Shanti Niketon, Road-05, Block-D, Sector-02, Aftabnagar, Badda, Dhaka-1212` |
| Telephone | `+880 1735-536678` |
| VAT registration (BIN) | `002016027-0208` |
| TIN | `155979113247` |
| Fiscal year starts in month | `7` |

**You should see:** `saved` beside each row and the badge change to **confirmed**.
`7` means the accounting year runs 1 July – 30 June.

## A4. VAT

Still in Configuration → *VAT*.

| Setting | Value | Why |
|---|---|---|
| Charge VAT | **on** | Ships on: the company is VAT-registered |
| Standard rate (%) | `15` | Confirm with the accountant |
| Prices include VAT | **off** | You quote prices before VAT |
| Input VAT account | `1130` | |
| Output VAT account | `2200` | |

**You should see:** the badges still read **pending client** on the rate — the value
is live, the confidence is not.

## A5. Add an account (optional, but it tests the new screen)

Chart of Accounts → **Add account**.

| Field | Value |
|---|---|
| Code | `6150` |
| Name | `Insurance` |
| Name (Bangla) | *(blank)* |
| Type | `Expense` |
| Segment | `Shared` |
| Normal balance | `Dr` |

**You should see:** `Account 6150 added`, and it listed. Now **48 + 1 = 49**
accounts. The code cannot be edited afterwards.

## A6. Add a second user

Administration → **Roles & Access** → **Add user**.

| Field | Value |
|---|---|
| Full name | `Resinova Accountant` |
| Email | `accountant@resinovabd.com` |
| Role | `Accountant` |
| Password (optional) | *(blank — one is generated)* |

**You should see:** a password shown once; write it down. The checklist item *Your
team can sign in* ticks.

## A7. Opening capital — the first entry

Journal Entries → **New journal entry**.

| Field | Value |
|---|---|
| Date | `2026-07-01` |
| Voucher | `JV-0001` (pre-filled) |
| Narration | `Share capital introduced` |
| Line 1 · Account | `1010 — Cash and Bank` |
| Line 1 · Debit | `500000` |
| Line 2 · Account | `3000 — Share Capital` |
| Line 2 · Credit | `500000` |

**You should see:** *Debits equal credits.* → **Post entry** succeeds.

**Check now — Dashboard, As of 2026-08-31:**

| Figure | Expected |
|---|---|
| Total assets | `500,000.00` |
| Owner's equity | `500,000.00` |
| Current period profit | `0.00` |
| Trial balance difference | `0.00` |
| Integrity checks | 4 green |

## A8. A supplier and a customer

Customers & Suppliers → **Add customer or supplier**, twice.

**Supplier**

| Field | Value |
|---|---|
| Code | `SUP-1` |
| Name | `Aftab Resin Supply` |
| Type | `Supplier` |
| Contact person | `Md. Karim` |
| Phone | `01711-000111` |
| Email | `sales@aftabresin.example` |
| Address | `Narayanganj` |
| Credit days | `30` |
| BIN | *(blank)* |

**Customer**

| Field | Value |
|---|---|
| Code | `CUS-1` |
| Name | `NovaCrete Trading` |
| Type | `Customer` |
| Contact person | `Ms. Farida` |
| Phone | `01811-000222` |
| Address | `Gulshan, Dhaka` |
| Credit days | `15` |
| BIN | `002016027-0208` |

**Why the BIN matters:** a business buyer's BIN is printed on the tax invoice; a
walk-in retail customer leaves it blank. Both are valid.

## A9. Items

Inventory & BOM → **Add item**, twice.

**Raw material**

| Field | Value |
|---|---|
| Code | `RMA-014` |
| Name | `Resin A` |
| Unit | `kg` |
| Category | `Raw Material` |
| Segment | `Manufacturing` |
| Reorder level | `50` |
| Active | on |

**Finished good**

| Field | Value |
|---|---|
| Code | `TRD-016` |
| Name | `NovaCrete PU-MF-A-Resin` |
| Unit | `kg` |
| Category | `Finished Good` |
| Segment | `Manufacturing` |
| Reorder level | *(blank — not watched yet)* |
| Active | on |

**You should see:** both listed at quantity `0` and cost `0` — stock comes from
transactions, never from typing.

## A10. The recipe

Inventory & BOM → click **TRD-016** (or its **Ledger** row button) → **Recipe** card.
The detail panel stays open; the recipe card is above *BOM explosion*.

| Field | Value |
|---|---|
| Add component | `RMA-014 — Resin A` |
| Qty per unit | `2` |

Press **Add to recipe**.

**You should see:** one row, `RMA-014`, `2.0000 kg`. Without this row Production
Entry has nothing to scale and the item is treated as a purchased material.

## A11. Buy the raw material

Purchase Entry. Set the line:

| Field | Value |
|---|---|
| Supplier | `Aftab Resin Supply` |
| Purchase date | `2026-07-10` |
| Settlement | `On credit (supplier payable)` |
| Line 1 · Item | `RMA-014 — Resin A` |
| Line 1 · Quantity | `100` |
| Line 1 · Unit cost | `1500` |

Press **Post purchase**.

**You should see** in the preview before posting: line value `150,000.00`, VAT
`22,500.00`, grand total `172,500.00`.

**Check:** Inventory shows `RMA-014` at **100 kg, average 1,500.00000000**.

## A12. Make the product

Production Entry.

| Field | Value |
|---|---|
| Item to produce | `TRD-016 — NovaCrete PU-MF-A-Resin` |
| Quantity produced | `10` |
| Production date | `2026-07-20` |
| Labor cost | `5000` |
| Overhead cost | `0` |

The component row fills itself from the recipe: **20 kg** of `RMA-014` (2 kg × 10).
Leave it as it is.

Press **Post production**.

**You should see:** total cost `35,000.00`, unit cost `3,500.00000000`
(= 20 kg × 1,500 + 5,000 labour, ÷ 10).

## A13. Sell it

Sales Entry.

| Field | Value |
|---|---|
| Customer | `NovaCrete Trading` |
| Sale date | `2026-08-01` |
| Line 1 · Item | `TRD-016 — NovaCrete PU-MF-A-Resin` |
| Line 1 · Quantity | `5` |
| Line 1 · Sale price | `5000` |

The sale price pre-fills with the average cost (3,500) — **overwrite it** with 5,000.
Press **Post sale**.

**You should see:** revenue `25,000.00`, VAT `3,750.00`, COGS `17,500.00`.

## A14. Take the customer's money

Receipts & Payments. Either press **Receive money**, or press **Settle** on the sale
row (which fills the invoice for you).

| Field | Value |
|---|---|
| Type | `Receipt — money in` |
| Customer | `NovaCrete Trading` |
| Date | `2026-08-10` — note this field defaults to **today**, not As of |
| Amount | `28750` |
| Account | `1010` |
| Reference | `TT-0001` |
| Note | `Full settlement` |
| Invoice allocation · Amount | `28750` |

Press **Record**.

**You should see:** *paid* on the invoice, and nothing left in *Invoices this
settles*. The amount is the **tax-inclusive** 28,750, not the 25,000 revenue.

## A15. Pay the supplier

Press **Pay supplier**.

| Field | Value |
|---|---|
| Type | `Payment — money out` |
| Supplier | `Aftab Resin Supply` |
| Date | `2026-08-15` |
| Amount | `172500` |
| Account | `1010` |
| Reference | `CHQ-0001` |
| Invoice allocation · Amount | `172500` |

## A16. Check the books

Dashboard, As of `2026-08-31`, Period from `2026-07-01`.

**Every step, checked as you go.** If one of these is wrong, the mistake was made
at that step — check it before carrying on. All figures are `assets =
liabilities + equity`; the trial balance difference must be `0.00` each time.

| After | Assets | L + E | Balanced |
|---|---|---|---|
| A7 opening capital | `500,000.00` | `500,000.00` | yes |
| A11 purchase | `672,500.00` | `672,500.00` | yes |
| A12 production | `672,500.00` | `672,500.00` | yes |
| A13 sale | `683,750.00` | `683,750.00` | yes |
| A14 receipt | `683,750.00` | `683,750.00` | yes |
| A15 supplier paid | `511,250.00` | `511,250.00` | yes |
| A17 payroll (optional) | `484,250.00` | `484,250.00` | yes |

**The final position:**

| Figure | Expected |
|---|---|
| Revenue | `25,000.00` |
| COGS | `17,500.00` |
| Gross profit / Net profit | `7,500.00` |
| Total assets | `511,250.00` |
| Total liabilities | `3,750.00` |
| Owner's equity (GL) | `500,000.00` |
| Current period profit | `7,500.00` |
| Assets = Liabilities + Equity | `511,250.00 = 511,250.00`, **balanced** |
| Trial balance difference | `0.00` |
| Integrity checks | 4 green |

**Inventory:** `RMA-014` 80 kg @ 1,500 = 120,000; `TRD-016` 5 @ 3,500 = 17,500.

**Where the 511,250 sits:** cash 351,250 + raw material 120,000 + finished goods
17,500 + input VAT 22,500. Against it: output VAT 3,750 + equity 507,500.

**Checklist:** 8 of 8, and the card disappears.

## A17. Optional: payroll

Only if you want to see it move the figures. It turns the profit into a loss,
which is a useful test of the red/neutral colours.

Employees → **Add employee**.

| Field | Value |
|---|---|
| Code | `EMP-001` |
| Name | `Rahim Uddin` |
| Department | `Office` |
| Designation | `Accounts Officer` |
| Personal email | `rahim@resinovabd.example` |
| Mobile | `01911-000333` |
| Joining date | `2026-07-01` |
| Bank account | `1234567890` |
| Gross salary | `30000` |
| Status | on (Active) |

Payroll Runs → **New payroll run**.

| Field | Value |
|---|---|
| Period start | `2026-08-01` |
| Period end | `2026-08-31` |
| Pay date | `2026-08-31` |

**You should see** in the preview: gross `30,000.00`, split Basic 18,000 /
House Rent 9,000 / Medical 1,500 / Transport 1,500; deductions `3,000.00` (the
statutory 10% placeholder, because no deduction list is configured yet); net
`27,000.00`.

**After posting:** cash falls by 27,000, the expense is 30,000, and net profit
becomes **−22,500.00** — shown red, not green.

---

# Part B — the workbook path

Use `SAMPLE_TEST_WORKBOOK.xlsx`. It is built for testing and reconciles exactly.

1. Administration → **Data**.
2. In **Coming from an existing system**, choose **Workbook (.xlsx)** →
   `SAMPLE_TEST_WORKBOOK.xlsx`.
3. Leave **Replace the books (empty them first)** ticked.
4. Press **Import workbook**.

**You should see, in Inventory & BOM:**

| Item | Quantity | Average cost | Value |
|---|---|---|---|
| `RM-100` | 100 | 20.00000000 | 2,000 |
| `RM-200` | 50 | 30.00000000 | 1,500 |
| `PKG-100` | 100 | 5.00000000 | 500 |
| `TRD-100` | 20 | 100.00000000 | 2,000 |
| `FG-100` | 0 | 0 | 0 |
| **Total** | | | **6,000** |

And all four integrity checks green, with the inventory check showing a variance of
`0.0000` — the stock ledger and the general ledger agree at **6,000**.

Item codes differ between the two paths: Part A uses `RMA-014` / `TRD-016` /
`SUP-1` / `CUS-1`; the sample workbook uses `RM-100` / `TRD-100` and has no parties.

---

# Part C — values for the remaining test cases

## Period close (Test Case 23)

Configuration → `posting.books_closed_through` = `2026-07-31`, **Save**. Then try a
purchase dated `2026-07-15` → refused: *The books are closed through 2026-07-31*.
Set it back to blank when done.

## Lockout (Test Case 24)

Sign out. Enter `admin@rpci.demo` with password `wrong` five times → *locked*.
Sign in as another administrator → Roles & Access → **Reset password** on that
account → sign in with the new one.

## A deposit before the invoice exists (Test Case 28)

Receipts & Payments → **Receive money**: Customer `NovaCrete Trading`, Date
`2026-08-20`, Amount `10000`, Account `1010`, and **no invoice allocation**.
The money is held **on account**; when an invoice exists, press **Apply** to use it.

## Compare two periods (Test Case 29)

Reports → **Period Comparison**. First period `2026-07-01`–`2026-07-31`, second
`2026-08-01`–`2026-08-31`. August shows the 25,000 revenue against July's 0, and the
percentage change is left **blank** because the baseline was zero — that is correct.

## Reorder list (Test Case 30)

Inventory & BOM → edit `TRD-016` → **Reorder level** `10`. Reports → **Low Stock**
now lists it: on hand 5, shortfall 5, at 3,500 → 17,500 to replace.

## Deleting an item with history (Test Case 25)

Try to delete `RMA-014` → refused, because it has been bought and consumed. Set
**Active** off instead; it keeps its history and leaves the pickers.

## Approvals (Test Case 17)

Configuration → `posting.require_second_approval` = on, `posting.approval_scope` =
`reversals`, **Save**. Sign in as the accountant, reverse a sale → it waits.
Sign in as the admin → **Approvals** → **Approve**.

## Restricted role (Test Case 22)

Create a user with role `Sales Staff`, sign in as them: Purchase Entry and Sales are
editable, Journal Entries and Configuration are not, and the menus they cannot read
are hidden rather than shown and failing.

---

# Part D — if a number is wrong, look here

| Symptom | Likely cause |
|---|---|
| Post button never appears on Purchase/Sale | No items yet, or the line has no item chosen |
| Production has no components | The item has no **Recipe** |
| Sale refuses with *insufficient stock* | You are selling more than was produced |
| VAT is 0 on a sale | `vat.charge_vat` is off, or the sale date is outside the period shown |
| Integrity check flags inventory | Stock was recorded without a matching journal entry — a workbook import, not a posting |
| Balance sheet does not balance | Check the Trial Balance difference; if that is 0, compare the period dates between screens |
| Checklist stuck at 8 of 8 but visible | It hides itself when complete; reload the page |
| Everything shows 0.00 | The top bar **As of** is before your postings |
