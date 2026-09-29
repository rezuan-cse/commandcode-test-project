# Sample Test Data & Walkthrough

A ready-made workbook and a scripted walkthrough for testing the system end to
end: **buy → make → sell**, plus payroll.

Everything below uses round figures, so you can check the maths by hand.

**Files**

| File | What it is |
|---|---|
| `SAMPLE_TEST_WORKBOOK.xlsx` | The sample workbook to import |
| `scripts/make_sample_workbook.py` | Rebuilds the workbook at any time |

Rebuild it whenever you like:

```bash
backend/.venv/bin/python scripts/make_sample_workbook.py
```

---

## Step 0 — Load the sample workbook

1. Sign in as **Admin**.
2. Click **Data** in the **Administration** group.
3. Under **Import an existing workbook**, click **Workbook (.xlsx)** and choose
   `SAMPLE_TEST_WORKBOOK.xlsx`.
4. Leave **Replace the books (empty them first)** ticked.
5. Click **Import workbook**.

**What you should see.** A green message such as *"Imported the workbook: 29
accounts, 5 items, 3 bom edges, 5 opening balances, 0 journal entries, 4 inventory
rows"*. (Wording lists whatever it loaded.)

> Importing **replaces** the books. The workbook is built for a clean test, so
> there is no history to lose.

### What the workbook contains

**Accounts (29)** — the standard set the system's automatic postings use, so every
account a purchase, production run or sale needs is present.

**Items (5)**

| Code | Name | Category | Segment | Unit |
|---|---|---|---|---|
| `RM-100` | Raw Material A | Raw Material | Manufacturing | kg |
| `RM-200` | Raw Material B | Raw Material | Manufacturing | kg |
| `PKG-100` | Packaging Box | Packaging | Packaging | Pcs |
| `FG-100` | Finished Good X | Finished Good | Manufacturing | Pcs |
| `TRD-100` | Trading Item | Trading Stock | Trading | Pcs |

**Recipe (BOM)** for `FG-100` — one unit needs:

- **2 kg** of `RM-100`
- **1 kg** of `RM-200`
- **1 Pcs** of `PKG-100`

**Opening balances** — Cash 494,000 and opening stock, against Share Capital
500,000. Because the opening inventory in the accounts equals the opening stock in
the ledger, all four integrity checks pass from the start.

### Starting position (check this after importing)

Open **Inventory & BOM**. You should see:

| Item | Qty on hand | Avg cost | Value |
|---|---|---|---|
| `RM-100` | 100 | 20.00000000 | 2,000.00 |
| `RM-200` | 50 | 30.00000000 | 1,500.00 |
| `PKG-100` | 100 | 5.00000000 | 500.00 |
| `TRD-100` | 20 | 100.00000000 | 2,000.00 |
| `FG-100` | 0 | 0.00000000 | 0.00 |

**Checkpoint:** open **Reports → Trial Balance**. The **Difference — must be zero**
row should read `0.0000`, and Total assets on the Dashboard should be `500,000.00`.

---

## Step 1 — Purchase: buy raw materials

Click **Purchase Entry**.

**Header**

| Field | Value to enter |
|---|---|
| **Supplier** | `Sample Supplier` |
| **Purchase date** | `2026-01-10` |
| **Settlement** | *On credit (supplier payable)* |

**Line 1** (the first row is already there)

| Field | Value |
|---|---|
| **Item** | `RM-100 — Raw Material A` |
| **Quantity** | `100` |
| **Unit cost** | `25` |

**Then click Add line, and fill the second row:**

| Field | Value |
|---|---|
| **Item** | `RM-200 — Raw Material B` |
| **Quantity** | `50` |
| **Unit cost** | `34` |

**Check the preview**, then click **Post purchase**.

**Expected result**

| Where | What you should see |
|---|---|
| **Purchase value** | `4,200.00` (2,500 + 1,700) |
| **Effect on average cost** | `RM-100` 20 → **22.5**; `RM-200` 30 → **32** |
| **Journal entry** | Debit Raw Material Inventory 2,500; Debit Raw Material Inventory 1,700; Credit Accounts Payable — Local 4,200 |

