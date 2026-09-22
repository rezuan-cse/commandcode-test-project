/**
 * Thin API client. Money arrives as decimal strings and is never coerced to
 * float, so figures shown in the browser match the ledger exactly.
 */

import type {
  Account,
  BalanceSheet,
  BomComponent,
  BomExplosion,
  GeneralLedger,
  IntegrityReport,
  InventoryRow,
  Item,
  JournalEntry,
  LoginResponse,
  Pnl,
  ProductionPostResult,
  ProductionPreview,
  ProductionRun,
  PurchasePostResult,
  PurchasePreview,
  RoleMatrix,
  Sale,
  SalePostResult,
  SalePreview,
  SessionResponse,
  Setting,
  TotpEnableResponse,
  TotpSetupResponse,
  TrialBalance,
  UserRow,
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

  sales: () => request<Sale[]>("/sales"),

  previewSale: (payload: unknown) =>
    request<SalePreview>("/sales/preview", { method: "POST", body: JSON.stringify(payload) }),

  postSale: (payload: unknown) =>
    request<SalePostResult>("/sales", { method: "POST", body: JSON.stringify(payload) }),

  previewPurchase: (payload: unknown) =>
    request<PurchasePreview>("/purchases/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  postPurchase: (payload: unknown) =>
    request<PurchasePostResult>("/purchases", { method: "POST", body: JSON.stringify(payload) }),

  roleMatrix: () => request<RoleMatrix>("/access/matrix"),

  users: () => request<UserRow[]>("/access/users"),

  settings: () => request<Setting[]>("/settings"),

  resetDemo: () =>
    request<{ seeded: boolean; counts: Record<string, number>; message: string }>(
      "/demo/reset",
      { method: "POST" },
    ),

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
