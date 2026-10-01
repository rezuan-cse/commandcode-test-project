/**
 * The menu, and who sees which part of it.
 *
 * Every item is governed by a `resource` — the same one the server enforces — so
 * the menu only offers screens the person may actually open, and an administrator
 * can grant any of them to an individual through the per-user access editor.
 *
 * One definition, used by the sidebar and by the "Menus by role" table on Roles &
 * Access, so the two can never disagree.
 */

import type { Access } from "./types";

export interface NavItem {
  to: string;
  text: string;
  /** Resource required to see this item. Omit for anything a signed-in role may open. */
  resource?: string;
  /** Match the route exactly rather than as a prefix. */
  end?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    // The Dashboard sums up the whole business, which is what the `reports`
    // permission already covers. Store and Sales have none, so it is hidden for
    // them — and an administrator can grant it to one person if they want to.
    label: "Overview",
    items: [{ to: "/", text: "Dashboard", end: true, resource: "reports" }],
  },
  {
    label: "Ledger",
    items: [
      { to: "/accounts", text: "Chart of Accounts", resource: "accounts" },
      { to: "/journal", text: "Journal Entries", resource: "journal_entries" },
    ],
  },
  {
    label: "Operations",
    items: [
      { to: "/parties", text: "Customers & Suppliers", resource: "parties" },
      { to: "/payments", text: "Receipts & Payments", resource: "payments" },
      { to: "/inventory", text: "Inventory & BOM", resource: "items_bom" },
      { to: "/purchases", text: "Purchase Entry", resource: "sales_purchase" },
      { to: "/production", text: "Production Entry", resource: "production" },
      { to: "/sales", text: "Sales Entry", resource: "sales_purchase" },
    ],
  },
  {
    label: "Payroll",
    items: [
      { to: "/payroll/employees", text: "Employees", resource: "payroll" },
      { to: "/payroll", text: "Payroll Runs", resource: "payroll", end: true },
    ],
  },
  {
    label: "Reports",
    items: [
      { to: "/reports/pnl-comparison", text: "Period Comparison", resource: "reports" },
      { to: "/reports/trial-balance", text: "Trial Balance", resource: "reports" },
      { to: "/reports/general-ledger", text: "General Ledger", resource: "reports" },
      { to: "/reports/balance-sheet", text: "Balance Sheet", resource: "reports" },
    ],
  },
  {
    // Configuration, data and account management. The area is a permission, so it
    // can be granted; the actions inside remain administrator-only.
    label: "Administration",
    items: [
      { to: "/access", text: "Roles & Access", resource: "administration" },
      { to: "/approvals", text: "Approvals", resource: "administration" },
      { to: "/settings", text: "Configuration", resource: "administration" },
      { to: "/data", text: "Data", resource: "administration" },
    ],
  },
  {
    // Everyone keeps this, so nobody depends on an administrator to change a
    // password or set up two-factor sign-in.
    label: "My account",
    items: [{ to: "/security", text: "Security" }],
  },
];

type Can = (resource: string, write?: boolean) => boolean;

/** Whether a person with these permissions sees one menu item. */
export function itemVisible(item: NavItem, can: Can): boolean {
  return !item.resource || can(item.resource);
}

/** The menu groups and items a person sees. */
export function visibleGroups(can: Can): NavGroup[] {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => itemVisible(item, can)),
  })).filter((group) => group.items.length > 0);
}

/**
 * Where a role should land after signing in.
 *
 * The Dashboard is not open to every role, so the first menu item the person can
 * open is the safe landing place. A role that works in one screen most of the day
 * gets that screen instead of the first one in the menu.
 */
export function landingRoute(role: string, can: Can): string {
  const shown = visibleGroups(can).flatMap((group) => group.items.map((item) => item.to));
  const preferred = PREFERRED_LANDING[role];
  if (preferred && shown.includes(preferred)) return preferred;
  return shown[0] ?? "/security";
}

/** Roles whose working screen is a better landing than the first menu item. */
const PREFERRED_LANDING: Record<string, string> = {
  "Store/Production Staff": "/inventory",
  "Sales Staff": "/sales",
};

/** The menu group labels a set of permissions entitles someone to. */
export function menuLabels(access: Record<string, Access>): string[] {
  const can: Can = (resource) =>
    access[resource] === "view" || access[resource] === "full";
  return visibleGroups(can).map((group) => group.label);
}
