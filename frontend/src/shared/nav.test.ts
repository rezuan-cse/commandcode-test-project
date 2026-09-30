/**
 * Who sees which menu.
 *
 * The rules mirror the server's permission matrix (users_roles/service.py) for
 * the resource-based groups, and add the two role-based ones: the Dashboard and
 * the Administration group.
 */

import { describe, expect, it } from "vitest";

import { landingRoute, menuLabelsForRole, visibleGroups } from "./nav";
import type { Access } from "./types";

const MATRIX: Record<string, Record<string, Access>> = {
  Admin: {
    accounts: "full", journal_entries: "full", items_bom: "full",
    production: "full", sales_purchase: "full", payroll: "full", reports: "full",
  },
  Accountant: {
    accounts: "view", journal_entries: "full", items_bom: "view",
    production: "view", sales_purchase: "view", payroll: "full", reports: "full",
  },
  "Store/Production Staff": {
    accounts: "none", journal_entries: "none", items_bom: "full",
    production: "full", sales_purchase: "none", payroll: "none", reports: "none",
  },
  "Sales Staff": {
    accounts: "none", journal_entries: "none", items_bom: "view",
    production: "none", sales_purchase: "full", payroll: "none", reports: "none",
  },
  "Owner/Viewer": {
    accounts: "view", journal_entries: "view", items_bom: "view",
    production: "view", sales_purchase: "view", payroll: "view", reports: "full",
  },
};

const can = (role: string) => (resource: string) =>
  MATRIX[role][resource] === "view" || MATRIX[role][resource] === "full";

const labels = (role: string) => menuLabelsForRole(role, MATRIX[role]);

describe("Menu visibility", () => {
  it("offers the Dashboard only to the finance roles", () => {
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

  it("drops the Ledger from the roles that cannot read it", () => {
    expect(labels("Store/Production Staff")).not.toContain("Ledger");
    expect(labels("Sales Staff")).not.toContain("Ledger");
    expect(labels("Accountant")).toContain("Ledger");
  });

  it("keeps the financial reports away from the shop-floor roles", () => {
    expect(labels("Store/Production Staff")).not.toContain("Reports");
    expect(labels("Sales Staff")).not.toContain("Reports");
    expect(labels("Accountant")).toContain("Reports");
    expect(labels("Owner/Viewer")).toContain("Reports");
  });

  it("shows Store and Sales only the work they do", () => {
    expect(labels("Store/Production Staff")).toEqual([
      "Operations",
      "My account",
    ]);
    expect(labels("Sales Staff")).toEqual(["Operations", "My account"]);
  });
});

describe("Landing page", () => {
  it("sends a role that cannot see the Dashboard somewhere it can open", () => {
    for (const role of ["Store/Production Staff", "Sales Staff"]) {
      const route = landingRoute(role, can(role));
      expect(route).not.toBe("/");
      const shown = visibleGroups(role, can(role)).flatMap((g) => g.items.map((i) => i.to));
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
