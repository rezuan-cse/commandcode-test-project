# RPCI — Production Manual

**Accounting & Production ERP**
A complete, plain-language guide for everyday users.

---

## About this manual

This manual explains the RPCI accounting and production system from the point of
view of the person using it. You do not need an accounting background to follow
it. Every term is explained in everyday words the first time it appears, and the
**Glossary** in Section 1 collects them all in one place.

It has three parts:

- **Section 1 — Terminology & Glossary.** Every menu, screen, field and word the
  software uses, explained plainly, plus a full tour of each screen.
- **Section 2 — System Calculations & Backend Logic.** How the software works out
  its numbers, with small worked examples using round figures so you can follow
  the arithmetic yourself.
- **Section 3 — End-to-End User Test Cases.** Step-by-step exercises you can carry
  out yourself, with the exact result to expect and an explanation of how the
  system arrived at it.

### How to read the steps

- **Bold text** marks an action or a button name — **Post sale**, **Save**.
- `Words in this style` are something you type or a value the system shows.
- Numbers are counted: *1, 2, 3*, one action each.

### A note on money and numbers

- All money in this system is kept in **Taka (BDT)**.
- Amounts are stored to **four decimal places** (for example `1,234.5000`).
- Average costs and unit costs are stored to **eight decimal places** (for
  example `32.27848101`), so dividing a total by a quantity never loses pennies.
- Rounding is always **round-half-up** (`.5` rounds upward), never "banker's
  rounding".
- On screen, money is usually shown with **two decimals** (for example
  `1,234.50`) so it is easy to read. Where extra precision matters — average and
  unit costs — more decimals are shown.

### A note on time

Every timestamp is **recorded in UTC and shown in Bangladesh time (GMT+6)**. You
never have to convert anything: the Dashboard, the posted lists, the audit log and
the approvals queue all read on the same clock, whichever computer or phone you
open them on.

Dates you choose yourself — a sale date, a purchase date, a pay date — are business
dates, and are not shifted. A posted transaction shows both: the date it belongs
to, and the moment it was entered.

---

# Section 1 — Terminology & Glossary

## 1.1 Finding your way around

When you sign in you see a **sidebar** down the left with the menu, and a **top
bar** across the top.

### The top bar

| Item | What it is |
|---|---|
| **Period from** | The start date for the reports you are looking at. Change it to look at a different span of time. |
| **As of** | The date the system reports up to. Everything on screen is worked out "as of" this date. |
| **Your name and role** | Shows who you are signed in as, and your role (for example, `Accountant`). If two-factor sign-in is on, it also says **`· 2FA on`**. |
| **Sign out** | Ends your session and returns you to the sign-in screen. |

The **Period from** and **As of** boxes feed almost every screen. Set them once
and every report, dashboard figure and balance updates to match.

### The menu

The menu is grouped into six sections. You only see the items your role is
allowed to read. If a whole group has nothing for you in it, the group
disappears too.

| Menu group | Menu item | Opens |
|---|---|---|
| **Overview** | **Dashboard** | The front page: profit and loss by segment, position at a glance, and the data-integrity checks. |
| **Ledger** | **Chart of Accounts** | The list of every account the books are kept in. |
| **Ledger** | **Journal Entries** | Every voucher in the system, typed or automatic. |
| **Operations** | **Customers & Suppliers** | The list of firms you trade with — customers, suppliers, or both. |
| **Operations** | **Receipts & Payments** | Money in from customers, money out to suppliers, and what is still owed. |
| **Operations** | **Inventory & BOM** | Items, quantity on hand, average cost, and the recipe (BOM) list. |
| **Operations** | **Purchase Entry** | Record goods you buy in. |
| **Operations** | **Production Entry** | Record a production run that makes something. |
| **Operations** | **Sales Entry** | Record goods you sell. |
| **Payroll** | **Employees** | The list of staff and their gross salary. |
| **Payroll** | **Payroll Runs** | Pay staff for a period and print payslips. |
| **Reports** | **Trial Balance** | Every account with a non-zero balance, which must total to zero. |
| **Reports** | **General Ledger** | Opening, movement and closing balance for every account. |
| **Reports** | **Balance Sheet** | Assets, liabilities and equity, which must balance. |
| **Administration** | **Roles & Access** | The permission table, who sees which menus, and (for Admin) user accounts and the audit log. |
| **Administration** | **Approvals** | Actions that are waiting for a second person to approve. |
| **Administration** | **Configuration** | Every rate, company detail and control switch, editable without a programmer. |
| **Administration** | **Data** | Import a workbook, or start the books over. Admin only. |
| **My account** | **Security** | Your own password and two-factor settings. |

The **Operations** group is the one everybody works in; the others are narrower.
Three groups depend on permissions rather than on your job:

- **Overview** (the Dashboard) — shown where the **Reports** permission is held,
  which by default means Admin, Accountant and Owner.
- **Administration** — its own **Administration** permission, held by Admin and
  Owner; an owner may look but not change anything.
- **My account** — held by everybody, so anyone can change their own password.

An administrator can **grant or deny any of these areas to one person** on Roles
& Access, without changing their role. See "Which menus each role is offered" in
1.2 for the defaults.

**On a narrow screen** — a phone or a small tablet — the menu folds away behind a
**menu button** at the top left. Tap it to slide the menu out; tap an item to open
that screen; tap anywhere outside the menu, or press Escape, to close it. Nothing
is lost: the same items are there, and Store and Sales users see only the work they
do.

---

## 1.2 Roles and permissions in plain English

The system has **five roles**. A role is a fixed job description that decides
what you may see and change. Permissions are checked **on the server** every
time, not hidden in the screen — so if you are not allowed to do something, the
system refuses it even if you reach the screen another way.

| Role | In one line | Can change | Can also read |
|---|---|---|---|
| **Admin** | Full control | Everything | Everything |
| **Accountant** | Keeps the books | Journal entries, payroll | Everything else |
| **Store/Production Staff** | Runs the warehouse and factory | Items, production runs | Nothing else |
| **Sales Staff** | Handles buying and selling | Purchases, sales | Items |
| **Owner/Viewer** | Watches, does not touch | Nothing | Everything |

### Which menus each role is offered

The sidebar only shows a group when the role may open something inside it.

| Menu group | Admin | Accountant | Store / Production | Sales Staff | Owner / Viewer |
|---|---|---|---|---|---|
| **Overview** — Dashboard | Yes | Yes | — | — | Yes |
| **Ledger** — accounts, journal | Yes | Yes | — | — | Yes |
| **Operations** — stock, buying, making, selling | Yes | Yes (read only) | Yes | Yes | Yes (read only) |
| **Payroll** — employees, runs | Yes | Yes | — | — | Yes (read only) |
| **Reports** — trial balance, ledger, balance sheet | Yes | Yes | — | — | Yes |
| **Administration** — roles, approvals, configuration, data | Yes | — | — | — | Yes (read only) |
| **My account** — your password and 2-FA | Yes | Yes | Yes | Yes | Yes |

Two of these are narrow because of the permission behind them, not because of who
you are — and an administrator can grant either to one person:

- The **Dashboard** is shown where **Reports** is held. That is what makes it
  Admin, Accountant and Owner, since Store and Sales hold no reports.
- The **Administration** group is shown where its own **Administration** permission
  is held: Admin and Owner. Inside it, an owner can look but not change — saving a
  setting, issuing a password, removing an account, importing or resetting data all
  remain administrator-only.

**Store/Production and Sales see only the work they do.** Store staff get
**Inventory & BOM** and **Production Entry**; sales staff get **Purchase Entry**
and **Sales Entry**, plus a read-only look at items so they can pick what they are
selling. Neither is offered the Dashboard, the ledger, payroll or the financial
reports — only the screens their own job needs. Both may also maintain
**Customers & Suppliers**, because a sale or a purchase needs a partner that
exists in the list — an administrator can narrow that to read-only if the list
should be controlled centrally.

**Every role keeps "My account"**, so anyone can change their own password and set
up two-factor sign-in without asking an administrator.

### The access words you will see

For each area, a role has one of three levels:

- **Full** — can read **and** change.
- **View** — can read, but the screens open without their input forms.
- **None** — the menu item is hidden and the server refuses the area.

### The three "you cannot do that" messages

When you try something your role may not do, the system explains it in one of
three ways:

- **Not available for your role** — you cannot even read that screen:
  *"The {area} screen is not available to the {your role} role. An administrator
  can grant access if it is needed."*
- **View only for your role** — you may read it but not change it:
  *"The {your role} role can view the {area} screen but cannot make changes on
  it."*
- **Administrators only** — for configuration and user management:
  *"This action is limited to administrators. You are signed in as {your role}."*

---

## 1.3 Glossary — every term, in everyday words

### A

- **Account** — A labelled bucket the books are kept in, such as "Cash and Bank"
  or "Sales — Trading". Every amount posted somewhere lands in an account.
- **Account code** — The short number that identifies an account, for example
  `1010` for Cash and Bank. Accounts are never chosen by typing a name freely;
  you always pick a code, so nothing can be mistyped.
