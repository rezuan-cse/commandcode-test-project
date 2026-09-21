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
  Setting,
  TrialBalance,
  UserRow,
} from "./types";

// When the interface and the API are served from the same origin, "/api" is
// correct. When the interface is hosted separately (for example on Vercel or
// Netlify) with the API elsewhere, set VITE_API_BASE to the API's full URL.
const BASE = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/$/, "");

let actingRole = "Admin";

/** Set the role sent on every subsequent request, for RBAC demonstration. */
export function setActingRole(role: string): void {
  actingRole = role;
}

/** The role currently being impersonated. */
export function getActingRole(): string {
  return actingRole;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Demo-Role": actingRole,
      ...(init?.headers ?? {}),
    },
  });
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
};
