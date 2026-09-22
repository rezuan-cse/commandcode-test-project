# Information Needed from RPCI

**For:** RPCI management
**About:** the accounting and production system being built for you

To finish the system we need a number of facts that only you can give us — mostly
tax rates and payroll rules. We have built the structure for all of it and left
the values empty on purpose. We will not guess a tax rate or a salary rule: if a
number is wrong, you are the one who has to file with it.

**How to use this document:** fill in the **Your answer** column. Where you are
unsure, write "check with our tax adviser" and we will follow up. The **Sample
answer** column shows the sort of answer we are looking for — it is an example,
not a recommendation, and it may not match your circumstances.

> **Important:** every sample in this document is illustrative only. None of it
> is tax advice. Your tax adviser should confirm the rates that apply to you.

---

## A. Company details

These are printed on the sales receipts the system produces.

| # | Question | Sample answer | Your answer |
|---|---|---|---|
| A1 | What is the company's registered or trading name? | RPCI Ltd | |
| A2 | What address should appear on a receipt? | 12 Gulshan Avenue, Dhaka 1212 | |
| A3 | What telephone number, if any? | +880 2 1234 5678 | |
| A4 | Are you registered for VAT? If so, what is the BIN? | Yes — BIN 001234567-0101 | |
| A5 | Do you have a TIN? | Yes — TIN 123456789012 | |

---

## B. VAT

| # | Question | Sample answer | Your answer |
|---|---|---|---|
| B1 | Do you charge VAT at all? | Yes | |
| B2 | What standard rate do you charge? | 15% | |
| B3 | Do any of your products carry a reduced, zero, or exempt rate? If so, which products and what rate? | Yes — one product is exempt | |
| B4 | Does VAT apply to all five segments (Import, Manufacturing, Packaging, Trading, Application), or only some? | Manufacturing, Packaging and Trading only | |
| B5 | Are the prices you agree with customers inclusive of VAT or exclusive? | Exclusive — VAT is added on top | |
| B6 | Is the input VAT you pay on purchases fully recoverable? | Yes, in full | |
| B7 | How often do you file a VAT return? | Monthly | |
| B8 | Roughly what share of your sales are to VAT-registered businesses? | About 60% | |

---

## C. AIT, TDS and VDS

These are all forms of tax withheld at source. We need to know which apply to you
and at what rates.

| # | Question | Sample answer | Your answer |
|---|---|---|---|
| C1 | When you import goods, is AIT collected at the import stage? At what rate? | Yes — 5% of assessable value | |
| C2 | On local purchases, do you deduct AIT from what you pay the supplier? At what rate? | Yes — 3% on supplies above 50,000 taka | |
| C3 | Do you deduct TDS from any payments — rent, professional fees, contractors, salaries? Which, and at what rates? | Yes — 10% on professional fees, 5% on rent | |
| C4 | Does VDS apply to you — VAT deducted at source on services? At what rate? | Yes — 7.5% of the VAT on services | |
| C5 | Is supplementary duty charged on any of your products? | No | |
| C6 | When a customer deducts tax from you before paying, do you need the system to record that? | Yes | |
| C7 | Who normally treats these as payable — you to the tax authority, or your customer? | Us, on purchases. Customers, on our sales. | |

---

## D. Payroll

| # | Question | Sample answer | Your answer |
|---|---|---|---|
| D1 | How often do you pay staff? | Monthly | |
| D2 | How many employees are there? | About 25 | |
| D3 | Which details do you keep about each employee? | Code, name, designation, department, joining date, bank account, mobile | |
| D4 | What are the parts of a salary — basic, house rent, medical, transport, dearness, anything else? | Basic, House Rent, Medical, Transport, Provident Fund | |
| D5 | What is a typical split? (as a percentage of gross, or an amount) | Basic 60%, House Rent 30%, Medical 5%, Transport 5% | |
| D6 | What is the payroll cycle — the 1st to the last day of the month, or something else? | Calendar month, paid on the 5th of the next month | |
| D7 | What deductions apply? | TDS on salaries, Provident Fund 10%, loan repayment | |
| D8 | Are there any statutory deductions you are required to make? | Provident Fund, salary TDS | |
| D9 | Do factory and office staff go to different accounts? | Yes, keep them separate | |
| D10 | How is production labour treated — as an expense of the period, or added to the cost of what you make? | Added to the cost of the goods produced | |
| D11 | How do you pay staff — bank transfer, cash, or both? | Bank transfer | |
| D12 | Do you need a printable payslip for each employee? | Yes | |
| D13 | Any gratuity, leave encashment, or other payments to be handled? | Gratuity after 5 years | |

---

## E. Permissions and controls

The specification lists which role may do what, but it does not cover payroll,
VAT, or who may undo a posting. We need you to decide these.

| # | Question | Sample answer | Your answer |
|---|---|---|---|
| E1 | Who should be able to see and run payroll? | Admin and Accountant | |
| E2 | Who should be able to see and change the VAT and tax settings? | Admin only | |
| E3 | Should reversing a posted transaction need a second person to approve it? | Yes, for sales over 100,000 taka | |
| E4 | When an administrator issues someone a new password, must that person change it when they next sign in? | Yes | |
| E5 | Should any posting need approval before it takes effect? If so, which? | Reversals only | |

---

## F. Loose questions

| # | Question | Sample answer | Your answer |
|---|---|---|---|
| F1 | Your hand-drawn list of modules goes 1 to 10, then 12, and 11 is missing. What was 11? | Inventory valuation report | |
| F2 | Do you need a VAT-compliant tax invoice (a Mushak-style document), or is a plain sales receipt enough? | A plain receipt is enough for now | |
| F3 | How many people will use the system, and should each have their own login? | 6 people, each with their own login | |
| F4 | Is there anything in your current spreadsheets that causes you regular difficulty, which you would like the system to fix? | Month-end stock reconciliation | |

---

## What we have assumed until you tell us otherwise

These are already built and working on the assumption shown. Tell us if any is
wrong and we will change it.

| Assumption | What we did |
|---|---|
| Currency and rounding | Everything in taka, to four decimal places; average costs to eight, so figures match your workbook exactly |
| VAT accounts | Output VAT to `2200 VAT Payable`, input VAT to `1130 VAT Current Account` |
| AIT and TDS accounts | `2220 AIT Payable` and `2210 TDS Payable` |
| Salary accounts | Office salaries to `6010`, factory labour to `5011`, sales commission to `6200` |
| Sales documents | A plain receipt showing the sale lines and total, marked as *not* a VAT invoice |
| Costing method | Weighted average, which is what your workbook already uses |
| Corrections | A wrong posting is reversed, never edited or deleted |

---

## Why some of this cannot wait

Two of these decide whether the next phase is useful at all:

- **B1 and B2** — without knowing whether you charge VAT and at what rate, we
  cannot make sales and purchases compute it. That is the whole of the next phase.
- **D1, D3, D4 and D7** — payroll cannot be built without knowing what a salary
  is made of and what is deducted from it.

Everything else can follow as we go.