- **Account type** — The broad family an account belongs to: **Asset** (things
  you own), **Liability** (things you owe), **Equity** (the owner's stake),
  **Revenue** (income), **COGS** (the cost of what you sold), **Expense**
  (running costs), and **Other Income**.
- **AIT (Advance Income Tax)** — A tax collected in advance, often at the import
  stage. The system has a rate and an account for it, both editable in
  Configuration. It is **off unless you set it up**.
- **Approval** — A second person's sign-off before an action takes effect. This
  is a switch you can turn on in Configuration; until then, nothing needs
  approval.
- **Approval threshold** — The amount at or above which an action needs
  approval. Left at `0`, **every** covered action needs it.
- **Asset** — Anything the business owns that has value: cash, money owed to you
  by customers, and stock.
- **As of** — The date the system reports up to. See 1.1.
- **Audit log** — A dated list of administrative actions (who cleared a second
  factor, who issued a password, who disabled an account). Nothing in it can be
  edited or removed.

### B

- **Balance** — The amount left in an account after adding and subtracting
  everything that has passed through it.
- **Balance Sheet** — A report showing what the business owns (Assets), what it
  owes (Liabilities), and the owner's stake (Equity) on a given date. It must
  always balance: Assets = Liabilities + Equity.
- **Bill of Materials (BOM)** — The recipe for a manufactured item: which
  components, and how much of each, go into one unit.
- **Below cost** — A warning that an item is being sold for less than it cost.
  Selling below cost is allowed — a clearance sale is real — but it is always
  flagged, never silent.
- **Book** (verb) — To record a transaction in the accounts.

### C

- **Category (item category)** — What kind of thing an item is: Raw Material,
  WIP (work in progress), Finished Good, Packaging, Trading Stock, or Imported
  Goods. The category decides which inventory account the item's value sits in.
- **Chart of Accounts** — The complete list of accounts. Everything else in the
  system refers to this list.
- **Closing balance** — The balance in an account at the end of the period you
  are looking at.
- **COGS (Cost of Goods Sold)** — What the goods you sold originally cost you.
  If you buy a bag for 5 and sell it for 8, the COGS is 5.
- **Component** — One ingredient in a BOM. A finished product is made of
  components.
- **Configuration** — The screen where every rate, company detail, payroll rule
  and control switch can be changed without a programmer. See 1.4.
- **Confirmed / Pending client** — Each configuration value carries a small
  badge. **Confirmed** means a person has checked it and it is settled.
  **Pending client** means it is a placeholder still waiting to be agreed.
- **Credit** — One of the two sides of every entry. Say "credit" as "what the
  account gives out" on the right-hand side of the ledger. See **Debit**.
- **Cutover date** — The date the system's opening balances start from. Before
  it, history is not in the system.

### D

- **Data (screen)** — Administration → Data. Where an Admin imports a workbook
  or starts the books over.
- **Debit** — The other side of every entry, on the left-hand side. Every entry
  has debits and credits, and the two sides always add up to the same total.
  (A simple way to hold it: money coming *into* an account is debited, money
  going *out* is credited. The system enforces the rule for you, so you never
  have to.)
- **Deduction** — Money taken out of an employee's gross pay before they are
  paid, such as tax or a provident fund.
- **Department (employee)** — **Office** or **Factory**. This decides which
  salary expense account their pay is charged to.

### E

- **Equity** — The owner's stake in the business: what is left when you subtract
  what the business owes from what it owns.
- **Expense** — A running cost of the business, such as salaries or rent.
- **Explode (a BOM)** — To work out the full shopping list for a production
  quantity, expanding every sub-assembly down to the materials you actually buy.

### G

- **General Ledger** — The full account-by-account story: opening balance, the
  movement in the period, and the closing balance.
- **Gross margin** — Gross profit shown as a percentage of revenue.
- **Gross profit** — Revenue minus the cost of the goods sold. What is left
  before running costs.
- **Gross salary** — An employee's total pay before deductions.

### I

- **Insufficient stock** — A refusal: you cannot take more of an item than you
  have. The message reads *"Cannot take {quantity} of {item}: only {quantity} on
  hand."*
- **Item** — Anything you buy, make, store or sell. Each has a code, a name, a
  category, a segment and a unit of measure.
- **Inventory ledger** (also **stock ledger**) — The running record of every
  stock movement, with the balance and average cost after each one.

### J

- **Journal entry** — A complete, balanced record of a transaction: the date, a
  voucher number, and two or more lines that are debits and credits. Nothing is
  stored unless the two sides match exactly.

### L

- **Liability** — Something the business owes, such as money owed to suppliers.

### M

- **Movement** — A single change to stock: a purchase in, a sale out, a
  production in or out, an opening balance, an adjustment, or a reversal.

### N

- **Net pay** — What an employee actually receives after deductions.
- **Net profit** — What is left after running costs: gross profit minus
  operating expenses, plus any other income.

### O

- **Opening balance** — The starting amounts in the accounts on the cutover
  date.
- **Operating expenses** — Running costs of the business that are not the direct
  cost of goods sold, such as office salaries.
- **Output VAT / Input VAT** — See **VAT**.

### P

- **Payroll run** — One payslip batch for a period, covering every active
  employee, which posts a single balanced entry to the books.
- **Payslip** — A printable statement of one employee's pay for a period,
  showing their gross, components, deductions and net.
- **Period from / As of** — The two date boxes in the top bar.
- **Posting** — Committing a transaction permanently into the books. Once
  posted, it is never edited or deleted — see **Reversal**.
- **Production run** — A posting that consumes components and receives a
  finished output at a calculated cost.

### R

- **Receipt** — The printable document a customer receives for a sale. It is a
  plain receipt by default; it becomes a **Tax Invoice** only when VAT is on and
  the receipt style is set to a tax invoice.
- **Reversal** — The honest way to undo a posting. The system writes a mirror
  entry (debits and credits swapped) numbered with a `-REV` suffix, and marks the
  original as reversed. Nothing is edited; nothing is deleted.
- **Revenue** — Income from selling goods or services.
- **Role** — See 1.2.

### S

- **Segment** — A business line an account, item and journal line is tagged
  with: **Import, Manufacturing, Packaging, Trading, Application** or
  **Shared**. Segment tags are what make segment-wise reporting possible.
- **Starter chart of accounts** — The standard set of 29 accounts a brand-new
  system begins with, so it is usable straight away.
- **Stock (on hand)** — How much of an item you have right now. It is always
  *worked out* from the ledger, never typed in.

### T

- **Tax Invoice** — A receipt that shows tax. The system prints one only when
  VAT is on **and** the receipt style is set to a tax invoice.
- **TDS (Tax Deducted at Source)** — Tax withheld from a payment and passed to
  the tax authority. Configurable; off unless set up.
- **Trial Balance** — A list of every account with a non-zero balance, split into
  debits and credits. The difference between the two columns must be exactly
  zero.
- **Two-factor authentication (2FA)** — An extra six-digit code from an
  authenticator app on top of your password. Optional; you set it up yourself on
  the Security screen.

### U

- **Unit cost** — The cost of making one unit of output: total production cost
  divided by the quantity produced.
- **UOM (Unit of Measure)** — How an item is counted: kilograms, pieces, litres,
  and so on.

### V

- **VAT (Value Added Tax)** — A tax added to sales (**output VAT**) and paid on
  purchases (**input VAT**). It is **off by default** and only switches on when
  you turn it on in Configuration.
- **VDS (VAT Deducted at Source)** — VAT withheld from a service payment.
  Configurable; off unless set up.
- **Voucher** — The document number for a journal entry, such as a sale
  numbered `SALE-004` or a purchase numbered `PUR-002`.

### W

- **WIP (Work in Progress)** — Items that are part-way through being made.
- **Weighted average cost** — The everyday costing method here. The value of
  everything you hold is divided by the quantity you hold, so each unit carries
  the same average cost. See Section 2.2.
- **Workbook** — An Excel file (`.xlsx`). You can import one to replace the books
  with existing data.

---

## 1.4 Every screen and its fields

Each screen below lists its purpose, what you can type, and what the buttons do.

### Sign in

- **Email** and **Password** boxes, and a **Sign in** button.
- If two-factor is on for your account, a second card asks for a **Code** — the
  six digits from your authenticator app, or one of your saved recovery codes.
  Then **Verify**.
- Beneath the form is a **Demo accounts** table listing the sample sign-in
  accounts, one per role. Clicking a row fills the form. Its footnote explains
  that signing in as different people is how you see the permission rules
  applied.

### Dashboard

The front page. Everything on it is calculated live.

- Five boxes across the top: **Revenue**, **COGS**, **Gross profit**, **Gross
  margin**, **Net profit**.
- **Profit & loss by segment** — each business line's revenue, cost, gross profit
  and margin, plus a **Total** row and lines for *Less: shared operating
  expenses*, *Add: other income* and *Net profit*. An **Open reports** button
  jumps to the Trial Balance.
- **Position at a glance** — **Total assets**, **Total liabilities**, **Owner's
  equity**, **Current period profit**, and a line confirming the accounting
  equation with a **balanced** or **out of balance** tag.
- **Data integrity** — four live checks (see Section 2.7), each with a ✓ or a !.

### Chart of Accounts

The list of every account.

- **Segment** and **Type** drop-downs, and a **Search** box (try `Inventory` or
  `1210`).
- The table shows **Code, Account name, Type, Segment, Normal balance**.

### Journal Entries

Every voucher in the system.

- Entries are listed newest-first as cards, each headed with its voucher number
  and date, its narration, and a tag showing whether it was **Manual**,
  **Production**, **Sales** or **Purchase**. Each card also gives the number of
  lines, who entered it, and **when — date and time** — so a voucher can be matched
  to the moment it was posted.
- **Show lines** expands the entry to its lines: **Account, Segment, Narration,
  Debit, Credit**, with a **Total** row.

### Customers & Suppliers

One list of the firms you trade with, with a **Type** of *Customer*, *Supplier*, or
*Customer and Supplier*. A single list is deliberate: the same firm often buys from
you and supplies you, and one record means one spelling of its name.

- Fields: **Code**, **Name**, **Type**, **Contact person**, **Phone**, **Email**,
  **Address**, **Credit days**, **Active**. **Credit days** blank means no terms
  were agreed — which is not the same as zero, so leave it blank unless you know.
- Filters: **Search name or code**, **All types**, and an **Active only** tick. The
  card's heading counts what is shown and how many are inactive.
- **Adopt existing names** — see below.
- **Add customer or supplier** opens the form. The **Code** is fixed once saved,
  because sales and purchases point at it. **Edit** on a row opens the same form.
  **Delete** works only while nothing refers to the record; otherwise the server
  refuses and tells you to set it **inactive** instead.
- **Sales Entry** and **Purchase Entry** pick the customer or supplier from this
  list. If the list is empty those screens fall back to a plain text box, so a sale
  can still be recorded before the list is set up.
- **Adopt existing names** is for a business that has already been trading. The
  customer and supplier names already sitting on your posted sales and purchases
  are your real trading partners, so they are turned into records in one step — each
  one then claims the transactions carrying its name. It is safe to press more than
  once: names that already have a record are counted and left alone.


### Receipts & Payments

Money in from a customer and money out to a supplier, in one place, and the answer
to **what is still owed**. This is the screen that makes a customer balance
possible, because the money is attached to the customer record rather than left in
a journal entry.

- **Outstanding invoices** — every invoice that is not fully settled, showing
  **Date, Invoice, Customer or supplier, Total, Settled, Outstanding**. It covers
  both directions: sales you are owed for, and purchases you owe.
- **Settle** on a row opens the form already filled in for that invoice.
- **Receive money** / **Pay supplier** open an empty form.
- The form: **Type** (Receipt = money in, Payment = money out), **Customer** or
  **Supplier**, **Date**, **Amount**, **Account** (the cash or bank account the
  money moved through), **Reference** (cheque number), **Note**, and the list of
  **Invoices this settles**.
- **Preview entry** shows the two journal lines before anything is posted —
  *Debit* the bank and *Credit* receivables for a receipt, the reverse for a
  payment — with how much settles invoices and how much is held on account.
- **Receipts & payments** — the list, newest first: **Voucher, Type, Customer or
  supplier, Amount, On account, Settles, Recorded by**.
- **Apply** on a payment with money on account opens the allocation panel.
- **Reverse** undoes a receipt or payment, with a reason. The invoices it had
  settled go back to outstanding, and nothing is edited or deleted.
- **Money on account** is the important idea: a receipt or payment with no invoice
  against it is held for that customer or supplier, not lost. **Apply** puts it
  against invoices later — which is exactly what a deposit or an advance is.

### Exporting a list or a report to Excel

Every list and report with an **Export CSV** button writes the rows on screen to a
file. **CSV** opens directly in Excel (or Google Sheets, or LibreOffice), so there
is nothing to install.

- The file is named after the screen and, for a report, the date it covers —
  `trial-balance-2026-10-31.csv`, `customers-and-suppliers.csv`.
- **Figures are written as stored**, not as displayed: `1234.0000` rather than
  `1,234.00`. That is deliberate — a formatted number reaches Excel as *text* and
  will not add up, which is the one thing an accountant needs it to do.
- The export contains **exactly what the screen is showing**, including any filter
  or search you have applied. So to export one segment's accounts, filter first.
- A customer or supplier name containing a comma — `Karim & Sons, Ltd` — is quoted
  properly, so the columns cannot shift and put a figure under the wrong heading.
- Long lists are capped by the same limit the screen uses (the transaction lists
  show the most recent 200 rows, the journal up to 1,000). For a month-end export
  that is normally well beyond what you need; if you ever need the whole history in
  one file, that is a change worth asking for.

**Where the button is:** every list and report — Chart of Accounts, Journal Entries,
Inventory, Customers & Suppliers, Receipts & Payments (both the outstanding invoices
and the payments list), Purchase Entry, Production Entry, Sales Entry, Employees,
Payroll Runs, Trial Balance, General Ledger and Balance Sheet.

**The Journal Entries export is the one an auditor asks for.** It writes **one row
per journal line**, not one per voucher, so a single file holds every debit and
credit with its voucher, account, segment and narration — ready to sort and total
in Excel. That is the general-ledger listing, and it is the file to hand over if
the books are ever examined.

### Using it on a phone

The system works on a phone for entering a purchase or a production run at the
delivery point, and it changes shape deliberately rather than just shrinking:

- **The menu becomes a ☰ drawer**, opened from the top-left of any screen.
- **One field per line.** On a laptop the fields sit two or three to a row; on a
  phone each gets its own full-width line, because a field too narrow to read what
  you typed is how a quantity gets entered wrong.
- **Bigger buttons and inputs** — sized for a thumb rather than a mouse. The small
  action buttons inside a table stay compact on purpose, or the rows would become
  unusably tall.
- **Wide tables scroll sideways** within their card, with the page itself staying
  still, so the rest of the screen does not slide around while you look at a
  column.

Long lists and reports are easier to read on a laptop; the phone is for **entering**
what happened while you are standing in front of it.


### Inventory & BOM

- **Inventory ledger** — every item with **Qty on hand**, **Avg cost** and
  **Value**. A **Search item…** box filters the list. The **Ledger** button opens
  that item's movement history: **Date, Type, Reference, In qty, In value, Out
  qty, Out value, Balance qty, Balance value, Avg cost**.
- **Item master** — **Add item** opens a form: **Code, Name, Unit, Category,
  Segment, Active**. The **Code** is fixed once saved, because every other record
  in the system points at it; everything else can be corrected afterwards with
  **Edit**. A **Delete** button removes an item that has no history at all — once
  it has been bought, sold, made or consumed the server refuses, and its message
  says to set the item **inactive** instead. That keeps the history intact and
  simply takes the item out of the pickers.
- **BOM explosion** — type a **Target quantity** and press **Explode BOM** to see
  the full component list with **Level, Component, Category, Per unit, Required,
  Avg cost, Estimated cost**, and an **Estimated material cost** total.

### Purchase Entry

Records goods bought in.

- Header fields: **Supplier**, **Purchase date**, and **Settlement** —
  *On credit (supplier payable)* or *Paid immediately (bank)*.
- Each line: **Item**, **Quantity**, **Unit cost**. The table shows **On hand**
  and **Current avg cost** for reference, and the **Line value**.
- Buttons: **Add line**, **Remove**, and **Post purchase**.
- A preview shows **Purchase value** (with **Input VAT** and **Total payable**
  when VAT is on), and an **Effect on average cost** table with **Before** and
  **After**.
- The **Posted purchases** list below shows **Order, Date, Supplier, Value,
  Entered by**, and a **Reverse** button.

### Production Entry

Records a production run.

- Fields: **Item to produce**, **Quantity produced**, **Production date**,
  **Labor cost**, **Overhead cost**.
- **Components consumed** — the recipe suggested from the BOM, with **On hand**,
  **Per unit**, an editable **Quantity consumed**, **Avg cost** and **Line
  cost**. Each component shows an **ok** or **short** tag.
- **Cost build-up** — **Material cost**, **Labor**, **Overhead**, **Total
  production cost**, **Quantity produced**, **Unit cost of output**.
- **Journal entry it will post** — a preview of the entry.
- **Post production**, then the **Posted production runs** list with a
  **Reverse** button per run.
- If there are no items at all, the screen explains that items must be added
  under Inventory & BOM, or a workbook imported from Administration → Data,
  before a run can be recorded.

### Sales Entry

Records a sale.

- Fields: **Customer**, **Sale date**.
- Each line: **Item**, **Quantity**, **Sale price**. The table shows **On hand**
  and **Avg cost**, and flags **short** or **below cost** where it applies.
- Buttons: **Add line**, **Remove**, **Post sale**.
- Preview: **Revenue and margin** (with **VAT** and **Total payable** when VAT is
  on), **Cost of goods sold**, **Gross profit**, **Gross margin**, and the
  **Journal entry it will post**.
- The **Posted sales** list has a **Receipt** button per sale, and a **Reverse**
  button.

### Receipt (printed)

Opened from a sale. Shows the company block, **Receipt no.**, **Date**, the
**Received from** customer, the item lines (**Item, Qty, Rate, Amount**), and a
**Total**. When VAT is on it also shows **Subtotal** and **VAT** and prints as a
**Tax Invoice**. A **Print** button prints the document alone — no menu, no
toolbar.

### Employees

- **Add an employee:** press **Add employee** on the Staff card, which opens the
  form: **Code**, **Name**, **Department** (Office or Factory), **Designation**,
  **Personal email**, **Mobile**, **Joining date**, **Bank account**, **Gross
  salary**, and **Status**. The form stays closed until you ask for it, so the
  list is not pushed down the screen. **Edit** on a row — or a click anywhere on
  that row — opens the same form for that person, and **Cancel** closes it without
  saving.
- **Staff** table: **Code, Name, Department, Designation, Joining date, Leaving
  date, Mobile, Gross, Status**. **Show active staff only** hides those who have
  left; the card's subtitle counts them.
- **When someone leaves,** select their row, switch **Status** to *Resigned* and
  save. A **Leaving date** appears, defaulting to today. They stay on the list with
  their joining and leaving dates and keep every payslip they were paid; payroll
  simply stops including them. Nothing is deleted, and switching the status back to
  *Active* brings them back — which clears the leaving date, so re-employing
  somebody does not carry their old resignation with them.

### Payroll Runs

- **Period start**, **Period end**, **Pay date**.
- A preview table of **Employee, Gross, Deductions, Net pay** with a **Total**
  row, and the **Journal entry it will post**.
- **Post payroll**, then the **Posted runs** list with a **Payslips** button and a
  **Reverse** button.

### Payslips (printed)

Opened from a run. Lists every employee with **Gross**, **Deductions**, **Net
pay**, and each person's component and deduction breakdown. A **Print** button.

### Approvals

- **Pending** lists actions waiting for a second person: **Action**, **Raised**
  (when it was asked for), **Amount**, **Requested by**, **Reason**, a **note
  (optional)** box, and **Approve** / **Reject** buttons.
- **History** lists decided requests with **Raised**, **Status**, **Decided** (when
  it was decided), who decided, and any note.

### Roles & Access

- **Permission matrix** — a role-by-area table showing **Full**, **View** or **—**,
  which is what each role gets by default.
- **Menus by role** — which menu groups each role is offered, from the same rules
  the sidebar uses.
- **User accounts** (Admin only) — every account with its role, second factor,
  status, and when it was **created** and **last updated**. From here an
  administrator can:
  - **Add user** — name, email, role, and a password (leave it blank and one is
    generated and shown once).
  - **Edit** — correct a name, email or role.
  - **Access** — grant or deny any area to that one person on top of their role.
    Anything left on *Follow the role* is not stored, so a later change to the role
    still reaches them.
  - **Reset 2FA**, **Reset password**, **Disable** / **Enable**, and **Delete**.
  - You cannot act on your own account here; use the Security page.
- **Administrative actions** (Admin only) — the audit log, newest first.

### Security

- **Two-factor authentication** — set it up, or turn it off with your password.
- **Change password** — current password, new password (at least eight
  characters).

### Configuration

Grouped cards — **Company details**, **VAT**, **AIT, TDS and VDS**, **Payroll**,
**Posting controls**, **Security**, **Inventory**, **Sales documents**. Each row
shows the **Setting**, its **Value**, a **Status** badge (**confirmed** or
**pending client**), and a **Description**. An Admin can edit the value and press
**Save**, or **Confirm** to mark it settled.

### Data (Admin only)

- **Import an existing workbook** — choose an `.xlsx` file, leave *Replace the
  books* ticked, and press **Import workbook**.
- **Start over** — **Start fresh (starter accounts)**, **Restore sample
  workbook**, or **Empty everything**.

# Section 2 — System Calculations & Backend Logic

This section explains what happens behind the scenes each time you post
something. You do not need to memorise it. It is here so that when a figure
appears — an average cost, a gross profit, a net pay — you can see exactly how it
was worked out.

## 2.0 The one rule that governs everything: one posting, one transaction

Every posting — a purchase, a production run, a sale, a payroll run — does two
things at once:

1. it **moves stock**, and
2. it **writes a balanced journal entry**.

Both are saved together, in a single change to the database. If anything goes
wrong partway through, **nothing** is saved: the stock move and the journal entry
are rolled back together. This is why the stock sheet and the accounts can never
disagree because of a half-finished posting.

A balanced entry means one simple thing:

> **The total of all debits equals the total of all credits.**

The system checks this before storing anything. If the two sides do not match, it
refuses the entry.

---

## 2.1 How money is stored and rounded

Two precision levels are used:

| What | Precision | Example |
|---|---|---|
| Money amounts (values, balances, totals) | **4 decimal places** | `1,234.5000` |
| Average and unit costs | **8 decimal places** | `32.27848101` |

Rounding is **round-half-up**. The fifth decimal digit decides:

- `1.00004` → **`1.0000`** (the fifth digit is 4, so it stays down)
- `1.00005` → **`1.0001`** (the fifth digit is 5, so it rounds up)

Money is never handled as a "floating point" number (the imprecise kind a
spreadsheet can produce). It is handled as an exact decimal throughout, so
1 + 1 is exactly 2 and never 1.9999999.

**Why costs keep more places.** If a total of `25,500` is spread over `790` units,
the true cost is `25500 ÷ 790 = 32.278481012658…`. Keeping only two decimals would
lose money every time you divide. So the system keeps eight:
**`32.27848101`**. That is exactly why the stock screen can show a cost like
`32.27848101`.

---

## 2.2 Weighted-average cost — how stock is valued

Every item carries three numbers: its **quantity**, its **total value**, and its
**average cost**. The average is simply:

> **average cost = total value ÷ quantity**

The clever part is what happens when stock comes in or goes out.

### When stock comes IN (a purchase or a production output)

The new items are added to the old, and the average is worked out fresh:

> **new average = (old value + value coming in) ÷ (old quantity + quantity coming in)**

**Worked example.** Suppose we hold 10 units that cost 100 each (value 1,000).
Then we buy 5 more at 130 each (value 650).

| Step | Arithmetic | Result |
|---|---|---|
| Old position | 10 units, value 1,000 | average = `1000 ÷ 10` = **100.00000000** |
| Value coming in | `5 × 130` | **650** |
| New quantity | `10 + 5` | **15** |
| New value | `1000 + 650` | **1,650** |
| New average | `1650 ÷ 15` | **110.00000000** |

So one number, the average (110), now values every unit. You never need to
remember which unit cost 100 and which cost 130.

### When stock goes OUT (a sale or a production consumption)

The quantity used is valued at the **current average**, and the average itself
usually does not move:

> **cost taken out = average cost × quantity going out**

**Worked example, continuing from above.** Sell 8 units.

| Step | Arithmetic | Result |
|---|---|---|
| Cost taken out | `110 × 8` | **880** |
| New quantity | `15 − 8` | **7** |
| New value | `1650 − 880` | **770** |
| New average | `770 ÷ 7` | **110.00000000** (unchanged) |

The average stays at 110 because everything left is still valued at the same
rate. It only moves when new stock arrives at a different price.

### The one hard rule: you cannot go negative

If you try to take out more than you hold, the system refuses and tells you
plainly:

> *"Cannot take 8 of RMC-003: only 7 on hand."*

Taking out exactly what you have is allowed — that empties the item to zero.

### Sanity check with a real-looking figure

| Step | Arithmetic | Result |
|---|---|---|
| Bring in 790 units for 25,500 | `25500 ÷ 790` | average **32.27848101** |
| Issue 100 units | `32.27848101 × 100` = `3227.8481` (4 dp) | cost **3,227.8481** |
| Remaining | value `25500 − 3227.8481` = 22,272.1519; `22272.1519 ÷ 690` | average **32.27848101** (holds) |

---

## 2.3 Purchases — what happens when you receive stock

You enter: a **supplier**, a **date**, whether it is **on credit or paid**, and one
or more lines of **item, quantity, unit cost**.

### The stock move
Each line adds its quantity in, and the item's average cost is recalculated by the
method in 2.2.

### The journal entry
For a purchase the entry is simple. Each item's own inventory account is debited;
one single credit line settles the whole order:

| Line | Account | Debit | Credit |
|---|---|---|---|
| Each item received | that item's inventory account | the line value | — |
| Input VAT *(only if VAT is on and recoverable)* | the input VAT account | the VAT | — |
| Settlement | **2010** supplier payable *(on credit)* **or** **1010** bank *(paid)* | — | the total |

Which account an item's value sits in depends on its **category**:

| Item category | Inventory account |
|---|---|
| Imported Goods | `1200` |
| Raw Material | `1210` |
| WIP | `1220` |
| Finished Good | `1230` |
| Packaging | `1240` |
| Trading Stock | `1250` |

**Worked example.** Buy 5 units of a raw material at 130 each, on credit, with VAT
off.

- Line value = `5 × 130` = **650**
- Journal: **Debit** Raw Material Inventory **650**; **Credit** Accounts Payable —
  Local **650**.
- New average cost for the item, if it was 10 units worth 1,000 before:
  `(1000 + 650) ÷ (10 + 5)` = **110.00000000**.

---

## 2.4 Production — how the cost of making something is worked out

You enter: the **item to produce**, the **quantity**, the **date**, and **labour**
and **overhead** costs. The components come from the item's **recipe (BOM)**, and
you may adjust the quantities.

### The five steps, in one transaction

1. **Consume components.** Each component is taken out of stock at its current
   average cost.
2. **Add labour and overhead.** These are the "conversion" costs of making the
   batch.
3. **Total the cost.** `total cost = material + labour + overhead`.
4. **Work out the unit cost.** `unit cost = total cost ÷ quantity produced`
   (kept to 8 decimals).
5. **Receipt the output** at that unit cost, which updates the finished item's own
   average cost.

### The journal entry

| Line | Account | Debit | Credit |
|---|---|---|---|
| Output received | the output item's inventory account | total cost | — |
| Each component consumed | that component's inventory account | — | its line cost |
| Labour + overhead *(only if greater than zero)* | **1010** bank | — | labour + overhead |

**Worked example.** Make **50 units** of a finished good. The recipe needs
**2 kg of Raw Material A** and **1 piece of Packaging B** per unit.

| Component | Per unit | Needed for 50 | Avg cost | Line cost |
|---|---|---|---|---|
| Raw Material A | 2 kg | 100 kg | 20 | `100 × 20` = **2,000** |
| Packaging B | 1 pc | 50 pcs | 5 | `50 × 5` = **250** |

- Material cost = `2000 + 250` = **2,250**
- Labour = **300**, Overhead = **50** → conversion = **350**
- **Total cost** = `2250 + 300 + 50` = **2,600**
- **Unit cost** = `2600 ÷ 50` = **52.00000000**
- Journal:

| Account | Debit | Credit |
|---|---|---|
| Finished Goods Inventory | 2,600 | — |
| Raw Material Inventory | — | 2,000 |
| Packaging Inventory | — | 250 |
| Bank (labour + overhead) | — | 350 |

And the 50 finished units enter stock at **52 each**. If the finished item already
held stock, its average is recalculated by the method in 2.2.

**A safety note.** If any component is short, the run is refused and nothing is
posted. If the run is later reversed, the output is taken out first — so a run
whose output has already been sold cannot be reversed until the sale is reversed.

---

## 2.5 Sales — revenue, cost of goods sold, profit, and VAT

You enter: a **customer**, a **date**, and lines of **item, quantity, sale price**.

For each line the system works out three things:

- **Revenue** = `quantity × sale price`
- **Cost of goods sold (COGS)** = `quantity × the item's current average cost`
- **Margin** = `revenue − COGS`

### The journal entry

A sale writes **both halves** in one entry — the sale itself, and the cost of the
goods leaving:

| Line | Account | Debit | Credit |
|---|---|---|---|
| What the customer owes | **1100** accounts receivable | revenue (+ VAT if any) | — |
| Each line's revenue | the item's segment sales account | — | line revenue |
| Output VAT *(only if VAT is on)* | the output VAT account | — | the VAT |
| Each line's cost | the item's segment COGS account | line COGS | — |
| Inventory reduced | the item's inventory account | — | line COGS |

Sales and COGS accounts depend on the item's **segment**:

| Segment | Sales account | COGS account |
|---|---|---|
| Import | 4000 | 5000 |
| Manufacturing | 4010 | 5010 |
| Packaging | 4020 | 5020 |
| Trading | 4030 | 5030 |
| Application | 4040 | 5010 |
| Shared | 4010 | 5010 |

**Worked example, VAT off.** Sell 4 units at 150 each; the item's average cost is
100.

- Revenue = `4 × 150` = **600**
- COGS = `4 × 100` = **400**
- Gross profit = `600 − 400` = **200**
- Gross margin = `200 ÷ 600 × 100` = **33.3333%**
- Journal: **Dr** Accounts Receivable **600**; **Cr** Sales **600**;
  **Dr** COGS **400**; **Cr** Trading Stock **400**.
- The item's stock falls from 10 to 6, and its value from 1,000 to 600. Its
  average stays at 100.

### How VAT is worked out when it is on

There are two ways prices can be entered, controlled by the **Prices include VAT**
switch in Configuration.

**If prices do NOT include VAT** (the usual case), VAT is added on top:

> **VAT = line amount × rate ÷ 100**

**Worked example.** 4 units at 150 (exclusive), rate 15%:
`VAT = 600 × 15 ÷ 100` = **90**, and the customer owes `600 + 90` = **690**.
Revenue stays **600**.

**If prices DO include VAT**, the tax is backed out of the amount you typed:

> **net = amount ÷ (1 + rate)** and **VAT = amount − net**

**Worked example.** 4 units at 150 (inclusive), rate 15%:
`net = 600 ÷ 1.15 = 521.7391` (to 4 decimals), and `VAT = 600 − 521.7391` =
**78.2609**. Revenue is the net figure, 521.7391; the customer owes the 600 you
typed.

### Warnings you may see on a sale

- **Insufficient stock for: {item}** — you do not have enough, and the sale cannot
  be posted until you do.
- **{item} is priced below cost (150 against a cost of 100), a loss of 50 on this
  line** — allowed, but never silent.
- **{item} has no sale price: this sale would give the goods away and still record
  a cost of {cost}** — a price of zero.

---

## 2.6 VAT, AIT, TDS and VDS — what the settings do

VAT is **off by default**. Nothing is taxed until someone turns **Charge VAT** on
in Configuration and sets a **standard rate**. These are the settings that govern
it:

| Setting | What it does |
|---|---|
| **Charge VAT** | The master switch. Off means no VAT is ever added. |
| **Standard rate (%)** | The percentage used, e.g. 15. |
| **Prices include VAT** | Whether your entered prices already contain the tax. |
| **Input VAT recoverable** | Whether VAT paid on purchases can be reclaimed. |
| **Segments VAT applies to** | Which business lines carry VAT. |
| **Zero-rated or exempt items** | Item codes that carry no VAT at all. |
| **Input VAT account / Output VAT account** | Where the tax is parked in the books. |
| **Return frequency** | How often a VAT return is filed (a note for your records). |

**Output VAT** is the tax you charge customers (a liability). **Input VAT** is the
tax you paid suppliers (usually reclaimable). The net figure you owe is
**output VAT − input VAT**.

**Worked example.** In a month you charge 900 of output VAT and pay 1,500 of
recoverable input VAT. Net = `900 − 1500` = **−600**, meaning 600 is
reclaimable that month.

**AIT, TDS and VDS** are the withholding taxes. Each has a rate and an account in
Configuration. Like VAT, they do nothing until they are set up — the defaults are
placeholders marked **pending client**.

---

## 2.7 The reports — what each one calculates

### Trial Balance

For every account:

> **net balance = Σ opening (debit − credit) + Σ all posted lines up to the date
> (debit − credit)**

A positive net is shown in the **Debit** column, a negative net in the **Credit**
column. Accounts that net to zero are left out.

> **Difference = total debits − total credits.** It must be **zero**.

### Profit & Loss by segment

For each of the five reporting segments:

- **Gross profit = revenue − COGS**
- **Gross margin % = gross profit ÷ revenue × 100** (zero revenue gives 0)

For the whole company:

- **Total gross profit = total revenue − total COGS**
- **Net profit = total gross profit − operating expenses + other income**

Operating expenses and other income are counted company-wide, not split by
segment.

**Worked example.**

| Segment | Revenue | COGS | Gross profit | Margin |
|---|---|---|---|---|
| Trading | 600 | 400 | 200 | 33.3333% |
| All others | 0 | 0 | 0 | 0 |
| **Total** | **600** | **400** | **200** | **33.3333%** |

With operating expenses of 50 and other income of 10:
**net profit = 200 − 50 + 10 = 160**.

> **A practical tip.** Tag your revenue and costs to one of the five reporting
> segments. Anything tagged **Shared** is not shown in the segment rows.

### Balance Sheet

- **Assets** = the net of every Asset account.
- **Liabilities** = the net of every Liability account.
- **Equity** = the net of every Equity account, **plus the profit made since
  1 January of the reporting year**.
- **Check = Assets − (Liabilities + Equity).** It must be **zero**.

**Worked example** (as of 30 June).

| Item | Amount |
|---|---|
| Cash and Bank | 120,000 |
| Inventory | 80,000 |
| **Total assets** | **200,000** |
| Accounts Payable | 50,000 |
| **Total liabilities** | **50,000** |
| Share Capital | 100,000 |
| Profit this year | 50,000 |
| **Total equity** | **150,000** |
| **Check** | `200,000 − (50,000 + 150,000)` = **0** ✓ |

### General Ledger

For each account: **opening balance**, the **movement** in the period, and the
**closing balance**:

> **closing = opening + period movement**, shown as a debit if positive and a
> credit if negative.

### Data integrity (the four dashboard checks)

| Check | Passes when |
|---|---|
| **Journal entries balance (debits = credits)** | total debits equal total credits |
| **Trial balance nets to zero** | the trial-balance difference is zero |
| **Balance sheet balances (Assets = Liabilities + Equity)** | the balance-sheet check is zero |
| **General Ledger inventory equals stock ledger value** | the inventory value in the accounts equals the total value in the stock ledger |

The fourth check is worth watching. On an imported workbook it can fail, because
the original stock sheet may never have posted matching journal entries. From
then on, every stock movement the system posts writes its own journal entry, so
the two stay in step.

---

## 2.8 Payroll — how a payslip and its entry are worked out

You enter a period; the system pays every **active** employee. The salary
structure lives in Configuration, so nothing is fixed in code.

### Splitting gross pay into components

> **component amount = gross salary × component percentage ÷ 100**

With the default structure (Basic 60%, House Rent 30%, Medical 5%, Transport 5%),
an employee on **30,000** splits as:

| Component | Arithmetic | Amount |
|---|---|---|
| Basic | `30000 × 60 ÷ 100` | 18,000 |
| House Rent | `30000 × 30 ÷ 100` | 9,000 |
| Medical | `30000 × 5 ÷ 100` | 1,500 |
| Transport | `30000 × 5 ÷ 100` | 1,500 |
| **Total** | | **30,000** |

The components are a *breakdown* of gross, not something added on top.

### Deductions and net pay

> **deduction amount = gross × deduction percentage ÷ 100**
> **net pay = gross − the sum of all deductions**

If a list of named deductions is configured, those are used. If none is
configured, a single **statutory deduction** at the configured percentage is
applied instead. With the default 10%:

| Employee | Gross | Statutory deduction (10%) | Net pay |
|---|---|---|---|
| Office employee | 30,000 | 3,000 | 27,000 |
| Factory employee | 20,000 | 2,000 | 18,000 |
| **Totals** | **50,000** | **5,000** | **45,000** |

### The journal entry

Office and factory pay go to **different expense accounts**; deductions and net
pay are credited:

| Account | Debit | Credit |
|---|---|---|
| 6010 Office Salaries (office staff gross) | 30,000 | — |
| 5011 Factory Labour (factory staff gross) | 20,000 | — |
| 2210 TDS Payable (the deductions) | — | 5,000 |
| 1010 Bank (the net paid out) | — | 45,000 |
| **Totals** | **50,000** | **50,000** |

It balances because **gross = deductions + net** (`50,000 = 5,000 + 45,000`).

---

## 2.9 Where voucher numbers come from

Every posting gets a number: purchases `PUR-…`, sales `SALE-…`, production
`PROD-…`, payroll `PAY-…`. A new number is always:

> **the highest number already used, plus one**, padded to at least three digits
> (`SALE-004`).

The system counts numbers used by the document **and** by journal entries, so a
new posting can never clash with one already in the books.

A **reversal** does not take a new number. It reuses the original with `-REV`
added: `SALE-004` becomes `SALE-004-REV`. That suffix is also the guard that stops
the same posting being reversed twice.

---

## 2.10 Reversals — why nothing is ever edited or deleted

When a posting was a mistake, the system writes a **mirror entry**: every debit
becomes a credit and every credit a debit, so the two entries cancel out. The
original stays exactly as it was, marked as reversed, with the reason recorded.

- Stock moves back at **exactly** the value it moved at, so the arithmetic unwinds
  precisely.
- The original and the correction both remain on the record — which is what makes
  the history explainable afterwards.

### What each kind of reversal does to stock

A reversal puts back exactly what a transaction took, or takes back exactly what it
put in. The only thing that can stop it is not having the stock to move:

| Reversing a… | Stock moves | Can it be refused? |
|---|---|---|
| **Sale** | goods come **back in** | **No.** Putting goods back can never overdraw stock, so a sale can always be reversed. |
| **Purchase** | goods go **out** | **Yes** — only while nothing has touched the item since the purchase. |
| **Production run** | the **output goes out first**, then the components come back in | **Yes** — only while the output is still on hand, i.e. none of what it made has been sold. Components always return freely. |
| **Payroll run** | nothing (accounts only) | No. |

A refusal always names the item and what is on hand, for example
*"Cannot take 30 of FG-100: only 20 on hand."* The whole reversal is one
transaction, so a refusal changes nothing at all.

**"Already reversed"** and **"an approval is required"** are the other two
reasons a reversal is stopped (see 2.12 for approvals).

### The order to reverse in

Undo in the **reverse order you did things** — the sale first, then the production
run, then the purchase. Reversing in that order is exact: stock quantity, stock
value and average cost all return precisely to where they started.

- **A production run cannot be reversed while its output has been sold.** Reverse
  the sale that consumed the output first.
- **A purchase cannot be reversed while anything has touched the item since.**
  Sold, consumed, or even topped up with another purchase — any of those changes
  the item's average, and taking the original purchase back out at its own value
  would leave what remains valued at a figure that never existed.

  The refusal names the item and both quantities, for example:
  *"RMC-100 has moved since this purchase (200.0000 on hand then, 140.0000 now).
  Reverse the later transactions first."* Do that, and the purchase reversal
  becomes exact — the item returns to exactly where it started.

> Reversals are recorded in the order you make them, however old the transaction
> they correct. The stock ledger lists rows in that order, so the running balance
> always reads correctly.

### Why a purchase is refused rather than recalculated

Suppose you hold 100 kg at 20 each, then buy 100 kg at 25. You now hold 200 kg
worth 4,500 — an average of **22.50**. You use 60 kg in production, leaving 140 kg
worth 3,150, the average still 22.50.

Reverse the purchase now, and it removes 100 kg at the 2,500 it came in at. What
is left is 40 kg worth `3,150 − 2,500 = 650` — **16.25 each**. But those 40 kg are
the original stock that cost **20**. The stock sheet and the accounts would still
agree with each other, yet the item would be carried at a price that never
existed, and every later cost drawn from it would be wrong.

So the system refuses, and asks you to reverse the production run first. Undoing
the run puts the 60 kg back, the item returns to 200 kg at 22.50, and the purchase
then comes out exactly.

---

## 2.11 Opening balances

Opening balances are the starting amounts on the **cutover date**. They are
imported, then locked, and they are shown read-only. As a batch they must prove
that debits equal credits; the opening-balance screen reports **balanced** when
they do.

---

## 2.12 The approval gate

Approvals are **off by default**. When an administrator turns **Require second
approval** on, an action that the policy covers is paused instead of being
carried out:

- A request is recorded with who asked, what for, and why.
- The action itself is **not** performed.
- A **different** person approves it, and only then does it happen.

The rules:

| Setting | Effect |
|---|---|
| **Require second approval** | Master switch. Off means nothing is paused. |
| **Approval threshold** | Only actions at or above this amount are paused. `0` means all of them. |
| **Actions needing approval** | *Reversals* only, or *reversals and postings*. |

The person who asked **cannot** approve their own request — a second person must
decide it. Approving carries the action out as the approver.

---

## 2.13 Bill of Materials — how "explode" works

A recipe can be multi-stage: a finished product contains a sub-assembly, which
itself is made of materials. **Explode** flattens all of that into the actual
materials you must buy.

It works recursively: any component that has its own recipe is expanded further,
with quantities scaled up. Components with no recipe are the leaves, and their
cost is estimated at their current average cost.

**Worked example.** Make **10** of product P.

- P needs **2** of sub-assembly S.
- S needs **3** of raw material R.

Exploding P for 10 gives S required = `10 × 2 = 20`, and R required =
`20 × 3 = 60`. The shopping list shows the leaf material, R, at 60.


## 2.14 Closing a year — how the system keeps a closed period closed

Once you have reported a year, nothing should be able to change it quietly. One
setting does that.

**Where:** Configuration → Posting controls → **Books closed through**.

- **Blank** (the default) means the books are **open**. Every date is accepted.
- Put a date in, and **nothing may be dated on or before it**.

That applies to every way a transaction gets into the books: purchases,
production runs, sales, payroll runs, manual journal entries, **and reversals**.

**Why reversals too.** A reversal is a posting like any other — it moves money and
stock. If it were allowed inside a closed year, it would change a year you have
already reported, which is exactly what closing it was meant to prevent.

**Worked example.** Suppose **Books closed through** is `2026-06-30`.

| You try to record | Dated | Result |
|---|---|---|
| A purchase | 2026-06-15 | **Refused** — inside the closed period |
| A purchase | 2026-07-01 | Accepted — in the open period |
| A reversal of a June sale | 2026-06-20 | **Refused** — a posting inside the closed period |

The refusal names both dates, so there is nothing to guess at:

> The books are closed through 2026-06-30, so a transaction cannot be dated
> 2026-06-15. Date it after the closing date, or move the closing date back in
> Configuration.

**Two honest ways forward.** Either move the closing date back, make the
correction, and set it forward again — or, as an accountant normally would, date
the correction in the **current** period and leave the closed year alone. The
second keeps the reported year exactly as reported.

**A refused posting changes nothing.** No order, no stock movement, no journal
entry. You get the error and the books are untouched, so there is no half-posted
purchase to hunt down afterwards.

## 2.15 Who entered it — the record that cannot be claimed

Every posted transaction stores **the signed-in user's email address** as the
person who entered it. The interface shows it as *Entered by* on the lists and
drawings, and as *Recorded by* on a receipt.

It is taken from the **sign-in session**, never from what the screen sends. That
matters: if the name came from the screen, anybody who could reach the system
could put somebody else's name on a transaction, and the record would be worth
nothing. Because it comes from the session, "who entered SALE-014?" has a true
answer.

- A purchase entered by `store@resinovabd.com` is recorded as entered by
  `store@resinovabd.com`, whoever else is around.
- A reversal is attributed to the person who **asked** for it.
- A manual journal entry is attributed to the person who posted it.

**About older rows.** Transactions entered before this was tightened show the old
labels — `Sales`, `Store`, `Payroll`, `system`, `import`. They are **kept as they
were** rather than rewritten, because the record is history and history is not
edited to look better. From the change onward, every row names a real person.

## 2.16 When someone cannot sign in

**"Too many failed attempts."** After **five** wrong passwords the account locks
for **15 minutes** (an administrator can change both numbers). The message tells
you how many minutes are left. While the lock is on, **the correct password is
refused too** — that is the point of it, so guessing cannot succeed by luck.
Waiting, or an administrator resetting the password, clears it.

The lock is per **account**, not per computer: trying a different sign-in from the
same laptop is unaffected.

**A good sign-in clears the count.** If somebody mistypes twice and then gets it
right, the two mistakes are forgotten — they are not left one typo away from a
lock.

**If nobody can sign in at all**, the accounts are still there — a data reset
never deletes them. Either ask an administrator to reset a password from
**Roles & Access → User accounts → Reset password**, or, with access to the
server, make an administrator from the command line:

```bash
backend/.venv/bin/python scripts/create_user.py \
    --email admin@resinovabd.com --name "Md. Sarwar Hossain" --role admin
```

## 2.17 Backing up, and proving the backup works

These are your account books. A nightly copy, kept somewhere other than the
machine that runs the database, is what stands between a bad day and losing them.

Two commands, and they work whatever the system is running on — a hosted cloud
database or a machine in your own office:

```bash
# Every night. Writes a dated file and keeps the last 30.
backend/.venv/bin/python scripts/backup_db.py --out /mnt/backups --keep 30

# Prove the file is good, into a scratch database — not the live one.
backend/.venv/bin/python scripts/restore_db.py <the-file> --scratch <scratch-url>

# Restore over the live database. Destructive: stop the application first.
backend/.venv/bin/python scripts/restore_db.py <the-file> --yes
```

**Schedule it:** nightly, plus one before every upgrade and before any workbook
import or data reset. On Linux or macOS use cron or a systemd timer; on Windows,
Task Scheduler.

**Test a restore at least once**, into a scratch database. A backup that has never
been restored is not a backup, it is a hope. After restoring, sign in and check
the **Dashboard**: the **trial balance difference must read `0.0000`** and the
account balances must match what you expect for that date.


# Section 3 — End-to-End User Test Cases

These exercises walk through the system the way a real user would. Each one lists
who you are, what you are trying to do, what must be in place first, the exact
steps, what you should see, and how the system reached the result.

A note that applies throughout: the system starts from a **starter chart of
accounts** with **no items and no stock**. So the tests that buy, make or sell
things ask you to load sample data first (Test Case 8). Once loaded, everything
else works from there.

---

## Test Case 1 — Sign in and see your role

- **User Persona:** Any user (start as **Admin**).
- **Objective:** Sign in and confirm the system knows who you are.
- **Prerequisites:** A running system, and the sign-in details from your
  administrator.
- **Steps:**
  1. Open the system's web address.
  2. In **Email**, type `admin@rpci.demo`.
  3. In **Password**, type the password given to you.
  4. Click **Sign in**.
  5. Look at the top-right corner of the screen.
- **Expected Behavior:** The Dashboard opens. The top right shows your name and
  your role (for example, `System Administrator` / `Admin`). The left menu shows
  every group.
- **Actual Results & Calculation Explanation:** The system looks up your email,
  checks the password against a securely hashed copy, and — because your account
  has no second factor — issues a signed session. Your role travels inside that
  session, so every later request is checked against it. No menu is hidden,
  because the Admin role has full access to every area.

---

## Test Case 2 — Prove the permission rule comes from the server

- **User Persona:** Any user.
- **Objective:** See that access is enforced by the server, not by hiding menus.
- **Prerequisites:** Signed in (Test Case 1).
- **Steps:**
  1. Click **Roles & Access** in the **Administration** group.
  2. Find the **Permission matrix** and read your role's row.
  3. Scroll to **Live permission probe**.
  4. Click the button that reads **Call the API as "{your role}"**.
  5. Read the result line.
- **Expected Behavior:** Either a green message, `GET /api/accounts allowed for
  "{role}"`, or a red message, `GET /api/accounts blocked for "{role}": …`. As
  Admin you should be allowed.
- **Actual Results & Calculation Explanation:** The button makes a real request to
  the server using your session. The server reads the role from your signed
  session — never from anything the screen sends — and compares it with the
  permission table. Reading the chart of accounts is allowed for Admin,
  Accountant and Owner/Viewer, and refused for Store/Production and Sales Staff.
  That is why the answer comes from the server: hiding a menu is a convenience,
  not the security.

---

## Test Case 3 — Change your password

- **User Persona:** Any user.
- **Objective:** Replace your password with one you choose.
- **Prerequisites:** Signed in.
- **Steps:**
  1. Click **Security** in the **Administration** group.
  2. Under **Change password**, type your current password in **Current
     password**.
  3. Type a new password of at least eight characters in **New password**.
  4. Click **Change password**.
- **Expected Behavior:** A green message, **"Password changed."**, appears.
- **Actual Results & Calculation Explanation:** The system checks the current
  password, then stores a new **hash** — a one-way scrambling of the password, so
  the password itself is never saved anywhere readable. If your new password is
  the same as your old one, the change is refused; if the current password is
  wrong, it is refused. This is your own account, so no administrator is needed.

---

## Test Case 4 — Turn on two-factor authentication

- **User Persona:** Any user.
- **Objective:** Add a second layer of protection to your sign-in.
- **Prerequisites:** Signed in, and an authenticator app on your phone (Google
  Authenticator, Authy, or any app that reads QR codes).
- **Steps:**
  1. Click **Security**.
  2. Under **Two-factor authentication**, click **Set up two-factor
     authentication**.
  3. Open your authenticator app and scan the QR code shown.
  4. In **Code from the app**, type the six-digit code the app displays.
  5. Click **Turn on**.
  6. Write down the recovery codes shown.
- **Expected Behavior:** The status changes to **on**, and a set of recovery codes
  is displayed with the message **"Save these now."**
- **Actual Results & Calculation Explanation:** The app and the system share a
  secret. The app turns that secret plus the current time into a six-digit code;
  the system does the same sum and checks they match. It allows one step of clock
  drift either way, so a phone a few seconds out still works. The recovery codes
  are shown once and stored only as hashes — they are the way back in if the
  phone is lost.

---

## Test Case 5 — Issue a new password and clear a second factor (Admin)

- **User Persona:** **Admin**.
- **Objective:** Help a colleague who cannot sign in.
- **Prerequisites:** Signed in as Admin; another user account exists.
- **Steps:**
  1. Click **Roles & Access**.
  2. Under **User accounts**, find the colleague's row.
  3. Click **Reset password**.
  4. Read the password shown and give it to your colleague directly.
  5. Click **Reset 2FA** for the same person (only if they have lost their phone
     and their recovery codes).
  6. Scroll to **Administrative actions**.
- **Expected Behavior:** A green box shows **"New password for {email}"** with the
  password beneath it. The person's **2FA** tag changes to **off**. The two
  actions appear at the top of **Administrative actions**.
- **Actual Results & Calculation Explanation:** Issuing a password generates a new
  random one and stores only its hash; the plain text is shown once and never
  stored. Clearing the second factor deletes the shared secret and voids the old
  recovery codes. Both actions are written to the audit log with who did it, to
  whom, and when. You cannot do either to your own account from here — **Security**
  is the place for that — which prevents an accidental lock-out.

---

## Test Case 6 — Put your company details on documents

- **User Persona:** **Admin**.
- **Objective:** Make receipts show the correct company name, address and phone.
- **Prerequisites:** Signed in as Admin.
- **Steps:**
  1. Click **Configuration**.
  2. In the **Company details** card, find **Company name**.
  3. Change the value and click **Save**.
  4. Click **Confirm** on the same row.
  5. Repeat for **Address** and **Telephone**.
- **Expected Behavior:** Each row saves with a brief **"saved"** marker, and its
  badge changes from **pending client** to **confirmed**.
- **Actual Results & Calculation Explanation:** Configuration values are stored
  centrally, not baked into the program. Changing one takes effect immediately —
  the next receipt prints the new details, with no redeploy. The **confirmed**
  badge records that a person has checked the value, so it is clear which facts
  are settled and which are still placeholders.

---

## Test Case 7 — Switch VAT on

- **User Persona:** **Admin**.
- **Objective:** Add VAT to sales and purchases at the agreed rate.
- **Prerequisites:** Signed in as Admin; the rate confirmed with your tax adviser.
- **Steps:**
  1. Click **Configuration**.
  2. In the **VAT** card, find **Charge VAT** and switch it to **on**, then
     **Save**.
  3. Find **Standard rate (%)**, set the rate, and **Save**.
  4. Find **Prices include VAT** and set it to match how you quote customers
     (**off** means prices are before VAT), then **Save**.
  5. Confirm the **Input VAT account** and **Output VAT account** are the accounts
     you intend.
- **Expected Behavior:** The badges show the new state; each save shows **"saved"**.
- **Actual Results & Calculation Explanation:** VAT was off, so every posting
  behaved as if no tax existed. With **Charge VAT** on, sales add **output VAT**
  and purchases add **input VAT** at the configured rate (see Section 2.5 for the
  arithmetic, including the inclusive-prices case). Nothing is hardcoded, so the
  books behave exactly as before until this switch is turned on.

---

## Test Case 8 — Load data so there is something to work with

- **User Persona:** **Admin**.
- **Objective:** Put items and stock into the system.
- **Prerequisites:** Signed in as Admin.
- **Steps:**
  1. Click **Data**.
  2. Read the warning under **Import an existing workbook**.
  3. In the **Start over** card, click **Restore sample workbook**.
  4. Wait for the message, then open **Inventory & BOM**.
- **Expected Behavior:** A green confirmation appears, and the Inventory screen now
  lists items with quantities and average costs.
- **Actual Results & Calculation Explanation:** Restoring the sample workbook
  loads a complete set of accounts, items, opening balances, journal history and
  stock movements. Every stock movement was replayed through the same
  weighted-average engine the system uses for new postings, which is why the
  figures match the source data exactly. This is the same path an import of your
  own workbook takes.

---

## Test Case 9 — Record a purchase and watch the average cost change

- **User Persona:** **Store/Production Staff** or **Admin**.
- **Objective:** Receive stock at a price and see the average cost update.
- **Prerequisites:** Test Case 8 done (items exist); signed in with permission to
  enter purchases.
- **Steps:**
  1. Click **Purchase Entry**.
  2. Leave **Settlement** on **On credit (supplier payable)**.
  3. On the line, choose an **Item**.
  4. Note the **Current avg cost** shown for that item.
  5. In **Quantity**, type a quantity (for example `10`).
  6. In **Unit cost**, type a price different from the current average (for
     example `130`).
  7. Read the **Effect on average cost** table.
  8. Click **Post purchase**.
- **Expected Behavior:** The **Before** and **After** columns differ. A green
  message appears confirming the posting. The **Posted purchases** list gains a
  row.
- **Actual Results & Calculation Explanation:** The purchase adds quantity and
  value, then divides: **new average = (old value + new value) ÷ (old quantity +
  new quantity)**. If you held 10 at 100 (value 1,000) and bought 10 at 130
  (value 1,300), the new average is `(1000 + 1300) ÷ 20` = **115**. The journal
  entry debits the item's inventory account by 1,300 and credits Accounts
  Payable — Local by the same amount, so the entry balances.

---

## Test Case 10 — Manufacture a product and read the cost build-up

- **User Persona:** **Store/Production Staff** or **Admin**.
- **Objective:** Produce a finished item and see how its unit cost is worked out.
- **Prerequisites:** Test Case 8 done; the item you choose has a recipe (BOM) and
  stock of its components.
- **Steps:**
  1. Click **Production Entry**.
  2. In **Item to produce**, choose an item that has a recipe.
  3. In **Quantity produced**, type the batch size (for example `50`).
  4. Leave **Labor cost** and **Overhead cost** at `0`, or type small amounts.
  5. Look at the **Components consumed** table and the **ok** / **short** tags.
  6. Read the **Cost build-up** table.
  7. Read the **Journal entry it will post**.
  8. Click **Post production**.
- **Expected Behavior:** The build-up shows **Material cost**, **Labor**,
  **Overhead**, **Total production cost** and **Unit cost of output**. The journal
  preview shows balanced debits and credits. Posting shows a confirmation and adds
  a row to **Posted production runs**.
- **Actual Results & Calculation Explanation:** The system suggested the
  components from the recipe, scaled to the batch, and valued each at its current
  average cost. It then added labour and overhead and divided:
  **unit cost = total cost ÷ quantity produced**. Example: material 2,250 + labour
  300 + overhead 50 = **2,600**; `2600 ÷ 50` = **52** per unit. The entry debits
  Finished Goods by 2,600, credits each component's inventory by its line cost,
  and credits Bank by the 350 of labour and overhead.

---

## Test Case 11 — Sell goods and print a receipt

- **User Persona:** **Sales Staff** or **Admin**.
- **Objective:** Record a sale and give the customer a document.
- **Prerequisites:** Test Case 8 done; the item is in stock.
- **Steps:**
  1. Click **Sales Entry**.
  2. Type a **Customer** name.
  3. Choose an **Item** that is in stock.
  4. Type a **Quantity** no larger than the **On hand** figure.
  5. Type a **Sale price** above the **Avg cost** (or expect the below-cost tag).
  6. Read the **Revenue and margin** panel and the journal preview.
  7. Click **Post sale**.
  8. In **Posted sales**, click **Receipt** on the new row.
  9. Click **Print**.
- **Expected Behavior:** The margin panel shows **Revenue**, **Cost of goods
  sold**, **Gross profit** and **Gross margin**. The receipt shows the company
  details, the customer, the item lines, and a **Total**. Printing produces the
  document alone — no menu or toolbar.
- **Actual Results & Calculation Explanation:** Revenue = `quantity × sale price`;
  COGS = `quantity × average cost`; gross profit = the difference; margin =
  `gross profit ÷ revenue × 100`. Selling 4 at 150 with an average cost of 100
  gives revenue **600**, COGS **400**, gross profit **200**, margin **33.3333%**.
  The single journal entry debits Receivable 600, credits Sales 600, debits COGS
  400 and credits Inventory 400. The receipt reads back the stored lines, so what
  the customer holds can never disagree with the books.

---

## Test Case 12 — Reverse a sale

- **User Persona:** **Sales Staff** or **Admin**.
- **Objective:** Undo a sale that should not have been posted.
- **Prerequisites:** A posted sale exists (Test Case 11); permission to change
  sales.
- **Steps:**
  1. Click **Sales Entry**.
  2. In **Posted sales**, on the sale you want to undo, click **Reverse**.
  3. Read the explanation that appears.
  4. In **Why is this being reversed?**, type a short reason.
  5. Click **Confirm reversal**.
  6. Open the row's **Receipt**.
- **Expected Behavior:** The sales row shows a **reversed** tag. The receipt shows
  a **"Reversed — this sale has been undone"** banner. On **Inventory & BOM**, the
  item's quantity is back to what it was.
- **Actual Results & Calculation Explanation:** The system wrote a mirror entry —
  every debit and credit swapped — numbered with a `-REV` suffix, and returned the
  goods to stock at exactly the cost they left at. Nothing was deleted: the
  original sale and its correction both remain, which is what makes the history
  explainable later. Reversing the same sale twice is refused.

---

## Test Case 13 — Try to reverse a purchase whose goods have been used

- **User Persona:** **Store/Production Staff** or **Admin**.
- **Objective:** See the system refuse to take back stock that no longer exists.
- **Prerequisites:** A posted purchase whose stock has since been consumed in a
  production run.
- **Steps:**
  1. Click **Purchase Entry**.
  2. In **Posted purchases**, find that purchase.
  3. Click **Reverse**.
  4. Type a reason and click **Confirm reversal**.
- **Expected Behavior:** A red message appears, naming the item and the quantity on
  hand, for example: *"Cannot take 10 of RMC-001: only 4 on hand."* The purchase is
  **not** reversed and stock is unchanged.
- **Actual Results & Calculation Explanation:** Taking the goods back would drive
  the quantity negative, which is impossible. The honest answer is to reverse the
  later transaction — the production run that used them — first. Because everything
  happens in one transaction, the refusal leaves the books exactly as they were.

---

## Test Case 14 — Read the voucher trail

- **User Persona:** **Accountant** or **Admin**.
- **Objective:** Trace what the system recorded, line by line.
- **Prerequisites:** At least one posting exists (for example Test Case 11).
- **Steps:**
  1. Click **Journal Entries**.
  2. Find the entry for the posting, using its voucher number and date.
  3. Read its tag (**Manual**, **Production**, **Sales** or **Purchase**).
  4. Click **Show lines**.
  5. Check the **Total** row at the foot of the lines.
- **Expected Behavior:** The lines expand to show **Account**, **Segment**,
  **Narration**, **Debit** and **Credit**, with a **Total** that has equal debits
  and credits.
- **Actual Results & Calculation Explanation:** Every posting in the system appears
  here, whether it came from a sale, a purchase, a production run, payroll, or a
  hand-written voucher. The screen is a reading view — entries are created by the
  module that owns them, so a sale's entry is created when you post the sale.
  Because the two sides are enforced equal before storage, the **Total** row
  always balances.

---

## Test Case 15 — Add an employee

- **User Persona:** **Admin** or **Accountant**.
- **Objective:** Put a member of staff on the payroll.
- **Prerequisites:** Signed in with permission for Payroll.
- **Steps:**
  1. Click **Payroll → Employees**.
  2. In **Code**, type a staff number.
  3. In **Name**, type the person's name.
  4. In **Department**, choose **Office** or **Factory**.
  5. Fill in **Designation**, **Personal email**, **Mobile**, **Joining date** and
     **Bank account** as you have them.
  6. In **Gross salary**, type their monthly gross (for example `30000`).
  7. Click **Save employee**.
- **Expected Behavior:** A green message, **"Employee added."**, appears, and the
  person appears in the **Staff** table with an **active** tag.
- **Actual Results & Calculation Explanation:** The employee record stores gross
  pay only. The split into Basic, House Rent and so on is **not** stored on the
  person — it is applied from the rules in Configuration. That means changing the
  structure later applies to everyone at once, without editing each record. The
  **Department** value decides whether their pay is charged to the Office Salaries
  or Factory Labour account when payroll runs.

---

## Test Case 16 — Run payroll and print a payslip

- **User Persona:** **Admin** or **Accountant**.
- **Objective:** Pay staff for a month and produce payslips.
- **Prerequisites:** At least one active employee (Test Case 15).
- **Steps:**
  1. Click **Payroll → Payroll Runs**.
  2. Set **Period start**, **Period end** and **Pay date**.
  3. Read the preview table: **Employee**, **Gross**, **Deductions**, **Net pay**.
  4. Read the **Journal entry it will post**.
  5. Click **Post payroll**.
  6. In **Posted runs**, click **Payslips** on the new run.
  7. Click **Print**.
- **Expected Behavior:** The preview shows one row per active employee with a
  **Total** row, and a balanced journal preview. Posting shows a confirmation. The
  payslip page lists each employee with their component and deduction breakdown.
- **Actual Results & Calculation Explanation:** For each person the system split
  gross into components and applied the deductions (**component = gross ×
  percentage ÷ 100**), then worked out **net = gross − deductions**. An employee on
  30,000 with the default 10% deduction has net **27,000**. The single journal
  entry debits Office Salaries (for office staff) and Factory Labour (for factory
  staff) by their total gross, and credits the deduction account and the Bank by
  the totals — which balances because gross equals deductions plus net.

---

## Test Case 17 — Require a second person to approve a reversal

- **User Persona:** **Admin** (setting up), then two different people.
- **Objective:** Make a reversal wait for a second person's approval.
- **Prerequisites:** A posted sale to reverse; two user accounts (for example the
  Admin and the Sales Staff).
- **Steps:**
  1. As **Admin**, open **Configuration**.
  2. In **Posting controls**, switch **Require second approval** to **on** and
     **Save**.
  3. Leave **Approval threshold** at `0` (meaning all reversals need approval).
  4. Sign out, and sign in as the **Sales Staff** user.
  5. Open **Sales Entry**, and click **Reverse** on the sale.
  6. Type a reason and click **Confirm reversal**.
  7. Sign out, and sign back in as the **Admin**.
  8. Open **Approvals**.
  9. Read the pending row, and click **Approve**.
- **Expected Behavior:** At step 6 the reversal does **not** happen; a message
  explains that a second person must approve it. At step 9 the request moves to
  **History** as **approved**, and the sale is now reversed.
- **Actual Results & Calculation Explanation:** With the switch on, the system
  records a request and pauses the action instead of performing it. The person who
  asked cannot approve their own request — a second person must decide it. When the
  Admin approves, the system carries the reversal out as the approver, which is why
  the sale ends up reversed. Turning the switch back off restores the old
  behaviour immediately.

---

## Test Case 18 — Read the three financial reports

- **User Persona:** **Owner/Viewer**, **Accountant** or **Admin**.
- **Objective:** Check the books add up.
- **Prerequisites:** Some postings exist; note the **As of** date in the top bar.
- **Steps:**
  1. Set **As of** to a date after your postings.
  2. Click **Reports → Trial Balance** and read the bottom **Difference** row.
  3. Click **Reports → Balance Sheet** and read the final check row.
  4. Click **Reports → General Ledger** and read the header total.
  5. Return to **Dashboard** and read the **Data integrity** card.
- **Expected Behavior:** The Trial Balance **Difference** is **0.0000**. The
  Balance Sheet check reads **0**. The General Ledger header shows period debits
  equal to period credits. The Dashboard checks show ticks.
- **Actual Results & Calculation Explanation:** The Trial Balance adds up every
  account's net balance and splits it into debits and credits; because every
  posting is balanced, the two columns are equal and the difference is zero. The
  Balance Sheet adds assets on one side and liabilities plus equity (including
  this year's profit) on the other; they match for the same reason. The General
  Ledger header total is simply the sum of all period debits and credits, which are
  equal by construction. If any of these ever disagreed, the Dashboard's fourth
  check — comparing the accounts' inventory value against the stock ledger — would
  be the one to look at.

---

## Test Case 19 — Work out the shopping list for a production run

- **User Persona:** **Store/Production Staff** or **Admin**.
- **Objective:** See exactly what materials a batch needs.
- **Prerequisites:** Test Case 8 done; the parent item has a recipe.
- **Steps:**
  1. Click **Inventory & BOM**.
  2. Scroll to **BOM explosion**.
  3. In **Target quantity**, type the batch size (for example `50`).
  4. Click **Explode BOM**.
  5. Read the table and the **Estimated material cost** row.
- **Expected Behavior:** A list appears with **Level**, **Component**,
  **Category**, **Per unit**, **Required**, **Avg cost** and **Estimated cost**,
  ending in a total. If the item has no recipe, the screen says so instead.
- **Actual Results & Calculation Explanation:** The system walked the recipe
  recursively. Any component that is itself manufactured was expanded further, with
  quantities scaled up — a parent needing 2 of a sub-assembly that needs 3 of a
  material, for a batch of 10, gives `10 × 2 × 3` = **60** of that material. Items
  with no recipe are the leaves, and their cost is estimated at their current
  average cost.

---

## Test Case 20 — Import your own workbook

- **User Persona:** **Admin**.
- **Objective:** Replace the books with your existing data.
- **Prerequisites:** Your data in an `.xlsx` file with the same sheet names as the
  sample (Chart of Accounts, Item Master, Opening Balances, BOM Master, Journal
  Entries, Inventory Ledger).
- **Steps:**
  1. Click **Data**.
  2. Under **Import an existing workbook**, click **Workbook (.xlsx)** and choose
     your file.
  3. Leave **Replace the books (empty them first)** ticked.
  4. Click **Import workbook**.
  5. Open **Trial Balance** and set **As of** to your cutover date.
- **Expected Behavior:** A green confirmation listing what was imported (accounts,
  items and so on). The Trial Balance shows your accounts, and the **Difference**
  is **0**.
- **Actual Results & Calculation Explanation:** The import reads each sheet, then
  loads accounts, items, recipes, opening balances, history and stock movements in
  that order, and re-creates the sign-in accounts and configuration afterwards.
  Because **Replace** is ticked, the books are emptied first — an import is a fresh
  set of books, not a merge that could double-count. If a sheet is missing or
  renamed, the import stops and says so rather than loading half the data.

---

## Test Case 21 — Start the books over

- **User Persona:** **Admin**.
- **Objective:** Clear everything and begin again.
- **Prerequisites:** Signed in as Admin.
- **Steps:**
  1. Click **Data**.
  2. In the **Start over** card, click **Start fresh (starter accounts)**.
  3. Acknowledge the result, then open **Chart of Accounts**.
  4. Open **Inventory & BOM**.
- **Expected Behavior:** A green confirmation appears. The Chart of Accounts shows
  the starter accounts, and the Inventory screen lists nothing.
- **Actual Results & Calculation Explanation:** The action empties every table and
  loads the standard starter chart of accounts — 29 accounts with no balances, no
  items and no stock. It then restores the sign-in accounts and configuration, so
  you can still get in. **Empty everything** does the same but loads no accounts at
  all, which leaves the books unusable until data is entered or imported. Both
  actions are irreversible, and an administrator may switch them off for a
  deployment whose data must never be lost.

---

## Test Case 22 — See a restricted role's view

- **User Persona:** **Store/Production Staff**, then **Sales Staff**.
- **Objective:** Confirm that different jobs see different menus.
- **Prerequisites:** The sample sign-in accounts exist.
- **Steps:**
  1. Click **Sign out**.
  2. Sign in as the **Store/Production Staff** user.
  3. Look at the left menu.
  4. Open **Production Entry** and confirm you can post.
  5. Open **Chart of Accounts** by typing its address, if you can reach it.
  6. Sign out, then sign in as the **Sales Staff** user and repeat steps 3–5.
- **Expected Behavior:** The Store/Production user sees **Inventory & BOM** and
  **Production Entry**, but not **Chart of Accounts** or **Sales Entry**. The Sales
  user sees **Sales Entry**, but not **Production Entry**. Trying to reach a hidden
  screen is refused by the server with the message that the screen is not available
  to that role.
- **Actual Results & Calculation Explanation:** The menu is built from your role's
  permissions, so items you cannot read are never offered. That alone would not be
  security, because the address could be typed by hand — which is why the server
  checks the role on every request and refuses it. You can see the same refusals
  the server will give in the **Menus by role** table on the **Roles & Access**
  screen.

---

## Test Case 23 — Close a period and be refused

- **User Persona:** Admin.
- **Objective:** Set a closing date, then prove nothing can be posted inside it.
- **Prerequisites:** Signed in as **Admin**; sample data loaded (Test Case 8); the
  purchase from Test Case 9 posted. Note the date you used for it.
- **Steps:**
  1. Go to **Administration → Configuration → Posting controls**.
  2. Set **Books closed through** to a date on or after your test purchase date,
     and click **Save**.
  3. Go to **Purchases** and enter a purchase dated **on or before** that closing
     date. Click **Post purchase**.
  4. Read the message.
  5. Change the date to **after** the closing date and post again.
  6. Go back to **Posting controls**, clear the field, and save.
- **Expected Behaviour:** Step 3 is refused with a red message naming both dates.
  Step 5 is accepted. In step 3 **nothing is posted** — the purchase list is
  unchanged. Step 6 returns the books to normal.
- **Actual Results & Calculation Explanation:** Every posting, whatever created
  it, builds a journal entry — and the entry is built only after the transaction
  date has been compared with the closing date. Inside the closed period the
  entry is never built, so no order row, no stock movement and no journal line is
  written. The refusal lists no partial work because there is none. Clearing the
  field means "no closing date", so every date is accepted again.

---

## Test Case 24 — Get locked out, and back in

- **User Persona:** Admin, testing with a spare account (use **Sales Staff**, so
  you do not lock the account you are working from).
- **Objective:** See the sign-in lock, and prove both ways it is released.
- **Prerequisites:** Signed in as **Admin**, and you know the Sales Staff
  password.
- **Steps:**
  1. **Sign out.**
  2. Try to sign in as the Sales Staff account with a **wrong** password. Repeat
     **five** times.
  3. Read the message.
  4. Now try with the **correct** password.
  5. Sign in as **Admin**. Go to **Administration → Roles & Access → User
     accounts**, find the Sales Staff row, and click **Reset password**.
  6. Copy the password shown, sign out, and sign in as Sales Staff with it.
- **Expected Behaviour:** After the fifth wrong attempt the message says the
  account is locked and how many minutes remain. In step 4 **the correct password
  is refused as well** — the lock is not bypassed. In step 6 the new password
  works immediately.
- **Actual Results & Calculation Explanation:** Each wrong password adds one to a
  count kept **against the account** (not against the computer), so it survives a
  restart of the service. At five, a lock time is written and the count is
  cleared, so once the lock expires the person gets a fresh set of attempts rather
  than locking again on their next typo. A **successful** sign-in also clears the
  count, and so does issuing a new password — which is why step 6 works: an
  administrator resetting a password releases the lock, otherwise the reset would
  hand over details that still did not work.

---

## Test Case 25 — Add a new item, and find out what cannot be deleted

- **User Persona:** **Store/Production Staff** or **Admin**.
- **Objective:** Add a product to the item master without importing a workbook,
  correct it, and see the rule that protects items with history.
- **Prerequisites:** Signed in as Admin or Store/Production Staff.
- **Steps:**
  1. Open **Inventory & BOM**.
  2. Click **Add item**.
  3. Fill in **Code** `NEW-100`, **Name** `New Resin Grade`, **Unit** `kg`,
     **Category** `Raw Material`, **Segment** `Manufacturing`, **Active** on.
  4. Click **Add item**.
  5. Find `NEW-100` in the list and read its **Qty on hand**, **Avg cost** and
     **Value**.
  6. Click **Edit** on that row, change the **Name**, and click **Save item**.
  7. Click **Edit** again and press **Delete**.
  8. Now try the same on an item that has been used — `TRD001` in the sample data —
     by clicking its **Edit**, then **Delete**.
- **Expected Behaviour:** Step 4 shows a green confirmation and the item appears
  with zero stock. Step 6 changes the name and leaves the unit and category alone.
  Step 7 removes the item, because nothing refers to it. Step 8 is **refused**,
  with a message saying how many records use the item and telling you to set it
  **inactive** instead.
- **Actual Results & Calculation Explanation:** The row holds only the master data
  — code, name, category, segment, unit. Quantity and average cost are **derived
  from the stock ledger**, so a brand-new item shows zero until it is bought or
  made; they are deliberately not editable here, which is what stops the stock
  sheet disagreeing with the accounts. The **code** is the key every other record
  points at, so it is fixed once saved — renaming it would orphan the purchases,
  sales and movements that named it. Deletion is allowed only when the count of
  references is zero, checked across the stock ledger, purchase lines, sales
  lines, production runs and the BOM. When it is not zero the refusal keeps the
  posted history whole, and **inactive** achieves what the user actually wanted:
  the item stops appearing in the pickers while its history stays readable.

---

## Test Case 26 — Add a customer, then sell to them

- **User Persona:** **Sales Staff** or **Admin**.
- **Objective:** Create a customer record, sell to it, and see that the sale cannot
  drift away from the record.
- **Prerequisites:** Signed in as Sales Staff or Admin; sample data loaded (Test Case
  8) so there is stock to sell.
- **Steps:**
  1. Open **Customers & Suppliers**.
  2. Click **Add customer or supplier**. Fill in **Code** `CUS-100`, **Name**
     `Karim Enterprise`, **Type** `Customer`. Save.
  3. Open **Sales Entry**. Look at the **Customer** field.
  4. Choose `Karim Enterprise`, pick an item with stock, and post the sale.
  5. Back on **Customers & Suppliers**, click **Edit** on `CUS-100`, change the name
     to `Karim Enterprise Ltd`, and save.
  6. Open **Sales Entry** and look at the posted sale you just made.
  7. Try to **Delete** `CUS-100`.
- **Expected Behaviour:** In step 3 the **Customer** box is a dropdown of your
  customer records, not a free-text box. In step 6 the sale still shows the name it
  was **posted under** — a posted document keeps the name it was issued with, and it
  is the customer **code** behind it that ties the two together. In step 7 the delete
  is **refused**, with a message saying how many transactions name the record and
  telling you to set it inactive instead.
- **Actual Results & Calculation Explanation:** The sale stores the customer's
  **code**, which is what makes the sale belong to a specific firm rather than to a
  spelling of its name. The name is kept on the sale as well, as the document was
  issued under it. So renaming a customer corrects the **master list** and every
  report built from it — a balance, a statement, an ageing list — while a posted
  invoice keeps the name it was printed with, which is what an auditor expects to
  see. The code, not the name, is the identity, which is why the code is fixed after
  creation and why two firms may share a name without becoming one. Deletion is
  refused once any transaction refers to the record: the count is taken across sales
  and purchases, and removing the record would leave those transactions pointing at
  nothing. Setting it **inactive** keeps the history readable and simply stops it
  being offered on new transactions.

---

## Test Case 27 — Take a customer's money, and settle an invoice

- **User Persona:** **Admin** or **Accountant** (receipts and payments are an
  accounting job; an administrator can widen this per user from Roles & Access).
- **Objective:** Record money received, settle an invoice with it, and see the
  balance answer itself.
- **Prerequisites:** Test Case 26 done, so there is a customer and a posted sale.
- **Steps:**
  1. Open **Receipts & Payments**.
  2. In **Outstanding invoices**, find the sale from Test Case 26 and read its
     **Total**, **Settled** and **Outstanding**.
  3. Click **Settle** on that row.
  4. Check the **Amount** is the outstanding figure, set **Account** to `1010`, and
     type a **Reference** such as `CHQ-1001`.
  5. Click **Preview entry** and read the two lines.
  6. Click **Record**.
  7. Look at **Outstanding invoices** again, and at **Journal Entries**.
- **Expected Behaviour:** In step 3 the form opens with **Type**, the **Customer**
  and the **Amount** already filled from the invoice. Step 5 shows exactly two
  lines — bank debited, receivables credited, for the same amount — and no
  difference. Step 7: the invoice has gone from the outstanding list, the receipt
  appears in **Receipts & payments** with **On account** empty, and the journal has
  a matching two-line entry recorded by you.
- **Actual Results & Calculation Explanation:** The receipt writes one balanced
  entry — debit the money account, credit Accounts Receivable — so the customer's
  receivable falls by exactly what the sale raised it by. **Paid and outstanding are
  not stored**: they are worked out from the allocations every time they are shown,
  which is why nothing can drift, and why reversing the receipt puts the invoice
  back to unpaid on its own. Settling in part is allowed and leaves the remainder
  visible; more than the invoice is worth is refused, and the refusal names the
  outstanding figure.

---

## Test Case 28 — Take a deposit before the invoice exists

- **User Persona:** **Admin** or **Accountant**.
- **Objective:** Record money received with no invoice to put it against, then
  apply it when the invoice arrives. This is the case that used to need a manual
  journal entry, and was invisible in the customer's balance.
- **Prerequisites:** Signed in as Admin. A customer record exists.
- **Steps:**
  1. Open **Receipts & Payments** and click **Receive money**.
  2. Choose the customer, set **Date** and **Amount** to `5000`, **Account** `1010`,
     and leave **Invoices this settles** empty.
  3. **Record** it.
  4. Look at the receipt in the **Receipts & payments** list.
  5. Sell something to that customer for less than 5,000 (Sales Entry), then come
     back to **Receipts & Payments**.
  6. Click **Apply** on the receipt, set the amount to the invoice's outstanding,
     and click **Apply**.
  7. Check **Outstanding invoices**.
- **Expected Behaviour:** In step 3 a green message says the money is held **on
  account**. Step 4 shows the full 5,000 under **On account** and nothing under
  **Settles**. In step 7 the invoice has been settled by the deposit, and the
  receipt's **On account** is down to whatever is left.
- **Actual Results & Calculation Explanation:** The receipt still posted the same
  balanced entry — bank debited, receivables credited — because the money really did
  arrive. What it did **not** do was claim an invoice, so the 5,000 is carried as a
  credit against that customer. Applying it later writes **no new journal entry**:
  the money already moved, and allocating only decides which invoice it clears. That
  is why a deposit shows in the customer's balance from the moment it is received
  rather than being parked somewhere until someone remembers it.

---

## A short checklist before you go live

1. **Configuration → Company details** — set and **Confirm** the name, address and
   phone.
2. **Configuration → VAT / AIT, TDS and VDS** — set the rates your tax adviser
   confirms, and confirm each row.
3. **Configuration → Payroll** — agree the salary components and deductions.
4. **Configuration → Posting controls** — decide whether reversals need a second
   person, and whether any year is **closed** (**Books closed through**). Leave it
   blank until you have reported a year.
5. **Configuration → Sales documents** — choose a plain receipt or a tax invoice.
6. **Security** — each user sets their own password, and turns on two-factor
   authentication if required.
7. **Roles & Access** — check the permission matrix matches the jobs people do,
   and **delete the five demo accounts** (`admin@rpci.demo` and the rest) once
   your own administrators exist and can sign in.
8. **Data** — import your workbook, or start fresh and begin entering.
9. **Backups** — set up the nightly `backup_db.py` run, keep the files off the
   machine that hosts the database, and **restore one into a scratch database** to
   prove it works.
10. **Try the two new guards once**, so you have seen them: close a period and be
    refused (Test Case 23), and lock an account and release it (Test Case 24).
11. **Item master** — add your real products under **Inventory & BOM**, or import
    your workbook, before the first purchase, production run or sale. Nothing can
    be bought, made or sold until its item exists.
12. **Customers & Suppliers** — if you have been trading already, press **Adopt
    existing names** to turn the names on your posted transactions into records in
    one step. Otherwise add your main customers and suppliers by hand. Sales and
    purchases pick from this list.
13. **Receipts & Payments** — decide who may record money (Admin and Accountant can
    by default; widen it per user if a cashier needs it), and confirm the **Accounts
    money moves through** setting lists every bank account you take money through.
    Then work through Test Cases 27 and 28 once, so you have seen an invoice settled
    and a deposit applied.

