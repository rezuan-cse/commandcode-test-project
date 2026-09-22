# RPCI ERP — User Manual

This manual is written for everyday users. It explains what each screen does,
who is allowed to do what, and shows a complete example with real numbers you
can follow along with.

---

## 1. What this software does

It keeps the company's books and stock in one place.

You record what you buy, what you make, and what you sell. The software then:

- Works out the cost of your stock, automatically.
- Writes the accounting entries for you.
- Shows you reports like the Trial Balance and Balance Sheet.

You do not need to know accounting to use it. The software does the accounting
part. You just record what actually happened.

---

## 2. How to open it

Open a web browser. Go to the address your administrator gives you.

During the demo, the address is usually **http://localhost:8000**.

The software works on a laptop, a tablet, and a mobile phone. The screen adjusts
itself to fit.

### Signing in

The software asks for an email and password before it shows anything.

The sign-in screen lists the demo accounts, and clicking a row fills the form.
They all use the same password: **`rpci`**

| Email | Role |
|---|---|
| `admin@rpci.demo` | Admin |
| `accountant@rpci.demo` | Accountant |
| `store@rpci.demo` | Store / Production |
| `sales@rpci.demo` | Sales Staff |
| `owner@rpci.demo` | Owner / Viewer |

Signing in as different people is how you see the permission rules at work. What
you are allowed to do comes from the account you signed in with, and the server
checks it every time — not the screen.

To change who you are, press **Sign out** in the top right and sign in again.

### If your account has two-factor authentication

Some accounts are protected by a second step. After your password, you will be
asked for a six-digit code from an authenticator app on your phone.

You can use a recovery code instead if you do not have the phone with you. Those
codes are given to you once when two-factor is switched on — keep them somewhere
safe.

### The two date boxes

At the top of the screen there are two dates:

| Box | What it means |
|---|---|
| **Period from** | The report starts counting from this date |
| **As of** | The report counts up to this date |

Change these to look at any period you like. The demo starts with
**1 January 2026** to **31 October 2026**.

---

## 3. The one rule you cannot break

**Money that goes out must equal money that comes in.**

Every entry must balance. If you put 1,000 on one side, you must put 1,000 on the
other side.

The software checks this for you. If an entry does not balance, it will not be
saved. You will see a message instead.

This rule protects you. It means the books can never quietly go wrong.

---

## 4. Who can do what

There are five kinds of users. Each one sees and does different things.

| Role | What they are for |
|---|---|
| **Admin** | The manager. Can do everything. |
| **Accountant** | Keeps the accounts. Checks the numbers. |
| **Store/Production Staff** | Makes the goods. Handles stock. |
| **Sales Staff** | Sells the goods. |
| **Owner/Viewer** | Looks at reports. Cannot change anything. |

### The detail

Yes = allowed. No = blocked.

| Action | Admin | Accountant | Store / Production | Sales | Owner / Viewer |
|---|---|---|---|---|---|
| See Chart of Accounts | Yes | Yes | **No** | **No** | Yes |
| See Journal Entries | Yes | Yes | **No** | **No** | Yes |
| Add a Journal Entry | Yes | Yes | **No** | **No** | **No** |
| See Items and BOM | Yes | Yes | Yes | Yes | Yes |
| Do a Purchase | Yes | **No** | **No** | Yes | **No** |
| Do a Production | Yes | **No** | Yes | **No** | **No** |
| Do a Sale | Yes | **No** | **No** | Yes | **No** |
| See Reports | Yes | Yes | Yes | Yes | Yes |
| Change Settings | Yes | **No** | **No** | **No** | **No** |

### Two things to check with the client

1. **Store staff cannot do purchases.** They can record production, but they
   cannot record buying materials. This follows the permission table in the
   specification, where "Sales/Purchase Entry" is one combined permission. If the
   store keeper should also be able to buy, this needs to be changed.

2. **Sales staff can do purchases.** For the same reason, the permission for
   purchases and sales is shared.

### How the restrictions appear

**Screens you may not read are not in the menu.** Signed in as Store staff, you
will not see Chart of Accounts or Journal Entries at all.

**Screens you may read but not change open without their form.** Purchase Entry,
Production Entry and Sales Entry are like this for an Accountant: the screen
opens, the list of what has already been posted is there, and the form for adding
something new is replaced by a short note explaining the position. There is
nothing to fill in that cannot be submitted.

