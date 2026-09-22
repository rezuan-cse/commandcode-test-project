/** TypeScript mirrors of the backend Pydantic schemas. */

export type AccountType =
  | "Asset"
  | "Liability"
  | "Equity"
  | "Revenue"
  | "COGS"
  | "Expense"
  | "Other Income";

export type Segment =
  | "Import"
  | "Manufacturing"
  | "Packaging"
  | "Trading"
  | "Application"
  | "Shared";

export type Access = "none" | "view" | "full";

export interface Account {
  code: string;
  name_en: string;
  name_bn: string | null;
  account_type: AccountType;
  segment: Segment;
  normal_balance: "Dr" | "Cr";
  is_active: boolean;
}

export interface AccountBalance {
  account_code: string;
  account_name: string;
  account_type: AccountType;
  segment: Segment;
  opening_debit: string;
  opening_credit: string;
  period_debit: string;
  period_credit: string;
  closing_debit: string;
  closing_credit: string;
}

export interface GeneralLedger {
  date_from: string;
  date_to: string;
  accounts: AccountBalance[];
  total_period_debit: string;
  total_period_credit: string;
}

export interface TrialBalanceRow {
  account_code: string;
  account_name: string;
  account_type: AccountType;
  segment: Segment;
  debit: string;
  credit: string;
}

export interface TrialBalance {
  as_of: string;
  rows: TrialBalanceRow[];
  total_debit: string;
  total_credit: string;
  difference: string;
  balanced: boolean;
}

export interface SegmentPnlRow {
  segment: string;
  revenue: string;
  cogs: string;
  gross_profit: string;
  gross_margin_pct: string;
}

export interface Pnl {
  date_from: string;
  date_to: string;
  segments: SegmentPnlRow[];
  total_revenue: string;
  total_cogs: string;
  total_gross_profit: string;
  gross_margin_pct: string;
  operating_expenses: string;
  other_income: string;
  net_profit: string;
}

export interface BalanceSheet {
  as_of: string;
  assets: TrialBalanceRow[];
  liabilities: TrialBalanceRow[];
  equity_accounts: TrialBalanceRow[];
  total_assets: string;
  total_liabilities: string;
  equity_per_gl: string;
  current_period_profit: string;
  total_equity: string;
  total_liabilities_and_equity: string;
  check: string;
  is_balanced: boolean;
}

export interface IntegrityCheck {
  name: string;
  passed: boolean;
  detail: string;
  value: string | null;
}

export interface IntegrityReport {
  checks: IntegrityCheck[];
  all_passed: boolean;
}

export interface Item {
  code: string;
  name: string;
  category: string;
  segment: Segment;
  uom: string;
  qty_on_hand: string;
  avg_cost: string;
  value_on_hand: string;
}

export interface BomComponent {
  parent_code: string;
  component_code: string;
  component_name: string;
  qty_per_unit: string;
  stage: number;
  uom: string;
}

export interface BomExplosionLine {
  item_code: string;
  item_name: string;
  category: string;
  uom: string;
  qty_per_unit: string;
  qty_required: string;
  avg_cost: string;
  est_cost: string;
  level: number;
}

export interface BomExplosion {
  parent_code: string;
  parent_name: string;
  qty: string;
  lines: BomExplosionLine[];
  total_estimated_cost: string;
}

export interface InventoryRow {
  id: number;
  movement_date: string;
  item_code: string;
  movement_type: string;
  reference: string | null;
  in_qty: string;
  in_value: string;
  out_qty: string;
  out_value: string;
  balance_qty: string;
  balance_value: string;
  avg_cost: string;
}

export interface JournalLinePreview {
  account_code: string;
  account_name: string;
  segment: string;
  debit: string;
  credit: string;
  narration: string | null;
}

export interface SuggestedComponent {
  component_code: string;
  component_name: string;
  uom: string;
  qty_per_unit: string;
  qty_consumed: string;
  unit_cost: string;
  line_cost: string;
  on_hand: string;
  sufficient: boolean;
}

