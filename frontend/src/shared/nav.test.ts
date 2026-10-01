/**
 * Who sees which menu.
 *
 * These mirror the server's permission matrix (users_roles/service.py). Every
 * menu group is governed by one of its resources, so an administrator can grant
 * any of them to an individual on top of their role.
 */

import { describe, expect, it } from "vitest";

import { landingRoute, menuLabels, visibleGroups } from "./nav";
import type { Access } from "./types";

const NONE: Record<string, Access> = {
  accounts: "none", journal_entries: "none", items_bom: "none",
  production: "none", sales_purchase: "none", payroll: "none",
  reports: "none", administration: "none",
};

const MATRIX: Record<string, Record<string, Access>> = {
  Admin: { ...NONE, accounts: "full", journal_entries: "full", items_bom: "full",
           production: "full", sales_purchase: "full", payroll: "full",
           reports: "full", administration: "full" },
  Accountant: { ...NONE, accounts: "view", journal_entries: "full", items_bom: "view",
                production: "view", sales_purchase: "view", payroll: "full",
                reports: "full" },
  "Store/Production Staff": { ...NONE, items_bom: "full", production: "full" },
  "Sales Staff": { ...NONE, items_bom: "view", sales_purchase: "full" },
  "Owner/Viewer": { ...NONE, accounts: "view", journal_entries: "view",
                    items_bom: "view", production: "view", sales_purchase: "view",
                    payroll: "view", reports: "full", administration: "view" },
};

const can = (role: string) => (resource: string) =>
  MATRIX[role][resource] === "view" || MATRIX[role][resource] === "full";

const labels = (role: string) => menuLabels(MATRIX[role]);

describe("Menu visibility", () => {
  it("offers the Dashboard only where reports are readable", () => {
    expect(labels("Admin")).toContain("Overview");
    expect(labels("Accountant")).toContain("Overview");
    expect(labels("Owner/Viewer")).toContain("Overview");
    expect(labels("Store/Production Staff")).not.toContain("Overview");
    expect(labels("Sales Staff")).not.toContain("Overview");
  });

  it("offers Administration only to Admin and Owner", () => {
    expect(labels("Admin")).toContain("Administration");
    expect(labels("Owner/Viewer")).toContain("Administration");
    expect(labels("Accountant")).not.toContain("Administration");
    expect(labels("Store/Production Staff")).not.toContain("Administration");
    expect(labels("Sales Staff")).not.toContain("Administration");
  });

  it("offers Payroll to Admin, Accountant and Owner only", () => {
    expect(labels("Admin")).toContain("Payroll");
    expect(labels("Accountant")).toContain("Payroll");
    expect(labels("Owner/Viewer")).toContain("Payroll");
    expect(labels("Store/Production Staff")).not.toContain("Payroll");
    expect(labels("Sales Staff")).not.toContain("Payroll");
  });

  it("offers My account to everybody, so passwords stay self-service", () => {
    for (const role of Object.keys(MATRIX)) {
      expect(labels(role)).toContain("My account");
    }
  });

  it("keeps the ledger and the reports away from the shop-floor roles", () => {
    for (const role of ["Store/Production Staff", "Sales Staff"]) {
      expect(labels(role)).not.toContain("Ledger");
      expect(labels(role)).not.toContain("Reports");
    }
  });

  it("shows Store and Sales only the work they do", () => {
    expect(labels("Store/Production Staff")).toEqual(["Operations", "My account"]);
    expect(labels("Sales Staff")).toEqual(["Operations", "My account"]);
  });

  it("opens a menu for one person when they are granted its area", () => {
    // A grant is what the per-user access editor writes: the role is unchanged,
    // the permission is not.
    const granted = { ...MATRIX["Store/Production Staff"], reports: "view" as Access };
    expect(menuLabels(granted)).toContain("Overview");
    expect(menuLabels(granted)).toContain("Reports");
  });

  it("closes a menu item for one person when their area is denied", () => {
    // Store staff keep Production Entry, but lose the inventory screens.
    const denied: Record<string, Access> = {
      ...MATRIX["Store/Production Staff"],
      items_bom: "none",
    };
    const items = visibleGroups(
      (resource) => denied[resource] === "view" || denied[resource] === "full",
    ).flatMap((group) => group.items.map((item) => item.text));

    expect(items).not.toContain("Inventory & BOM");
    expect(items).toContain("Production Entry");
  });
});

describe("Landing page", () => {
  it("sends a role that cannot see the Dashboard somewhere it can open", () => {
    for (const role of ["Store/Production Staff", "Sales Staff"]) {
      const route = landingRoute(role, can(role));
      expect(route).not.toBe("/");
      const shown = visibleGroups(can(role)).flatMap((g) => g.items.map((i) => i.to));
      expect(shown).toContain(route);
    }
  });

  it("sends each role to its own working screen", () => {
    expect(landingRoute("Store/Production Staff", can("Store/Production Staff"))).toBe("/inventory");
    expect(landingRoute("Sales Staff", can("Sales Staff"))).toBe("/sales");
  });

  it("still lands the finance roles on the Dashboard", () => {
    for (const role of ["Admin", "Accountant", "Owner/Viewer"]) {
      expect(landingRoute(role, can(role))).toBe("/");
    }
  });
});