If you reach a screen you are not allowed to see — by typing its address, for
example — you get a plain explanation rather than an error.

**The menu is not the security.** Your permissions travel with your signed-in
session, and the server checks them on every request. Nobody can reach a screen
by typing its address, and nobody can grant themselves access by changing what
the browser sends.

---

## 5. The screens at a glance

The menu on the left is grouped into five parts.

**Overview**
- **Dashboard** — the main numbers on one page.

**Ledger**
- **Chart of Accounts** — the list of all accounts.
- **Journal Entries** — every voucher the system has recorded.

**Operations**
- **Inventory & BOM** — stock, costs, and the recipe for each product.
- **Purchase Entry** — buying materials.
- **Production Entry** — making goods.
- **Sales Entry** — selling goods.

**Reports**
- **Trial Balance** — every account balance on one page.
- **General Ledger** — the full detail, account by account.
- **Balance Sheet** — what the company owns and owes.

**Administration**
- **Roles & Access** — who can do what.
- **Security** — your password and two-factor authentication.
- **Configuration** — settings like VAT rates.

---

## 6. Screen-by-screen guide

### 6.1 Dashboard

This is the first screen. It shows the health of the business at a glance.

**Top right — Reset demo data:**

A button in the top right of the page. Press it to put everything back to the
original workbook figures. Anything you have entered is removed, and the demo
looks exactly as it did the first time you opened it.

Nothing is permanently lost by exploring. If you are unsure whether something on
screen is your doing or the original data, press this and start again.

Only an **Admin** can press it, because it erases everyone's entries.

**Top row — five boxes:**
Revenue, COGS, Gross profit, Gross margin, and Net profit.

COGS means "cost of goods sold" — what the goods you sold originally cost you.
Gross profit is revenue minus COGS.

**Middle — Profit & loss by segment:**

One row for each part of the business: Import, Manufacturing, Packaging,
Trading, and Application. You can see which part is making money and which is not.

**Bottom left — Position at a glance:**

Total assets, total liabilities, owner's equity, and current period profit.

**Bottom right — Data integrity:**

This is the most important box on the screen. It runs four checks:

| Check | What it proves |
|---|---|
| Journal entries balance | Debits equal credits |
| Trial balance nets to zero | Nothing has gone missing |
| Balance sheet balances | What you own equals what you owe plus what is yours |
| GL inventory equals stock ledger | The accounts and the stock sheet agree |

The first three should always say ✓. If any of them fails, something is wrong and
you should tell your accountant.

The fourth one is different. It compares your accounting records with your stock
records. **In the demo, this one shows a warning.** That is not a fault in the
software — it is a real problem in the original spreadsheet. See section 9.

---

### 6.2 Chart of Accounts

This screen lists every account in the company. The demo has 89 accounts.

Each account has:

| Field | Meaning | Example |
|---|---|---|
| Code | The account number | `1210` |
| Account name | The name | `Inventory - Raw Materials` |
| Type | What kind of account it is | Asset |
| Segment | Which part of the business | Manufacturing |
| Normal balance | Which side it grows on | Dr |

**You can filter** using the three boxes at the top:

- **Segment** — show only one part of the business.
- **Type** — show only assets, or only expenses, and so on.
- **Search** — type a code or a name.

**Who can use it:** Admin, Accountant, and Owner can see it. Store and Sales staff
cannot.

**Note:** In the demo this screen is for looking only. There is no button to add a
new account. All other screens pick accounts from this list — you can never type a
free account name anywhere.

---

### 6.3 Journal Entries

This screen shows every voucher in the system.

A voucher is one complete accounting entry. It can have two lines or twenty.

Each voucher box shows:

- The voucher number and date
- A badge telling you where it came from:
  - **Manual** — typed by a person
  - **Production** — made automatically when goods were produced
  - **Sales** — made automatically when goods were sold
  - **Purchase** — made automatically when goods were bought
- A green **balanced** badge

Press **Show lines** to see the detail.

**Example of what you will see:**

```
PROD-004 · 2026-10-20                        [Production] [balanced]
Production Order PROD-004: TRD-018 output

Account                          Segment        Debit      Credit
1230 Inventory - Finished Goods  Manufacturing  3,368.60       —
1210 Inventory - Raw Materials   Manufacturing       —     2,818.60
1240 Inventory - Packaging       Packaging           —        50.00
1010 Bank Account - Main         Shared              —       500.00
                                        Total   3,368.60   3,368.60
```