export interface ProductionPreview {
  output_item_code: string;
  output_item_name: string;
  qty_produced: string;
  components: SuggestedComponent[];
  material_cost: string;
  labor_cost: string;
  overhead_cost: string;
  total_cost: string;
  unit_cost: string;
  journal_lines: JournalLinePreview[];
  balanced: boolean;
  can_post: boolean;
  warnings: string[];
}

export interface ProductionRun {
  id: number;
  order_no: string;
  production_date: string;
  output_item_code: string;
  qty_produced: string;
  material_cost: string;
  labor_cost: string;
  overhead_cost: string;
  total_cost: string;
  unit_cost: string;
  journal_entry_id: number | null;
  posted_by: string;
}

export interface ProductionPostResult {
  order: ProductionRun;
  preview: ProductionPreview;
  message: string;
}

export interface SaleLinePreview {
  item_code: string;
  item_name: string;
  qty: string;
  sale_price: string;
  unit_cost: string;
  line_revenue: string;
  line_cogs: string;
  line_margin: string;
  on_hand: string;
  sufficient: boolean;
  below_cost: boolean;
}

export interface SalePreview {
  customer: string;
  lines: SaleLinePreview[];
  revenue: string;
  cogs: string;
  gross_profit: string;
  gross_margin_pct: string;
  journal_lines: JournalLinePreview[];
  balanced: boolean;
  can_post: boolean;
  warnings: string[];
}

export interface Sale {
  id: number;
  order_no: string;
  sale_date: string;
  customer: string;
  revenue: string;
  cogs: string;
  journal_entry_id: number | null;
  posted_by: string;
}

export interface SalePostResult {
  order: Sale;
  preview: SalePreview;
  message: string;
}

/** One line of a posted sale, as printed on the receipt. */
export interface SaleLine {
  item_code: string;
  qty: string;
  sale_price: string;
  line_revenue: string;
}

/** A posted sale with its lines. */
export interface SaleDetail extends Sale {
  lines: SaleLine[];
}

export interface JournalLine {
  account_code: string;
  segment: Segment;
  debit: string;
  credit: string;
  narration: string | null;
}

export interface PurchaseLinePreview {
  item_code: string;
  item_name: string;
  qty: string;
  unit_cost: string;
  line_value: string;
  on_hand_before: string;
  avg_cost_before: string;
  avg_cost_after: string;
}

export interface PurchasePreview {
  supplier: string;
  lines: PurchaseLinePreview[];
  total_value: string;
  journal_lines: JournalLinePreview[];
  balanced: boolean;
  can_post: boolean;
  warnings: string[];
}

export interface Purchase {
  id: number;
  order_no: string;
  purchase_date: string;
  supplier: string;
  total_value: string;
  journal_entry_id: number | null;
  posted_by: string;
}

export interface PurchasePostResult {
  order: Purchase;
  preview: PurchasePreview;
  message: string;
}

export interface JournalEntry {
  id: number;
  voucher_no: string;
  entry_date: string;
  narration: string | null;
  source: string;
  reference: string | null;
  posted_by: string;
  posted_at: string;
  lines: JournalLine[];
}

export interface RoleAccessRow {
  role: string;
  access: Record<string, Access>;
}

export interface RoleMatrix {
  resources: string[];
  roles: RoleAccessRow[];
}

export interface UserRow {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_2fa_enabled: boolean;
  last_login_at: string | null;
  /** Access level per resource: "none", "view" or "full". */
  permissions: Record<string, Access>;
}

/** Step one of sign-in. Either a session, or a request for the second factor. */
export interface LoginResponse {
  needs_2fa: boolean;
  challenge_token: string | null;
  access_token: string | null;
  expires_in_minutes: number | null;
  user: UserRow | null;
}

export interface SessionResponse {
  access_token: string;
  expires_in_minutes: number;
  user: UserRow;
}

export interface TotpSetupResponse {
  secret: string;
  otpauth_uri: string;
  qr_png_data_uri: string;
}

export interface TotpEnableResponse {
  recovery_codes: string[];
  message: string;
}

export interface Setting {
  key: string;
  value: string;
  description: string | null;
  confirmed_by_client: boolean;
}
