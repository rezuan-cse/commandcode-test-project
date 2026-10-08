"""The catalogue of configurable rules.

Every fact the system needs from the client lives here as a :class:`SettingSpec`:
its key, how it is named and grouped in the interface, what kind of value it holds,
its default, and whether the client has confirmed it. The *values* live in the
`settings` table; this is the shape they must take.

Nothing a client has not confirmed is hardcoded. A rate that is wrong is a rate the
client has to file with, so the default is a clearly-labelled placeholder and the
interface shows it as *pending client* until someone confirms it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SettingSpec:
    """One configurable rule."""

    key: str
    label: str
    group: str
    value_type: str  # string | number | bool | enum | json
    default: object
    description: str
    options: list[str] | None = None
    # Pre-confirmed from the client's answers, so the interface shows it as
    # settled rather than pending. Only the answers the client actually gave.
    confirmed: bool = False
    sort_order: int = 0


ALL_SEGMENTS = [
    "Import",
    "Manufacturing",
    "Packaging",
    "Trading",
    "Application",
    "Shared",
]

# Order and heading text for the Configuration screen.
GROUP_ORDER: list[str] = [
    "company",
    "vat",
    "tax",
    "payroll",
    "posting",
    "security",
    "inventory",
    "sales",
]

GROUP_TITLES: dict[str, str] = {
    "company": "Company details",
    "vat": "VAT",
    "tax": "AIT, TDS and VDS",
    "payroll": "Payroll",
    "posting": "Posting controls",
    "security": "Security",
    "inventory": "Inventory",
    "sales": "Sales documents",
}

GROUP_NOTES: dict[str, str] = {
    "company": "Printed on the documents the system produces.",
    "vat": "Rate and scope. Left off until the client confirms the rules.",
    "tax": "Withholding rates. Pending the client's tax adviser.",
    "payroll": "Salary structure and deductions, editable without a redeploy.",
    "posting": "Whether a second person must approve an action before it commits.",
    "security": "Login hardening options.",
    "inventory": "Costing method used by the stock ledger.",
    "sales": "What a sales document looks like.",
}


def _specs() -> list[SettingSpec]:
    """Build the catalogue. Kept as a function so the list reads top-to-bottom."""
    return [
        # --- Company details (confirmed from the client's answers) -----------
        SettingSpec("company.name", "Company name", "company", "string",
                    "Resinova Bangladesh", "Registered company name on documents.",
                    confirmed=True, sort_order=10),
        SettingSpec("company.address", "Address", "company", "string",
                    "10, Shanti Niketon, Road-05, Block-D, Sector-02, Aftabnagar, "
                    "Badda, Dhaka-1212", "Address printed on receipts.",
                    confirmed=True, sort_order=20),
        SettingSpec("company.phone", "Telephone", "company", "string",
                    "+880 1735-536678", "Contact number printed on receipts.",
                    confirmed=True, sort_order=30),
        SettingSpec("company.currency", "Currency", "company", "string",
                    "BDT", "Currency the books are kept in.", sort_order=40),
        SettingSpec("company.vat_reg_no", "VAT registration (BIN)", "company",
                    "string", "002016027-0208",
                    "VAT registration number. Printed on tax invoices and used on "
                    "the Mushak returns.", confirmed=True, sort_order=50),
        SettingSpec("company.tin", "TIN", "company", "string", "155979113247",
                    "Tax identification number.", confirmed=True, sort_order=60),

        # --- VAT -------------------------------------------------------------
        SettingSpec("vat.charge_vat", "Charge VAT", "vat", "bool", False,
                    "Whether the system adds VAT to sales and purchases. "
                    "TBD (client).", sort_order=10),
        SettingSpec("vat.standard_rate_pct", "Standard rate (%)", "vat", "number",
                    15, "Standard VAT rate. TBD (client).", sort_order=20),
        SettingSpec("vat.prices_include_vat", "Prices include VAT", "vat", "bool",
                    False, "Whether agreed prices already contain VAT. TBD "
                    "(client).", sort_order=30),
        SettingSpec("vat.input_recoverable", "Input VAT recoverable", "vat", "bool",
                    True, "Whether VAT paid on purchases is recoverable in full. "
                    "TBD (client).", sort_order=40),
        SettingSpec("vat.applies_to_segments", "Segments VAT applies to", "vat",
                    "json", ALL_SEGMENTS, "Which segments carry VAT. TBD (client).",
                    sort_order=50),
        SettingSpec("vat.return_frequency", "Return frequency", "vat", "enum",
                    "monthly", "How often a VAT return is filed. TBD (client).",
                    options=["monthly", "quarterly", "yearly"], sort_order=60),
        SettingSpec("vat.zero_rated_items", "Zero-rated or exempt items", "vat",
                    "json", [], "Item codes carrying a reduced, zero or exempt "
                    "rate. TBD (client).", sort_order=70),
        SettingSpec("vat.input_account", "Input VAT account", "vat", "string",
                    "1130", "Input VAT tracking account.", sort_order=80),
        SettingSpec("vat.output_account", "Output VAT account", "vat", "string",
                    "2200", "Output VAT tracking account.", sort_order=90),

        # --- AIT, TDS and VDS ------------------------------------------------
        SettingSpec("tax.ait_rate_pct", "AIT rate (%)", "tax", "number", 5,
                    "Advance income tax rate. TBD (client).", sort_order=10),
        SettingSpec("tax.tds_rate_pct", "TDS rate (%)", "tax", "number", 5,
                    "Tax deducted at source rate. TBD (client).", sort_order=20),
        SettingSpec("tax.vds_rate_pct", "VDS rate (%)", "tax", "number", 0,
                    "VAT deducted at source on services. TBD (client).",
                    sort_order=30),
        SettingSpec("tax.supplementary_duty_pct", "Supplementary duty (%)", "tax",
                    "number", 0, "Supplementary duty on any product. TBD (client).",
                    sort_order=40),
        SettingSpec("tax.ait_account", "AIT payable account", "tax", "string",
                    "2220", "Account AIT is credited to.", sort_order=50),
        SettingSpec("tax.tds_account", "TDS payable account", "tax", "string",
                    "2210", "Account TDS is credited to.", sort_order=60),
        SettingSpec("tax.vds_account", "VDS payable account", "tax", "string",
                    "2200", "Account VDS is credited to.", sort_order=70),

        # --- Payroll ---------------------------------------------------------
        SettingSpec("payroll.pay_frequency", "Pay frequency", "payroll", "enum",
                    "monthly", "How often staff are paid.",
                    options=["monthly", "fortnightly", "weekly"], confirmed=True,
                    sort_order=10),
        SettingSpec("payroll.pay_day", "Pay day of month", "payroll", "number", 5,
                    "Day of the next month staff are paid.", confirmed=True,
                    sort_order=20),
        SettingSpec("payroll.cycle", "Payroll cycle", "payroll", "string",
                    "calendar_month_paid_5th",
                    "Calendar month, paid on the 5th of the next month.",
                    confirmed=True, sort_order=30),
        SettingSpec("payroll.employee_fields", "Employee details kept", "payroll",
                    "json",
                    ["Code", "Name", "Personal Email", "Designation", "Department",
                     "Joining Date", "Bank Account", "Mobile"],
                    "The details held about each employee.", confirmed=True,
                    sort_order=40),
        SettingSpec("payroll.salary_components", "Salary components", "payroll",
                    "json",
                    [
                        {"name": "Basic", "pct": 60},
                        {"name": "House Rent", "pct": 30},
                        {"name": "Medical", "pct": 5},
                        {"name": "Transport", "pct": 5},
                    ],
                    "Parts of a salary and their share of gross, as a percentage.",
                    confirmed=True, sort_order=50),
        SettingSpec("payroll.deductions", "Deductions", "payroll", "json", [],
                    "Deductions applied to gross pay, each with a name, account "
                    "and percentage. TBD (client).", sort_order=60),
        SettingSpec("payroll.statutory_deduction_pct",
                    "Statutory deduction (%)", "payroll", "number", 10,
                    "Statutory deduction percentage. TBD (client).", sort_order=70),
        SettingSpec("payroll.departments", "Departments", "payroll", "json",
                    [{"name": "Office", "salary_account": "6010"},
                     {"name": "Factory", "salary_account": "5011"}],
                    "Departments employees can belong to, each with the "
                    "account its salaries are charged to. Shown as the "
                    "Department dropdown on the employee form.",
                    confirmed=True, sort_order=74),
        SettingSpec("payroll.designations", "Designations", "payroll", "json",
                    ["General Manager", "Accounts Officer", "Machine Operator",
                     "Store Keeper", "Helper", "Sales Executive"],
                    "Job titles offered as the Designation dropdown on the "
                    "employee form.", confirmed=True, sort_order=76),
        SettingSpec("payroll.commission_account", "Sales commission account",
                    "payroll", "string", "6200",
                    "Account sales commission is charged to.", sort_order=100),
        SettingSpec("payroll.payslip_required", "Printable payslips", "payroll",
                    "bool", True, "Whether a printable payslip is produced per "
                    "employee.", confirmed=True, sort_order=110),

        # --- Posting controls ------------------------------------------------
        SettingSpec("posting.require_second_approval", "Require second approval",
                    "posting", "bool", False,
                    "Whether an action needs a second person. TBD (client).",
                    sort_order=10),
        SettingSpec("posting.approval_threshold", "Approval threshold", "posting",
                    "number", 0,
                    "Only actions at or above this amount need approval; 0 means "
                    "all. TBD (client).", sort_order=20),
        SettingSpec("posting.approval_scope", "Actions needing approval",
                    "posting", "enum", "reversals",
                    "Which actions need approval. TBD (client).",
                    options=["reversals", "reversals_and_postings"], sort_order=30),
        SettingSpec("posting.books_closed_through", "Books closed through",
                    "posting", "string", "",
                    "No transaction may be dated on or before this date, which is "
                    "what keeps a closed year closed. Blank means the books are "
                    "open. Use YYYY-MM-DD, e.g. 2026-06-30.", sort_order=40),
        SettingSpec("payments.money_accounts", "Accounts money moves through",
                    "posting", "json", ["1010"],
                    "The cash and bank accounts a receipt or payment may be recorded "
                    "against. Add a second bank account's code here and it appears "
                    "in the payment form.", sort_order=50),

        # --- Security --------------------------------------------------------
        SettingSpec("security.require_2fa", "Require two-factor login", "security",
                    "bool", False, "Whether login requires a second factor. TBD "
                    "(client).", sort_order=10),
        SettingSpec("security.require_password_change_on_reset",
                    "Force change on reset", "security", "bool", True,
                    "Whether an administrator-issued password must be changed at "
                    "next sign-in. TBD (client).", sort_order=20),

        # --- Inventory -------------------------------------------------------
        SettingSpec("inventory.costing_method", "Costing method", "inventory",
                    "enum", "weighted_average", "Method used by the stock ledger.",
                    options=["weighted_average"], sort_order=10),

        # --- Sales documents -------------------------------------------------
        SettingSpec("sales.receipt_style", "Receipt style", "sales", "enum",
                    "plain", "Whether a sale produces a plain receipt or a "
                    "VAT-compliant tax invoice. TBD (client).",
                    options=["plain", "tax_invoice"], sort_order=10),
    ]


SETTING_CATALOG: list[SettingSpec] = _specs()

CATALOG_BY_KEY: dict[str, SettingSpec] = {spec.key: spec for spec in SETTING_CATALOG}

# Backwards-compatible view of the catalogue as (key, default, description).
DEFAULT_SETTINGS: list[tuple[str, object, str]] = [
    (spec.key, spec.default, spec.description) for spec in SETTING_CATALOG
]