Notice the two totals are the same. That is what "balanced" means.

**Who can use it:** Admin, Accountant, and Owner can see it. Store and Sales staff
cannot.

**Who can add one:** Admin and Accountant. (In the demo there is no button for it
on this screen — it would be added in the full version.)

---

### 6.4 Inventory & BOM

This screen has two parts.

**Part 1 — the stock list**

Every item the company holds, with:

| Column | Meaning |
|---|---|
| Code | The item code, e.g. `RMC-003` |
| Item | The item name, e.g. `Elephent Cement` |
| Category | Raw Material, WIP, Finished Good, Packaging, or Trading Stock |
| Qty on hand | How much you have |
| Avg cost | What one unit cost you on average |
| Value | Quantity × average cost |

**Qty on hand and average cost are calculated.** You cannot type them. They come
from the record of every movement in and out.

This is important. In a spreadsheet, someone can type a wrong number and nobody
notices. Here the number is always the result of the movements.

**Part 2 — open one item**

Press the **Ledger** button on any row. You will see:

- Every movement for that item, oldest first
- Quantity in and out, with the value
- The running balance after each movement
- The average cost at each point

**BOM explosion**

At the bottom of the item detail you can explode a Bill of Materials.

A Bill of Materials (BOM) is a recipe. It says: to make one TRD-018, you need
6 kg of RMC-001, 1 kg of RMC-002, 4.2 kg of RMC-003, and so on.

Type a quantity and press **Explode BOM**. The software shows the full shopping
list. If a component is itself something you make, it opens that up too, all the
way down to the raw materials you buy.

*Example:* explode `TRD-018` for **50**. It shows you need **210 kg** of Elephent
Cement. That is the same number written in the client's own Production Entry sheet.

**Who can use it:** everyone except Store and Sales staff cannot see the accounts,
but all five roles can see items.

---

### 6.5 Purchase Entry

Use this screen when you buy materials from a supplier.

**The boxes at the top:**

| Box | What to put | Example |
|---|---|---|
| Supplier | Who you bought from | `Rahman Traders` |
| Purchase date | The date on the bill | `2026-10-18` |
| Settlement | On credit or paid now | On credit |

- **On credit** means the supplier will be paid later. The software records a
  payable.
- **Paid immediately** means the money left the bank.

**The lines:**

Press **Add line** for each item. For every line choose the item, the quantity,
and the unit cost. The line value is worked out for you.

**Shortcut button:** press **Load TRD-018 requirements**. This fills the grid with
everything needed to make 50 units of TRD-018. Change the quantities and prices to
match your real bill. (If an item has no cost yet, the box shows 20 — replace it
with your real price.)

**What happens when you post:**

1. Stock goes up for each item.
2. The average cost is recalculated for each item.
3. A balanced journal entry is written automatically.

**Worked example:** see section 7.

**Who can use it:** Admin and Sales staff.

---

### 6.6 Production Entry

Use this screen when you make goods.

**The boxes at the top:**

| Box | What to put | Example |
|---|---|---|
| Item to produce | What you are making | `TRD-018` |
| Quantity produced | How many you made | `10` |
| Production date | The date you finished | `2026-10-20` |
| Labor cost | Wages for this run | `500` |
| Overhead cost | Power, machine time | `0` |

**The components list:**

You do not type these. The software reads the recipe (BOM) and fills them in,
scaled to the quantity you are making.

If you made more or less than the recipe expects, you can type over the quantity.

Each line shows:
- How much is needed
- How much you have on hand
- A green **ok** badge, or a red **short** badge if you do not have enough

If anything is short, the Post button is disabled. You must buy the material
first.

**The two boxes at the bottom:**

**Cost build-up** shows you the arithmetic:

```
Material cost          2,868.60
Labor                    500.00
Overhead                   0.00
───────────────────────────────
Total production cost  3,368.60
Quantity produced           10
───────────────────────────────
Unit cost of output      336.8605
```

**Journal entry it will post** shows the accounting entry before you commit to it,
with a green banner confirming it is balanced.

**The Post button**

Press **Post production** to save. The software does all of this at once:

