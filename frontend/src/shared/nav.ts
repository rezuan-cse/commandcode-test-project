/**
 * The menu, and who sees which part of it.
 *
 * One definition, used by the sidebar and by the "Menus by role" table on Roles
 * & Access, so the two can never disagree. Two kinds of rule apply to an item:
 *
 *  - `resource` — the same resource the server enforces, so the menu only offers
 *    screens the role may read.
 *  - `roles` — for items that are not governed by a resource (the Dashboard and
 *    the Administration group). The server is still the boundary for what those
 *    screens can actually do; this only decides who is offered them.
 */

import type { Access } from "./types";

export interface NavItem {
  to: string;
  text: string;
  /** Resource required to see this item. Omit for anything signed-in roles may open. */
  resource?: string;
  /** Roles allowed to see this item, when it is not governed by a resource. */
  roles?: string[];
  /** Match the route exactly rather than as a prefix. */
  end?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

/** The Dashboard summarises the financials, so it is limited to the finance roles. */
export const OVERVIEW_ROLES = ["Admin", "Owner/Viewer", "Accountant"];

/** Configuration, data and user administration: the manager and the owner. */
export const ADMINISTRATION_ROLES = ["Admin", "Owner/Viewer"];

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { to: "/", text: "Dashboard", end: true, roles: OVERVIEW_ROLES },
    ],
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
      { to: "/reports/trial-balance", text: "Trial Balance", resource: "reports" },
      { to: "/reports/general-ledger", text: "General Ledger", resource: "reports" },
      { to: "/reports/balance-sheet", text: "Balance Sheet", resource: "reports" },
    ],
  },
  {
    label: "Administration",
    items: [
      { to: "/access", text: "Roles & Access", roles: ADMINISTRATION_ROLES },
      { to: "/approvals", text: "Approvals", roles: ADMINISTRATION_ROLES },
      { to: "/settings", text: "Configuration", roles: ADMINISTRATION_ROLES },
      { to: "/data", text: "Data", roles: ADMINISTRATION_ROLES },
    ],
  },
  {
    label: "My account",
    items: [{ to: "/security", text: "Security" }],
  },
];

/** Whether one role sees one menu item. */
export function itemVisible(
  item: NavItem,
  role: string,
  can: (resource: string, write?: boolean) => boolean,
): boolean {
  if (item.roles && !item.roles.includes(role)) return false;
  if (item.resource && !can(item.resource)) return false;
  return true;
}

/** The menu groups and items a role sees. */
export function visibleGroups(
  role: string,
  can: (resource: string, write?: boolean) => boolean,
): NavGroup[] {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => itemVisible(item, role, can)),
  })).filter((group) => group.items.length > 0);
}

/**
 * Where a role should land after signing in.
 *
 * The Dashboard is no longer open to everyone, so the first menu item the role
 * can actually open is the safe landing place. Every role has "My account", so
 * there is always somewhere to go.
 */
export function landingRoute(
  role: string,
  can: (resource: string, write?: boolean) => boolean,
): string {
  for (const group of visibleGroups(role, can)) {
    for (const item of group.items) return item.to;
  }
  return "/security";
}

/** The menu group labels a role sees, from a permission map. */
export function menuLabelsForRole(
  role: string,
  access: Record<string, Access>,
): string[] {
  const can = (resource: string) => access[resource] === "view" || access[resource] === "full";
  return visibleGroups(role, can).map((group) => group.label);
}
