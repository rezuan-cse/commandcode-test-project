/**
 * Client-side view of the permission matrix.
 *
 * The server is the authority and checks every request. This exists only so the
 * interface can avoid *offering* actions that will be refused — hiding a menu
 * item, or showing a screen read-only instead of presenting a form that cannot
 * be submitted.
 *
 * The wording deliberately mirrors `denial_message` in the backend's
 * users_roles/service.py. If you change one, change both.
 */

import type { Access } from "./types";

export const RESOURCE_LABELS: Record<string, string> = {
  accounts: "Chart of Accounts",
  journal_entries: "Journal Entries",
  items_bom: "Inventory & BOM",
  production: "Production Entry",
  sales_purchase: "Purchase and Sales Entry",
  reports: "Reports",
};

/** The human name for a resource key. */
export function resourceLabel(resource: string): string {
  return RESOURCE_LABELS[resource] ?? resource;
}

/** True when the level permits reading. */
export function canRead(level: Access | undefined): boolean {
  return level === "view" || level === "full";
}

/** True when the level permits changing things. */
export function canWrite(level: Access | undefined): boolean {
  return level === "full";
}

/**
 * Explain, in the same words the server would use, why an action is refused.
 * Distinguishes "cannot see it" from "can see it but not change it", because
 * the reader should do different things in each case.
 */
export function denialMessage(
  role: string,
  resource: string,
  level: Access | undefined,
  write: boolean,
): string {
  const label = resourceLabel(resource);
  if (!canRead(level)) {
    return (
      `The ${label} screen is not available to the ${role} role. ` +
      `An administrator can grant access if it is needed.`
    );
  }
  if (write && !canWrite(level)) {
    return (
      `The ${role} role can view the ${label} screen but cannot make changes ` +
      `on it.`
    );
  }
  return `The ${role} role does not have access to ${label}.`;
}