1. Takes the components out of stock at their average cost.
2. Adds up material, labour, and overhead.
3. Divides by the quantity to get the unit cost.
4. Puts the finished goods into stock at that cost.
5. Writes the balanced journal entry.

If any one of these five steps fails, **none of them happen.** Your stock and your
books stay exactly as they were.

**Try it yourself:** tick the box **"Inject a failure mid-transaction"** and press
Post. You will see an error, and the numbers will not change. Untick it and post
again to see it work. This is how you know the records can never end up half-done.

**A limitation to know about:** this screen needs an item to have a recipe (BOM).
In the demo data, only `TRD-018` has one. If you choose an item with no recipe,
there will be no components and the Post button will stay disabled.

**Who can use it:** Admin and Store/Production staff.

---

### 6.7 Sales Entry

Use this screen when you sell goods.

**The boxes at the top:**

| Box | What to put | Example |
|---|---|---|
| Customer | Who bought | `Karim Enterprise` |
| Sale date | Date of sale | `2026-10-25` |

**The lines:**

Choose the item, the quantity, and the sale price you charged.

When you pick an item, the sale price box fills in with that item's average cost
— what it cost you. Change it to the price you are actually charging. This way
you are never left with a price from a different product.

The screen shows you, for each line:
- How much you have on hand
- The average cost of the item
- A red **short** badge if you are selling more than you have
- A red **below cost** badge if your price is lower than the cost

You cannot sell stock you do not have. The Post button is disabled if any line is
short.

**If you price something below cost**

The software will not stop you. Selling at a loss is sometimes the right thing to
do — clearing old stock, for example. But it will tell you plainly, in a yellow
box under the form:

> TRD-018 is priced below cost (5 against a cost of 336.86047000), a loss of
> 1327.4419 on this line

Check your price before posting when you see this. If the loss is not what you
intended, the price box usually still holds a value from the item you selected
before.

**The two boxes at the bottom:**

**Revenue and margin** shows:

```
Revenue                          2,400.00
Cost of goods sold (at avg cost) 1,347.44
──────────────────────────────────────────
Gross profit                     1,052.56
Gross margin                       43.86%
```

**Journal entry it will post** shows both halves of the accounting entry — the
sales side and the cost side — in one balanced entry.

**What happens when you post:**

1. Stock goes down at the average cost.
2. The sale is recorded as income.
3. The cost of what you sold is recorded as an expense.
4. Both go into one balanced journal entry.

**Who can use it:** Admin and Sales staff.

---

### 6.8 Trial Balance

A list of every account that has a balance, as of the date you chose.

**The important line is the last one:**

```
Difference — must be zero        0.00
```

If this is zero, your books are sound. If it is not zero, something is wrong.

**Who can use it:** everyone.

---

### 6.9 General Ledger

The same idea, but with more detail. For each account you see:

| Column | Meaning |
|---|---|
| Opening Dr / Cr | The balance it started the period with |
| Period Dr / Cr | What moved during the period |
| Closing Dr / Cr | The balance at the end |

This is the screen your accountant will use most.

**Who can use it:** everyone.

---

### 6.10 Balance Sheet

What the company owns, what it owes, and what belongs to the owners.

Three sections:

- **Assets** — what the company owns (cash, stock, machines).
- **Liabilities** — what the company owes (supplier bills, loans).
- **Equity** — what is left for the owners.

At the bottom there is a check line:

```
Check: assets − liabilities − equity — must be zero      0.00
```

It will always be zero. If it is ever not zero, something has gone badly wrong.

**Who can use it:** everyone.

---

### 6.11 Roles & Access

This screen shows the permission table from section 4.

It also has a **Live permission probe**. Press the button and the screen calls the
server as whoever you are currently acting as.

- If you are Admin, Accountant, or Owner, you will see a green message.
- If you are Store or Sales staff, you will see a red message with the word
  `403`.

403 is the standard code for "you are not allowed". Seeing it proves the block is
real.

Try it: sign out, sign in as **`sales@rpci.demo`**. The Ledger menu is gone,
because that role may not read the accounts. Then sign in as
**`accountant@rpci.demo`** and open Purchase Entry — the screen opens for reading,
with the form replaced by a note explaining that the role cannot post.

---

### 6.12 Security

Your own account. Three things live here.

