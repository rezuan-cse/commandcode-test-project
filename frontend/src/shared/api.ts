/**
 * Thin API client. Money arrives as decimal strings and is never coerced to
 * float, so figures shown in the browser match the ledger exactly.
 */

import type {
  Account,
  ApprovalRequest,
  AuditEntry,
  BalanceSheet,
  BomComponent,
  BomExplosion,
  DataResult,
  Employee,
  GeneralLedger,
  IntegrityReport,
  InventoryRow,
  Item,
  JournalEntry,
  LoginResponse,
  PayrollDetail,
  PayrollPostResult,
  PayrollPreview,
  PayrollRun,
  Pnl,
  ProductionPostResult,
  ProductionPreview,
  ProductionRun,
  PurchasePostResult,
  PurchasePreview,
  Purchase,
  RoleMatrix,
  Sale,
  SaleDetail,
  SalePostResult,
  SalePreview,
  SessionResponse,
  Setting,
  TotpEnableResponse,
  TotpSetupResponse,
  TrialBalance,
  UserCreated,
  UserPermissions,
  UserRow,
  VatSummary,
} from "./types";

// When the interface and the API are served from the same origin, "/api" is
// correct. When the interface is hosted separately (for example on Vercel or
// Netlify) with the API elsewhere, set VITE_API_BASE to the API's full URL.
const BASE = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/$/, "");

const TOKEN_KEY = "rpci.session";

// Kept in local storage so a refresh does not sign the user out. That is
// readable by any script on the page, so it is the weaker of the two options
// against cross-site scripting; httpOnly cookies would need CSRF handling and
// credential-bearing CORS, which this demo deliberately avoids.
let accessToken: string | null = localStorage.getItem(TOKEN_KEY);