**New stock position**

| Item | Qty | Avg cost | Value |
|---|---|---|---|
| `RM-100` | 200 | 22.50000000 | 4,500.00 |
| `RM-200` | 100 | 32.00000000 | 3,200.00 |

**How the numbers were reached**

- `RM-100`: old 100 at 20 = 2,000; bought 100 at 25 = 2,500.
  New average = `(2000 + 2500) ÷ (100 + 100)` = `4500 ÷ 200` = **22.5**.
- `RM-200`: old 50 at 30 = 1,500; bought 50 at 34 = 1,700.
  New average = `(1500 + 1700) ÷ (50 + 50)` = `3200 ÷ 100` = **32**.

**Checkpoint:** Trial Balance difference still `0.0000`; Total assets now
`504,200.00`.

---

## Step 2 — Production: make finished goods

Click **Production Entry**.

| Field | Value to enter |
|---|---|
| **Item to produce** | `FG-100 — Finished Good X` |
| **Quantity produced** | `30` |
| **Production date** | `2026-01-20` |
| **Labor cost** | `240` |
| **Overhead cost** | `60` |

The **Components consumed** table fills in from the recipe. Leave the quantities as
suggested:

| Component | Quantity consumed | Avg cost | Line cost |
|---|---|---|---|
| `RM-100` | 60 kg | 22.5 | 1,350 |
| `RM-200` | 30 kg | 32 | 960 |
| `PKG-100` | 30 Pcs | 5 | 150 |

**Check the Cost build-up**, then click **Post production**.

**Expected result**

| Field | Value |
|---|---|
| **Material cost** | `2,460.00` (1,350 + 960 + 150) |
| **Labor** | `240.00` |
| **Overhead** | `60.00` |
| **Total production cost** | `2,760.00` |
| **Unit cost of output** | `92.00000000` |

**Journal entry it posts**

| Account | Debit | Credit |
|---|---|---|
| Finished Goods Inventory (1230) | 2,760 | — |
| Raw Material Inventory (1210) — RM-100 | — | 1,350 |
| Raw Material Inventory (1210) — RM-200 | — | 960 |
| Packaging Inventory (1240) — PKG-100 | — | 150 |
| Bank (1010) — labour + overhead | — | 300 |

**New stock position**

| Item | Qty | Avg cost | Value |
|---|---|---|---|
| `RM-100` | 140 | 22.50000000 | 3,150.00 |
| `RM-200` | 70 | 32.00000000 | 2,240.00 |
| `PKG-100` | 70 | 5.00000000 | 350.00 |
| `FG-100` | 30 | 92.00000000 | 2,760.00 |

**How the numbers were reached**

- Components needed: `FG-100` needs 2 + 1 + 1 per unit, so for 30 units it needs
  `30 × 2 = 60` kg of `RM-100`, `30 × 1 = 30` kg of `RM-200`, and `30 × 1 = 30` of
  `PKG-100`.
- Each component left stock at its **current average cost**: `60 × 22.5 = 1,350`;
  `30 × 32 = 960`; `30 × 5 = 150`.
- Total cost = material 2,460 + labour 240 + overhead 60 = **2,760**.
- Unit cost = `2760 ÷ 30` = **92**.

**Checkpoint:** Trial Balance difference still `0.0000`; Total assets unchanged at
`504,200.00` (stock has been reclassified, not added to, except the 300 of labour
and overhead).

---

## Step 3 — Sale: sell finished goods

Click **Sales Entry**.

| Field | Value to enter |
|---|---|
| **Customer** | `Karim Enterprise` |
| **Sale date** | `2026-01-25` |

**Line 1**

| Field | Value |
|---|---|
| **Item** | `FG-100 — Finished Good X` |
| **Quantity** | `10` |
| **Sale price** | `150` |

**Check the Revenue and margin panel**, then click **Post sale**.

**Expected result**