**Two-factor authentication.** A second step at sign-in, using an authenticator
app on your phone. Press **Set up two-factor authentication**, scan the QR code
with the app, then type the six-digit code it shows. That last step matters: the
app has to prove it works before the protection is switched on, so you cannot
lock yourself out by accident.

When it is on you are given **eight recovery codes**. They are shown once.
Print them or save them somewhere safe — they are the only way back in if you
lose your phone.

To turn it off, you must type your password again. Being signed in is not enough,
in case someone finds your laptop unlocked.

**Change password.** Type your current password, then the new one. At least eight
characters.

---

### 6.13 Configuration

This screen holds the settings that the client has not yet decided.

Each setting shows a badge:

- **pending client** — not confirmed yet. The value shown is a sensible default.
- **confirmed** — agreed.

Examples: VAT rate, tax rates, payroll frequency, and whether a second person must
approve postings.

Nothing here is fixed in the code. When the client decides, the value is changed
here and takes effect immediately.

---

## 7. A full example, step by step

Follow this from a fresh demo. Every number below is real — you will see exactly
these figures.

We will buy materials, make 10 units, and sell 4.

---

### Step 1 — Buy the materials

Go to **Purchase Entry**. Fill in:

- Supplier: `Rahman Traders`
- Purchase date: `2026-10-18`
- Settlement: `On credit`

Press **Add line** until you have six lines, and enter:

| Item | Quantity | Unit cost | Line value |
|---|---|---|---|
| RMC-001 Sand 30/80 | 400 | 10 | 4,000.00 |
| RMC-002 Lime 200 | 100 | 20 | 2,000.00 |
| RMC-003 Elephent Cement | 500 | 30 | 15,000.00 |
| RMC-004 H.Lime | 150 | 10 | 1,500.00 |
| RMCD-005 T2 C/D | 100 | 50 | 5,000.00 |
| PKC-026 Filler Bag C Printed | 100 | 5 | 500.00 |
| | | **Total** | **28,000.00** |

Press **Post purchase**.

**Result:** voucher `PUR-001`, total 28,000.00, balanced.

**The journal entry created:**

```
1210 Inventory - Raw Materials        Dr   4,000.00
1210 Inventory - Raw Materials        Dr   2,000.00
1210 Inventory - Raw Materials        Dr  15,000.00
1210 Inventory - Raw Materials        Dr   1,500.00
1210 Inventory - Raw Materials        Dr   5,000.00
1240 Inventory - Packaging Materials  Dr     500.00
2010 Accounts Payable - Local         Cr  28,000.00
                            Total     Dr  28,000.00  =  Cr  28,000.00
```

In plain words: the stock went up by 28,000, and we owe the supplier 28,000.

**One thing to notice.** Look at Elephent Cement's average cost. Before the
purchase it was **32.27848101**. After buying 500 kg at 30, it becomes **31.3953**.

Why? Because it now blends the old stock with the new:

```
Old:  790 kg costing 25,500
New:  500 kg costing 15,000
All: 1,290 kg costing 40,500
40,500 ÷ 1,290 = 31.39534884 per kg
```

The software does this for you every time. You never have to work it out.

---

### Step 2 — Make 10 units

Go to **Production Entry**. Fill in:

- Item to produce: `TRD-018 NovaCrete PU-MF-C-Filler`
- Quantity produced: `10`
- Production date: `2026-10-20`
- Labor cost: `500`
- Overhead cost: `0`

The components fill in by themselves from the recipe:

| Component | Needed | Avg cost | Cost |
|---|---|---|---|
| RMC-001 Sand 30/80 | 60 | 10.00000000 | 600.00 |
| RMC-002 Lime 200 | 10 | 20.00000000 | 200.00 |
| RMC-003 Elephent Cement | 42 | 31.39534884 | 1,318.60 |
| RMC-004 H.Lime | 20 | 10.00000000 | 200.00 |
| RMCD-005 T2 C/D | 10 | 50.00000000 | 500.00 |
| PKC-026 Filler Bag C Printed | 10 | 5.00000000 | 50.00 |
| | | **Material** | **2,868.60** |

Where does "60" come from? The recipe needs 6 kg of RMC-001 per unit, and we are
making 10 units. So 6 × 10 = 60.

Press **Post production**.

**Result:** voucher `PROD-004`, balanced.