/** Called when the server rejects our token, so the app can return to sign-in. */
let onUnauthorized: (() => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getAccessToken(): string | null {
  return accessToken;
}

/** Register the handler invoked when the session is no longer valid. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

/**
 * @param handleUnauthorized run the session-expired handler on 401. Sign-in
 *   calls pass false: a wrong password is a 401 too, and it must not be treated
 *   as an expired session.
 */
async function request<T>(
  path: string,
  init?: RequestInit,
  handleUnauthorized = true,
): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 401 && handleUnauthorized) {
    // The token is gone, expired, or the account was disabled. Drop it so the
    // app cannot keep retrying with a credential the server will never accept.
    setAccessToken(null);
    onUnauthorized?.();
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      // keep the status text
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  accounts: (params?: { segment?: string; account_type?: string; search?: string }) => {
    const query = new URLSearchParams();
    if (params?.segment) query.set("segment", params.segment);
    if (params?.account_type) query.set("account_type", params.account_type);
    if (params?.search) query.set("search", params.search);
    const suffix = query.toString() ? `?${query}` : "";
    return request<Account[]>(`/accounts${suffix}`);
  },

  generalLedger: (dateFrom: string, dateTo: string) =>
    request<GeneralLedger>(
      `/reports/general-ledger?date_from=${dateFrom}&date_to=${dateTo}`,
    ),

  trialBalance: (asOf: string) => request<TrialBalance>(`/reports/trial-balance?as_of=${asOf}`),

  pnl: (dateFrom: string, dateTo: string) =>
    request<Pnl>(`/reports/pnl?date_from=${dateFrom}&date_to=${dateTo}`),

  balanceSheet: (asOf: string) => request<BalanceSheet>(`/reports/balance-sheet?as_of=${asOf}`),

  integrity: (asOf: string) => request<IntegrityReport>(`/reports/integrity?as_of=${asOf}`),

  items: (search?: string) =>
    request<Item[]>(`/items${search ? `?search=${encodeURIComponent(search)}` : ""}`),

  createItem: (payload: unknown) =>
    request<Item>("/items", { method: "POST", body: JSON.stringify(payload) }),

  updateItem: (code: string, payload: unknown) =>
    request<Item>(`/items/${encodeURIComponent(code)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteItem: (code: string) =>
    request<{ message: string }>(`/items/${encodeURIComponent(code)}`, {
      method: "DELETE",
    }),

  bom: (code: string) => request<BomComponent[]>(`/items/${code}/bom`),

  explode: (code: string, qty: string) =>
    request<BomExplosion>(`/items/${code}/explode?qty=${encodeURIComponent(qty)}`),

  inventory: (itemCode?: string) =>
    request<InventoryRow[]>(`/inventory${itemCode ? `?item_code=${itemCode}` : ""}`),

  journalEntries: () => request<JournalEntry[]>("/journal-entries"),

  productionRuns: () => request<ProductionRun[]>("/production"),

  previewProduction: (payload: unknown) =>
    request<ProductionPreview>("/production/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  postProduction: (payload: unknown) =>
    request<ProductionPostResult>("/production", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  reverseProduction: (id: number, reason: string) =>
    request<ProductionRun>(`/production/${id}/reverse`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  sales: () => request<Sale[]>("/sales"),

  sale: (id: number | string) => request<SaleDetail>(`/sales/${id}`),

  previewSale: (payload: unknown) =>
    request<SalePreview>("/sales/preview", { method: "POST", body: JSON.stringify(payload) }),

  postSale: (payload: unknown) =>
    request<SalePostResult>("/sales", { method: "POST", body: JSON.stringify(payload) }),

  reverseSale: (id: number, reason: string) =>
    request<SaleDetail>(`/sales/${id}/reverse`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  previewPurchase: (payload: unknown) =>
    request<PurchasePreview>("/purchases/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  purchases: () => request<Purchase[]>("/purchases"),

  postPurchase: (payload: unknown) =>
    request<PurchasePostResult>("/purchases", { method: "POST", body: JSON.stringify(payload) }),

  reversePurchase: (id: number, reason: string) =>
    request<Purchase>(`/purchases/${id}/reverse`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  roleMatrix: () => request<RoleMatrix>("/access/matrix"),

  // --- Payroll (Admin and Accountant) ------------------------------------

  employees: () => request<Employee[]>("/payroll/employees"),

  createEmployee: (payload: Partial<Employee>) =>
    request<Employee>("/payroll/employees", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateEmployee: (code: string, payload: Partial<Employee>) =>
    request<Employee>(`/payroll/employees/${encodeURIComponent(code)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  payrollRuns: () => request<PayrollRun[]>("/payroll/runs"),

  payrollRun: (id: number | string) => request<PayrollDetail>(`/payroll/runs/${id}`),

  previewPayroll: (payload: unknown) =>
    request<PayrollPreview>("/payroll/runs/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  postPayroll: (payload: unknown) =>
    request<PayrollPostResult>("/payroll/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  reversePayroll: (id: number, reason: string) =>
    request<PayrollRun>(`/payroll/runs/${id}/reverse`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  vatSummary: (dateFrom: string, dateTo: string) =>
    request<VatSummary>(
      `/vat/summary?date_from=${dateFrom}&date_to=${dateTo}`,
    ),

  // --- Approvals ---------------------------------------------------------

  approvals: () => request<ApprovalRequest[]>("/approvals"),

  approveApproval: (id: number, note?: string) =>
    request<ApprovalRequest>(`/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),

  rejectApproval: (id: number, note?: string) =>
    request<ApprovalRequest>(`/approvals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),

  // --- Data administration (Admin only) ----------------------------------

  /**
   * Import a workbook. Uses a multipart body, so it cannot go through the JSON
   * `request` helper — the browser must set the multipart boundary itself.
   */
  importData: async (file: File, replace = true): Promise<DataResult> => {
    const body = new FormData();
    body.append("file", file);
    body.append("replace", String(replace));

    const response = await fetch(`${BASE}/data/import`, {
      method: "POST",
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
      body,
    });

    if (response.status === 401) {
      setAccessToken(null);
      onUnauthorized?.();
    }
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const parsed = await response.json();
        if (parsed?.detail) detail = typeof parsed.detail === "string" ? parsed.detail : detail;
      } catch {
        // keep the status text
      }
      throw new Error(detail);
    }
    return (await response.json()) as DataResult;
  },

  resetData: (mode?: "fresh" | "workbook" | "none") =>
    request<DataResult>(`/data/reset${mode ? `?mode=${mode}` : ""}`, {
      method: "POST",
    }),

  users: () => request<UserRow[]>("/access/users"),

  createUser: (payload: { email: string; full_name: string; role: string; password?: string }) =>
    request<UserCreated>("/access/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateUser: (userId: number, payload: { email?: string; full_name?: string; role?: string }) =>
    request<UserRow>(`/access/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteUser: (userId: number) =>
    request<{ message: string }>(`/access/users/${userId}`, { method: "DELETE" }),

  userPermissions: (userId: number) =>
    request<UserPermissions>(`/access/users/${userId}/permissions`),

  setUserPermissions: (userId: number, access: Record<string, string>) =>
    request<{ message: string }>(`/access/users/${userId}/permissions`, {
      method: "PUT",
      body: JSON.stringify({ access }),
    }),

  // --- Account administration (Admin only) ------------------------------

  resetTwoFactor: (userId: number) =>
    request<{ message: string }>(`/access/users/${userId}/reset-two-factor`, {
      method: "POST",
    }),

  resetUserPassword: (userId: number, newPassword?: string) =>
    request<{ password: string; message: string }>(
      `/access/users/${userId}/reset-password`,
      {
        method: "POST",
        body: JSON.stringify({ new_password: newPassword || null }),
      },
    ),

  setUserActive: (userId: number, isActive: boolean) =>
    request<{ message: string }>(`/access/users/${userId}/active`, {
      method: "POST",
      body: JSON.stringify({ is_active: isActive }),
    }),

  auditLog: () => request<AuditEntry[]>("/access/audit"),

  settings: () => request<Setting[]>("/settings"),

  updateSetting: (key: string, value: string, confirmed?: boolean) =>
    request<Setting>(`/settings/${encodeURIComponent(key)}`, {
      method: "PATCH",
      body: JSON.stringify({ value, confirmed_by_client: confirmed ?? null }),
    }),

  // --- Authentication ---------------------------------------------------

  login: (email: string, password: string) =>
    request<LoginResponse>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false,
    ),

  loginWithTotp: (challengeToken: string, code: string) =>
    request<SessionResponse>(
      "/auth/login/totp",
      {
        method: "POST",
        body: JSON.stringify({ challenge_token: challengeToken, code }),
      },
      false,
    ),

  me: () => request<UserRow>("/auth/me"),

  setupTwoFactor: () =>
    request<TotpSetupResponse>("/auth/2fa/setup", { method: "POST" }),

  enableTwoFactor: (code: string) =>
    request<TotpEnableResponse>("/auth/2fa/enable", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  disableTwoFactor: (password: string) =>
    request<{ message: string }>("/auth/2fa/disable", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),

  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ message: string }>("/auth/password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }),
};