| Field | Value |
|---|---|
| **Revenue** | `1,500.00` (`10 × 150`) |
| **Cost of goods sold** | `920.00` (`10 × 92`) |
| **Gross profit** | `580.00` |
| **Gross margin** | `38.6667%` (`580 ÷ 1500 × 100`) |

**Journal entry it posts**

| Account | Debit | Credit |
|---|---|---|
| Accounts Receivable (1100) | 1,500 | — |
| Sales — Manufacturing (4010) | — | 1,500 |
| COGS — Manufacturing (5010) | 920 | — |
| Finished Goods Inventory (1230) | — | 920 |

**New stock position:** `FG-100` = 20 units, still at an average of **92**, value
1,840.

**Then:** in **Posted sales**, click **Receipt** on the new row and **Print**. The
receipt should show the company details, the customer, the line, and a **Total** of
`1,500.00`.

**Checkpoint:** Trial Balance difference `0.0000`; Total assets `504,780.00`. On
the Dashboard, the **Manufacturing** segment shows revenue 1,500, COGS 920 and
gross profit 580.

---

## Step 4 (optional) — Reverse the sale

1. In **Posted sales**, click **Reverse** on the sale.
2. Type a reason, e.g. `Testing a reversal`, and click **Confirm reversal**.
3. Re-open the **Receipt**.

**Expected:** the sale is marked **reversed**, the receipt carries a *"Reversed"*
banner, and `FG-100` is back to **30 units** at **92**. Nothing is deleted — the
original and its mirror entry both remain, and the mirror voucher is numbered
`SALE-001-REV`.

**Try this too:** reverse the **purchase** from Step 1. It will be refused, because
those materials have since been consumed in production — the message names the item
and the quantity on hand.

---

## Step 5 — Employees and payroll

Click **Payroll → Employees**. For each person below, fill the form and click
**Save employee** (after the first, click **New** to clear the form):

| Code | Name | Department | Designation | Personal email | Mobile | Joining date | Bank account | Gross salary |
|---|---|---|---|---|---|---|---|---|
| `EMP-001` | Rahim Uddin | Office | Accountant | `rahim@example.com` | `01711-000001` | `2024-01-15` | `AC-1001` | `30000` |
| `EMP-002` | Karim Mia | Factory | Machine Operator | `karim@example.com` | `01711-000002` | `2023-06-01` | `AC-1002` | `20000` |
| `EMP-003` | Salma Begum | Office | Store Keeper | `salma@example.com` | `01711-000003` | `2024-03-10` | `AC-1003` | `25000` |
| `EMP-004` | Jamal Hossain | Factory | Helper | `jamal@example.com` | `01711-000004` | `2025-02-01` | `AC-1004` | `15000` |
| `EMP-005` | Nasrin Akter | Office | Sales Executive | `nasrin@example.com` | `01711-000005` | `2025-05-20` | `AC-1005` | `22000` |

Then click **Payroll → Payroll Runs**.

| Field | Value to enter |
|---|---|
| **Period start** | `2026-02-01` |
| **Period end** | `2026-02-28` |
| **Pay date** | `2026-03-05` |

**Check the preview**, then click **Post payroll**.

**Expected result**

| Employee | Gross | Deductions (10%) | Net pay |
|---|---|---|---|
| Rahim Uddin | 30,000 | 3,000 | 27,000 |
| Karim Mia | 20,000 | 2,000 | 18,000 |
| Salma Begum | 25,000 | 2,500 | 22,500 |
| Jamal Hossain | 15,000 | 1,500 | 13,500 |
| Nasrin Akter | 22,000 | 2,200 | 19,800 |
| **Total** | **112,000** | **11,200** | **100,800** |

**Journal entry it posts**

| Account | Debit | Credit |
|---|---|---|
| Office Salaries (6010) — office staff | 77,000 | — |
| Factory Labour (5011) — factory staff | 35,000 | — |
| TDS Payable (2210) — the deductions | — | 11,200 |
| Bank (1010) — the net paid out | — | 100,800 |

Click **Payslips** on the new run to see (and **Print**) each person's breakdown.
The run is numbered `PAY-001`.

**How the numbers were reached**