**The cost build-up:**

```
Material cost          2,868.60
Labor                    500.00
Overhead                   0.00
───────────────────────────────
Total production cost  3,368.60
Quantity produced            10
───────────────────────────────
Unit cost of output      336.8605
```

3,368.60 ÷ 10 = 336.8605 per unit. Each unit now sits in stock at that cost.

**The journal entry created:**

```
1230 Inventory - Finished Goods       Dr   3,368.60
1210 Inventory - Raw Materials        Cr   2,818.60
1240 Inventory - Packaging Materials  Cr      50.00
1010 Bank Account - Main              Cr     500.00
                            Total     Dr   3,368.60  =  Cr   3,368.60
```

In plain words: the finished goods are now worth 3,368.60. The raw materials went
down by 2,818.60, the packaging by 50, and we paid 500 in wages.

---

### Step 3 — Sell 4 units

Go to **Sales Entry**. Fill in:

- Customer: `Karim Enterprise`
- Sale date: `2026-10-25`

One line:

| Item | Quantity | Sale price |
|---|---|---|
| TRD-018 | 4 | 600 |

Press **Post sale**.

**Result:** voucher `SALE-002`, balanced.

**Revenue and margin:**

```
Revenue                          2,400.00
Cost of goods sold (at avg cost) 1,347.44
──────────────────────────────────────────
Gross profit                     1,052.56
Gross margin                       43.86%
```

4 × 600 = 2,400 in sales. 4 × 336.8605 = 1,347.44 in cost. Profit: 1,052.56.

**The journal entry created:**

```
1100 Accounts Receivable - Local      Dr   2,400.00
4030 Trading Sales                    Cr   2,400.00
5030 COGS - Trading                   Dr   1,347.44
1230 Inventory - Finished Goods       Cr   1,347.44
                            Total     Dr   3,747.44  =  Cr   3,747.44
```

Notice this one entry contains two things at once: the sale (first two lines) and
the cost of the sale (last two lines). That is why the total is 3,747.44 and not
2,400.

---

### Step 4 — Check the results

All three steps are done. Now look at what changed. The figures are spread over
three screens, so this last step says which screen to open.

**On the Dashboard:**

| What | Value | Why |
|---|---|---|
| Manufacturing profit | 1,600.00 | Unchanged — this came from the original workbook data |
| Trading profit | 1,052.56 | Your sale: 2,400.00 revenue less 1,347.44 cost |
| Net profit | 2,652.56 | 1,600.00 + 1,052.56 |
| Total assets | 830,652.56 | Up from 801,600.00 — see the note below |
| Total liabilities | 28,000.00 | The purchase was on credit, so you now owe the supplier |
| Balance sheet check | 0.00 | Still balanced |

**On Inventory & BOM** (search for `TRD-018`):

| What | Value | Why |
|---|---|---|
| Quantity on hand | 6 | 10 made, 4 sold |
| Average cost | 336.86046667 | The unit cost worked out in step 2 |

**On Trial Balance** (Reports → Trial Balance):

| What | Value | Why |
|---|---|---|
| Difference | 0.00 | The books still net to zero |

**Why total assets rose by more than the profit**

Total assets went from 801,600.00 to 830,652.56, an increase of 29,052.56. That
is more than the profit, and it is worth understanding why. It is two things:

- **28,000.00 of new stock**, bought in step 1. The goods arrived, so an asset
  went up.
- **1,052.56 of profit** from the sale in step 3.

The purchase was on credit. That is why total liabilities now read 28,000.00:
you gained the stock, and you owe the supplier for it. Both sides moved together,
which is why the balance sheet still balances:

```
Assets 830,652.56  =  Liabilities 28,000.00  +  Equity 802,652.56
```

Equity is the 800,000.00 you started with, plus the 2,652.56 of profit.

Everything adds up, and the books are still sound after all three transactions.
That is the whole point of the system.

---

## 8. What the system will not let you do

The software actively blocks these. You will see an error message, not a silent
mistake.

| You try to | What happens |
|---|---|
| Save an entry where debits do not equal credits | Refused |
| Sell more than you have in stock | Refused |
| Use a material in production that you do not have | Refused, and it lists which ones |
| Use the same voucher number twice | Refused |
| Open a screen your role does not allow | You see an error saying you do not have access |
| Post something that fails halfway | The whole thing is undone. Nothing is saved. |