- Each employee's gross is split into components by the structure in
  Configuration: Basic 60%, House Rent 30%, Medical 5%, Transport 5%. For 30,000
  that is Basic 18,000, House Rent 9,000, Medical 1,500, Transport 1,500.
- With no named deductions configured, a single **statutory deduction** at the
  default **10%** applies: `30,000 × 10 ÷ 100` = 3,000, leaving net 27,000.
- The entry balances because **gross = deductions + net**
  (`112,000 = 11,200 + 100,800`).
- Office pay (77,000 = 30,000 + 25,000 + 22,000) goes to Office Salaries; factory
  pay (35,000 = 20,000 + 15,000) goes to Factory Labour.

**Checkpoint:** Trial Balance difference `0.0000`; Total assets `403,980.00`
(the bank has paid out the net wages).

---

## Step 6 (optional) — Test VAT

Turn VAT on and repeat a sale to see tax added.

1. **Configuration → VAT**: switch **Charge VAT** to **on** and **Save**; set
   **Standard rate (%)** to `15` and **Save**; leave **Prices include VAT** off.
2. **Sales Entry**: sell `10` of `TRD-100` (average cost 100) at `150`, date
   `2026-01-28`.
3. **Expected:** the preview adds **VAT 225.00** (`1,500 × 15 ÷ 100`) and **Total
   payable 1,725.00**. Revenue stays 1,500.
4. The journal entry gains a credit to **VAT Payable (2200)** of 225, and the
   receivable debit becomes 1,725.
5. Set **Receipt style** to `tax_invoice` in **Configuration → Sales documents**,
   then open the receipt: it now reads **Tax Invoice** and shows **Subtotal**,
   **VAT** and **Total**.

To back VAT out of an inclusive price instead, switch **Prices include VAT** on
before the sale: on a 1,500 line the net becomes `1500 ÷ 1.15` = **1,304.3478** and
the VAT **195.6522**.

---

## Step 7 (optional) — Test the approval gate

1. **Configuration → Posting controls**: switch **Require second approval** to
   **on** and **Save**.
2. Sign out, and sign in as the **Sales Staff** user.
3. **Sales Entry** → **Reverse** the sale → type a reason → **Confirm reversal**.
4. **Expected:** the reversal does **not** happen; a message says a second person
   must approve it.
5. Sign out, sign in as **Admin**, open **Approvals**, and click **Approve**.

**Expected:** the sale is now reversed. You cannot approve a request you raised
yourself — that is the point of the check.

---

## Verification checkpoints

After each step, the **Dashboard** and **Reports → Trial Balance** should agree
with this table.

| After | Trial Balance difference | Total assets | Balance sheet check |
|---|---|---|---|
| Import | `0.0000` | `500,000.00` | `0.0000` |
| Purchase | `0.0000` | `504,200.00` | `0.0000` |
| Production | `0.0000` | `504,200.00` | `0.0000` |
| Sale | `0.0000` | `504,780.00` | `0.0000` |
| Payroll | `0.0000` | `403,980.00` | `0.0000` |

On the **Dashboard → Data integrity** card, all four checks should show a tick.

---

## If something looks wrong

- **"Insufficient stock for: …"** — you are trying to take out more than you have.
  Check **Inventory & BOM** for the current quantity. For a sale, reduce the
  quantity; for production, buy more of the component first.
- **A component shows "short"** — the on-hand quantity is less than the recipe
  needs. Buy more of that component (Step 1) before posting the run.
- **A purchase will not reverse** — its stock has already been used, so the later
  production run must be reversed first.
- **VAT is not appearing** — check **Charge VAT** is on, and that the item's
  **segment** is in **Segments VAT applies to**.
- **Nothing to buy, make or sell** — the books are empty of items. Import the
  sample workbook again (**Data → Restore sample workbook**) or your own file.

## Resetting between runs

To start the walkthrough again from a clean slate, either:

- **Data → Restore sample workbook** (reloads this exact starting position), or
- **Data → Start fresh (starter accounts)** (empties everything and loads only the
  standard accounts).