---

## 9. When something looks wrong

### "The dashboard shows a warning about inventory"

This is expected in the demo, and it is worth understanding.

The fourth integrity check says:

```
General Ledger inventory equals stock ledger value
GL inventory 301400 vs stock ledger 775500 (variance -474100)
```

It means: the stock sheet says there is 775,500 of stock, but the accounts only
show 301,400. There is a gap of 474,100.

Those two figures change as you buy and sell, so you may see different ones from
the example above. **The 474,100 gap between them does not change** — that is the
size of the problem in the workbook, and it stays put.

This is **not a fault in the software**. It is a real problem in the original
spreadsheet.

Here is why. In the client's workbook, the Inventory Ledger is only a note sheet.
The Instructions tab says so. It tracks quantities and costs, but it never writes
any accounting entries.

So stock exists on the stock sheet with nothing to match it in the accounts. Two
examples:

- Resin A shows 500 kg at 1,500 = 750,000 in the stock sheet. The accounts only
  carry 90,000 of raw materials.
- Elephent Cement records 7,000 for a 210 kg issue. The workbook's own
  "suggested value" column says it should be 6,825. Someone typed a different
  number.

The new software cannot make this mistake, because every stock movement writes its
accounting entry at the same moment, in the same transaction. That is exactly the
kind of error this system removes.

**What to do:** show this to the client. It is a real finding, not a bug.

### "I cannot see a screen my colleague can see"

Check which account you are signed in as — it is shown in the top right. You may
be signed in as the wrong person, in which case sign out and sign in again.

Then check section 4. Your role may simply not be allowed.

### "The Post button is greyed out"

Look for the red **short** badges, or the warning message. Usually it means you do
not have enough stock. Buy the material first, then try again.

On Production Entry, it can also mean the item has no recipe (BOM).

### "I want to start over"

Press **Reset demo data** on the Dashboard. Everything goes back to the original
workbook figures and anything you entered is removed.

If you are running the software yourself on your own computer, and it is keeping
its data in a file, you can instead delete the `rpci_demo.db` file in the project
folder and restart. On a hosted copy there is no file for you to delete — use the
button.

---

## 10. Words we use

| Word | Simple meaning |
|---|---|
| **Account** | A named bucket for money, e.g. "Inventory - Raw Materials". |
| **Debit (Dr)** | The left side of an entry. |
| **Credit (Cr)** | The right side of an entry. |
| **Journal entry** | One complete accounting record. Also called a voucher. |
| **Voucher** | Same as a journal entry. |
| **Balanced** | Debits equal credits. |
| **Trial balance** | A list of all account balances. It must add up to zero. |
| **Balance sheet** | What you own, what you owe, and what is yours. |
| **COGS** | Cost of goods sold. What the sold items cost you. |
| **Gross profit** | Sales minus COGS. |
| **Segment** | A part of the business: Import, Manufacturing, Packaging, Trading, Application. |
| **Item** | Anything you keep in stock. |
| **BOM** | Bill of Materials. The recipe for making an item. |
| **Average cost** | What one unit cost you on average, across all your purchases. |
| **Stock ledger** | The list of every movement in and out of stock. |
| **Post** | To save something permanently. |
| **Rollback** | Undoing everything when part of a job fails. |
| **403** | The server's way of saying "not allowed". |

---

## 11. Quick reference

| I want to... | Go to | Who can |
|---|---|---|
| See how the business is doing | Dashboard | Everyone |
| Find an account | Chart of Accounts | Admin, Accountant, Owner |
| See a voucher | Journal Entries | Admin, Accountant, Owner |
| Check what is in stock | Inventory & BOM | Everyone |
| See a shopping list for a product | Inventory & BOM → Explode BOM | Everyone |
| Buy materials | Purchase Entry | Admin, Sales Staff |
| Make goods | Production Entry | Admin, Store/Production Staff |
| Sell goods | Sales Entry | Admin, Sales Staff |
| Check the books add up | Reports → Trial Balance | Everyone |
| See account detail | Reports → General Ledger | Everyone |
| See the company position | Reports → Balance Sheet | Everyone |
| Test permissions | Roles & Access | Everyone |
| Set up two-factor or change password | Security | Everyone (your own account) |
| See what is still undecided | Configuration | Everyone |
